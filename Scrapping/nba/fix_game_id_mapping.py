"""
Repara espn.game_id_mapping usando sólo datos internos de la DB.

Problema: 477 juegos en espn.games no tienen NBA ID en game_id_mapping.

Estrategia (sin APIs externas):
  1. Carga nba_player_boxscores → por cada NBA game_id, obtiene los dos tricódigos de equipo
  2. Del game_id NBA infiere el tipo de temporada (002230x = regular 2023-24, 004230x = playoffs, etc.)
  3. Para cada ESPN game sin mapping (fecha, home_tc, away_tc):
     - Determina el prefijo de temporada según la fecha
     - Filtra los NBA game_ids con el mismo par de equipos en la misma temporada
     - Si hay un único candidato → match directo
     - Si hay varios (el mismo par juega 2-4 veces en regular / hasta 7 en playoffs) →
       ordena los ESPN games por fecha y los NBA game_ids por número de secuencia
       y los empareja en el mismo orden cronológico

El NBA game_id tiene formato: {2 digits league}{1 digit season_type}{2 digits year}{5 digits sequence}
  Ejemplo: 0022300001
    - 00 = NBA
    - 2  = regular season (1=pre, 4=playoffs)
    - 23 = temporada 2023-24
    - 00001 = juego #1 de la temporada

Uso:
    python fix_game_id_mapping.py               # analiza y repara
    python fix_game_id_mapping.py --dry-run     # solo muestra matches, no inserta
    python fix_game_id_mapping.py --audit-only  # solo estadísticas
"""

import sys
import argparse
from pathlib import Path
from datetime import date
from collections import defaultdict

import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config


# ---------------------------------------------------------------------------
# Rangos de temporada → prefijo de NBA game_id
# ---------------------------------------------------------------------------
# El prefijo de un game_id NBA indica: tipo + año
#   Regular 2023-24 → "002230"
#   Playoffs 2023-24 → "004230"
#   Regular 2024-25 → "002240"
#   Playoffs 2024-25 → "004240"
#   Regular 2025-26 → "002250"
SEASON_DATE_RANGES = [
    # (start_date, end_date, nba_id_prefix)
    (date(2023, 10, 24), date(2024, 4, 14), "002230"),
    (date(2024, 4, 15),  date(2024, 6, 17), "004230"),
    (date(2024, 10, 22), date(2025, 4, 13), "002240"),
    (date(2025, 4, 14),  date(2025, 6, 22), "004240"),
    (date(2025, 10, 22), date(2026, 6, 30), "002250"),
]


def get_nba_prefix(game_date) -> str | None:
    """Devuelve el prefijo NBA game_id correspondiente a una fecha."""
    if isinstance(game_date, str):
        game_date = date.fromisoformat(game_date)
    elif hasattr(game_date, "date"):
        game_date = game_date.date()
    for start, end, prefix in SEASON_DATE_RANGES:
        if start <= game_date <= end:
            return prefix
    return None


# ---------------------------------------------------------------------------
# Mapa de nombres ESPN → tricódigos NBA
# ---------------------------------------------------------------------------
ESPN_NAME_TO_TRICODE = {
    "Atlanta Hawks":            "ATL",
    "Boston Celtics":           "BOS",
    "Brooklyn Nets":            "BKN",
    "Charlotte Hornets":        "CHA",
    "Chicago Bulls":            "CHI",
    "Cleveland Cavaliers":      "CLE",
    "Dallas Mavericks":         "DAL",
    "Denver Nuggets":           "DEN",
    "Detroit Pistons":          "DET",
    "Golden State Warriors":    "GSW",
    "Houston Rockets":          "HOU",
    "Indiana Pacers":           "IND",
    "LA Clippers":              "LAC",
    "Los Angeles Clippers":     "LAC",
    "Los Angeles Lakers":       "LAL",
    "Memphis Grizzlies":        "MEM",
    "Miami Heat":               "MIA",
    "Milwaukee Bucks":          "MIL",
    "Minnesota Timberwolves":   "MIN",
    "New Orleans Pelicans":     "NOP",
    "New York Knicks":          "NYK",
    "Oklahoma City Thunder":    "OKC",
    "Orlando Magic":            "ORL",
    "Philadelphia 76ers":       "PHI",
    "Phoenix Suns":             "PHX",
    "Portland Trail Blazers":   "POR",
    "Sacramento Kings":         "SAC",
    "San Antonio Spurs":        "SAS",
    "Toronto Raptors":          "TOR",
    "Utah Jazz":                "UTA",
    "Washington Wizards":       "WAS",
}


