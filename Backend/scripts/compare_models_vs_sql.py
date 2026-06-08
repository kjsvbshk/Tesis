#!/usr/bin/env python3
"""
Script para comparar modelos SQLAlchemy con scripts de migración SQL
NO asume autoridad - reporta conflictos sin prejuicios
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.database import sys_engine, espn_engine, SysBase, EspnBase

# Importar todos los modelos
from app.models.user_accounts import UserAccount, Client, Administrator, Operator
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user_role import UserRole
from app.models.bet import Bet  # Legacy bet
from app.models.transaction import Transaction
from app.models.idempotency_key import IdempotencyKey
from app.models.request import Request
from app.models.model_version import ModelVersion
from app.models.prediction import Prediction
from app.models.provider import Provider
from app.models.provider_endpoint import ProviderEndpoint
from app.models.odds_snapshot import OddsSnapshot
from app.models.odds_line import OddsLine
from app.models.audit_log import AuditLog
from app.models.outbox import Outbox
from app.models.two_factor import UserTwoFactor
from app.models.user_session import UserSession
# ESPN models
from app.models.team import Team
from app.models.game import Game
from app.models.team_stats import TeamStatsGame
# ESPN Bet models
from app.models.espn_bet import BetType, BetStatus, Bet as EspnBet, BetSelection, BetResult, GameOdds

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class ModelSQLComparator:
    """Compara modelos SQLAlchemy con SQL real"""
    
    def __init__(self):
        self.conflicts = []
        self.migrations_dir = Path(__file__).parent.parent / "migrations"
        self.sql_files = list(self.migrations_dir.glob("*.sql"))
        
    def extract_sql_table_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Extrae definiciones de tablas de archivos SQL"""
        sql_tables = {}
        
        for sql_file in self.sql_files:
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Buscar CREATE TABLE statements
                create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:(\w+)\.)?(\w+)\s*\((.*?)\);'
                matches = re.finditer(create_table_pattern, content, re.IGNORECASE | re.DOTALL)
                
                for match in matches:
                    schema = match.group(1) or 'app'  # Default schema
                    table_name = match.group(2)
                    table_def = match.group(3)
                    
                    full_name = f"{schema}.{table_name}"
                    
                    # Extraer columnas
                    columns = self._parse_table_definition(table_def)
                    
                    if full_name not in sql_tables:
                        sql_tables[full_name] = {
                            'schema': schema,
                            'table': table_name,
                            'columns': columns,
                            'source_file': sql_file.name
                        }
            except Exception as e:
                print(f"⚠️  Error procesando {sql_file}: {e}", file=sys.stderr)
        
        return sql_tables
    
    def _parse_table_definition(self, table_def: str) -> Dict[str, Dict[str, Any]]:
        """Parsea la definición de tabla para extraer columnas"""
        columns = {}
        
        # Dividir por comas, pero respetar paréntesis
        lines = []
        current_line = ""
        paren_depth = 0
        
        for char in table_def:
            if char == '(':
                paren_depth += 1
                current_line += char
            elif char == ')':
                paren_depth -= 1
                current_line += char
            elif char == ',' and paren_depth == 0:
                lines.append(current_line.strip())
                current_line = ""
            else:
                current_line += char
        
        if current_line.strip():
            lines.append(current_line.strip())
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('PRIMARY KEY') or line.startswith('CONSTRAINT') or line.startswith('FOREIGN KEY'):
                continue
            
            # Extraer nombre de columna y tipo
            col_match = re.match(r'(\w+)\s+(\w+(?:\([^)]+\))?)', line)
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2)
                
                nullable = 'NULL' in line.upper() or 'NOT NULL' not in line.upper()
                has_default = 'DEFAULT' in line.upper()
                
                columns[col_name] = {
                    'type': col_type,
                    'nullable': nullable,
                    'has_default': has_default
                }
        
        return columns
    
    def get_sqlalchemy_tables(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene definiciones de tablas desde SQLAlchemy"""
        sqla_tables = {}
        
        # Inspeccionar tablas en esquema app
        inspector = sqlalchemy_inspect(sys_engine)
        app_tables = inspector.get_table_names(schema='app')
        
        for table_name in app_tables:
            full_name = f"app.{table_name}"
            columns = {}
            
            for col in inspector.get_columns(table_name, schema='app'):
                columns[col['name']] = {
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'default': col.get('default')
                }
            
            sqla_tables[full_name] = {
                'schema': 'app',
                'table': table_name,
                'columns': columns
            }
        
        # Inspeccionar tablas en esquema espn
        espn_inspector = sqlalchemy_inspect(espn_engine)
        espn_tables = espn_inspector.get_table_names(schema='espn')
        
        for table_name in espn_tables:
            full_name = f"espn.{table_name}"
            columns = {}
            
            for col in espn_inspector.get_columns(table_name, schema='espn'):
                columns[col['name']] = {
                    'type': str(col['type']),
                    'nullable': col['nullable'],
                    'default': col.get('default')
                }
            
            sqla_tables[full_name] = {
                'schema': 'espn',
                'table': table_name,
                'columns': columns
            }
        
        return sqla_tables
    
    def compare(self):
        """Compara modelos SQLAlchemy con SQL"""
        print("=" * 60)
        print("🔍 COMPARACIÓN: SQLAlchemy vs SQL")
        print("=" * 60)
        print()
        
        sql_tables = self.extract_sql_table_definitions()
        sqla_tables = self.get_sqlalchemy_tables()
        
        print(f"📊 Tablas en SQL (migraciones): {len(sql_tables)}")
        print(f"📊 Tablas en SQLAlchemy (BD real): {len(sqla_tables)}")
        print()
        
        # Comparar tablas que existen en ambos
        all_tables = set(sql_tables.keys()) | set(sqla_tables.keys())
        
        conflicts = []
        
        for table_name in sorted(all_tables):
            sql_def = sql_tables.get(table_name)
            sqla_def = sqla_tables.get(table_name)
            
            if sql_def and not sqla_def:
                conflicts.append({
                    'table': table_name,
                    'type': 'SQL_ONLY',
                    'message': f'Tabla definida en SQL pero no existe en BD real',
                    'source': sql_def.get('source_file', 'unknown')
                })
            elif sqla_def and not sql_def:
                conflicts.append({
                    'table': table_name,
                    'type': 'SQLALCHEMY_ONLY',
                    'message': f'Tabla existe en BD real pero no definida en migraciones SQL',
                })
            elif sql_def and sqla_def:
                # Comparar columnas
                sql_cols = set(sql_def['columns'].keys())
                sqla_cols = set(sqla_def['columns'].keys())
                
                missing_in_sqla = sql_cols - sqla_cols
                missing_in_sql = sqla_cols - sql_cols
                
                if missing_in_sqla:
                    conflicts.append({
                        'table': table_name,
                        'type': 'COLUMN_MISMATCH',
                        'message': f'Columnas en SQL pero no en BD: {", ".join(missing_in_sqla)}',
                        'details': {'missing_in_bd': list(missing_in_sqla)}
                    })
                
                if missing_in_sql:
                    conflicts.append({
                        'table': table_name,
                        'type': 'COLUMN_MISMATCH',
                        'message': f'Columnas en BD pero no en SQL: {", ".join(missing_in_sql)}',
                        'details': {'missing_in_sql': list(missing_in_sql)}
                    })
                
                # Comparar tipos de columnas comunes
                common_cols = sql_cols & sqla_cols
                for col_name in common_cols:
                    sql_type = sql_def['columns'][col_name]['type']
                    sqla_type = str(sqla_def['columns'][col_name]['type'])
                    
                    # Normalizar tipos para comparación
                    sql_type_norm = self._normalize_type(sql_type)
                    sqla_type_norm = self._normalize_type(sqla_type)
                    
                    if sql_type_norm != sqla_type_norm:
                        conflicts.append({
                            'table': table_name,
                            'column': col_name,
                            'type': 'TYPE_MISMATCH',
                            'message': f'Tipo diferente: SQL={sql_type}, BD={sqla_type}',
                            'details': {
                                'sql_type': sql_type,
                                'bd_type': sqla_type
                            }
                        })
        
        self.conflicts = conflicts
        return conflicts
    
    def _normalize_type(self, type_str: str) -> str:
        """Normaliza tipos para comparación"""
        type_str = type_str.upper()
        
        # Mapeos comunes
        mappings = {
            'INTEGER': 'INT',
            'BIGINT': 'BIGINT',
            'VARCHAR': 'VARCHAR',
            'TEXT': 'TEXT',
            'BOOLEAN': 'BOOL',
            'NUMERIC': 'NUMERIC',
            'FLOAT': 'FLOAT',
            'TIMESTAMP': 'TIMESTAMP',
            'DATE': 'DATE'
        }
        
        for key, value in mappings.items():
            if key in type_str:
                return value
        
        return type_str
    
    def generate_report(self) -> str:
        """Genera reporte de conflictos"""
        report = []
        report.append("# Comparación: SQLAlchemy vs SQL\n")
        report.append(f"**Total de conflictos**: {len(self.conflicts)}\n")
        report.append("\n## Conflictos Detectados\n")
        
        if not self.conflicts:
            report.append("✅ No se encontraron conflictos\n")
            return "\n".join(report)
        
        # Agrupar por tipo
        by_type = defaultdict(list)
        for conflict in self.conflicts:
            by_type[conflict['type']].append(conflict)
        
        for conflict_type, conflicts in sorted(by_type.items()):
            report.append(f"\n### {conflict_type} ({len(conflicts)})\n")
            
            for conflict in conflicts:
                report.append(f"\n#### `{conflict['table']}`\n")
                report.append(f"**Mensaje**: {conflict['message']}\n")
                
                if 'column' in conflict:
                    report.append(f"**Columna**: `{conflict['column']}`\n")
                
                if 'details' in conflict:
                    report.append("**Detalles**:\n")
                    for key, value in conflict['details'].items():
                        report.append(f"- {key}: {value}\n")
                
                if 'source' in conflict:
                    report.append(f"**Archivo SQL**: `{conflict['source']}`\n")
                
                report.append("\n**Decisión requerida**: Revisar y alinear definiciones\n")
        
        return "\n".join(report)
    
    def run(self):
        """Ejecuta la comparación"""
        conflicts = self.compare()
        
        # Generar reporte
        output_dir = Path(__file__).parent.parent / "data" / "schema_inspection"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report_file = output_dir / f"models_vs_sql_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"📄 Reporte: {report_file}")
        print()
        print("=" * 60)
        print("✅ Comparación completada")
        print("=" * 60)


if __name__ == "__main__":
    comparator = ModelSQLComparator()
    comparator.run()
