#!/usr/bin/env python3
"""
Script para analizar campos NULL en ml_ready_games
Identifica qué columnas tienen NULLs y por qué
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config


def analyze_nulls():
    """Analiza campos NULL en ml_ready_games"""
    database_url = db_config.get_database_url()
    ml_schema = db_config.get_schema("ml")
    espn_schema = db_config.get_schema("espn")
    
    print("=" * 60)
    print("🔍 Análisis de Campos NULL en ml_ready_games")
    print("=" * 60)
    print()
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    
    try:
        with engine.connect() as conn:
            conn.execute(text(f"SET search_path TO {ml_schema}, {espn_schema}, public"))
            conn.commit()
            
            # 1. Obtener todas las columnas de ml_ready_games
            print("📋 Paso 1: Columnas en ml_ready_games")
            print("-" * 60)
            columns_query = text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'ml' 
                AND table_name = 'ml_ready_games'
                ORDER BY ordinal_position
            """)
            result = conn.execute(columns_query)
            ml_columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result.fetchall()}
            print(f"   Total de columnas: {len(ml_columns)}")
            print()
            
            # 2. Contar NULLs por columna
            print("📊 Paso 2: Análisis de NULLs por columna")
            print("-" * 60)
            
            total_rows_query = text("SELECT COUNT(*) FROM ml.ml_ready_games")
            result = conn.execute(total_rows_query)
            total_rows = result.fetchone()[0]
            print(f"   Total de registros: {total_rows}")
            print()
            
            null_analysis = []
            for col_name in ml_columns.keys():
                if col_name == 'created_at':  # Skip created_at
                    continue
                    
                null_query = text(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT({col_name}) as non_null,
                        COUNT(*) - COUNT({col_name}) as null_count,
                        ROUND(100.0 * (COUNT(*) - COUNT({col_name})) / COUNT(*), 2) as null_pct
                    FROM ml.ml_ready_games
                """)
                result = conn.execute(null_query)
                row = result.fetchone()
                
                if row[2] > 0:  # Si hay NULLs
                    null_analysis.append({
                        'column': col_name,
                        'null_count': row[2],
                        'null_pct': row[3],
                        'non_null': row[1]
                    })
            
            # Ordenar por porcentaje de NULLs
            null_analysis.sort(key=lambda x: x['null_pct'], reverse=True)
            
            print("   Columnas con NULLs:")
            print()
            for item in null_analysis:
                print(f"   {item['column']:<35} NULLs: {item['null_count']:>5} ({item['null_pct']:>6.2f}%)")
            print()
            
            # 3. Verificar qué columnas existen en espn.games
            print("🔍 Paso 3: Columnas disponibles en espn.games")
            print("-" * 60)
            espn_columns_query = text("""
                SELECT column_name, data_type
                FROM information_schema.columns 
                WHERE table_schema = 'espn' 
                AND table_name = 'games'
                ORDER BY ordinal_position
            """)
            result = conn.execute(espn_columns_query)
            espn_columns = {row[0]: row[1] for row in result.fetchall()}
            print(f"   Total de columnas en espn.games: {len(espn_columns)}")
            print(f"   Columnas: {', '.join(list(espn_columns.keys())[:20])}...")
            print()
            
            # 4. Comparar columnas esperadas vs disponibles
            print("📝 Paso 4: Comparación de columnas")
            print("-" * 60)
            
            # Columnas que esperamos copiar
            expected_columns = [
                'game_id', 'fecha', 'home_team', 'away_team',
                'home_score', 'away_score', 'home_win', 'point_diff',
                'home_fg_pct', 'home_3p_pct', 'home_ft_pct', 'home_reb', 
                'home_ast', 'home_stl', 'home_blk', 'home_to', 'home_pts',
                'away_fg_pct', 'away_3p_pct', 'away_ft_pct', 'away_reb',
                'away_ast', 'away_stl', 'away_blk', 'away_to', 'away_pts',
                'net_rating_diff', 'reb_diff', 'ast_diff', 'tov_diff'
            ]
            
            missing_in_espn = []
            available_in_espn = []
            
            for col in expected_columns:
                if col in espn_columns:
                    available_in_espn.append(col)
                else:
                    missing_in_espn.append(col)
            
            print("   ✅ Columnas disponibles en espn.games:")
            for col in available_in_espn:
                print(f"      - {col:<30} ({espn_columns[col]})")
            print()
            
            if missing_in_espn:
                print("   ❌ Columnas NO encontradas en espn.games:")
                for col in missing_in_espn:
                    print(f"      - {col}")
                print()
            
            # 5. Verificar si hay columnas similares (variaciones de nombre)
            print("🔎 Paso 5: Buscando columnas similares")
            print("-" * 60)
            
            # Mapeo de posibles variaciones
            variations = {
                'home_fg_pct': ['home_fg%', 'home_fg_pct', 'home_field_goal_pct'],
                'home_3p_pct': ['home_3p%', 'home_3p_pct', 'home_three_point_pct'],
                'home_ft_pct': ['home_ft%', 'home_ft_pct', 'home_free_throw_pct'],
                'home_reb': ['home_reb', 'home_rebounds', 'home_reb_total'],
                'home_ast': ['home_ast', 'home_assists', 'home_ast_total'],
                'home_stl': ['home_stl', 'home_steals', 'home_stl_total'],
                'home_blk': ['home_blk', 'home_blocks', 'home_blk_total'],
                'home_to': ['home_to', 'home_turnovers', 'home_to_total', 'home_tov'],
                'home_pts': ['home_pts', 'home_points', 'home_score'],
            }
            
            for missing_col in missing_in_espn:
                if missing_col in variations:
                    print(f"   Buscando variaciones de '{missing_col}':")
                    for variant in variations[missing_col]:
                        if variant in espn_columns:
                            print(f"      ✅ Encontrado: '{variant}' (tipo: {espn_columns[variant]})")
                    print()
            
            # 6. Verificar columnas que deberían tener datos pero tienen NULLs
            print("📋 Paso 6: Columnas base con NULLs (no deberían tener)")
            print("-" * 60)
            
            base_columns = [
                'home_fg_pct', 'home_3p_pct', 'home_ft_pct', 'home_reb', 
                'home_ast', 'home_stl', 'home_blk', 'home_to', 'home_pts',
                'away_fg_pct', 'away_3p_pct', 'away_ft_pct', 'away_reb',
                'away_ast', 'away_stl', 'away_blk', 'away_to', 'away_pts',
                'net_rating_diff', 'reb_diff', 'ast_diff', 'tov_diff'
            ]
            
            base_with_nulls = []
            for col in base_columns:
                null_info = next((x for x in null_analysis if x['column'] == col), None)
                if null_info and null_info['null_count'] > 0:
                    base_with_nulls.append(null_info)
            
            if base_with_nulls:
                print("   ⚠️  Columnas base con NULLs:")
                for item in base_with_nulls:
                    print(f"      {item['column']:<30} NULLs: {item['null_count']:>5} ({item['null_pct']:>6.2f}%)")
            else:
                print("   ✅ Todas las columnas base tienen datos")
            print()
            
            # 7. Verificar si hay columnas adicionales en espn.games que no estamos usando
            print("📋 Paso 7: Columnas adicionales en espn.games no copiadas")
            print("-" * 60)
            
            all_espn_cols = set(espn_columns.keys())
            copied_cols = set(available_in_espn)
            unused_cols = all_espn_cols - copied_cols
            
            if unused_cols:
                print(f"   Columnas disponibles pero no copiadas ({len(unused_cols)}):")
                for col in sorted(unused_cols):
                    print(f"      - {col:<30} ({espn_columns[col]})")
            else:
                print("   ✅ Todas las columnas relevantes fueron copiadas")
            print()
            
            # 7. Resumen y recomendaciones
            print("=" * 60)
            print("📝 Resumen y Recomendaciones")
            print("=" * 60)
            print()
            
            if missing_in_espn:
                print("⚠️  Columnas faltantes que necesitan ser calculadas o adaptadas:")
                for col in missing_in_espn:
                    null_info = next((x for x in null_analysis if x['column'] == col), None)
                    if null_info:
                        print(f"   - {col}: {null_info['null_pct']:.2f}% NULL")
                    else:
                        print(f"   - {col}: No encontrada en espn.games")
                print()
            
            print("💡 Próximos pasos:")
            print("   1. Revisar si las columnas faltantes se pueden calcular")
            print("   2. Verificar si existen con nombres diferentes")
            print("   3. Adaptar el script de población para calcular valores")
            print()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    analyze_nulls()