def name_to_tricode(name: str) -> str | None:
    if not name:
        return None
    tc = ESPN_NAME_TO_TRICODE.get(name.strip())
    if tc:
        return tc
    name_upper = name.upper()
    for full, code in ESPN_NAME_TO_TRICODE.items():
        if full.upper() in name_upper or name_upper in full.upper():
            return code
    return None


# ---------------------------------------------------------------------------
# Carga de datos desde DB
# ---------------------------------------------------------------------------

def load_unmapped_espn_games(engine, espn_schema: str) -> pd.DataFrame:
    """ESPN games jugados sin mapping, con tricódigos normalizados."""
    df = pd.read_sql(text(f"""
        SELECT g.game_id::text AS espn_id,
               g.fecha::date   AS fecha,
               g.home_team,
               g.away_team
        FROM {espn_schema}.games g
        LEFT JOIN {espn_schema}.game_id_mapping m ON g.game_id::text = m.espn_id
        WHERE m.espn_id IS NULL
          AND g.home_score > 0
        ORDER BY g.fecha
    """), engine)
    df["home_tc"]   = df["home_team"].apply(name_to_tricode)
    df["away_tc"]   = df["away_team"].apply(name_to_tricode)
    df["prefix"]    = df["fecha"].apply(get_nba_prefix)
    logger.info(f"ESPN games sin mapping: {len(df)}")
    missing_tc = df["home_tc"].isna().sum() + df["away_tc"].isna().sum()
    if missing_tc > 0:
        logger.warning(f"  {missing_tc} valores de tricode sin resolver:")
        unk = df[df["home_tc"].isna() | df["away_tc"].isna()][["espn_id", "home_team", "away_team"]].head(5)
        logger.warning(f"\n{unk.to_string()}")
    return df


def load_nba_boxscore_index(engine, espn_schema: str) -> pd.DataFrame:
    """
    Construye índice: por cada NBA game_id, obtiene los dos tricódigos de equipo.
    Solo incluye game_ids que NO están ya en game_id_mapping.
    """
    logger.info("Cargando índice desde nba_player_boxscores...")
    df = pd.read_sql(text(f"""
        SELECT b.game_id::text AS nba_id,
               array_agg(DISTINCT b.team_tricode ORDER BY b.team_tricode) AS tricodes
        FROM {espn_schema}.nba_player_boxscores b
        WHERE NOT EXISTS (
            SELECT 1 FROM {espn_schema}.game_id_mapping m
            WHERE m.nba_id::text = b.game_id::text
        )
        GROUP BY b.game_id
    """), engine)

    if df.empty:
        logger.warning("No hay NBA game_ids sin mapping en boxscores.")
        return pd.DataFrame()

    df["tc1"] = df["tricodes"].apply(lambda x: x[0] if x and len(x) >= 1 else None)
    df["tc2"] = df["tricodes"].apply(lambda x: x[1] if x and len(x) >= 2 else None)
    df["team_key"] = df.apply(
        lambda r: frozenset([r["tc1"], r["tc2"]]) if r["tc1"] and r["tc2"] else None,
        axis=1,
    )
    # Inferir prefijo desde el game_id
    df["prefix"] = df["nba_id"].str[:6]
    df = df.dropna(subset=["team_key"])
    logger.info(f"NBA game_ids sin mapping en boxscores: {len(df)}")
    return df


