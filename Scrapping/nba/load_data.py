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
        from dotenv import load_dotenv
        
        # Cargar variables de entorno desde .env
        if os.path.exists('.env'):
            load_dotenv('.env')
        else:
            load_dotenv()
        
        config = {}
        # Cargar desde archivo si existe (fallback)
        if os.path.exists('config.yaml'):
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f) or {}
        
        # Construir DATABASE_URL desde variables individuales o usar la completa
        db_url = os.getenv("DATABASE_URL")
        
        # Si no hay DATABASE_URL completa, construir desde variables individuales
        if not db_url:
            db_host = os.getenv("NEON_DB_HOST") or config.get("DB_HOST")
            db_port = os.getenv("NEON_DB_PORT") or config.get("DB_PORT", "5432")
            db_name = os.getenv("NEON_DB_NAME") or config.get("DB_NAME")
            db_user = os.getenv("NEON_DB_USER") or config.get("DB_USER")
            db_password = os.getenv("NEON_DB_PASSWORD") or config.get("DB_PASSWORD")
            sslmode = os.getenv("NEON_DB_SSLMODE") or config.get("DB_SSLMODE", "require")
            channel_binding = os.getenv("NEON_DB_CHANNEL_BINDING") or config.get("DB_CHANNEL_BINDING", "require")
            
            if all([db_host, db_port, db_name, db_user, db_password]):
                db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?sslmode={sslmode}&channel_binding={channel_binding}"
            else:
                # Intentar desde config.yaml
                db_url = config.get('DATABASE_URL')
                # Reemplazar ${VAR} con variables de entorno si es necesario
                if db_url and db_url.startswith("${") and db_url.endswith("}"):
                    env_var = db_url[2:-1]
                    db_url = os.getenv(env_var) or db_url
        
        if not db_url:
            raise ValueError(
                "DATABASE_URL no está configurada. "
                "Configúrala usando:\n"
                "  - Variables de entorno: DATABASE_URL o NEON_DB_* variables\n"
                "  - Archivo .env (copiar desde .env.example)\n"
                "  - Archivo config.yaml"
            )
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
        
        # self._analyze_processed_dataset()
        
        # Analizar archivos raw
        # self._analyze_standings()
        # self._analyze_team_stats()
        # self._analyze_team_stats()
        # self._analyze_player_stats()
        self._analyze_nba_player_boxscores()
        # self._analyze_injuries()
        # self._analyze_odds()
        
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
        
        # Buscar archivos en la nueva estructura: {season}_{season_type}/offensive/all_teams.csv y defensive/all_teams.csv
        csv_files = []
        
        # Buscar en subdirectorios por temporada (formato: 2023-24_regular, 2024-25_playoffs, etc.)
        season_dirs = [d for d in team_stats_dir.iterdir() if d.is_dir() and '_' in d.name]
        if season_dirs:
            # Archivos organizados por temporada y categoría (offensive/defensive)
            for season_dir in season_dirs:
                # Buscar en subdirectorios offensive y defensive
                for category_dir in ['offensive', 'defensive']:
                    category_path = season_dir / category_dir
                    if category_path.exists():
                        all_teams_file = category_path / 'all_teams.csv'
                        if all_teams_file.exists():
                            csv_files.append(all_teams_file)
        
        if not csv_files:
            return
        
        # Leer todos los archivos para obtener todas las columnas posibles
        # (ofensivas y defensivas pueden tener diferentes columnas)
        all_columns = set()
        sample_dfs = []
        
        for csv_file in csv_files:
            df_temp = pd.read_csv(csv_file, nrows=100)
            all_columns.update(df_temp.columns)
            sample_dfs.append(df_temp)
        
        # Combinar todos los DataFrames para inferir columnas completas
        df_combined = pd.concat(sample_dfs, ignore_index=True)
        
        # Inferir columnas desde el DataFrame combinado
        sample_columns = self._infer_columns(df_combined)
        
        # Asegurar que team_abbrev esté presente
        if 'team_abbrev' not in sample_columns:
            sample_columns['team_abbrev'] = {
                'type': 'VARCHAR(10)',
                'nullable': False,
                'sample_values': ['bos', 'atl', 'mil']
            }
        
        # Asegurar que season y season_type sean VARCHAR
        if 'season' not in sample_columns:
            sample_columns['season'] = {
                'type': 'VARCHAR(10)',
                'nullable': True,
                'sample_values': ['2023-24', '2024-25']
            }
        else:
            sample_columns['season']['type'] = 'VARCHAR(10)'
        
        if 'season_type' not in sample_columns:
            sample_columns['season_type'] = {
                'type': 'VARCHAR(20)',
                'nullable': True,
                'sample_values': ['regular', 'playoffs']
            }
        else:
            sample_columns['season_type']['type'] = 'VARCHAR(20)'
        
        # Agregar columna category (offensive/defensive)
        if 'category' not in sample_columns:
            sample_columns['category'] = {
                'type': 'VARCHAR(20)',
                'nullable': False,
                'sample_values': ['offensive', 'defensive']
            }
        
        # Asegurar que todas las columnas numéricas sean nullable (excepto las esenciales)
        # Esto evita problemas con columnas que pueden no tener datos
        essential_columns = ['team_name', 'team_abbrev', 'season', 'season_type', 'category']
        for col_name, col_info in sample_columns.items():
            if col_name not in essential_columns:
                col_info['nullable'] = True
        
        # Contar total de registros válidos
        total_rows = 0
        for f in csv_files:
            df_temp = pd.read_csv(f)
            # Filtrar filas inválidas
            if 'team_name' in df_temp.columns:
                df_temp = df_temp[df_temp['team_name'].notna()]
                df_temp = df_temp[df_temp['team_name'] != 'Unknown']
            total_rows += len(df_temp)
        
        self.metadata['team_stats'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'team_stats',
            'columns': sample_columns,
            'primary_key': None,  # Composite key: team_abbrev + season + season_type + category
            'indexes': ['team_name', 'team_abbrev', 'season', 'season_type', 'category'],
            'row_count': total_rows
        }
        
        print(f"  ✓ team_stats: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_player_stats(self):
        """Analizar player_stats CSV files"""
        player_stats_dir = self.config.data_dir / 'raw' / 'player_stats'
        
        if not player_stats_dir.exists():
            return
        
        # Buscar todos los archivos all_stats.csv en subdirectorios
        csv_files = list(player_stats_dir.glob('*/all_stats.csv'))
        if not csv_files:
            return
        
        # Leer primer archivo como muestra
        df = pd.read_csv(csv_files[0], nrows=100)
        
        # Contar total de registros de todos los archivos
        total_rows = sum(len(pd.read_csv(f)) for f in csv_files)
        
        # Inferir columnas
        columns_info = self._infer_columns(df)
        
        # Asegurar que player_id sea BIGINT (puede venir como string)
        if 'player_id' in columns_info:
            columns_info['player_id']['type'] = 'BIGINT'
        
        # Asegurar que season_type sea VARCHAR
        if 'season_type' in columns_info:
            columns_info['season_type']['type'] = 'VARCHAR(20)'
        
        # Asegurar que season sea VARCHAR (formato "2023-24")
        if 'season' in columns_info:
            columns_info['season']['type'] = 'VARCHAR(10)'
        
        self.metadata['player_stats'] = {
            'source_files': [str(f) for f in csv_files],
            'source_type': 'csv_multiple',
            'table_name': 'player_stats',
            'columns': columns_info,
            'primary_key': None,  # No hay PK única (mismo jugador en múltiples temporadas)
            'indexes': ['player_id', 'player_name', 'season', 'season_type'],
            'row_count': total_rows
        }
        
        print(f"  ✓ player_stats: {total_rows} registros de {len(csv_files)} archivos")
    
    def _analyze_nba_player_boxscores(self):
        """Analizar nba_player_boxscores.csv"""
        file_path = self.config.data_dir / 'processed' / 'nba_player_boxscores.csv'
        
        if not file_path.exists():
            return
        
        df = pd.read_csv(file_path, nrows=100)
        
        columns_info = self._infer_columns(df)
        
        # Ajustes de tipos específicos
        if 'game_id' in columns_info:
            columns_info['game_id']['type'] = 'VARCHAR(20)' # IDs como '0022300001'
        if 'player_id' in columns_info:
            columns_info['player_id']['type'] = 'BIGINT'
        if 'team_tricode' in columns_info:
            columns_info['team_tricode']['type'] = 'VARCHAR(5)'
            
        self.metadata['nba_player_boxscores'] = {
            'source_file': str(file_path),
            'source_type': 'csv',
            'table_name': 'nba_player_boxscores',
            'columns': columns_info,
            # No hay PK única en CSV, pero podemos decir que (game_id, player_id) es único
            # O dejar que la DB cree una PK serial si quisiéramos, pero usando COPY el loader crea tabla basada en CSV
            # Mejor dejar sin PK explicita en metadata y crear indices
            'primary_key': None, 
            'indexes': ['game_id', 'player_id', 'team_tricode'],
            'row_count': len(pd.read_csv(file_path))
        }
        
        # Nota: Idealmente agregaríamos una columna SERIAL 'id' en la base de datos después
        # pero para carga masiva inicial, esto funciona bien.
        
        print(f"  ✓ nba_player_boxscores: {self.metadata['nba_player_boxscores']['row_count']} registros")

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
        if 'player_stats' in self.metadata:
            order.append('player_stats')
        if 'nba_player_boxscores' in self.metadata:
            order.append('nba_player_boxscores')
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
            # Para estructura dinámica, todas las columnas son nullable excepto PK
            # La base de datos se adapta al CSV
            if table_meta.get('primary_key') == col_name:
                nullable = 'NOT NULL'
            else:
                nullable = 'NULL'
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
        
        # Asegurar que todas las tablas tengan las columnas correctas según los datos
        self._sync_table_structure(cursor)
        
        cursor.close()
        print("✅ DDL ejecutado\n")
    
    def _sync_table_structure(self, cursor):
        """Sincronizar estructura de tablas con los datos que llegan"""
        for table_name, table_meta in self.metadata.items():
            try:
                # Verificar si la tabla existe
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    )
                """, (self.config.schema, table_name))
                
                if not cursor.fetchone()[0]:
                    continue  # La tabla no existe, se creará con el DDL
                
                # Obtener columnas actuales de la tabla con sus tipos
                cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length, udt_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                """, (self.config.schema, table_name))
                
                existing_columns = {}
                for row in cursor.fetchall():
                    col_name, data_type, max_length, udt_name = row
                    # Normalizar tipo de datos para comparación
                    if data_type == 'character varying':
                        pg_type = f"VARCHAR({max_length})" if max_length else 'VARCHAR'
                    elif data_type == 'bigint':
                        pg_type = 'BIGINT'
                    elif data_type == 'double precision':
                        pg_type = 'DOUBLE PRECISION'
                    elif data_type == 'integer':
                        pg_type = 'INTEGER'
                    elif data_type == 'date':
                        pg_type = 'DATE'
                    elif data_type == 'jsonb':
                        pg_type = 'JSONB'
                    else:
                        pg_type = data_type.upper()
                    existing_columns[col_name] = pg_type
                
                # Obtener columnas esperadas según los datos
                expected_columns = table_meta.get('columns', {})
                
                # Agregar columnas faltantes o cambiar tipo si es necesario
                for col_name, col_info in expected_columns.items():
                    expected_type = col_info.get('type', 'TEXT')
                    
                    if col_name not in existing_columns:
                        # Columna no existe, agregarla
                        nullable = 'NULL' if col_info.get('nullable', True) else 'NOT NULL'
                        
                        try:
                            alter_sql = f"""
                                ALTER TABLE {self.config.schema}.{table_name}
                                ADD COLUMN IF NOT EXISTS {col_name} {expected_type} {nullable}
                            """
                            cursor.execute(alter_sql)
                            self.conn.commit()
                            print(f"  ✓ Agregada columna {col_name} ({expected_type}) a {table_name}")
                        except Exception as e:
                            print(f"  ⚠️  Error agregando columna {col_name} a {table_name}: {e}")
                            self.conn.rollback()
                    else:
                        # Columna existe, verificar si el tipo coincide
                        existing_type = existing_columns[col_name]
                        
                        # Normalizar tipos para comparación
                        def normalize_type(t):
                            t = t.upper().strip()
                            if 'VARCHAR' in t:
                                return 'VARCHAR'
                            return t
                        
                        if normalize_type(existing_type) != normalize_type(expected_type):
                            # Tipo no coincide, cambiar tipo de columna
                            try:
                                # Para cambiar tipo, primero necesitamos verificar si hay datos
                                cursor.execute(f"""
                                    SELECT COUNT(*) FROM {self.config.schema}.{table_name}
                                """)
                                row_count = cursor.fetchone()[0]
                                
                                if row_count == 0:
                                    # Tabla vacía, cambiar tipo directamente
                                    alter_sql = f"""
                                        ALTER TABLE {self.config.schema}.{table_name}
                                        ALTER COLUMN {col_name} TYPE {expected_type}
                                    """
                                    cursor.execute(alter_sql)
                                    self.conn.commit()
                                    print(f"  ✓ Cambiado tipo de columna {col_name} de {existing_type} a {expected_type} en {table_name}")
                                else:
                                    # Tabla con datos, usar USING para conversión
                                    # Para VARCHAR, simplemente convertir a texto
                                    if 'VARCHAR' in expected_type.upper():
                                        alter_sql = f"""
                                            ALTER TABLE {self.config.schema}.{table_name}
                                            ALTER COLUMN {col_name} TYPE {expected_type} USING {col_name}::text
                                        """
                                    else:
                                        # Para otros tipos, intentar conversión directa
                                        alter_sql = f"""
                                            ALTER TABLE {self.config.schema}.{table_name}
                                            ALTER COLUMN {col_name} TYPE {expected_type} USING {col_name}::{expected_type}
                                        """
                                    cursor.execute(alter_sql)
                                    self.conn.commit()
                                    print(f"  ✓ Cambiado tipo de columna {col_name} de {existing_type} a {expected_type} en {table_name}")
                            except Exception as e:
                                print(f"  ⚠️  Error cambiando tipo de columna {col_name} en {table_name}: {e}")
                                self.conn.rollback()
                
            except Exception as e:
                print(f"  ⚠️  Error sincronizando estructura de {table_name}: {e}")
                self.conn.rollback()
    
    def load_all_data(self):
        """Cargar todos los datos"""
        print("📦 Cargando datos...")
        
        for table_name, table_meta in self.metadata.items():
            print(f"\n  📊 Cargando {table_name}...")
            
            try:
                # Para games, truncar la tabla antes de cargar
                if table_name == 'games':
                    cursor = self.conn.cursor()
                    cursor.execute(f"TRUNCATE TABLE {self.config.schema}.{table_name}")
                    self.conn.commit()
                    cursor.close()
                    print(f"    ✓ Tabla {table_name} truncada")
                
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
                print(f"    ✅ {count_after} registros totales ({new_records} nuevos)")
                
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
            
            # Para team_stats, extraer información del path
            if table_name == 'team_stats':
                file_path_obj = Path(file_path)
                # Estructura: data/raw/team_stats/{season}_{season_type}/offensive|defensive/all_teams.csv
                # El padre del archivo es la categoría (offensive/defensive)
                category_dir = file_path_obj.parent.name  # offensive o defensive
                # El abuelo es la temporada (2023-24_regular, etc.)
                season_dir = file_path_obj.parent.parent.name
                
                # Extraer season y season_type del nombre del directorio
                if '_' in season_dir:
                    parts = season_dir.split('_')
                    if len(parts) == 2:
                        season_from_dir = parts[0]
                        season_type_from_dir = parts[1]
                        # Si season y season_type no están en el DataFrame, agregarlos
                        if 'season' not in df.columns:
                            df['season'] = season_from_dir
                        if 'season_type' not in df.columns:
                            df['season_type'] = season_type_from_dir
                
                # Agregar categoría (offensive/defensive) como columna
                if 'category' not in df.columns:
                    df['category'] = category_dir
                
                # Asegurar que team_abbrev esté presente
                if 'team_abbrev' not in df.columns and 'team_name' in df.columns:
                    # Intentar obtener team_abbrev del team_name
                    df['team_abbrev'] = df['team_name'].map(TEAM_ABBREV_MAP)
            
            # Para player_stats, los datos ya vienen con season y season_type
            # No necesitamos agregar nada adicional, solo cargar los datos
            
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
        
        # Para games, NO filtrar columnas - usar todas las del CSV procesado
        # Esto permite incluir campos calculados como home_win y point_diff
        if table_meta['table_name'] != 'games':
            # Para otras tablas, seleccionar solo columnas que existen en la tabla
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
        
        # Para player_stats y team_stats, mantener season como VARCHAR (formato "2023-24")
        if table_meta['table_name'] in ['player_stats', 'team_stats']:
            # Asegurar que player_id sea numérico (solo para player_stats)
            if table_meta['table_name'] == 'player_stats' and 'player_id' in df.columns:
                df['player_id'] = pd.to_numeric(df['player_id'], errors='coerce')
                df['player_id'] = df['player_id'].where(pd.notna(df['player_id']), None)
            
            # Para team_stats, convertir columnas numéricas correctamente
            if table_meta['table_name'] == 'team_stats':
                # Columnas que deben ser enteras (solo rank)
                integer_columns = ['rank']
                for col in integer_columns:
                    if col in df.columns:
                        # Convertir a float primero para manejar valores como "47.0"
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        # Convertir a int, pero mantener None para valores faltantes
                        df[col] = df[col].apply(lambda x: int(x) if pd.notna(x) else None)
                
                # Todas las columnas estadísticas deben ser flotantes (incluyendo off_fgm, def_fgm)
                float_columns = [
                    'off_fgm', 'off_fga', 'off_fg_pct', 'off_3pm', 'off_3pa', 'off_3p_pct', 
                    'off_ftm', 'off_fta', 'off_ft_pct', 'off_or', 'off_dr', 'off_reb',
                    'off_ast', 'off_stl', 'off_blk', 'off_to', 'off_pf', 'off_pts',
                    'def_fgm', 'def_fga', 'def_fg_pct', 'def_3pm', 'def_3pa', 'def_3p_pct',
                    'def_ftm', 'def_fta', 'def_ft_pct', 'def_or', 'def_dr', 'def_reb',
                    'def_ast', 'def_stl', 'def_blk', 'def_to', 'def_pf', 'def_pts'
                ]
                for col in float_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                        df[col] = df[col].where(pd.notna(df[col]), None)
            
            # Season y season_type ya vienen como string, mantenerlos así
        # Convertir season a integer si existe (para otras tablas)
        elif 'season' in df.columns and table_meta['table_name'] not in ['player_stats', 'team_stats']:
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
        
        # Verificar duplicados antes de cargar
        if table_name == 'player_stats':
            # Eliminar duplicados basados en player_id + season + season_type
            initial_count = len(df)
            df = df.drop_duplicates(subset=['player_id', 'season', 'season_type'], keep='first')
            if len(df) < initial_count:
                print(f"    ⚠️  Se eliminaron {initial_count - len(df)} duplicados antes de cargar")
        
        cursor = self.conn.cursor()
        
        # El DataFrame ya viene con columnas sanitizadas desde _clean_dataframe
        # Crear archivo temporal CSV
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as f:
            temp_file = f.name
            df.to_csv(f, index=False, header=False, na_rep='\\N')
        
        try:
            # Usar INSERT con ON CONFLICT DO NOTHING para omitir duplicados
            # Esto es más lento que COPY pero permite manejar duplicados correctamente
            self._insert_with_skip_duplicates(table_name, df, columns_meta)
            
        except Exception as e:
            self.conn.rollback()
            print(f"    ⚠️  Error cargando {table_name}: {e}")
        finally:
            cursor.close()
            # Limpiar archivo temporal
            os.unlink(temp_file)
    
    def _insert_with_skip_duplicates(self, table_name: str, df: pd.DataFrame, columns_meta: Dict):
        """Insertar registros usando COPY con manejo de duplicados"""
        cursor = self.conn.cursor()
        
        # El DataFrame ya viene con columnas sanitizadas desde _clean_dataframe
        columns = list(df.columns)
        
        # Obtener metadata de la tabla para saber si tiene PK
        table_meta = self.metadata.get(table_name, {})
        pk_col = table_meta.get('primary_key')
        
        # Para games, obtener todas las columnas de la base de datos y sincronizar
        if table_name == 'games':
            # Obtener columnas existentes en la DB
            cursor.execute(f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (self.config.schema, table_name))
            
            db_columns_info = {}
            for row in cursor.fetchall():
                col_name, data_type, max_length = row
                if data_type == 'character varying':
                    pg_type = f"VARCHAR({max_length})" if max_length else 'TEXT'
                elif data_type == 'bigint':
                    pg_type = 'BIGINT'
                elif data_type == 'double precision':
                    pg_type = 'DOUBLE PRECISION'
                elif data_type == 'integer':
                    pg_type = 'INTEGER'
                elif data_type == 'date':
                    pg_type = 'DATE'
                else:
                    pg_type = data_type.upper()
                db_columns_info[col_name] = pg_type
            
            # Obtener todas las columnas de la DB primero
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
            """, (self.config.schema, table_name))
            all_db_columns = [row[0] for row in cursor.fetchall()]
            
            # Agregar columnas faltantes del CSV a la tabla
            columns_info = table_meta.get('columns', {})
            for col in columns:
                if col not in db_columns_info:
                    # Columna no existe en DB, agregarla
                    col_info = columns_info.get(col, {})
                    col_type = col_info.get('type', 'TEXT')
                    # Para estructura dinámica, todas las columnas nuevas son nullable
                    nullable = 'NULL'
                    
                    try:
                        alter_sql = f"""
                            ALTER TABLE {self.config.schema}.{table_name}
                            ADD COLUMN IF NOT EXISTS "{col}" {col_type} {nullable}
                        """
                        cursor.execute(alter_sql)
                        self.conn.commit()
                        print(f"    ✓ Columna {col} agregada a {table_name}")
                        # Actualizar lista de columnas de DB
                        all_db_columns.append(col)
                    except Exception as e:
                        print(f"    ⚠️  Error agregando columna {col}: {e}")
                        self.conn.rollback()
            
            # Asegurar que todas las columnas existentes sean nullable (excepto PK)
            # Esto permite que la base de datos se adapte dinámicamente al CSV
            pk_col = table_meta.get('primary_key')
            for col_name in all_db_columns:
                if col_name != pk_col:
                    try:
                        # Verificar si la columna tiene restricción NOT NULL
                        cursor.execute(f"""
                            SELECT is_nullable
                            FROM information_schema.columns
                            WHERE table_schema = %s 
                            AND table_name = %s 
                            AND column_name = %s
                        """, (self.config.schema, table_name, col_name))
                        result = cursor.fetchone()
                        if result and result[0] == 'NO':
                            # La columna es NOT NULL, cambiarla a NULL
                            alter_sql = f"""
                                ALTER TABLE {self.config.schema}.{table_name}
                                ALTER COLUMN "{col_name}" DROP NOT NULL
                            """
                            cursor.execute(alter_sql)
                            self.conn.commit()
                    except Exception as e:
                        # Ignorar errores (puede que la columna no tenga restricción)
                        pass
            
            # Para games, usar TODAS las columnas del DataFrame (incluyendo home_win, point_diff, etc.)
            # Agregar columnas faltantes del DataFrame a la DB si no existen
            for col in df.columns:
                if col not in all_db_columns:
                    # Columna del CSV no existe en DB, agregarla
                    if col in df.columns:
                        dtype = df[col].dtype
                        if pd.api.types.is_integer_dtype(dtype):
                            col_type = 'BIGINT'
                        elif pd.api.types.is_float_dtype(dtype):
                            col_type = 'DOUBLE PRECISION'
                        elif pd.api.types.is_datetime64_any_dtype(dtype):
                            col_type = 'DATE'
                        else:
                            col_type = 'TEXT'
                        
                        try:
                            alter_sql = f"""
                                ALTER TABLE {self.config.schema}.{table_name}
                                ADD COLUMN IF NOT EXISTS "{col}" {col_type} NULL
                            """
                            cursor.execute(alter_sql)
                            self.conn.commit()
                            print(f"    ✓ Columna {col} agregada a {table_name}")
                            all_db_columns.append(col)
                        except Exception as e:
                            print(f"    ⚠️  Error agregando columna {col}: {e}")
                            self.conn.rollback()
            
            # Agregar columnas faltantes de la DB al DataFrame con None
            for col in all_db_columns:
                if col not in df.columns:
                    df[col] = None
            
            # Usar TODAS las columnas del DataFrame (no solo las de la DB)
            columns = list(df.columns)
        
        # Crear tabla temporal para cargar datos
        temp_table = f"{table_name}_temp_{int(pd.Timestamp.now().timestamp())}"
        
        try:
            # Crear tabla temporal basándose en las columnas del DataFrame y metadatos
            # Esto es necesario porque la tabla original puede no tener todas las columnas del DataFrame
            table_meta = self.metadata.get(table_name, {})
            columns_info = table_meta.get('columns', {})
            
            # Construir definición de columnas para la tabla temporal
            # Las columnas del DataFrame ya vienen sanitizadas desde _clean_dataframe
            temp_columns = []
            for col in columns:
                # La columna ya está sanitizada, buscar en metadatos o inferir tipo
                if col in columns_info:
                    col_info = columns_info.get(col, {})
                    col_type = col_info.get('type', 'TEXT')
                else:
                    # Inferir tipo desde el DataFrame
                    if col in df.columns:
                        dtype = df[col].dtype
                        if pd.api.types.is_integer_dtype(dtype):
                            col_type = 'BIGINT'
                        elif pd.api.types.is_float_dtype(dtype):
                            col_type = 'DOUBLE PRECISION'
                        elif pd.api.types.is_datetime64_any_dtype(dtype):
                            col_type = 'DATE'
                        else:
                            col_type = 'TEXT'
                    else:
                        col_type = 'TEXT'
                temp_columns.append(f'"{col}" {col_type}')
            
            create_temp_sql = f"""
                CREATE TEMP TABLE {temp_table} (
                    {','.join(temp_columns)}
                )
            """
            cursor.execute(create_temp_sql)
            
            # Cargar datos en tabla temporal usando COPY (rápido)
            # Antes de escribir, asegurar que los enteros se escriban sin decimales
            df_for_copy = df.copy()
            for col in df_for_copy.columns:
                col_info = columns_info.get(col, {})
                col_type = col_info.get('type', 'TEXT')
                # Si la columna es BIGINT o INTEGER, convertir a int antes de escribir
                if 'BIGINT' in col_type.upper() or 'INTEGER' in col_type.upper():
                    df_for_copy[col] = df_for_copy[col].apply(
                        lambda x: int(x) if pd.notna(x) and x != '' else None
                    )
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as f:
                temp_file = f.name
                # No usar float_format para preservar decimales en valores flotantes
                df_for_copy.to_csv(f, index=False, header=False, na_rep='\\N')
            
            columns_str = ','.join(columns)
            copy_sql = f"""
                COPY {temp_table} ({columns_str})
                FROM STDIN
                WITH (FORMAT CSV, NULL '\\N', ENCODING 'UTF8')
            """
            
            with open(temp_file, 'r', encoding='utf-8') as f:
                cursor.copy_expert(copy_sql, f)
            
            # Insertar desde tabla temporal a tabla real, omitiendo duplicados
            if table_name == 'player_stats':
                # Para player_stats, usar player_id + season + season_type como clave única
                insert_sql = f"""
                    INSERT INTO {self.config.schema}.{table_name} ({columns_str})
                    SELECT {columns_str}
                    FROM {temp_table} t
                    WHERE NOT EXISTS (
                        SELECT 1 FROM {self.config.schema}.{table_name} e
                        WHERE e.player_id = t.player_id 
                        AND e.season = t.season 
                        AND e.season_type = t.season_type
                    )
                """
            elif table_name == 'team_stats':
                # Para team_stats, usar team_abbrev + season + season_type + category como clave única
                # Si category no está en las columnas, usar solo team_abbrev + season + season_type
                if 'category' in columns:
                    insert_sql = f"""
                        INSERT INTO {self.config.schema}.{table_name} ({columns_str})
                        SELECT {columns_str}
                        FROM {temp_table} t
                        WHERE NOT EXISTS (
                            SELECT 1 FROM {self.config.schema}.{table_name} e
                            WHERE e.team_abbrev = t.team_abbrev 
                            AND e.season = t.season 
                            AND e.season_type = t.season_type
                            AND e.category = t.category
                        )
                    """
                else:
                    insert_sql = f"""
                        INSERT INTO {self.config.schema}.{table_name} ({columns_str})
                        SELECT {columns_str}
                        FROM {temp_table} t
                        WHERE NOT EXISTS (
                            SELECT 1 FROM {self.config.schema}.{table_name} e
                            WHERE e.team_abbrev = t.team_abbrev 
                            AND e.season = t.season 
                            AND e.season_type = t.season_type
                        )
                    """
            elif pk_col:
                # Para tablas con PK
                if table_name == 'games':
                    # Para games, como ya truncamos la tabla, solo insertar
                    insert_sql = f"""
                        INSERT INTO {self.config.schema}.{table_name} ({columns_str})
                        SELECT {columns_str}
                        FROM {temp_table}
                    """
                else:
                    # Para otras tablas con PK, solo insertar si no existe
                    insert_sql = f"""
                        INSERT INTO {self.config.schema}.{table_name} ({columns_str})
                        SELECT {columns_str}
                        FROM {temp_table}
                        ON CONFLICT ({pk_col}) DO NOTHING
                    """
            else:
                # Para otras tablas sin PK, insertar todos (pueden tener duplicados)
                insert_sql = f"""
                    INSERT INTO {self.config.schema}.{table_name} ({columns_str})
                    SELECT {columns_str}
                    FROM {temp_table}
                """
            
            cursor.execute(insert_sql)
            inserted_count = cursor.rowcount
            
            self.conn.commit()
            print(f"    ✓ {inserted_count}/{len(df)} registros nuevos insertados (duplicados omitidos)")
            
        except Exception as e:
            self.conn.rollback()
            # Fallback: insertar uno por uno
            print(f"    ⚠️  Error con tabla temporal, usando inserción individual: {e}")
            self._insert_one_by_one(table_name, df, columns)
        finally:
            cursor.close()
            # Limpiar archivo temporal
            if 'temp_file' in locals():
                os.unlink(temp_file)
    
    def _insert_one_by_one(self, table_name: str, df: pd.DataFrame, columns: List[str]):
        """Insertar o actualizar registros uno por uno como fallback"""
        cursor = self.conn.cursor()
        
        # Obtener PK de la tabla
        table_meta = self.metadata.get(table_name, {})
        pk_col = table_meta.get('primary_key')
        
        # Filtrar columnas que existen en la base de datos
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
        """, (self.config.schema, table_name))
        db_columns = [row[0] for row in cursor.fetchall()]
        
        # Solo usar columnas que existen en la DB
        valid_columns = [col for col in columns if col in db_columns]
        
        if not valid_columns:
            print(f"    ⚠️  No hay columnas válidas para cargar")
            cursor.close()
            return
        
        placeholders = ','.join(['%s'] * len(valid_columns))
        
        if pk_col and pk_col in valid_columns:
            # Para tablas con PK, usar UPSERT
            if table_name == 'games':
                # Para games, actualizar si existe
                update_cols = [col for col in valid_columns if col != pk_col]
                update_set = ','.join([f'"{col}" = EXCLUDED."{col}"' for col in update_cols])
                
                insert_sql = f"""
                    INSERT INTO {self.config.schema}.{table_name} ({','.join(valid_columns)})
                    VALUES ({placeholders})
                    ON CONFLICT ({pk_col}) DO UPDATE SET {update_set}
                """
            else:
                # Para otras tablas, solo insertar si no existe
                insert_sql = f"""
                    INSERT INTO {self.config.schema}.{table_name} ({','.join(valid_columns)})
                    VALUES ({placeholders})
                    ON CONFLICT ({pk_col}) DO NOTHING
                """
        else:
            # Sin PK, solo insertar
            insert_sql = f"""
                INSERT INTO {self.config.schema}.{table_name} ({','.join(valid_columns)})
                VALUES ({placeholders})
            """
        
        success_count = 0
        updated_count = 0
        
        for _, row in df.iterrows():
            try:
                values = tuple(row[col] for col in valid_columns)
                cursor.execute(insert_sql, values)
                
                if cursor.rowcount > 0:
                    if table_name == 'games' and pk_col and pk_col in valid_columns:
                        # Verificar si fue actualización o inserción
                        cursor.execute(f"""
                            SELECT COUNT(*) FROM {self.config.schema}.{table_name}
                            WHERE "{pk_col}" = %s
                        """, (row[pk_col],))
                        if cursor.fetchone()[0] > 0:
                            updated_count += 1
                        else:
                            success_count += 1
                    else:
                        success_count += 1
            except Exception as e:
                continue
        
        self.conn.commit()
        cursor.close()
        
        if updated_count > 0:
            print(f"    ✓ {success_count} nuevos, {updated_count} actualizados de {len(df)} registros")
        else:
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
    # response = input("¿Continuar con la carga? (s/n): ")
    response = 's'
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

