"""
Pipeline completo de actualización de odds NBA.

Ejecuta 3 pasos en secuencia:
  1. Fetch desde The Odds API → INSERT/UPDATE en espn.odds
  2. Normalizar JSONB → espn.game_odds  (moneyline_home / moneyline_away)
  3. Calcular implied_prob → UPDATE ml.ml_ready_games

Detecta automáticamente el formato de cuotas (americano o decimal).

Uso:
    cd Scrapping/nba
    python refresh_odds_pipeline.py            # todos los pasos
    python refresh_odds_pipeline.py --step 1   # solo fetch API
    python refresh_odds_pipeline.py --step 2   # solo normalizar
    python refresh_odds_pipeline.py --step 3   # solo implied_prob
    python refresh_odds_pipeline.py --dry-run  # sin escribir en BD
"""

import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import requests
import pandas as pd
from sqlalchemy import create_engine, text
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config

# ──────────────────────────────────────────────────────────────────────────────
# Configuración
# ──────────────────────────────────────────────────────────────────────────────

ODDS_API_KEY = "e123f1c13b19f4cdc29d9393c978ec4e"
ODDS_API_URL = (
    "https://api.the-odds-api.com/v4/sports/basketball_nba/odds"
    "?regions=us&markets=h2h,spreads,totals&oddsFormat=american&apiKey={key}"
)

TEAM_NORMALIZE = {
    "Atlanta Hawks": "hawks", "Boston Celtics": "celtics", "Brooklyn Nets": "nets",
    "Charlotte Hornets": "hornets", "Chicago Bulls": "bulls", "Cleveland Cavaliers": "cavaliers",
    "Dallas Mavericks": "mavericks", "Denver Nuggets": "nuggets", "Detroit Pistons": "pistons",
    "Golden State Warriors": "warriors", "Houston Rockets": "rockets", "Indiana Pacers": "pacers",
    "Los Angeles Clippers": "clippers", "LA Clippers": "clippers",
    "Los Angeles Lakers": "lakers", "Memphis Grizzlies": "grizzlies",
    "Miami Heat": "heat", "Milwaukee Bucks": "bucks", "Minnesota Timberwolves": "timberwolves",
    "New Orleans Pelicans": "pelicans", "New York Knicks": "knicks",
    "Oklahoma City Thunder": "thunder", "Orlando Magic": "magic",
    "Philadelphia 76ers": "76ers", "Phoenix Suns": "suns",
    "Portland Trail Blazers": "trail blazers", "Sacramento Kings": "kings",
    "San Antonio Spurs": "spurs", "Toronto Raptors": "raptors",
    "Utah Jazz": "jazz", "Washington Wizards": "wizards",
}


def norm_team(name: str) -> str:
    return TEAM_NORMALIZE.get(name, name.lower().strip())


# ──────────────────────────────────────────────────────────────────────────────
# Paso 1: Fetch desde The Odds API
# ──────────────────────────────────────────────────────────────────────────────

def step1_fetch_odds(engine, espn_schema: str, dry_run: bool = False) -> int:
    logger.info("── PASO 1: Fetch desde The Odds API ──────────────────────────")
    url = ODDS_API_URL.format(key=ODDS_API_KEY)

    try:
        resp = requests.get(url, timeout=20)
    except requests.RequestException as e:
        logger.error(f"Error de conexión: {e}")
        return 0

    # Verificar cuota restante
    remaining = resp.headers.get("x-requests-remaining", "?")
    used      = resp.headers.get("x-requests-used", "?")
    logger.info(f"API quota — usada: {used} / restante: {remaining}")

    if resp.status_code == 401:
        logger.error("API Key inválida o expirada.")
        return 0
    if resp.status_code == 429:
        logger.error("Límite de requests alcanzado.")
        return 0
    resp.raise_for_status()

    games = resp.json()
    logger.info(f"Partidos recibidos desde API: {len(games)}")

    if not games:
        logger.warning("La API no devolvió partidos. Posiblemente la temporada está terminada.")
        return 0

    for g in games:
        logger.info(
            f"  {g.get('commence_time', '')[:10]}  "
            f"{g.get('away_team', '')} @ {g.get('home_team', '')}  "
            f"({len(g.get('bookmakers', []))} books)"
        )

    if dry_run:
        logger.info("[DRY RUN] No se escribe en BD.")
        return len(games)

    inserted = 0
    with engine.begin() as conn:
        for g in games:
            conn.execute(text(f"""
                INSERT INTO {espn_schema}.odds
                    (game_id, sport_key, sport_title, commence_time,
                     home_team, away_team, bookmakers)
                VALUES
                    (:gid, :sk, :st, :ct, :ht, :at, CAST(:bm AS jsonb))
                ON CONFLICT (game_id) DO UPDATE
                    SET bookmakers    = EXCLUDED.bookmakers,
                        commence_time = EXCLUDED.commence_time,
                        home_team     = EXCLUDED.home_team,
                        away_team     = EXCLUDED.away_team
            """), {
                "gid": g["id"],
                "sk":  g.get("sport_key"),
                "st":  g.get("sport_title"),
                "ct":  g.get("commence_time"),
                "ht":  g.get("home_team"),
                "at":  g.get("away_team"),
                "bm":  json.dumps(g.get("bookmakers", [])),
            })
            inserted += 1

    logger.info(f"[OK] {inserted} partidos insertados/actualizados en espn.odds")
    return inserted