def load_existing_mapping(engine, espn_schema: str) -> pd.DataFrame:
    return pd.read_sql(
        text(f"SELECT espn_id::text, nba_id::text FROM {espn_schema}.game_id_mapping"),
        engine,
    )


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_games(
    espn_games: pd.DataFrame,
    nba_index: pd.DataFrame,
) -> pd.DataFrame:
    """
    Empareja ESPN games con NBA game_ids por equipo + temporada.

    Cuando hay varios candidatos NBA para el mismo par de equipos en la misma
    temporada, los ordena por game_id (secuencia cronológica) y los empareja
    con los ESPN games ordenados por fecha.

    Returns:
        DataFrame con espn_id, nba_id, confidence ('exact' | 'positional')
    """
    # Construir índice NBA: (prefix, frozenset{tc1,tc2}) → lista de nba_ids (sorted)
    nba_lookup: dict[tuple, list[str]] = defaultdict(list)
    for _, row in nba_index.iterrows():
        key = (row["prefix"], row["team_key"])
        nba_lookup[key].append(row["nba_id"])
    # Ordenar cada lista por game_id (secuencia NBA)
    for key in nba_lookup:
        nba_lookup[key].sort()

    # Construir índice ESPN: (prefix, frozenset{home_tc, away_tc}) → lista de espn_ids (sorted por fecha)
    espn_games = espn_games.dropna(subset=["home_tc", "away_tc", "prefix"])
    espn_groups: dict[tuple, list[tuple]] = defaultdict(list)
    for _, row in espn_games.iterrows():
        team_key = frozenset([row["home_tc"], row["away_tc"]])
        key = (row["prefix"], team_key)
        espn_groups[key].append((row["fecha"], row["espn_id"]))
    for key in espn_groups:
        espn_groups[key].sort(key=lambda x: x[0])  # sort by date

    matches = []
    no_nba_candidate = 0
    size_mismatch = 0

    for key, espn_list in espn_groups.items():
        nba_list = nba_lookup.get(key, [])

        if not nba_list:
            no_nba_candidate += len(espn_list)
            logger.debug(f"Sin candidatos NBA para {key}: {len(espn_list)} ESPN games")
            continue

        if len(espn_list) == len(nba_list):
            # Match 1:1 por posición cronológica
            confidence = "exact" if len(espn_list) == 1 else "positional"
            for (fecha, espn_id), nba_id in zip(espn_list, nba_list):
                matches.append({
                    "espn_id":     espn_id,
                    "nba_id":      nba_id,
                    "confidence":  confidence,
                    "fecha":       fecha,
                })
        elif len(nba_list) > len(espn_list):
            # Más candidatos NBA que ESPN: emparejar los ESPN con los primeros NBA
            # (podría pasar si hay más variantes del juego en boxscores)
            for (fecha, espn_id), nba_id in zip(espn_list, nba_list):
                matches.append({
                    "espn_id":     espn_id,
                    "nba_id":      nba_id,
                    "confidence":  "positional_partial",
                    "fecha":       fecha,
                })
            logger.debug(f"Más candidatos NBA ({len(nba_list)}) que ESPN ({len(espn_list)}) para {key}")
        else:
            # Más ESPN que NBA: solo los que tienen candidato
            size_mismatch += len(espn_list) - len(nba_list)
            for (fecha, espn_id), nba_id in zip(espn_list, nba_list):
                matches.append({
                    "espn_id":     espn_id,
                    "nba_id":      nba_id,
                    "confidence":  "positional_partial",
                    "fecha":       fecha,
                })
            logger.debug(f"Más ESPN ({len(espn_list)}) que NBA ({len(nba_list)}) para {key}")

    if no_nba_candidate > 0:
        logger.info(f"Sin candidato NBA: {no_nba_candidate} ESPN games")
    if size_mismatch > 0:
        logger.info(f"Mismatch de tamaño: {size_mismatch} ESPN games sin NBA candidato extra")

    return pd.DataFrame(matches) if matches else pd.DataFrame(
        columns=["espn_id", "nba_id", "confidence", "fecha"]
    )


