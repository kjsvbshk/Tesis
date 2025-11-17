#!/usr/bin/env python3
"""
Script para crear la tabla ml_ready_games en el esquema ML (Fase 1)
Consolida datos de partidos con columnas base y espacio para features
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config


def create_ml_ready_games_table():
    """
    Crea la tabla ml_ready_games en el esquema ML
    """
    database_url = db_config.get_database_url()
    ml_schema = db_config.get_schema("ml")
    espn_schema = db_config.get_schema("espn")
    
    print("=" * 60)
    print(f"🔧 Creando Tabla ml_ready_games (Fase 1)")
    print("=" * 60)
    print(f"Base de datos: Neon (cloud)")
    print(f"Esquema ML: {ml_schema}")
    print(f"Esquema ESPN: {espn_schema}")
    print()
    
    # Crear engine
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            # Establecer search_path
            conn.execute(text(f"SET search_path TO {ml_schema}, {espn_schema}, public"))
            conn.commit()
            
            # Verificar si la tabla ya existe
            check_table_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = :schema_name
                AND table_name = 'ml_ready_games'
            """)
            result = conn.execute(check_table_query, {"schema_name": ml_schema})
            table_exists = result.fetchone() is not None
            
            if table_exists:
                print(f"⚠️  La tabla '{ml_schema}.ml_ready_games' ya existe")
                response = input("   ¿Deseas eliminarla y recrearla? (s/N): ")
                if response.lower() != 's':
                    print("   Operación cancelada")
                    return
                print(f"   Eliminando tabla existente...")
                conn.execute(text(f"DROP TABLE IF EXISTS {ml_schema}.ml_ready_games CASCADE"))
                conn.commit()
                print(f"   ✅ Tabla eliminada")
                print()
            
            # Crear tabla ml_ready_games
            print("📝 Creando tabla ml_ready_games...")
            
            create_table_query = text(f"""
                CREATE TABLE IF NOT EXISTS {ml_schema}.ml_ready_games (
                    game_id bigint PRIMARY KEY,
                    fecha date,
                    home_team varchar,
                    away_team varchar,
                    home_score double precision,
                    away_score double precision,
                    home_win boolean,
                    point_diff double precision,
                    
                    -- stats base (copiar nombres de tu tabla games)
                    home_fg_pct double precision,
                    home_3p_pct double precision,
                    home_ft_pct double precision,
                    home_reb double precision,
                    home_ast double precision,
                    home_stl double precision,
                    home_blk double precision,
                    home_to double precision,
                    home_pts double precision,
                    
                    away_fg_pct double precision,
                    away_3p_pct double precision,
                    away_ft_pct double precision,
                    away_reb double precision,
                    away_ast double precision,
                    away_stl double precision,
                    away_blk double precision,
                    away_to double precision,
                    away_pts double precision,
                    
                    -- diffs ya calculados en games
                    net_rating_diff double precision,
                    reb_diff double precision,
                    ast_diff double precision,
                    tov_diff double precision,
                    
                    -- placeholders para rolling features
                    home_ppg_last5 double precision,
                    away_ppg_last5 double precision,
                    home_net_rating_last10 double precision,
                    away_net_rating_last10 double precision,
                    home_rest_days integer,
                    away_rest_days integer,
                    home_injuries_count integer,
                    away_injuries_count integer,
                    implied_prob_home double precision,
                    implied_prob_away double precision,
                    
                    created_at timestamp with time zone default now()
                );
            """)
            
            conn.execute(create_table_query)
            conn.commit()
            print("  ✅ Tabla 'ml_ready_games' creada exitosamente")
            print()
            
            # Crear índices útiles
            print("📊 Creando índices...")
            indexes = [
                f"CREATE INDEX IF NOT EXISTS idx_ml_ready_games_fecha ON {ml_schema}.ml_ready_games(fecha)",
                f"CREATE INDEX IF NOT EXISTS idx_ml_ready_games_home_team ON {ml_schema}.ml_ready_games(home_team)",
                f"CREATE INDEX IF NOT EXISTS idx_ml_ready_games_away_team ON {ml_schema}.ml_ready_games(away_team)",
            ]
            
            for index_sql in indexes:
                conn.execute(text(index_sql))
            
            conn.commit()
            print("  ✅ Índices creados")
            print()
            
            print("=" * 60)
            print("✅ Tabla ml_ready_games creada exitosamente")
            print("=" * 60)
            print()
            
    except Exception as e:
        print(f"❌ Error al crear tabla: {e}")
        import traceback
        traceback.print_exc()
        raise


