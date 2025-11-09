#!/usr/bin/env python3
"""
Sistema de Carga Dinámica de Datos NBA a PostgreSQL
====================================================

Este script analiza automáticamente la estructura de los datos y crea
las tablas necesarias en PostgreSQL usando COPY nativo para máxima velocidad.

Características:
- Detección automática de tipos de datos
- Detección automática de Primary Keys
- Detección automática de Foreign Keys
- Uso de COPY nativo de PostgreSQL
- Skip de duplicados
- Todo en un solo archivo
"""

import os
import json
import yaml
import pandas as pd
import psycopg2
from psycopg2 import sql
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import tempfile
from loguru import logger

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

class Config:
    """Configuración del sistema de carga"""
    
    def __init__(self):
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Parsear DATABASE_URL
        db_url = config['DATABASE_URL']
        # postgresql://postgres:admin@localhost:5432/nba_data
        parts = db_url.replace('postgresql://', '').split('@')
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
        
        self.schema = config.get('DB_SCHEMA', 'espn')
        self.data_dir = Path('data')

# ============================================================================
# MAPEO DE EQUIPOS NBA
# ============================================================================

TEAM_NAMES_MAP = {
    'atl': 'Atlanta Hawks',
    'bkn': 'Brooklyn Nets',
    'bos': 'Boston Celtics',
    'cha': 'Charlotte Hornets',
    'chi': 'Chicago Bulls',
    'cle': 'Cleveland Cavaliers',
    'dal': 'Dallas Mavericks',
    'den': 'Denver Nuggets',
    'det': 'Detroit Pistons',
    'gs': 'Golden State Warriors',
    'hou': 'Houston Rockets',
    'ind': 'Indiana Pacers',
    'lac': 'LA Clippers',
    'lal': 'Los Angeles Lakers',
    'mem': 'Memphis Grizzlies',
    'mia': 'Miami Heat',
    'mil': 'Milwaukee Bucks',
    'min': 'Minnesota Timberwolves',
    'no': 'New Orleans Pelicans',
    'ny': 'New York Knicks',
    'okc': 'Oklahoma City Thunder',
    'orl': 'Orlando Magic',
    'phi': 'Philadelphia 76ers',
    'phx': 'Phoenix Suns',
    'por': 'Portland Trail Blazers',
    'sa': 'San Antonio Spurs',
    'sac': 'Sacramento Kings',
    'tor': 'Toronto Raptors',
    'utah': 'Utah Jazz',
    'wsh': 'Washington Wizards'
}

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
        print("🔍 Analizando estructura de datos...")
        
        # Analizar dataset consolidado
        self._analyze_processed_dataset()
        
        # Analizar archivos raw
        self._analyze_standings()
        self._analyze_team_stats()
        self._analyze_injuries()
        self._analyze_odds()
        
        print(f"✅ {len(self.metadata)} tablas detectadas\n")
        return self.metadata
    
    def _analyze_processed_dataset(self):
        """Analizar nba_full_dataset.csv"""
        file_path = self.config.data_dir / 'processed' / 'nba_full_dataset.csv'
        
        if not file_path.exists():
            print(f"⚠️  {file_path} no encontrado")
            return
        
        df = pd.read_csv(file_path, nrows=100)  # Muestra para análisis
        
        self.metadata['games'] = {
            'source_file': str(file_path),
            'source_type': 'csv',
            'table_name': 'games',
            'columns': self._infer_columns(df),
            'primary_key': 'game_id',  # Detectado: unique identifier
            'indexes': ['fecha', 'home_team', 'away_team'],
            'row_count': len(pd.read_csv(file_path))
        }
        
        print(f"  ✓ games: {self.metadata['games']['row_count']} registros")
    
    def _analyze_standings(self):
        """Analizar standings CSV files"""
        standings_dir = self.config.data_dir / 'raw' / 'standings'
        
        if not standings_dir.exists():
            return
        
        all_csv_files = list(standings_dir.glob('*.csv'))
        if not all_csv_files:
            return
        
        # Filtrar solo archivos válidos (que siguen el patrón YYYY-YY.csv)
        # Ejemplo: 2025-26.csv, 2024-25.csv
        csv_files = []
        for f in all_csv_files:
            # Validar que el archivo tenga el formato esperado
            if '-' in f.stem and len(f.stem.split('-')) == 2:
                try:
                    # Verificar que sean años válidos
                    parts = f.stem.split('-')
                    int(parts[0])  # Año inicial
                    int(parts[1])  # Año final
                    csv_files.append(f)
                except ValueError:
                    logger.warning(f"⚠️  Archivo de standings ignorado (formato inválido): {f.name}")
            else:
                logger.warning(f"⚠️  Archivo de standings ignorado (no es temporada válida): {f.name}")
        
        if not csv_files:
            logger.warning("⚠️  No se encontraron archivos de standings válidos")
            return
        
        # Leer primer archivo válido como muestra
        df = pd.read_csv(csv_files[0], nrows=100)
        
        # Contar total de registros de archivos válidos
        total_rows = sum(len(pd.read_csv(f)) for f in csv_files)
        
        columns_info = self._infer_columns(df)
        
        # Forzar GB a DOUBLE PRECISION (viene como string con decimales)
        if 'gb' in columns_info:
            columns_info['gb']['type'] = 'DOUBLE PRECISION'
        
        self.metadata['standings'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'standings',
            'columns': columns_info,
            'primary_key': None,  # No hay PK única
            'indexes': ['team_name', 'season', 'conference'],
            'row_count': total_rows
        }
        
        print(f"  ✓ standings: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_team_stats(self):
        """Analizar team_stats CSV files"""
        team_stats_dir = self.config.data_dir / 'raw' / 'team_stats'
        
        if not team_stats_dir.exists():
            return
        
        csv_files = list(team_stats_dir.glob('*.csv'))
        if not csv_files:
            return
        
        # Leer primer archivo como muestra
        df = pd.read_csv(csv_files[0], nrows=100)
        
        # Agregar columna team_abbrev del nombre del archivo
        sample_columns = self._infer_columns(df)
        sample_columns['team_abbrev'] = {
            'type': 'VARCHAR(10)',
            'nullable': False,
            'sample_values': [f.stem for f in csv_files[:5]]
        }
        
        # Contar total de registros válidos
        total_rows = 0
        for f in csv_files:
            df_temp = pd.read_csv(f)
            # Filtrar filas inválidas
            df_temp = df_temp[df_temp['team_name'].notna()]
            df_temp = df_temp[df_temp['team_name'] != 'Unknown']
            total_rows += len(df_temp)
        
        self.metadata['team_stats'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'team_stats',
            'columns': sample_columns,
            'primary_key': None,  # Composite key: team_abbrev + season
            'indexes': ['team_name', 'team_abbrev', 'season'],
            'row_count': total_rows
        }
        
        print(f"  ✓ team_stats: {total_rows} registros de {len(csv_files)} equipos")
    
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
            'primary_key': None,  # No hay PK única
            'indexes': ['Team', 'Player'],
            'row_count': len(df),
            'note': 'Datos actuales - se reemplazan en cada carga'
        }
        
        print(f"  ✓ injuries: {len(df)} registros (archivo más reciente)")
    
    def _analyze_odds(self):
        """Analizar odds JSON files"""
        odds_dir = self.config.data_dir / 'raw' / 'odds'
        
        if not odds_dir.exists():
            return
        
        json_files = list(odds_dir.glob('*.json'))
        if not json_files:
            return
        
        # Usar el archivo más reciente
        latest_file = max(json_files, key=lambda p: p.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
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
            'indexes': ['home_team', 'away_team', 'commence_time'],
            'row_count': len(data),
            'note': 'Datos actuales - se reemplazan en cada carga'
        }
        
        print(f"  ✓ odds: {len(data)} registros (archivo más reciente)")
    
    def _sanitize_column_name(self, col: str) -> str:
        """
        Sanitizar nombres de columnas para PostgreSQL
        
        Reglas:
        - % → _percent (más descriptivo que _pct)
        - Espacios → _
        - Guiones → _
        - Si empieza con número, agregar prefijo descriptivo
        """
        col_safe = col.strip()
        
        # Casos especiales conocidos (estadísticas NBA)
        special_cases = {
            '3P%': 'three_point_percent',
            '3P': 'three_pointers',
            'FG%': 'field_goal_percent',
            'FT%': 'free_throw_percent',
            'Win%': 'win_percent',
            '2P%': 'two_point_percent',
            '3PA': 'three_point_attempts',
            'FGA': 'field_goal_attempts',
            'FTA': 'free_throw_attempts'
        }
        
        if col_safe in special_cases:
            return special_cases[col_safe]
        
        # Reemplazar % por _percent
        col_safe = col_safe.replace('%', '_percent')
        
        # Reemplazar espacios y guiones
        col_safe = col_safe.replace(' ', '_').replace('-', '_')
        
        # Si empieza con número, agregar prefijo
        if col_safe and col_safe[0].isdigit():
            col_safe = 'stat_' + col_safe
        
        # Convertir a minúsculas para consistencia
        col_safe = col_safe.lower()
        
        # Palabras reservadas de PostgreSQL - agregar sufijo
        reserved_words = ['to', 'from', 'select', 'where', 'order', 'group', 'by', 'as', 'table', 'user']
        if col_safe in reserved_words:
            col_safe = col_safe + '_stat'
        
        return col_safe
    
    def _infer_columns(self, df: pd.DataFrame) -> Dict:
        """Inferir tipos de columnas desde DataFrame"""
        columns = {}
        
        for col in df.columns:
            # Sanitizar nombre de columna
            col_safe = self._sanitize_column_name(col)
            
            dtype = df[col].dtype
            sample_values = df[col].dropna().head(5).tolist()
            
            # Mapear tipo de pandas a PostgreSQL
            if dtype == 'int64':
                pg_type = 'BIGINT'
            elif dtype == 'float64':
                pg_type = 'DOUBLE PRECISION'
            elif dtype == 'bool':
                pg_type = 'BOOLEAN'
            elif dtype == 'datetime64[ns]':
                pg_type = 'TIMESTAMP'
            elif dtype == 'object':
                # Intentar detectar tipo específico
                if col.lower() in ['fecha', 'date', 'game_date']:
                    pg_type = 'DATE'
                else:
                    # Intentar convertir a numérico para ver si son números
                    try:
                        numeric_test = pd.to_numeric(df[col].dropna(), errors='coerce')
                        if numeric_test.notna().sum() > len(df[col].dropna()) * 0.8:  # 80% son números
                            # Verificar si tiene decimales
                            if (numeric_test % 1 != 0).any():
                                pg_type = 'DOUBLE PRECISION'
                            else:
                                pg_type = 'BIGINT'
                        else:
                            # Es texto
                            max_len = df[col].dropna().astype(str).str.len().max()
                            if pd.isna(max_len) or max_len < 50:
                                pg_type = 'VARCHAR(255)'
                            elif max_len < 500:
                                pg_type = 'VARCHAR(1000)'
                            else:
                                pg_type = 'TEXT'
                    except:
                        # Calcular longitud máxima
                        max_len = df[col].dropna().astype(str).str.len().max()
                        if pd.isna(max_len) or max_len < 50:
                            pg_type = 'VARCHAR(255)'
                        elif max_len < 500:
                            pg_type = 'VARCHAR(1000)'
                        else:
                            pg_type = 'TEXT'
            else:
                pg_type = 'TEXT'
            
            # Detectar nullabilidad
            nullable = df[col].isna().any()
            
            columns[col_safe] = {
                'type': pg_type,
                'nullable': nullable,
                'sample_values': sample_values,
                'original_name': col  # Guardar nombre original para mapeo
            }
        
        return columns

