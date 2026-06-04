"""
Auditoría exhaustiva de la arquitectura de base de datos HAW (Neon PostgreSQL).

Cubre 8 dimensiones de calidad:
  1. Inventario de tablas, columnas y tipos por schema
  2. Constraints existentes (PK, UNIQUE, FK, CHECK)
  3. Duplicados directos en la DB (por tabla y clave natural)
  4. Análisis de NULLs por columna (% de completitud)
  5. Rangos y distribución de valores clave
  6. Integridad referencial cruzada (huérfanos entre tablas)
  7. Consistencia espn ↔ ml (cobertura del pipeline)
  8. Recomendaciones accionables

Uso:
    cd Scrapping/nba
    python db_audit_completo.py
    python db_audit_completo.py --schema espn
    python db_audit_completo.py --skip-nulls      # más rápido
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ML"))
from src.config import db_config

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de presentación
# ──────────────────────────────────────────────────────────────────────────────

PASS  = "✓"
FAIL  = "✗"
WARN  = "⚠"
SEP   = "─" * 72

def section(title):
    print(f"\n{'═' * 72}")
    print(f"  {title}")
    print('═' * 72)

def subsection(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def ok(msg):   print(f"  {PASS}  {msg}")
def fail(msg): print(f"  {FAIL}  {msg}")
def warn(msg): print(f"  {WARN}  {msg}")

findings = []   # lista global de hallazgos para el resumen final

def record(severity, area, message):
    findings.append({"severity": severity, "area": area, "message": message})
    if severity == "ERROR":  fail(message)
    elif severity == "WARN": warn(message)
    else:                    ok(message)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Inventario de tablas y columnas
# ──────────────────────────────────────────────────────────────────────────────

def check_inventory(engine, schemas):
    section("1. INVENTARIO DE TABLAS Y COLUMNAS")

    for schema in schemas:
        tables = pd.read_sql(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :s AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """), engine, params={"s": schema})

        views = pd.read_sql(text("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = :s
            ORDER BY table_name
        """), engine, params={"s": schema})

        subsection(f"Schema: {schema}  ({len(tables)} tablas, {len(views)} vistas)")

        for _, t in tables.iterrows():
            tname = t["table_name"]
            count = pd.read_sql(
                text(f'SELECT COUNT(*) AS n FROM "{schema}"."{tname}"'), engine
            )["n"].iloc[0]

            cols = pd.read_sql(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = :s AND table_name = :t
                ORDER BY ordinal_position
            """), engine, params={"s": schema, "t": tname})

            print(f"\n  [{schema}.{tname}]  {count:,} filas  |  {len(cols)} columnas")
            for _, c in cols.iterrows():
                nn  = "" if c["is_nullable"] == "YES" else " NOT NULL"
                df_ = f" DEFAULT {c['column_default']}" if c["column_default"] else ""
                print(f"      {c['column_name']:<38} {c['data_type']}{nn}{df_}")

        if not views.empty:
            print(f"\n  Vistas: {', '.join(views['table_name'].tolist())}")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Constraints (PK, UNIQUE, FK, CHECK)
# ──────────────────────────────────────────────────────────────────────────────