# ──────────────────────────────────────────────────────────────────────────────
# Paso 2: Normalizar JSONB → espn.game_odds
# ──────────────────────────────────────────────────────────────────────────────

def _build_espn_games_lookup(engine, espn_schema: str) -> dict:
    """
    Carga espn.games y construye un lookup:
      (date_str, home_norm, away_norm) → espn_game_id

    También acepta ventana de ±1 día para diferencias de timezone entre
    The Odds API (UTC) y ESPN (Eastern).
    """
    espn_games = pd.read_sql(text(f"""
        SELECT game_id AS espn_game_id, fecha, home_team, away_team
        FROM {espn_schema}.games
        WHERE home_team IS NOT NULL AND home_team != ''
    """), engine)

    lookup = {}
    for _, g in espn_games.iterrows():
        fecha = g['fecha']
        if hasattr(fecha, 'strftime'):
            date_str = fecha.strftime('%Y-%m-%d')
        else:
            date_str = str(fecha)[:10]

        h = norm_team(g['home_team'])
        a = norm_team(g['away_team'])
        lookup[(date_str, h, a)] = int(g['espn_game_id'])

    return lookup


def _resolve_espn_game_id(odds_id: str, commence_time_str: str,
                           home_raw: str, away_raw: str,
                           lookup: dict) -> int | None:
    """
    Intenta resolver el ESPN game_id a partir de fecha + equipos.
    Prueba la fecha exacta y ±1 día (para diferencias de timezone UTC vs Eastern).
    """
    try:
        dt_utc = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None

    # Timezone eastern = UTC-4 (EDT, mayo-junio)
    dt_et = dt_utc - timedelta(hours=4)
    base_date = dt_et.date()

    h = norm_team(home_raw)
    a = norm_team(away_raw)

    for delta in (0, -1, 1):
        from datetime import date as _date
        d = base_date + timedelta(days=delta)
        key = (d.strftime('%Y-%m-%d'), h, a)
        if key in lookup:
            return lookup[key]

    return None