# ============================================================================
# DETECTOR DE RELACIONES
# ============================================================================

class RelationshipDetector:
    """Detecta relaciones (Foreign Keys) entre tablas"""
    
    def __init__(self, metadata: Dict):
        self.metadata = metadata
        self.relationships = []
    
    def detect_relationships(self) -> List[Dict]:
        """Detecta todas las relaciones posibles entre tablas"""
        print("\n🔗 Detectando relaciones entre tablas...")
        
        # Relaciones conocidas por convención de nombres
        self._detect_by_naming_convention()
        
        print(f"✅ {len(self.relationships)} relaciones detectadas\n")
        return self.relationships
    
    def _detect_by_naming_convention(self):
        """Detectar FKs por convención de nombres"""
        
        # Relación: standings.team_name -> team_stats.team_name
        if 'standings' in self.metadata and 'team_stats' in self.metadata:
            standings_cols = self.metadata['standings']['columns']
            team_stats_cols = self.metadata['team_stats']['columns']
            
            if 'team_name' in standings_cols and 'team_name' in team_stats_cols:
                self.relationships.append({
                    'from_table': 'standings',
                    'from_column': 'team_name',
                    'to_table': 'team_stats',
                    'to_column': 'team_name',
                    'constraint_name': 'fk_standings_team_stats'
                })
                print("  ✓ standings.team_name → team_stats.team_name")
        
        # Relación: injuries.Team -> team_stats.team_name
        if 'injuries' in self.metadata and 'team_stats' in self.metadata:
            injuries_cols = self.metadata['injuries']['columns']
            team_stats_cols = self.metadata['team_stats']['columns']
            
            if 'Team' in injuries_cols and 'team_name' in team_stats_cols:
                self.relationships.append({
                    'from_table': 'injuries',
                    'from_column': 'Team',
                    'to_table': 'team_stats',
                    'to_column': 'team_name',
                    'constraint_name': 'fk_injuries_team_stats'
                })
                print("  ✓ injuries.Team → team_stats.team_name")