# ---------------------------------------------------------------------------
# Inserción
# ---------------------------------------------------------------------------

def insert_mappings(conn, espn_schema: str, matches: pd.DataFrame, existing_ids: set) -> int:
    inserted = 0
    for _, row in matches.iterrows():
        if row["espn_id"] in existing_ids:
            continue
        try:
            conn.execute(text(f"""
                INSERT INTO {espn_schema}.game_id_mapping (espn_id, nba_id)
                VALUES (:eid, :nid)
            """), {"eid": row["espn_id"], "nid": row["nba_id"]})
            existing_ids.add(row["espn_id"])
            inserted += 1
        except Exception as e:
            logger.warning(f"Error insertando {row['espn_id']} -> {row['nba_id']}: {e}")
    return inserted


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def fix_mapping(dry_run: bool = False, audit_only: bool = False):
    database_url = db_config.get_database_url()
    espn_schema  = db_config.get_schema("espn")
    engine = create_engine(database_url, pool_pre_ping=True)

    print("\n" + "=" * 65)
    print("REPARACION DE game_id_mapping (ESPN -> NBA) - solo datos internos")
    print("=" * 65)

    existing_mapping = load_existing_mapping(engine, espn_schema)
    espn_no_map      = load_unmapped_espn_games(engine, espn_schema)

    print(f"  Mappings existentes:    {len(existing_mapping)}")
    print(f"  ESPN games sin mapping: {len(espn_no_map)}")

    if audit_only or espn_no_map.empty:
        print("  Nada que reparar (o modo audit-only).")
        return

    # Cargar índice NBA (sólo game_ids no mapeados aún)
    nba_index = load_nba_boxscore_index(engine, espn_schema)
    if nba_index.empty:
        print("  No hay NBA game_ids disponibles para matching. Abortando.")
        return

    # Matching
    print("\n  Haciendo matching por equipo + temporada + posición cronológica...")
    matches = match_games(espn_no_map, nba_index)

    exact      = (matches["confidence"] == "exact").sum() if not matches.empty else 0
    positional = (matches["confidence"].isin(["positional", "positional_partial"])).sum() if not matches.empty else 0
    unmatched  = len(espn_no_map) - len(matches)

    print(f"  Matches exactos (1 candidato):    {exact}")
    print(f"  Matches posicionales (N:N):        {positional}")
    print(f"  Sin match:                         {unmatched}")
    print(f"  Total matches:                     {len(matches)}")

    if matches.empty:
        print("  No se encontraron matches.")
        return

    # Sample
    print("\n  Sample (primeros 15 matches):")
    sample = matches.head(15)
    espn_lookup = espn_no_map.set_index("espn_id")
    for _, row in sample.iterrows():
        er = espn_lookup.loc[row["espn_id"]] if row["espn_id"] in espn_lookup.index else None
        if er is not None:
            print(f"    ESPN {row['espn_id']} ({row['fecha']} "
                  f"{er['away_team']} @ {er['home_team']}) "
                  f"-> NBA {row['nba_id']} [{row['confidence']}]")

    if dry_run:
        print(f"\n  [DRY RUN] Se insertarían {len(matches)} nuevos mappings.")
        return

    # Inserción
    print(f"\n  Insertando {len(matches)} mappings...")
    existing_ids = set(existing_mapping["espn_id"].astype(str).tolist())
    with engine.begin() as conn:
        inserted = insert_mappings(conn, espn_schema, matches, existing_ids)

    print(f"  Insertados: {inserted}")
    new_count = load_existing_mapping(engine, espn_schema)
    print(f"  Mapping total ahora: {len(new_count)} entradas")
    if inserted > 0:
        print("  --> Re-ejecutar build_features.py para actualizar rolling features.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repara espn.game_id_mapping (datos internos)")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    fix_mapping(dry_run=args.dry_run, audit_only=args.audit_only)