def step2_normalize(engine, espn_schema: str, dry_run: bool = False) -> int:
    logger.info("── PASO 2: Normalizar JSONB → espn.game_odds ─────────────────")

    # Cargar todas las odds crudas
    odds_raw = pd.read_sql(text(f"""
        SELECT game_id AS odds_id, commence_time, home_team, away_team, bookmakers
        FROM {espn_schema}.odds
        WHERE bookmakers IS NOT NULL
    """), engine)

    logger.info(f"Registros en espn.odds: {len(odds_raw)}")

    # Construir lookup ESPN games por (fecha, home_norm, away_norm)
    games_lookup = _build_espn_games_lookup(engine, espn_schema)
    logger.info(f"ESPN games en lookup: {len(games_lookup)}")

    # Resolver ESPN game_id para cada odds record (inline, sin depender de odds_event_game_map)
    def resolve(row):
        # Primero intentar odds_event_game_map si ya existe
        return _resolve_espn_game_id(
            row['odds_id'], row['commence_time'],
            row['home_team'], row['away_team'],
            games_lookup,
        )

    odds_raw['espn_game_id'] = odds_raw.apply(resolve, axis=1)
    mapped_count = odds_raw['espn_game_id'].notna().sum()
    logger.info(f"Odds con mapping a ESPN game_id: {mapped_count} / {len(odds_raw)}")

    if mapped_count == 0:
        logger.warning("Ninguna odds pudo mapearse a un ESPN game_id. "
                       "Verifica que espn.games contenga los partidos correspondientes.")
        return 0

    # Persistir nuevos mappings en odds_event_game_map (para referencia futura)
    if not dry_run:
        mapped_rows = odds_raw[odds_raw['espn_game_id'].notna()]
        with engine.begin() as conn:
            for _, row in mapped_rows.iterrows():
                conn.execute(text(f"""
                    INSERT INTO {espn_schema}.odds_event_game_map (odds_id, game_id)
                    VALUES (:oid, :gid)
                    ON CONFLICT (odds_id) DO UPDATE SET game_id = EXCLUDED.game_id
                """), {"oid": row['odds_id'], "gid": int(row['espn_game_id'])})

    entries = []
    for _, row in odds_raw.iterrows():
        gid = row['espn_game_id']
        if pd.isna(gid):
            continue

        b_data = row['bookmakers']
        if isinstance(b_data, str):
            b_data = json.loads(b_data)

        home_name = row['home_team']
        away_name = row['away_team']

        for bookie in b_data:
            provider = bookie.get('key', 'unknown')
            for market in bookie.get('markets', []):
                mkey = market.get('key')
                for out in market.get('outcomes', []):
                    price = out.get('price')
                    point = out.get('point')
                    name  = out.get('name', '')
                    if price is None:
                        continue

                    if mkey == 'h2h':
                        if name == home_name:
                            otype = 'moneyline_home'
                        elif name == away_name:
                            otype = 'moneyline_away'
                        else:
                            continue
                    elif mkey == 'spreads':
                        if name == home_name:
                            otype = 'spread_home'
                        elif name == away_name:
                            otype = 'spread_away'
                        else:
                            continue
                    elif mkey == 'totals':
                        otype = f"total_{name.lower()}"  # total_over / total_under
                    else:
                        continue

                    entries.append({
                        'game_id':    int(gid),
                        'odds_type':  otype,
                        'odds_value': float(price),
                        'line_value': float(point) if point is not None else None,
                        'provider':   provider,
                    })

    if not entries:
        logger.warning("No hay entradas normalizadas para insertar.")
        return 0

    df_entries = pd.DataFrame(entries)

    # Diagnóstico de formato
    moneyline = df_entries[df_entries['odds_type'].isin(['moneyline_home', 'moneyline_away'])]
    if not moneyline.empty:
        med = moneyline['odds_value'].abs().median()
        fmt = "AMERICANO" if med >= 100 else "DECIMAL"
        mn, mx = moneyline['odds_value'].min(), moneyline['odds_value'].max()
        logger.info(f"Formato detectado: {fmt}  (rango=[{mn:.1f}, {mx:.1f}], mediana_abs={med:.1f})")

    logger.info(f"Total entradas normalizadas: {len(df_entries)}")
    logger.info(f"  moneyline_home: {(df_entries['odds_type']=='moneyline_home').sum()}")
    logger.info(f"  moneyline_away: {(df_entries['odds_type']=='moneyline_away').sum()}")
    logger.info(f"  spread:         {df_entries['odds_type'].str.startswith('spread').sum()}")
    logger.info(f"  total:          {df_entries['odds_type'].str.startswith('total').sum()}")

    if dry_run:
        logger.info("[DRY RUN] No se escribe en BD.")
        return len(df_entries)

    # Truncar y re-insertar (más limpio que ON CONFLICT con 4 columnas)
    with engine.begin() as conn:
        # Solo borrar los game_ids que vamos a re-insertar
        game_ids = df_entries['game_id'].unique().tolist()
        conn.execute(text(f"""
            DELETE FROM {espn_schema}.game_odds
            WHERE game_id = ANY(:ids)
        """), {"ids": game_ids})

        for _, r in df_entries.iterrows():
            conn.execute(text(f"""
                INSERT INTO {espn_schema}.game_odds
                    (game_id, odds_type, odds_value, line_value, provider)
                VALUES (:gid, :ot, :ov, :lv, :pr)
                ON CONFLICT DO NOTHING
            """), {
                "gid": int(r['game_id']),
                "ot":  r['odds_type'],
                "ov":  r['odds_value'],
                "lv":  r['line_value'],
                "pr":  r['provider'],
            })

    logger.info(f"[OK] {len(df_entries)} entradas escritas en espn.game_odds")
    return len(df_entries)


# ──────────────────────────────────────────────────────────────────────────────
# Paso 3: Calcular implied_prob → ml_ready_games
# ──────────────────────────────────────────────────────────────────────────────

def american_to_decimal(odds: float) -> float:
    if odds > 0:
        return 1 + odds / 100.0
    else:
        return 1 + 100.0 / abs(odds)


def to_decimal(odds: float) -> float | None:
    """Auto-detecta formato americano vs decimal y convierte a decimal."""
    if odds is None:
        return None
    if abs(odds) >= 100:          # americano
        return american_to_decimal(odds)
    elif 1.0 < abs(odds) < 50.0:  # ya es decimal
        return float(odds)
    return None