# ============================================================================
# GENERADOR DE DDL
# ============================================================================

class DDLGenerator:
    """Genera statements SQL para crear tablas"""
    
    def __init__(self, metadata: Dict, relationships: List[Dict], schema: str):
        self.metadata = metadata
        self.relationships = relationships
        self.schema = schema
    
    def generate_ddl(self) -> List[str]:
        """Genera todos los statements DDL"""
        print("📝 Generando SQL DDL...")
        
        statements = []
        
        # 1. Crear esquema
        statements.append(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
        
        # 2. Crear tablas (en orden de dependencias)
        table_order = self._determine_table_order()
        
        for table_name in table_order:
            table_meta = self.metadata[table_name]
            create_stmt = self._generate_create_table(table_name, table_meta)
            statements.append(create_stmt)
            print(f"  ✓ CREATE TABLE {self.schema}.{table_name}")
        
        # 3. Crear índices
        for table_name in table_order:
            table_meta = self.metadata[table_name]
            index_stmts = self._generate_indexes(table_name, table_meta)
            statements.extend(index_stmts)
        
        # 4. Crear Foreign Keys (opcional, pero útil para integridad)
        # for rel in self.relationships:
        #     fk_stmt = self._generate_foreign_key(rel)
        #     statements.append(fk_stmt)
        
        print(f"✅ {len(statements)} statements SQL generados\n")
        return statements
    
    def _determine_table_order(self) -> List[str]:
        """Determina el orden de creación de tablas según dependencias"""
        # Por ahora, orden manual (se puede hacer topological sort)
        order = []
        
        # Tablas sin dependencias primero
        if 'team_stats' in self.metadata:
            order.append('team_stats')
        if 'games' in self.metadata:
            order.append('games')
        if 'standings' in self.metadata:
            order.append('standings')
        if 'injuries' in self.metadata:
            order.append('injuries')
        if 'odds' in self.metadata:
            order.append('odds')
        
        return order
    
    def _generate_create_table(self, table_name: str, table_meta: Dict) -> str:
        """Genera CREATE TABLE statement"""
        columns_def = []
        
        for col_name, col_info in table_meta['columns'].items():
            col_type = col_info['type']
            nullable = 'NULL' if col_info['nullable'] else 'NOT NULL'
            columns_def.append(f"    {col_name} {col_type} {nullable}")
        
        # Agregar Primary Key si existe
        if table_meta.get('primary_key'):
            pk = table_meta['primary_key']
            columns_def.append(f"    PRIMARY KEY ({pk})")
        
        columns_sql = ',\n'.join(columns_def)
        
        return f"""
CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (
{columns_sql}
);"""
    
    def _generate_indexes(self, table_name: str, table_meta: Dict) -> List[str]:
        """Genera CREATE INDEX statements"""
        statements = []
        
        indexes = table_meta.get('indexes', [])
        
        for idx_col in indexes:
            if idx_col in table_meta['columns']:
                idx_name = f"idx_{table_name}_{idx_col}"
                stmt = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {self.schema}.{table_name}({idx_col});"
                statements.append(stmt)
        
        return statements
    
    def _generate_foreign_key(self, rel: Dict) -> str:
        """Genera ALTER TABLE para Foreign Key"""
        return f"""
ALTER TABLE {self.schema}.{rel['from_table']} 
ADD CONSTRAINT {rel['constraint_name']} 
FOREIGN KEY ({rel['from_column']}) 
REFERENCES {self.schema}.{rel['to_table']}({rel['to_column']});"""

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
        self.conn = psycopg2.connect(**self.config.db_config)
        print("✅ Conectado a PostgreSQL\n")
    
    def disconnect(self):
        """Desconectar de PostgreSQL"""
        if self.conn:
            self.conn.close()
            print("\n✅ Desconectado de PostgreSQL")
    
    def execute_ddl(self, statements: List[str]):
        """Ejecutar statements DDL"""
        print("🏗️  Ejecutando DDL...")
        
        cursor = self.conn.cursor()
        
        for stmt in statements:
            try:
                cursor.execute(stmt)
                self.conn.commit()
            except Exception as e:
                print(f"⚠️  Error ejecutando DDL: {e}")
                self.conn.rollback()
        
        cursor.close()
        print("✅ DDL ejecutado\n")
    
    def load_all_data(self):
        """Cargar todos los datos"""
        print("📦 Cargando datos...")
        
        for table_name, table_meta in self.metadata.items():
            print(f"\n  📊 Cargando {table_name}...")
            
            try:
                if table_meta['source_type'] == 'csv':
                    self._load_from_csv(table_name, table_meta)
                elif table_meta['source_type'] == 'csv_multiple':
                    self._load_from_multiple_csv(table_name, table_meta)
                elif table_meta['source_type'] == 'json':
                    self._load_from_json(table_name, table_meta)
                
                # Verificar carga
                count = self._count_records(table_name)
                print(f"    ✅ {count} registros cargados")
                
            except Exception as e:
                print(f"    ❌ Error cargando {table_name}: {e}")
    
    def _load_from_csv(self, table_name: str, table_meta: Dict):
        """Cargar desde un archivo CSV usando COPY"""
        file_path = table_meta['source_file']
        
        # Leer CSV
        df = pd.read_csv(file_path)
        
        # Limpiar datos
        df = self._clean_dataframe(df, table_meta)
        
        # Usar COPY con archivo temporal
        self._copy_from_dataframe(table_name, df, table_meta['columns'])
    
    def _load_from_multiple_csv(self, table_name: str, table_meta: Dict):
        """Cargar desde múltiples archivos CSV"""
        dfs = []
        
        for file_path in table_meta['source_files']:
            df = pd.read_csv(file_path)
            
            # Para team_stats, agregar team_abbrev y nombre completo del equipo
            if table_name == 'team_stats':
                team_abbrev = Path(file_path).stem.lower()
                df['team_abbrev'] = team_abbrev
                
                # Reemplazar 'Unknown' con el nombre real del equipo
                if team_abbrev in TEAM_NAMES_MAP:
                    df['team_name'] = TEAM_NAMES_MAP[team_abbrev]
            
            dfs.append(df)
        
        # Combinar todos los DataFrames
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Limpiar datos
        df_combined = self._clean_dataframe(df_combined, table_meta)
        
        # Usar COPY
        self._copy_from_dataframe(table_name, df_combined, table_meta['columns'])
    
    def _load_from_json(self, table_name: str, table_meta: Dict):
        """Cargar desde archivo JSON"""
        file_path = table_meta['source_file']
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        
        # Para odds, convertir bookmakers a JSON string
        if 'bookmakers' in df.columns:
            df['bookmakers'] = df['bookmakers'].apply(json.dumps)
        
        # Limpiar datos
        df = self._clean_dataframe(df, table_meta)
        
        # Usar COPY
        self._copy_from_dataframe(table_name, df, table_meta['columns'])
    
    def _clean_dataframe(self, df: pd.DataFrame, table_meta: Dict) -> pd.DataFrame:
        """Limpiar DataFrame antes de cargar"""
        
        # Filtrar filas inválidas (para team_stats)
        if table_meta['table_name'] == 'team_stats':
            if 'team_name' in df.columns:
                df = df[df['team_name'].notna()]
                df = df[df['team_name'] != 'Unknown']
        
        # Filtrar registros duplicados en encabezados
        if table_meta['table_name'] == 'standings':
            if 'team' in df.columns:
                df = df[df['team'] != 'Team']
                df = df[df['team'] != 'W']
                df = df[df['team'] != 'Unknown']
                df = df[df['team'].notna()]
        
        # Mapear nombres de columnas originales del DataFrame a nombres sanitizados de la tabla
        # Crear mapeo inverso: original_name -> safe_name
        original_to_safe = {}
        for safe_name, col_meta in table_meta['columns'].items():
            if 'original_name' in col_meta:
                original_to_safe[col_meta['original_name']] = safe_name
        
        # Renombrar columnas del DataFrame primero
        df = df.rename(columns=original_to_safe)
        
        # Ahora seleccionar solo columnas que existen en la tabla
        table_columns = list(table_meta['columns'].keys())
        available_columns = [col for col in table_columns if col in df.columns]
        df = df[available_columns]
        
        # Convertir fecha si existe
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce').dt.date
        
        # Para standings, convertir columnas numéricas correctamente
        if table_meta['table_name'] == 'standings':
            # Columnas que deben ser INTEGER (no convertir 0 a None aquí, 0 es válido)
            numeric_int_columns = ['wins', 'losses', 'season']
            for col in numeric_int_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # Columnas que deben ser FLOAT (con punto decimal)  
            numeric_float_columns = ['gb', 'win_percent']
            for col in numeric_float_columns:
                if col in df.columns:
                    # Convertir a float, reemplazando valores problemáticos
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Convertir NaN a None para PostgreSQL NULL
                    df[col] = df[col].where(pd.notna(df[col]), None)
        
        # Convertir season a integer si existe (para otras tablas)
        elif 'season' in df.columns:
            df['season'] = df['season'].fillna(0).astype(int)
            df['season'] = df['season'].replace(0, None)
        
        # Reemplazar NaN con None para PostgreSQL NULL
        df = df.where(pd.notnull(df), None)
        
        return df
    
    def _copy_from_dataframe(self, table_name: str, df: pd.DataFrame, columns_meta: Dict):
        """Usar COPY de PostgreSQL para cargar datos"""
        
        if df.empty:
            print("    ⚠️  No hay datos para cargar")
            return
        
        cursor = self.conn.cursor()
        
        # El DataFrame ya viene con columnas sanitizadas desde _clean_dataframe
        # Crear archivo temporal CSV
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as f:
            temp_file = f.name
            df.to_csv(f, index=False, header=False, na_rep='\\N')
        
        try:
            # Usar COPY para cargar
            columns = ','.join(df.columns)
            copy_sql = f"""
                COPY {self.config.schema}.{table_name} ({columns})
                FROM STDIN
                WITH (FORMAT CSV, NULL '\\N', ENCODING 'UTF8')
            """
            
            with open(temp_file, 'r', encoding='utf-8') as f:
                cursor.copy_expert(copy_sql, f)
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            print(f"    ⚠️  Error en COPY: {e}")
            # Fallback: usar INSERT individual (más lento pero maneja duplicados)
            self._insert_with_skip_duplicates(table_name, df, columns_meta)
        finally:
            cursor.close()
            # Limpiar archivo temporal
            os.unlink(temp_file)
    
    def _insert_with_skip_duplicates(self, table_name: str, df: pd.DataFrame, columns_meta: Dict):
        """Insertar registros uno por uno, skipeando duplicados"""
        cursor = self.conn.cursor()
        
        # El DataFrame ya viene con columnas sanitizadas desde _clean_dataframe
        columns = list(df.columns)
        placeholders = ','.join(['%s'] * len(columns))
        
        insert_sql = f"""
            INSERT INTO {self.config.schema}.{table_name} ({','.join(columns)})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """
        
        success_count = 0
        for _, row in df.iterrows():
            try:
                values = tuple(row[col] for col in columns)
                cursor.execute(insert_sql, values)
                success_count += 1
            except Exception:
                continue
        
        self.conn.commit()
        cursor.close()
        print(f"    ✓ {success_count}/{len(df)} registros insertados (duplicados skipeados)")
    
    def _count_records(self, table_name: str) -> int:
        """Contar registros en una tabla"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self.config.schema}.{table_name}")
        count = cursor.fetchone()[0]
        cursor.close()
        return count

# ============================================================================
# REPORTADOR
# ============================================================================

class Reporter:
    """Genera reportes del proceso de carga"""
    
    @staticmethod
    def print_summary(metadata: Dict, relationships: List[Dict]):
        """Imprime resumen antes de ejecutar"""
        print("\n" + "="*80)
        print("📊 RESUMEN DE CARGA DINÁMICA")
        print("="*80)
        
        print(f"\n📋 TABLAS A CREAR ({len(metadata)}):")
        for table_name, meta in metadata.items():
            col_count = len(meta['columns'])
            row_count = meta['row_count']
            print(f"  ✓ {table_name}: {col_count} columnas, {row_count} registros")
        
        if relationships:
            print(f"\n🔗 RELACIONES DETECTADAS ({len(relationships)}):")
            for rel in relationships:
                print(f"  ✓ {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}")
        
        print("\n" + "="*80 + "\n")
    
    @staticmethod
    def print_final_report(config: Config, metadata: Dict):
        """Imprime reporte final después de la carga"""
        print("\n" + "="*80)
        print("✅ CARGA COMPLETADA")
        print("="*80)
        
        print(f"\n📊 Base de datos: {config.db_config['database']}")
        print(f"📦 Esquema: {config.schema}")
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n" + "="*80 + "\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal"""
    
    print("\n" + "="*80)
    print("🚀 SISTEMA DE CARGA DINÁMICA DE DATOS NBA")
    print("="*80 + "\n")
    
    # 1. Cargar configuración
    config = Config()
    
    # 2. Analizar datos
    analyzer = DataAnalyzer(config)
    metadata = analyzer.analyze_all_files()
    
    if not metadata:
        print("❌ No se encontraron datos para cargar")
        return
    
    # 3. Detectar relaciones
    detector = RelationshipDetector(metadata)
    relationships = detector.detect_relationships()
    
    # 4. Mostrar resumen
    Reporter.print_summary(metadata, relationships)
    
    # 5. Generar DDL
    ddl_generator = DDLGenerator(metadata, relationships, config.schema)
    ddl_statements = ddl_generator.generate_ddl()
    
    # 6. Confirmar ejecución
    response = input("¿Continuar con la carga? (s/n): ")
    if response.lower() != 's':
        print("❌ Carga cancelada")
        return
    
    # 7. Ejecutar carga
    loader = DataLoader(config, metadata)
    
    try:
        loader.connect()
        loader.execute_ddl(ddl_statements)
        loader.load_all_data()
        
        # 8. Reporte final
        Reporter.print_final_report(config, metadata)
        
    except Exception as e:
        print(f"\n❌ Error durante la carga: {e}")
    finally:
        loader.disconnect()


if __name__ == "__main__":
    main()

