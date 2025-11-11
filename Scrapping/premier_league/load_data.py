#!/usr/bin/env python3
"""
Sistema de Carga Dinámica de Datos Premier League a PostgreSQL
==============================================================

Este script analiza automáticamente la estructura de los datos y crea
las tablas necesarias en PostgreSQL usando COPY nativo para máxima velocidad.

Características:
- Detección automática de tipos de datos
- Detección automática de Primary Keys
- Uso de COPY nativo de PostgreSQL
- Skip de duplicados
"""

import os
import yaml
import pandas as pd
import psycopg2
from psycopg2 import sql
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import tempfile
from loguru import logger
import sys

# Agregar utils al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.logger import setup_logger

# Configurar logger
setup_logger()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

class Config:
    """Configuración del sistema de carga"""
    
    def __init__(self):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Parsear DATABASE_URL (soporta URLs con parámetros de query)
        db_url = config['DATABASE_URL']
        # Remover parámetros de query si existen
        if '?' in db_url:
            db_url_base = db_url.split('?')[0]
        else:
            db_url_base = db_url
        
        # postgresql://user:password@host:port/database
        parts = db_url_base.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        host_port = host_db[0].split(':')
        
        self.db_config = {
            'user': user_pass[0],
            'password': user_pass[1],
            'host': host_port[0],
            'port': int(host_port[1]),
            'database': host_db[1]
        }
        
        # Agregar parámetros SSL si están en la URL original
        if 'sslmode=require' in db_url:
            self.db_config['sslmode'] = 'require'
        if 'channel_binding=require' in db_url:
            self.db_config['channel_binding'] = 'require'
        
        self.schema = config.get('DB_SCHEMA', 'espn')
        self.data_dir = Path('data')

# ============================================================================
# ANALIZADOR DE DATOS
# ============================================================================