def step3_implied_prob(engine, espn_schema: str, ml_schema: str, dry_run: bool = False) -> int:
    logger.info("── PASO 3: Calcular implied_prob → ml_ready_games ────────────")

    go = pd.read_sql(text(f"""
        SELECT game_id, odds_type, AVG(odds_value) AS avg_odds
        FROM {espn_schema}.game_odds
        WHERE odds_type IN ('moneyline_home', 'moneyline_away')
          AND odds_value IS NOT NULL
        GROUP BY game_id, odds_type
    """), engine)

    if go.empty:
        logger.warning("No hay datos de moneyline en espn.game_odds.")
        return 0

    go_pivot = go.pivot(index='game_id', columns='odds_type', values='avg_odds').reset_index()
    go_pivot.columns.name = None

    if 'moneyline_home' not in go_pivot.columns or 'moneyline_away' not in go_pivot.columns:
        logger.warning("Faltan columnas moneyline_home o moneyline_away.")
        return 0

    # Diagnóstico de formato
    med = go_pivot['moneyline_home'].abs().median()
    fmt = "AMERICANO" if med >= 100 else "DECIMAL"
    logger.info(f"Formato en game_odds: {fmt} (mediana_abs home={med:.1f})")

    go_pivot['dec_home'] = go_pivot['moneyline_home'].apply(to_decimal)
    go_pivot['dec_away'] = go_pivot['moneyline_away'].apply(to_decimal)
    go_pivot = go_pivot.dropna(subset=['dec_home', 'dec_away'])

    go_pivot['raw_home'] = 1.0 / go_pivot['dec_home']
    go_pivot['raw_away'] = 1.0 / go_pivot['dec_away']
    total = go_pivot['raw_home'] + go_pivot['raw_away']

    go_pivot['implied_prob_home'] = (go_pivot['raw_home'] / total).round(4)
    go_pivot['implied_prob_away'] = (go_pivot['raw_away'] / total).round(4)

    # Validar rango
    valid = go_pivot['implied_prob_home'].between(0.01, 0.99)
    go_pivot = go_pivot[valid]

    logger.info(f"Partidos con implied_prob válida: {len(go_pivot)}")

    # Muestra
    sample = go_pivot.head(8)
    logger.info(f"\n  {'game_id':>12}  {'ml_home':>8}  {'ml_away':>8}  "
                f"{'imp_home':>10}  {'imp_away':>10}")
    for _, r in sample.iterrows():
        logger.info(
            f"  {int(r['game_id']):>12}  {r['moneyline_home']:>8.1f}  "
            f"{r['moneyline_away']:>8.1f}  "
            f"{r['implied_prob_home']:>10.4f}  {r['implied_prob_away']:>10.4f}"
        )

    if dry_run:
        logger.info("[DRY RUN] No se escribe en BD.")
        return len(go_pivot)

    updated = 0
    with engine.begin() as conn:
        for _, row in go_pivot.iterrows():
            res = conn.execute(text(f"""
                UPDATE {ml_schema}.ml_ready_games
                SET implied_prob_home = :iph,
                    implied_prob_away = :ipa
                WHERE game_id = :gid
            """), {
                "iph": float(row['implied_prob_home']),
                "ipa": float(row['implied_prob_away']),
                "gid": int(row['game_id']),
            })
            updated += res.rowcount

    pct = updated / pd.read_sql(
        text(f"SELECT COUNT(*) AS n FROM {ml_schema}.ml_ready_games"), engine
    )["n"].iloc[0] * 100
    logger.info(f"[OK] {updated} filas actualizadas en ml_ready_games ({pct:.1f}% del dataset)")
    return updated


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pipeline de odds NBA")
    parser.add_argument("--step", type=int, choices=[1, 2, 3],
                        help="Ejecutar solo este paso (1=fetch, 2=normalizar, 3=implied_prob)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular sin escribir en BD")
    args = parser.parse_args()

    database_url = db_config.get_database_url()
    espn_schema  = db_config.get_schema("espn")
    ml_schema    = db_config.get_schema("ml")
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    logger.info("=" * 60)
    logger.info("PIPELINE DE ODDS NBA")
    logger.info(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.dry_run:
        logger.info("[DRY RUN ACTIVO — no se escribirá en BD]")
    logger.info("=" * 60)

    run_all = args.step is None
    results = {}

    if run_all or args.step == 1:
        results[1] = step1_fetch_odds(engine, espn_schema, dry_run=args.dry_run)
        if results[1] == 0 and run_all:
            logger.warning("Paso 1 sin nuevos datos. Continuando con datos existentes...")

    if run_all or args.step == 2:
        results[2] = step2_normalize(engine, espn_schema, dry_run=args.dry_run)

    if run_all or args.step == 3:
        results[3] = step3_implied_prob(engine, espn_schema, ml_schema, dry_run=args.dry_run)

    logger.info("\n" + "=" * 60)
    logger.info("RESUMEN")
    if 1 in results: logger.info(f"  Paso 1 (fetch):        {results[1]} partidos de API")
    if 2 in results: logger.info(f"  Paso 2 (normalizar):   {results[2]} entradas en game_odds")
    if 3 in results: logger.info(f"  Paso 3 (implied_prob): {results[3]} filas en ml_ready_games")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