def check_constraints(engine, schemas):
    section("2. CONSTRAINTS (PK / UNIQUE / FK / CHECK)")

    for schema in schemas:
        subsection(f"Schema: {schema}")

        constraints = pd.read_sql(text("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                tc.constraint_type,
                kcu.column_name,
                ccu.table_schema  AS ref_schema,
                ccu.table_name    AS ref_table,
                ccu.column_name   AS ref_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
               AND tc.table_schema    = kcu.table_schema
            LEFT JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
               AND tc.table_schema    = rc.constraint_schema
            LEFT JOIN information_schema.constraint_column_usage ccu
                ON rc.unique_constraint_name = ccu.constraint_name
               AND rc.unique_constraint_schema = ccu.table_schema
            WHERE tc.table_schema = :s
            ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name
        """), engine, params={"s": schema})

        if constraints.empty:
            record("WARN", f"{schema}/constraints",
                   f"Schema {schema}: ningún constraint registrado en information_schema")
            continue

        tables_with_pk   = set(constraints[constraints["constraint_type"] == "PRIMARY KEY"]["table_name"])
        tables_with_uq   = set(constraints[constraints["constraint_type"] == "UNIQUE"]["table_name"])
        tables_with_fk   = set(constraints[constraints["constraint_type"] == "FOREIGN KEY"]["table_name"])

        # Listar todas las tablas del schema
        all_tables = pd.read_sql(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = :s AND table_type = 'BASE TABLE'
        """), engine, params={"s": schema})["table_name"].tolist()

        print(f"\n  Tablas sin PRIMARY KEY: ", end="")
        no_pk = [t for t in all_tables if t not in tables_with_pk]
        if no_pk:
            record("WARN", f"{schema}/PK", f"Sin PK: {', '.join(no_pk)}")
        else:
            record("OK", f"{schema}/PK", "Todas las tablas tienen PK")

        print(f"\n  Tablas con UNIQUE constraint: {', '.join(sorted(tables_with_uq)) or 'ninguna'}")
        print(f"  Tablas con FOREIGN KEY:       {', '.join(sorted(tables_with_fk)) or 'ninguna'}")

        # Detalle de cada constraint
        for _, row in constraints.drop_duplicates(
            subset=["table_name", "constraint_name", "constraint_type"]
        ).iterrows():
            ref = f" → {row['ref_schema']}.{row['ref_table']}.{row['ref_column']}" \
                  if row["constraint_type"] == "FOREIGN KEY" else ""
            col_row = constraints[constraints["constraint_name"] == row["constraint_name"]]
            cols_str = ", ".join(col_row["column_name"].tolist())
            print(f"    [{row['constraint_type']:<15}] {row['table_name']}.({cols_str}){ref}")


# ──────────────────────────────────────────────────────────────────────────────
# 3. Duplicados directamente en la DB
# ──────────────────────────────────────────────────────────────────────────────