def populate_ml_ready_games():
    """
    Pobla la tabla ml_ready_games con datos desde espn.games
    """
    database_url = db_config.get_database_url()
    ml_schema = db_config.get_schema("ml")
    espn_schema = db_config.get_schema("espn")
    
    print("=" * 60)
    print(f"📥 Poblando Tabla ml_ready_games desde {espn_schema}.games")
    print("=" * 60)
    print()
    
    # Crear engine
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            # Establecer search_path
            conn.execute(text(f"SET search_path TO {ml_schema}, {espn_schema}, public"))
            conn.commit()
            
            # Primero, verificar qué columnas existen en espn.games
            print("🔍 Verificando estructura de espn.games...")
            check_columns_query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = :schema_name 
                AND table_name = 'games'
                ORDER BY ordinal_position
            """)
            result = conn.execute(check_columns_query, {"schema_name": espn_schema})
            columns = {row[0]: row[1] for row in result.fetchall()}
            
            if not columns:
                print(f"❌ No se encontró la tabla {espn_schema}.games")
                return
            
            print(f"   ✅ Encontradas {len(columns)} columnas en {espn_schema}.games")
            print(f"   Columnas: {', '.join(list(columns.keys())[:10])}...")
            print()
            
            # Verificar cuántos registros hay en games
            count_query = text(f"SELECT COUNT(*) FROM {espn_schema}.games")
            result = conn.execute(count_query)
            total_games = result.fetchone()[0]
            print(f"📊 Total de partidos en {espn_schema}.games: {total_games}")
            print()
            
            # Construir el INSERT adaptándose a las columnas disponibles
            # Mapeo de columnas esperadas vs disponibles
            column_mapping = {
                'game_id': 'game_id',
                'fecha': 'fecha',
                'home_team': 'home_team',
                'away_team': 'away_team',
                'home_score': 'home_score',
                'away_score': 'away_score',
                'home_win': 'home_win',
                'point_diff': 'point_diff',
                'home_fg_pct': 'home_fg_pct',
                'home_3p_pct': 'home_3p_pct',
                'home_ft_pct': 'home_ft_pct',
                'home_reb': 'home_reb',
                'home_ast': 'home_ast',
                'home_stl': 'home_stl',
                'home_blk': 'home_blk',
                'home_to': 'home_to',
                'home_pts': 'home_pts',
                'away_fg_pct': 'away_fg_pct',
                'away_3p_pct': 'away_3p_pct',
                'away_ft_pct': 'away_ft_pct',
                'away_reb': 'away_reb',
                'away_ast': 'away_ast',
                'away_stl': 'away_stl',
                'away_blk': 'away_blk',
                'away_to': 'away_to',
                'away_pts': 'away_pts',
                'net_rating_diff': 'net_rating_diff',
                'reb_diff': 'reb_diff',
                'ast_diff': 'ast_diff',
                'tov_diff': 'tov_diff',
            }
            
            # Verificar qué columnas están disponibles
            available_cols = []
            missing_cols = []
            
            for target_col, source_col in column_mapping.items():
                if source_col in columns:
                    available_cols.append((target_col, source_col))
                else:
                    missing_cols.append(source_col)
            
            if missing_cols:
                print(f"⚠️  Columnas no encontradas en {espn_schema}.games:")
                for col in missing_cols:
                    print(f"   - {col}")
                print()
                print("   Se insertarán como NULL las columnas faltantes")
                print()
            
            # Construir SELECT con las columnas disponibles y casts necesarios
            select_cols = []
            insert_cols = []
            
            # Mapeo de tipos de datos esperados vs disponibles
            type_casts = {
                'home_win': 'boolean',  # Necesita cast si es bigint
                'point_diff': 'double precision',
            }
            
            for target_col, source_col in available_cols:
                insert_cols.append(target_col)
                
                # Aplicar cast si es necesario
                if target_col in type_casts:
                    expected_type = type_casts[target_col]
                    actual_type = columns.get(source_col, '')
                    
                    # Si home_win es bigint pero esperamos boolean, calcularlo
                    if target_col == 'home_win' and actual_type in ('bigint', 'integer'):
                        # Calcular home_win desde home_score y away_score
                        select_cols.append("(home_score > away_score)::boolean")
                    elif target_col == 'home_win' and actual_type == 'boolean':
                        select_cols.append(f"{source_col}")
                    else:
                        select_cols.append(f"{source_col}::{expected_type}")
                else:
                    select_cols.append(f"{source_col}")
            
            # Agregar columnas que no existen (serán NULL)
            for target_col, source_col in column_mapping.items():
                if source_col not in columns:
                    insert_cols.append(target_col)
                    select_cols.append("NULL")
            
            # Construir query INSERT
            insert_query = f"""
                INSERT INTO {ml_schema}.ml_ready_games ({', '.join(insert_cols)})
                SELECT {', '.join(select_cols)}
                FROM {espn_schema}.games
                ON CONFLICT (game_id) DO NOTHING
            """
            
            print("📥 Insertando datos...")
            result = conn.execute(text(insert_query))
            conn.commit()
            
            # Verificar cuántos registros se insertaron
            count_query = text(f"SELECT COUNT(*) FROM {ml_schema}.ml_ready_games")
            result = conn.execute(count_query)
            inserted_count = result.fetchone()[0]
            
            print(f"✅ Datos insertados exitosamente")
            print(f"   Total de registros en ml_ready_games: {inserted_count}")
            print()
            
            # Mostrar muestra de datos
            print("📋 Muestra de datos (primeros 5 registros):")
            sample_query = text(f"""
                SELECT game_id, fecha, home_team, away_team, 
                       home_score, away_score, home_win, point_diff
                FROM {ml_schema}.ml_ready_games 
                ORDER BY fecha DESC 
                LIMIT 5
            """)
            result = conn.execute(sample_query)
            rows = result.fetchall()
            
            if rows:
                print()
                for row in rows:
                    print(f"   Game ID: {row[0]}, Fecha: {row[1]}, {row[2]} vs {row[3]}, "
                          f"Score: {row[4]}-{row[5]}, Home Win: {row[6]}, Diff: {row[7]}")
            else:
                print("   (No hay datos)")
            
            print()
            print("=" * 60)
            print("✅ Tabla ml_ready_games poblada exitosamente")
            print("=" * 60)
            print()
            
    except Exception as e:
        print(f"❌ Error al poblar tabla: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Crear y poblar tabla ml_ready_games")
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Solo crear la tabla, no poblar"
    )
    parser.add_argument(
        "--populate-only",
        action="store_true",
        help="Solo poblar la tabla (asume que ya existe)"
    )
    
    args = parser.parse_args()
    
    if args.populate_only:
        populate_ml_ready_games()
    elif args.create_only:
        create_ml_ready_games_table()
    else:
        # Por defecto, crear y poblar
        create_ml_ready_games_table()
        populate_ml_ready_games()


if __name__ == "__main__":
    main()

