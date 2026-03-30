"""
Inspeccionar esquema completo de la base de datos Neon.

Muestra todos los schemas, tablas, columnas y conteos
para dar contexto completo del modelo en produccion.

Uso:
    cd Scrapping/nba
    python inspect_schema.py
    python inspect_schema.py --schema espn
    python inspect_schema.py --schema ml
"""

import argparse
from load_data import Config
import psycopg2


SCHEMAS = ["espn", "ml", "app", "sys"]


def inspect_schema(schemas=None):
    config = Config()
    conn = psycopg2.connect(**config.db_config)
    cur = conn.cursor()

    if schemas is None:
        schemas = SCHEMAS

    # Descubrir schemas que realmente existen
    cur.execute("""
        SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast', 'public')
        ORDER BY schema_name;
    """)
    existing = [row[0] for row in cur.fetchall()]
    print(f"Schemas en la base de datos: {existing}\n")

    schemas_to_inspect = [s for s in schemas if s in existing]
    if not schemas_to_inspect:
        print("Ningun schema solicitado existe.")
        conn.close()
        return

    for schema in schemas_to_inspect:
        # Listar tablas
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """, (schema,))
        tables = [row[0] for row in cur.fetchall()]

        print("=" * 60)
        print(f"  Schema: {schema} ({len(tables)} tablas)")
        print("=" * 60)

        if not tables:
            print("  (vacio)\n")
            continue

        for table in tables:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
            """, (schema, table))
            columns = cur.fetchall()

            try:
                cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                count = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                count = "?"

            print(f"\n  {schema}.{table} ({count} registros)")
            print(f"  {'-' * 50}")
            for col_name, data_type, nullable, default in columns:
                null_flag = "" if nullable == "YES" else " NOT NULL"
                default_str = f" DEFAULT {default}" if default else ""
                print(f"    {col_name:<35} {data_type}{null_flag}{default_str}")

        # Listar vistas
        cur.execute("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = %s
            ORDER BY table_name;
        """, (schema,))
        views = [row[0] for row in cur.fetchall()]
        if views:
            print(f"\n  Vistas en {schema}: {views}")

        print()

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspeccionar esquema de Neon PostgreSQL")
    parser.add_argument("--schema", help="Schema especifico (espn, ml, app, sys). Sin argumento muestra todos.")
    args = parser.parse_args()

    if args.schema:
        inspect_schema([args.schema])
    else:
        inspect_schema()