def check_duplicates(engine, espn_schema, ml_schema):
    section("3. DUPLICADOS EN LA BASE DE DATOS")

    checks = [
        # (label, query)
        ("espn.games — game_id duplicado",
         f"""
         SELECT game_id, COUNT(*) AS n
         FROM {espn_schema}.games
         GROUP BY game_id HAVING COUNT(*) > 1
         """),

        ("espn.nba_player_boxscores — (game_id, player_id, team_tricode) duplicado",
         f"""
         SELECT game_id, player_id, team_tricode, COUNT(*) AS n
         FROM {espn_schema}.nba_player_boxscores
         GROUP BY game_id, player_id, team_tricode HAVING COUNT(*) > 1
         LIMIT 5
         """),

        ("espn.game_id_mapping — espn_id duplicado",
         f"""
         SELECT espn_id, COUNT(*) AS n
         FROM {espn_schema}.game_id_mapping
         GROUP BY espn_id HAVING COUNT(*) > 1
         """),

        ("ml.ml_ready_games — game_id duplicado",
         f"""
         SELECT game_id, COUNT(*) AS n
         FROM {ml_schema}.ml_ready_games
         GROUP BY game_id HAVING COUNT(*) > 1
         """),
    ]

    for label, query in checks:
        try:
            dupes = pd.read_sql(text(query), engine)
            if dupes.empty:
                record("OK", "duplicados", f"{label}: sin duplicados")
            else:
                record("ERROR", "duplicados",
                       f"{label}: {len(dupes)} grupos duplicados (muestra: {dupes.head(3).to_dict('records')})")
        except Exception as e:
            record("WARN", "duplicados", f"{label}: error al consultar — {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Análisis de NULLs por columna
# ──────────────────────────────────────────────────────────────────────────────

def check_nulls(engine, schemas):
    section("4. ANÁLISIS DE NULLs POR COLUMNA")

    # Tablas clave a revisar (evitar tablas con cientos de columnas que tarden mucho)
    key_tables = {
        "espn": ["games", "nba_player_boxscores", "game_id_mapping"],
        "ml":   ["ml_ready_games"],
        "app":  ["predictions"],
        "sys":  ["model_versions"],
    }

    for schema in schemas:
        tables = key_tables.get(schema, [])
        if not tables:
            continue

        subsection(f"Schema: {schema}")

        for tname in tables:
            try:
                total = pd.read_sql(
                    text(f'SELECT COUNT(*) AS n FROM "{schema}"."{tname}"'), engine
                )["n"].iloc[0]

                if total == 0:
                    warn(f"{schema}.{tname}: tabla vacía")
                    continue

                cols = pd.read_sql(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = :s AND table_name = :t
                    ORDER BY ordinal_position
                """), engine, params={"s": schema, "t": tname})["column_name"].tolist()

                null_counts = {}
                for col in cols:
                    try:
                        n_null = pd.read_sql(
                            text(f'SELECT COUNT(*) AS n FROM "{schema}"."{tname}" WHERE "{col}" IS NULL'),
                            engine
                        )["n"].iloc[0]
                        if n_null > 0:
                            null_counts[col] = n_null
                    except Exception:
                        pass

                print(f"\n  {schema}.{tname} ({total:,} filas)")
                if not null_counts:
                    ok("Sin columnas con NULLs")
                else:
                    critical = {c: n for c, n in null_counts.items() if n / total > 0.5}
                    moderate = {c: n for c, n in null_counts.items() if 0.05 < n / total <= 0.5}
                    low      = {c: n for c, n in null_counts.items() if n / total <= 0.05}

                    if critical:
                        for col, n in critical.items():
                            record("ERROR", f"NULLs/{schema}.{tname}",
                                   f"  {col}: {n:,} NULLs ({n/total*100:.1f}%) — columna mayormente vacía")
                    if moderate:
                        for col, n in moderate.items():
                            record("WARN", f"NULLs/{schema}.{tname}",
                                   f"  {col}: {n:,} NULLs ({n/total*100:.1f}%)")
                    if low:
                        for col, n in low.items():
                            ok(f"  {col}: {n:,} NULLs ({n/total*100:.1f}%) — aceptable")

            except Exception as e:
                warn(f"{schema}.{tname}: error — {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 5. Rangos y distribución de valores clave
# ──────────────────────────────────────────────────────────────────────────────

def check_value_ranges(engine, espn_schema, ml_schema):
    section("5. RANGOS Y DISTRIBUCIÓN DE VALORES CLAVE")

    range_checks = [
        # (label, query, col, min_valid, max_valid)
        ("espn.games — home_score",
         f"SELECT MIN(home_score) AS mn, MAX(home_score) AS mx, AVG(home_score)::NUMERIC(6,1) AS avg "
         f"FROM {espn_schema}.games WHERE home_score > 0",
         70, 175),

        ("espn.games — away_score",
         f"SELECT MIN(away_score) AS mn, MAX(away_score) AS mx, AVG(away_score)::NUMERIC(6,1) AS avg "
         f"FROM {espn_schema}.games WHERE away_score > 0",
         70, 175),

        ("espn.nba_player_boxscores — pts por jugador",
         f"SELECT MIN(pts) AS mn, MAX(pts) AS mx, AVG(pts)::NUMERIC(6,1) AS avg "
         f"FROM {espn_schema}.nba_player_boxscores",
         0, 75),

        ("espn.nba_player_boxscores — reb por jugador",
         f"SELECT MIN(reb) AS mn, MAX(reb) AS mx, AVG(reb)::NUMERIC(6,1) AS avg "
         f"FROM {espn_schema}.nba_player_boxscores",
         0, 30),

        ("ml.ml_ready_games — home_reb (post-ETL fix)",
         f"SELECT MIN(home_reb) AS mn, MAX(home_reb) AS mx, "
         f"AVG(home_reb)::NUMERIC(6,1) AS avg, "
         f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY home_reb) AS mediana "
         f"FROM {ml_schema}.ml_ready_games WHERE home_reb > 0",
         25, 75),

        ("ml.ml_ready_games — home_score",
         f"SELECT MIN(home_score) AS mn, MAX(home_score) AS mx, AVG(home_score)::NUMERIC(6,1) AS avg "
         f"FROM {ml_schema}.ml_ready_games WHERE home_score > 0",
         70, 175),

        ("ml.ml_ready_games — home_win (distribución)",
         f"SELECT home_win, COUNT(*) AS n FROM {ml_schema}.ml_ready_games "
         f"WHERE home_win IS NOT NULL GROUP BY home_win ORDER BY home_win",
         None, None),
    ]

    for entry in range_checks:
        label, query, mn_valid, mx_valid = entry
        try:
            res = pd.read_sql(text(query), engine)
            if res.empty:
                warn(f"{label}: sin datos")
                continue

            row = res.iloc[0]

            # Para queries de distribución (home_win)
            if mn_valid is None:
                print(f"\n  {label}:")
                print(res.to_string(index=False))
                continue

            mn, mx, avg = row.get("mn"), row.get("mx"), row.get("avg")
            mediana = row.get("mediana", "—")
            print(f"\n  {label}:")
            print(f"    min={mn}  max={mx}  avg={avg}  mediana={mediana}")

            if mn is not None and mx is not None:
                if mn < mn_valid:
                    record("WARN", f"rangos/{label}",
                           f"valor mínimo {mn} < esperado {mn_valid}")
                if mx > mx_valid:
                    record("WARN", f"rangos/{label}",
                           f"valor máximo {mx} > esperado {mx_valid}")
                if mn_valid <= (avg or 0) <= mx_valid:
                    record("OK", f"rangos/{label}", f"avg={avg} dentro del rango [{mn_valid}, {mx_valid}]")
        except Exception as e:
            warn(f"{label}: error — {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 6. Integridad referencial cruzada (huérfanos)
# ──────────────────────────────────────────────────────────────────────────────

def check_referential_integrity(engine, espn_schema, ml_schema):
    section("6. INTEGRIDAD REFERENCIAL CRUZADA (HUÉRFANOS)")

    checks = [
        # (label, query_count_orphans, description)
        (
            "nba_player_boxscores → games (game_id no existe en games)",
            f"""
            SELECT COUNT(*) AS n
            FROM {espn_schema}.nba_player_boxscores pb
            LEFT JOIN {espn_schema}.game_id_mapping m ON pb.game_id::text = m.nba_id
            LEFT JOIN {espn_schema}.games g ON m.espn_id = g.game_id::text
            WHERE g.game_id IS NULL
            """,
            "Boxscores sin partido padre en espn.games"
        ),
        (
            "game_id_mapping → games (espn_id sin partido en games)",
            f"""
            SELECT COUNT(*) AS n
            FROM {espn_schema}.game_id_mapping m
            LEFT JOIN {espn_schema}.games g ON m.espn_id = g.game_id::text
            WHERE g.game_id IS NULL
            """,
            "Mappings huérfanos sin partido en espn.games"
        ),
        (
            "ml_ready_games → espn.games (game_id sin partido ESPN)",
            f"""
            SELECT COUNT(*) AS n
            FROM {ml_schema}.ml_ready_games ml
            LEFT JOIN {espn_schema}.games g ON ml.game_id::text = g.game_id::text
            WHERE g.game_id IS NULL
            """,
            "Filas en ml_ready_games sin partido ESPN correspondiente"
        ),
        (
            "espn.games jugados → ml_ready_games (sin features ML)",
            f"""
            SELECT COUNT(*) AS n
            FROM {espn_schema}.games g
            LEFT JOIN {ml_schema}.ml_ready_games ml ON g.game_id::text = ml.game_id::text
            WHERE g.home_score > 0 AND g.away_score > 0
              AND ml.game_id IS NULL
            """,
            "Partidos jugados sin fila en ml_ready_games (ETL pendiente)"
        ),
        (
            "espn.games con score=0 (partidos futuros o sin score)",
            f"""
            SELECT COUNT(*) AS n
            FROM {espn_schema}.games
            WHERE home_score = 0 AND away_score = 0
            """,
            "Partidos sin score (pueden ser futuros o scraping incompleto)"
        ),
    ]

    for label, query, description in checks:
        try:
            n = pd.read_sql(text(query), engine)["n"].iloc[0]
            if n == 0:
                record("OK", "referencial", f"{description}: sin huérfanos")
            elif n < 50:
                record("WARN", "referencial", f"{description}: {n} registros huérfanos")
            else:
                record("ERROR", "referencial",
                       f"{description}: {n:,} registros huérfanos — revisar pipeline")
        except Exception as e:
            warn(f"{label}: error — {e}")


# ──────────────────────────────────────────────────────────────────────────────
# 7. Consistencia espn ↔ ml (cobertura del pipeline)
# ──────────────────────────────────────────────────────────────────────────────

def check_pipeline_consistency(engine, espn_schema, ml_schema):
    section("7. CONSISTENCIA ESPN ↔ ML (COBERTURA DEL PIPELINE)")

    subsection("7a. Cobertura por temporada")
    coverage = pd.read_sql(text(f"""
        SELECT
            CASE
                WHEN g.fecha >= '2023-10-24' AND g.fecha < '2024-09-01' THEN '2023-24'
                WHEN g.fecha >= '2024-10-22' AND g.fecha < '2025-09-01' THEN '2024-25'
                WHEN g.fecha >= '2025-10-22'                             THEN '2025-26'
                ELSE 'otro'
            END AS season,
            COUNT(g.game_id)                                     AS espn_jugados,
            COUNT(m.espn_id)                                     AS con_mapping,
            COUNT(ml.game_id)                                    AS en_ml_ready,
            COUNT(CASE WHEN ml.off_rating_diff IS NOT NULL THEN 1 END) AS con_off_rating,
            COUNT(CASE WHEN ml.home_reb IS NOT NULL AND ml.home_reb > 0 THEN 1 END) AS con_home_reb
        FROM {espn_schema}.games g
        LEFT JOIN {espn_schema}.game_id_mapping m  ON g.game_id::text = m.espn_id
        LEFT JOIN {ml_schema}.ml_ready_games ml    ON g.game_id::text = ml.game_id::text
        WHERE g.home_score > 0 OR g.away_score > 0
        GROUP BY 1
        ORDER BY 1
    """), engine)

    print(f"\n  {'Season':<12} {'ESPN':>8} {'Mapping':>10} {'ml_ready':>10} {'off_rating':>12} {'home_reb':>10}")
    print(f"  {SEP}")
    for _, r in coverage.iterrows():
        cov_map = f"({r['con_mapping']/r['espn_jugados']*100:.0f}%)" if r['espn_jugados'] else ""
        cov_ml  = f"({r['en_ml_ready']/r['espn_jugados']*100:.0f}%)" if r['espn_jugados'] else ""
        print(f"  {r['season']:<12} {r['espn_jugados']:>8} {r['con_mapping']:>6} {cov_map:<5} "
              f"{r['en_ml_ready']:>6} {cov_ml:<5} {r['con_off_rating']:>10} {r['con_home_reb']:>10}")

    # Detectar problemas
    for _, r in coverage.iterrows():
        if r["espn_jugados"] > 0:
            map_pct = r["con_mapping"] / r["espn_jugados"]
            ml_pct  = r["en_ml_ready"] / r["espn_jugados"]
            or_pct  = r["con_off_rating"] / r["en_ml_ready"] if r["en_ml_ready"] > 0 else 0
            reb_pct = r["con_home_reb"] / r["en_ml_ready"] if r["en_ml_ready"] > 0 else 0

            if map_pct < 0.80:
                record("ERROR", "cobertura", f"{r['season']}: mapping solo {map_pct*100:.1f}% (< 80%)")
            elif map_pct < 0.95:
                record("WARN", "cobertura", f"{r['season']}: mapping {map_pct*100:.1f}%")
            else:
                record("OK", "cobertura", f"{r['season']}: mapping {map_pct*100:.1f}%")

            if or_pct < 0.70:
                record("ERROR", "cobertura", f"{r['season']}: off_rating solo {or_pct*100:.1f}% de ml_ready")
            elif or_pct < 0.90:
                record("WARN", "cobertura", f"{r['season']}: off_rating {or_pct*100:.1f}%")
            else:
                record("OK", "cobertura", f"{r['season']}: off_rating {or_pct*100:.1f}%")

            if reb_pct < 0.70:
                record("ERROR", "cobertura",
                       f"{r['season']}: home_reb válido solo {reb_pct*100:.1f}% — revisar ETL deduplicación")
            elif reb_pct < 0.90:
                record("WARN", "cobertura", f"{r['season']}: home_reb válido {reb_pct*100:.1f}%")
            else:
                record("OK", "cobertura", f"{r['season']}: home_reb válido {reb_pct*100:.1f}%")

    subsection("7b. Features con alta tasa de NULL en ml_ready_games")
    feature_cols = [
        "ppg_diff", "net_rating_diff_rolling", "pace_diff", "off_rating_diff",
        "def_rating_diff", "reb_rolling_diff", "ast_rolling_diff", "tov_rolling_diff",
        "efg_pct_diff", "tov_rate_diff", "oreb_pct_diff", "dreb_pct_diff",
        "elo_diff", "streak_diff", "home_elo", "away_elo", "home_reb", "away_reb",
        "home_ast", "away_ast", "home_stl", "away_stl",
    ]

    total_ml = pd.read_sql(
        text(f"SELECT COUNT(*) AS n FROM {ml_schema}.ml_ready_games WHERE home_win IS NOT NULL"),
        engine
    )["n"].iloc[0]

    print(f"\n  {'Feature':<35} {'NULL':>8} {'% NULL':>8}  Estado")
    print(f"  {SEP}")
    for col in feature_cols:
        try:
            n_null = pd.read_sql(
                text(f"SELECT COUNT(*) AS n FROM {ml_schema}.ml_ready_games "
                     f"WHERE \"{col}\" IS NULL AND home_win IS NOT NULL"),
                engine
            )["n"].iloc[0]
            pct = n_null / total_ml * 100 if total_ml else 0
            status = PASS if pct < 5 else (WARN if pct < 30 else FAIL)
            print(f"  {col:<35} {n_null:>8,} {pct:>7.1f}%  {status}")
        except Exception:
            print(f"  {col:<35} {'N/A':>8}  {'—':>7}   ?")


# ──────────────────────────────────────────────────────────────────────────────
# 8. Resumen final y recomendaciones
# ──────────────────────────────────────────────────────────────────────────────

def print_summary():
    section("8. RESUMEN EJECUTIVO Y RECOMENDACIONES")

    errors = [f for f in findings if f["severity"] == "ERROR"]
    warns  = [f for f in findings if f["severity"] == "WARN"]
    oks    = [f for f in findings if f["severity"] == "OK"]

    print(f"\n  Hallazgos: {len(errors)} errores | {len(warns)} advertencias | {len(oks)} OK\n")

    if errors:
        print(f"  {FAIL} ERRORES (acción requerida):")
        for e in errors:
            print(f"     [{e['area']}] {e['message']}")

    if warns:
        print(f"\n  {WARN} ADVERTENCIAS (revisar):")
        for w in warns:
            print(f"     [{w['area']}] {w['message']}")

    print(f"\n  Acciones recomendadas:")
    if any("UNIQUE" in e["message"] or "duplicados" in e["message"] for e in errors):
        print("  1. Añadir UNIQUE constraint en espn.nba_player_boxscores:")
        print("     ALTER TABLE espn.nba_player_boxscores")
        print("     ADD CONSTRAINT uq_player_boxscore UNIQUE (game_id, player_id, team_tricode);")

    if any("mapping" in e["message"].lower() for e in errors + warns):
        print("  2. Mejorar cobertura de game_id_mapping:")
        print("     cd Scrapping/nba && python fix_game_id_mapping.py")

    if any("ml_ready" in e["message"] for e in errors + warns):
        print("  3. Re-ejecutar ETL para llenar partidos faltantes:")
        print("     cd ML && python -m src.etl.build_features")

    print(f"\n  Auditoría completada: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Auditoría exhaustiva de DB HAW")
    parser.add_argument("--schema", help="Solo auditar este schema")
    parser.add_argument("--skip-nulls", action="store_true",
                        help="Omitir análisis de NULLs (más rápido)")
    args = parser.parse_args()

    database_url = db_config.get_database_url()
    espn_schema  = db_config.get_schema("espn")
    ml_schema    = db_config.get_schema("ml")
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    all_schemas = [espn_schema, ml_schema, "app", "sys"]
    schemas = [args.schema] if args.schema else all_schemas

    # Filtrar solo los que existen
    existing = pd.read_sql(text("""
        SELECT schema_name FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema','pg_catalog','pg_toast','public')
    """), engine)["schema_name"].tolist()

    schemas = [s for s in schemas if s in existing]
    print(f"\n  Schemas en DB: {existing}")
    print(f"  Auditando:     {schemas}")

    check_inventory(engine, schemas)
    check_constraints(engine, schemas)
    check_duplicates(engine, espn_schema, ml_schema)

    if not args.skip_nulls:
        check_nulls(engine, schemas)
    else:
        print("\n  [skip-nulls] Análisis de NULLs omitido.")

    check_value_ranges(engine, espn_schema, ml_schema)
    check_referential_integrity(engine, espn_schema, ml_schema)
    check_pipeline_consistency(engine, espn_schema, ml_schema)
    print_summary()


if __name__ == "__main__":
    main()