class DataAnalyzer:
    """Analiza la estructura de los archivos de datos"""
    
    def __init__(self, config: Config):
        self.config = config
        self.metadata = {}
    
    def analyze_all_files(self) -> Dict:
        """Analiza todos los archivos de datos y extrae metadata"""
        logger.info("Analizando estructura de datos...")
        
        # Analizar dataset consolidado
        self._analyze_processed_dataset()
        
        # Analizar archivos raw
        self._analyze_standings()
        self._analyze_team_stats()
        self._analyze_match_stats()
        self._analyze_player_stats()
        self._analyze_injuries()
        self._analyze_odds()
        
        logger.info(f"{len(self.metadata)} tablas detectadas")
        return self.metadata
    
    def _analyze_processed_dataset(self):
        """Analizar premier_league_full_dataset.csv"""
        file_path = self.config.data_dir / 'processed' / 'premier_league_full_dataset.csv'
        
        if not file_path.exists():
            logger.warning(f"{file_path} no encontrado")
            return
        
        df = pd.read_csv(file_path, nrows=100)  # Muestra para análisis
        
        self.metadata['matches'] = {
            'source_file': str(file_path),
            'source_type': 'csv',
            'table_name': 'matches',
            'columns': self._infer_columns(df),
            'primary_key': 'match_id',  # ID único del partido
            'indexes': ['date', 'home_team', 'away_team', 'season'],
            'row_count': len(pd.read_csv(file_path))
        }
        
        logger.info(f"  matches: {self.metadata['matches']['row_count']} registros")
    
    def _analyze_standings(self):
        """Analizar standings CSV files"""
        standings_dir = self.config.data_dir / 'raw' / 'standings'
        
        if not standings_dir.exists():
            return
        
        csv_files = list(standings_dir.glob('*.csv'))
        if not csv_files:
            return
        
        # Leer TODOS los archivos completos para obtener estructura real
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        
        # Combinar todos los DataFrames para análisis completo
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Inferir columnas desde TODOS los datos (no solo muestra)
        sample_columns = self._infer_columns(df_combined)
        
        # Contar total de registros
        total_rows = len(df_combined)
        
        self.metadata['standings'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'standings',
            'columns': sample_columns,
            'primary_key': None,  # Composite key: season + date + team_name
            'indexes': ['season', 'date', 'team_name', 'position'],
            'row_count': total_rows
        }
        
        logger.info(f"  standings: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_team_stats(self):
        """Analizar team_stats CSV files"""
        team_stats_dir = self.config.data_dir / 'raw' / 'team_stats'
        
        if not team_stats_dir.exists():
            return
        
        csv_files = list(team_stats_dir.glob('*.csv'))
        if not csv_files:
            return
        
        # Leer TODOS los archivos para obtener estructura completa
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        
        # Combinar todos los DataFrames para análisis completo
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Contar total de registros
        total_rows = len(df_combined)
        
        # Inferir columnas desde TODOS los datos (no solo muestra)
        columns_info = self._infer_columns(df_combined)
        
        self.metadata['team_stats'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'team_stats',
            'columns': columns_info,
            'primary_key': None,  # Composite key: season + team_name
            'indexes': ['season', 'team_name', 'date'],
            'row_count': total_rows
        }
        
        logger.info(f"  team_stats: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_match_stats(self):
        """Analizar match_stats CSV files"""
        match_stats_dir = self.config.data_dir / 'raw' / 'match_stats'
        
        if not match_stats_dir.exists():
            return
        
        csv_files = list(match_stats_dir.glob('*.csv'))
        if not csv_files:
            return
        
        # Leer TODOS los archivos completos para obtener estructura real
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        
        # Combinar todos los DataFrames para análisis completo
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Inferir columnas desde TODOS los datos (no solo muestra)
        columns_info = self._infer_columns(df_combined)
        
        # Contar total de registros
        total_rows = len(df_combined)
        
        self.metadata['match_stats'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'match_stats',
            'columns': columns_info,
            'primary_key': 'match_id',  # ID único del partido
            'indexes': ['match_id', 'date', 'home_team', 'away_team'],
            'row_count': total_rows
        }
        
        logger.info(f"  match_stats: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_player_stats(self):
        """Analizar player_stats CSV files"""
        player_stats_dir = self.config.data_dir / 'raw' / 'player_stats'
        
        if not player_stats_dir.exists():
            return
        
        csv_files = list(player_stats_dir.glob('*.csv'))
        if not csv_files:
            return
        
        # Leer TODOS los archivos completos para obtener estructura real
        dfs = []
        for csv_file in csv_files:
            df = pd.read_csv(csv_file)
            dfs.append(df)
        
        # Combinar todos los DataFrames para análisis completo
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Inferir columnas desde TODOS los datos (no solo muestra)
        sample_columns = self._infer_columns(df_combined)
        
        # Contar total de registros
        total_rows = len(df_combined)
        
        self.metadata['player_stats'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'player_stats',
            'columns': sample_columns,
            'primary_key': None,  # Composite key: season + player_name + team_name
            'indexes': ['season', 'player_name', 'team_name', 'category'],
            'row_count': total_rows
        }
        
        logger.info(f"  player_stats: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_injuries(self):
        """Analizar injuries CSV files"""
        injuries_dir = self.config.data_dir / 'raw' / 'injuries'
        
        if not injuries_dir.exists():
            return
        
        csv_files = list(injuries_dir.glob('*.csv'))
        if not csv_files:
            return
        
        # Usar el archivo más reciente
        latest_file = max(csv_files, key=lambda p: p.stat().st_mtime)
        df = pd.read_csv(latest_file)
        
        self.metadata['injuries'] = {
            'source_file': str(latest_file),
            'source_type': 'csv',
            'table_name': 'injuries',
            'columns': self._infer_columns(df),
            'primary_key': None,  # Composite key: date + player_name + team_name
            'indexes': ['date', 'team_name', 'player_name', 'status'],
            'row_count': len(df),
            'note': 'Datos actuales - se reemplazan en cada carga'
        }
        
        logger.info(f"  injuries: {len(df)} registros (archivo más reciente)")
    
    def _analyze_odds(self):
        """Analizar odds JSON files"""
        import json
        odds_dir = self.config.data_dir / 'raw' / 'odds'
        
        if not odds_dir.exists():
            return
        
        json_files = list(odds_dir.glob('*.json'))
        if not json_files:
            return
        
        # Usar el archivo más reciente
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            return
        
        # Convertir a DataFrame para análisis
        df = pd.DataFrame(data)
        
        # Columnas especiales para JSON
        columns = self._infer_columns(df)
        if 'bookmakers' in columns:
            columns['bookmakers']['type'] = 'JSONB'
        
        self.metadata['odds'] = {
            'source_file': str(latest_file),
            'source_type': 'json',
            'table_name': 'odds',
            'columns': columns,
            'primary_key': 'game_id',
            'indexes': ['date', 'home_team', 'away_team', 'commence_time'],
            'row_count': len(data),
            'note': 'Datos actuales - se reemplazan en cada carga'
        }
        
        logger.info(f"  odds: {len(data)} registros (archivo más reciente)")
    
    def _infer_columns(self, df: pd.DataFrame) -> Dict:
        """Inferir tipos de columnas desde DataFrame"""
        columns = {}
        
        for col_name, dtype in df.dtypes.items():
            # Sanitizar nombre de columna
            clean_name = self._sanitize_column_name(col_name)
            
            # Inferir tipo SQL
            sql_type = self._infer_sql_type(col_name, dtype, df[col_name])
            
            columns[clean_name] = {
                'type': sql_type,
                'nullable': True,  # Todas las columnas son nullable excepto PK
                'original_name': col_name
            }
        
        return columns
    
    def _sanitize_column_name(self, name: str) -> str:
        """Sanitizar nombre de columna para SQL"""
        # Reemplazar espacios y caracteres especiales
        name = name.replace(' ', '_').lower()
        name = name.replace('%', '_pct')
        name = name.replace('-', '_')
        
        # Si empieza con número, agregar prefijo
        if name and name[0].isdigit():
            name = f"col_{name}"
        
        # Remover caracteres no válidos
        name = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        
        return name
    
    def _infer_sql_type(self, col_name: str, dtype, series: pd.Series) -> str:
        """Inferir tipo SQL desde pandas dtype y datos reales"""
        # Tipos específicos conocidos
        if 'id' in col_name.lower():
            return 'VARCHAR(255)'
        
        if 'date' in col_name.lower():
            # Intentar convertir a fecha para verificar
            try:
                pd.to_datetime(series.dropna().head(10), errors='raise')
                return 'DATE'
            except:
                return 'VARCHAR(255)'
        
        # Columnas que son promedios o porcentajes (deben ser DOUBLE PRECISION)
        if any(keyword in col_name.lower() for keyword in ['_per_', '_pct', '_percent', '_avg', '_average', 'per_game']):
            return 'DOUBLE PRECISION'
        
        # Verificar datos reales para inferir tipo numérico
        # Intentar convertir a numérico
        numeric_series = pd.to_numeric(series.dropna(), errors='coerce')
        non_null_numeric = numeric_series.dropna()
        
        has_decimals = False
        if len(non_null_numeric) > 0:
            # Hay valores numéricos válidos
            # Verificar si tiene decimales
            has_decimals = (non_null_numeric % 1 != 0).any()
            
            if has_decimals:
                return 'DOUBLE PRECISION'
            else:
                # Es entero, verificar rango
                max_val = non_null_numeric.max()
                min_val = non_null_numeric.min()
                if min_val >= -2147483648 and max_val <= 2147483647:
                    return 'INTEGER'
                else:
                    return 'BIGINT'
        
        # Columnas de goles/score que son enteros (no promedios)
        if ('score' in col_name.lower() or 'goals' in col_name.lower()) and 'per' not in col_name.lower():
            # Verificar si realmente es entero o float
            if pd.api.types.is_float_dtype(dtype) or (len(non_null_numeric) > 0 and has_decimals):
                return 'DOUBLE PRECISION'
            return 'INTEGER'
        
        if 'win' in col_name.lower() or 'diff' in col_name.lower():
            # Verificar si realmente es entero o float
            if pd.api.types.is_float_dtype(dtype) or (len(non_null_numeric) > 0 and has_decimals):
                return 'DOUBLE PRECISION'
            return 'INTEGER'
        
        # Inferir desde dtype
        if pd.api.types.is_integer_dtype(dtype):
            return 'INTEGER'
        elif pd.api.types.is_float_dtype(dtype):
            return 'DOUBLE PRECISION'
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return 'DATE'
        elif pd.api.types.is_bool_dtype(dtype):
            return 'BOOLEAN'
        else:
            # String - calcular longitud máxima desde datos reales
            non_null_series = series.dropna()
            if len(non_null_series) > 0:
                max_len = non_null_series.astype(str).str.len().max()
                if pd.isna(max_len) or max_len < 50:
                    return 'VARCHAR(255)'
                elif max_len < 500:
                    return 'VARCHAR(500)'
                else:
                    return 'TEXT'
            else:
                return 'VARCHAR(255)'

# ============================================================================
# GENERADOR DE DDL
# ============================================================================

class DDLGenerator:
    """Genera DDL statements para crear tablas"""
    
    def __init__(self, metadata: Dict, schema: str):
        self.metadata = metadata
        self.schema = schema
    
    def generate_ddl(self) -> List[str]:
        """Generar todos los statements DDL"""
        statements = []
        
        # Crear schema si no existe
        statements.append(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
        
        # Crear tablas
        for table_name, table_meta in self.metadata.items():
            statements.append(self._generate_create_table(table_name, table_meta))
            
            # Crear índices
            if 'indexes' in table_meta:
                for idx_col in table_meta['indexes']:
                    statements.append(
                        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{idx_col} "
                        f"ON {self.schema}.{table_name}({idx_col});"
                    )
        
        return statements
    
    def _generate_create_table(self, table_name: str, table_meta: Dict) -> str:
        """Generar CREATE TABLE statement"""
        columns_def = []
        
        for col_name, col_info in table_meta['columns'].items():
            col_type = col_info['type']
            # Todas las columnas son nullable excepto PK
            if table_meta.get('primary_key') == col_name:
                nullable = 'NOT NULL'
            else:
                nullable = 'NULL'
            columns_def.append(f"    {col_name} {col_type} {nullable}")
        
        # Primary key
        pk = table_meta.get('primary_key')
        if pk:
            # La PK ya viene sanitizada en los metadatos
            pk_col = pk
            columns_def.append(f"    PRIMARY KEY ({pk_col})")
        
        return f"""
CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (
{','.join(columns_def)}
);
""".strip()

# ============================================================================
# CARGADOR DE DATOS (COPY NATIVO)
# ============================================================================

class DataLoader:
    """Carga datos usando COPY nativo de PostgreSQL"""
    
    def __init__(self, config: Config, metadata: Dict):
        self.config = config
        self.metadata = metadata
        self.conn = None
    
    def connect(self):
        """Conectar a PostgreSQL"""
        try:
            self.conn = psycopg2.connect(**self.config.db_config)
            logger.info("Conectado a PostgreSQL")
        except psycopg2.OperationalError as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            logger.error("Asegúrate de que la base de datos exista y PostgreSQL esté corriendo")
            raise
    
    def disconnect(self):
        """Desconectar de PostgreSQL"""
        if self.conn:
            self.conn.close()
            logger.info("Desconectado de PostgreSQL")
    
    def execute_ddl(self, statements: List[str]):
        """Ejecutar statements DDL"""
        logger.info("Ejecutando DDL...")
        
        cursor = self.conn.cursor()
        
        for stmt in statements:
            try:
                cursor.execute(stmt)
                self.conn.commit()
            except Exception as e:
                logger.warning(f"Error ejecutando DDL: {e}")
                self.conn.rollback()
        
        cursor.close()
        logger.info("DDL ejecutado")
    
    def load_all_data(self):
        """Cargar todos los datos"""
        logger.info("Cargando datos...")
        
        for table_name, table_meta in self.metadata.items():
            logger.info(f"Cargando {table_name}...")
            
            try:
                # Obtener conteo antes de cargar
                count_before = self._count_records(table_name)
                
                if table_meta['source_type'] == 'csv':
                    self._load_from_csv(table_name, table_meta)
                elif table_meta['source_type'] == 'csv_multiple':
                    self._load_from_multiple_csv(table_name, table_meta)
                elif table_meta['source_type'] == 'json':
                    self._load_from_json(table_name, table_meta)
                
                # Verificar carga
                count_after = self._count_records(table_name)
                new_records = count_after - count_before
                logger.info(f"  {table_name}: {count_after} registros totales ({new_records} nuevos)")
                
            except Exception as e:
                logger.error(f"Error cargando {table_name}: {e}")
    
    def _load_from_csv(self, table_name: str, table_meta: Dict):
        """Cargar desde un archivo CSV usando COPY"""
        file_path = table_meta['source_file']
        
        # Leer CSV completo
        df = pd.read_csv(file_path)
        
        # Limpiar datos
        df = self._clean_dataframe(df, table_meta)
        
        # Usar COPY con archivo temporal
        self._copy_from_dataframe(table_name, df, table_meta)
    
    def _clean_dataframe(self, df: pd.DataFrame, table_meta: Dict) -> pd.DataFrame:
        """Limpiar DataFrame antes de cargar"""
        # Convertir fechas
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convertir tipos numéricos
        numeric_columns = ['home_score', 'away_score', 'home_win', 'goal_diff', 'total_goals']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Eliminar filas con valores críticos faltantes
        critical_columns = ['date', 'home_team', 'away_team']
        df = df.dropna(subset=[col for col in critical_columns if col in df.columns])
        
        return df
    
    def _load_from_multiple_csv(self, table_name: str, table_meta: Dict):
        """Cargar desde múltiples archivos CSV"""
        import json
        dfs = []
        
        for file_path in table_meta['source_files']:
            df = pd.read_csv(file_path)
            dfs.append(df)
        
        # Combinar todos los DataFrames
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Limpiar datos
        df_combined = self._clean_dataframe(df_combined, table_meta)
        
        # Usar COPY
        self._copy_from_dataframe(table_name, df_combined, table_meta)
    
    def _load_from_json(self, table_name: str, table_meta: Dict):
        """Cargar desde archivo JSON"""
        import json
        file_path = table_meta['source_file']
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Para odds, convertir bookmakers a JSON string
        if 'bookmakers' in df.columns:
            df['bookmakers'] = df['bookmakers'].apply(json.dumps)
        
        # Limpiar datos
        df = self._clean_dataframe(df, table_meta)
        
        # Usar COPY
        self._copy_from_dataframe(table_name, df, table_meta)
    
    def _copy_from_dataframe(self, table_name: str, df: pd.DataFrame, table_meta: Dict):
        """Usar COPY de PostgreSQL para cargar datos desde DataFrame"""
        if df.empty:
            logger.warning(f"No hay datos para cargar en {table_name}")
            return
        
        # Mapear nombres de columnas originales a sanitizados
        column_mapping = {col_info['original_name']: col_name 
                        for col_name, col_info in table_meta['columns'].items()}
        
        # Seleccionar solo columnas que existen en la tabla
        available_cols = [col for col in df.columns if col in column_mapping]
        df_for_copy = df[available_cols].copy()
        
        # Renombrar columnas a nombres sanitizados
        df_for_copy.columns = [column_mapping[col] for col in df_for_copy.columns]
        
        # Crear archivo temporal para COPY
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as f:
            temp_file = f.name
            df_for_copy.to_csv(f, index=False, header=False, na_rep='\\N')
        
        try:
            cursor = self.conn.cursor()
            
            # Obtener columnas de la tabla
            columns = list(table_meta['columns'].keys())
            
            # Crear tabla temporal para cargar datos
            temp_table = f"{table_name}_temp_{int(pd.Timestamp.now().timestamp())}"
            
            # Crear tabla temporal
            temp_columns = []
            for col in columns:
                if col in df_for_copy.columns:
                    col_info = table_meta['columns'].get(col, {})
                    col_type = col_info.get('type', 'TEXT')
                    temp_columns.append(f'"{col}" {col_type}')
            
            if temp_columns:
                create_temp_sql = f"""
                    CREATE TEMP TABLE {temp_table} (
                        {','.join(temp_columns)}
                    )
                """
                cursor.execute(create_temp_sql)
                
                # Cargar datos en tabla temporal usando COPY
                with open(temp_file, 'r', encoding='utf-8') as f:
                    copy_sql = f"""
                    COPY {temp_table} ({', '.join([col for col in columns if col in df_for_copy.columns])})
                    FROM STDIN WITH (FORMAT CSV, NULL '\\N', DELIMITER ',')
                    """
                    cursor.copy_expert(copy_sql, f)
                
                # Insertar desde tabla temporal a tabla real, omitiendo duplicados
                pk_col = table_meta.get('primary_key')
                if pk_col and pk_col in df_for_copy.columns:
                    # Usar ON CONFLICT DO NOTHING para omitir duplicados
                    insert_sql = f"""
                        INSERT INTO {self.config.schema}.{table_name} ({', '.join([col for col in columns if col in df_for_copy.columns])})
                        SELECT {', '.join([col for col in columns if col in df_for_copy.columns])}
                        FROM {temp_table}
                        ON CONFLICT ({pk_col}) DO NOTHING
                    """
                else:
                    # Sin PK, insertar todos
                    insert_sql = f"""
                        INSERT INTO {self.config.schema}.{table_name} ({', '.join([col for col in columns if col in df_for_copy.columns])})
                        SELECT {', '.join([col for col in columns if col in df_for_copy.columns])}
                        FROM {temp_table}
                    """
                
                cursor.execute(insert_sql)
                inserted_count = cursor.rowcount
                
                self.conn.commit()
                cursor.close()
                
                logger.info(f"  {inserted_count}/{len(df_for_copy)} registros insertados (duplicados omitidos)")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error cargando datos: {e}")
            raise
        finally:
            # Eliminar archivo temporal
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def _count_records(self, table_name: str) -> int:
        """Contar registros en una tabla"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.config.schema}.{table_name}")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception:
            return 0

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal"""
    
    logger.info("=" * 80)
    logger.info("SISTEMA DE CARGA DINAMICA DE DATOS PREMIER LEAGUE")
    logger.info("=" * 80)
    logger.info("")
    
    # 1. Cargar configuración
    try:
        config = Config()
    except Exception as e:
        logger.error(f"Error cargando configuración: {e}")
        logger.error("Asegúrate de que config.yaml existe y tiene la configuración correcta")
        return
    
    # 2. Analizar datos
    analyzer = DataAnalyzer(config)
    metadata = analyzer.analyze_all_files()
    
    if not metadata:
        logger.error("No se encontraron datos para cargar")
        return
    
    # 3. Mostrar resumen
    logger.info("")
    logger.info("RESUMEN DE DATOS A CARGAR:")
    logger.info("-" * 80)
    for table_name, table_meta in metadata.items():
        logger.info(f"  {table_name}: {table_meta['row_count']} registros")
    logger.info("")
    
    # 4. Generar DDL
    ddl_generator = DDLGenerator(metadata, config.schema)
    ddl_statements = ddl_generator.generate_ddl()
    
    # 5. Confirmar ejecución
    response = input("¿Continuar con la carga? (s/n): ")
    if response.lower() != 's':
        logger.info("Carga cancelada")
        return
    
    # 6. Ejecutar carga
    loader = DataLoader(config, metadata)
    
    try:
        loader.connect()
        loader.execute_ddl(ddl_statements)
        loader.load_all_data()
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("CARGA COMPLETADA EXITOSAMENTE")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"Error durante la carga: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        loader.disconnect()


if __name__ == "__main__":
    main()

