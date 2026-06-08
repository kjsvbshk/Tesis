#!/usr/bin/env python3
"""
Script de inspección comprehensiva de esquemas de base de datos
Genera 3 niveles de salida:
1. JSON raw (máquina)
2. Markdown estructural (humano)
3. Alertas clasificadas por riesgo (decisiones)
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

# Configurar codificación UTF-8 para Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class SchemaInspector:
    """Inspector comprehensivo de esquemas"""
    
    def __init__(self):
        self.app_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        self.espn_engine = create_engine(settings.NBA_DATABASE_URL, pool_pre_ping=True)
        self.schemas = ['app', 'espn', 'ml', 'premier_league']
        self.results = {}
        self.alerts = {
            'high': [],
            'medium': [],
            'low': []
        }
    
    def inspect_schema(self, schema_name: str, engine) -> Dict[str, Any]:
        """Inspecciona un esquema completo"""
        schema_data = {
            'schema_name': schema_name,
            'tables': {},
            'foreign_keys': [],
            'indexes': {},
            'views': [],
            'functions': [],
            'constraints': {}
        }
        
        try:
            with engine.connect() as conn:
                # Establecer search_path
                conn.execute(text(f"SET search_path TO {schema_name}, public"))
                conn.commit()
                
                # Verificar si el esquema existe
                schema_exists = conn.execute(text("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = :schema_name
                    )
                """), {"schema_name": schema_name}).scalar()
                
                if not schema_exists:
                    return schema_data
                
                # Obtener tablas
                tables_result = conn.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables 
                    WHERE table_schema = :schema_name
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """), {"schema_name": schema_name})
                
                tables = [row[0] for row in tables_result.fetchall()]
                
                # Inspeccionar cada tabla
                for table_name in tables:
                    table_info = self._inspect_table(conn, schema_name, table_name)
                    schema_data['tables'][table_name] = table_info
                
                # Obtener foreign keys
                fks = self._get_foreign_keys(conn, schema_name)
                schema_data['foreign_keys'] = fks
                
                # Obtener índices
                indexes = self._get_indexes(conn, schema_name)
                schema_data['indexes'] = indexes
                
                # Obtener vistas
                views = self._get_views(conn, schema_name)
                schema_data['views'] = views
                
                # Obtener constraints
                constraints = self._get_constraints(conn, schema_name)
                schema_data['constraints'] = constraints
                
        except Exception as e:
            print(f"⚠️  Error inspeccionando esquema {schema_name}: {e}", file=sys.stderr)
        
        return schema_data
    
    def _inspect_table(self, conn, schema_name: str, table_name: str) -> Dict[str, Any]:
        """Inspecciona una tabla específica"""
        table_info = {
            'columns': {},
            'primary_key': None,
            'row_count': 0
        }
        
        # Obtener columnas
        columns_result = conn.execute(text("""
            SELECT 
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default,
                ordinal_position
            FROM information_schema.columns 
            WHERE table_schema = :schema_name AND table_name = :table_name
            ORDER BY ordinal_position
        """), {"schema_name": schema_name, "table_name": table_name})
        
        for col in columns_result:
            table_info['columns'][col[0]] = {
                'type': col[1],
                'max_length': col[2],
                'nullable': col[3] == 'YES',
                'default': col[4],
                'position': col[5]
            }
        
        # Obtener primary key
        pk_result = conn.execute(text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = :schema_name 
            AND tc.table_name = :table_name
            AND tc.constraint_type = 'PRIMARY KEY'
            ORDER BY kcu.ordinal_position
        """), {"schema_name": schema_name, "table_name": table_name})
        
        pk_columns = [row[0] for row in pk_result.fetchall()]
        if pk_columns:
            table_info['primary_key'] = pk_columns[0] if len(pk_columns) == 1 else pk_columns
        
        # Obtener row count (aproximado)
        try:
            count_result = conn.execute(text(f"""
                SELECT COUNT(*) FROM {schema_name}.{table_name}
            """))
            table_info['row_count'] = count_result.scalar()
        except:
            table_info['row_count'] = None
        
        return table_info
    
    def _get_foreign_keys(self, conn, schema_name: str) -> List[Dict[str, Any]]:
        """Obtiene foreign keys del esquema"""
        fks = []
        
        fk_result = conn.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = :schema_name
            ORDER BY tc.table_name, kcu.ordinal_position
        """), {"schema_name": schema_name})
        
        for fk in fk_result:
            fks.append({
                'table': fk[0],
                'column': fk[1],
                'foreign_schema': fk[2],
                'foreign_table': fk[3],
                'foreign_column': fk[4],
                'constraint_name': fk[5]
            })
        
        return fks
    
    def _get_indexes(self, conn, schema_name: str) -> Dict[str, List[str]]:
        """Obtiene índices del esquema"""
        indexes = defaultdict(list)
        
        idx_result = conn.execute(text("""
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = :schema_name
            ORDER BY tablename, indexname
        """), {"schema_name": schema_name})
        
        for idx in idx_result:
            indexes[idx[0]].append({
                'name': idx[1],
                'definition': idx[2]
            })
        
        return dict(indexes)
    
    def _get_views(self, conn, schema_name: str) -> List[str]:
        """Obtiene vistas del esquema"""
        views_result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = :schema_name
            ORDER BY table_name
        """), {"schema_name": schema_name})
        
        return [row[0] for row in views_result.fetchall()]
    
    def _get_constraints(self, conn, schema_name: str) -> Dict[str, List[Dict[str, Any]]]:
        """Obtiene constraints (CHECK, UNIQUE) del esquema"""
        constraints = defaultdict(list)
        
        check_result = conn.execute(text("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
                ON tc.constraint_name = cc.constraint_name
            WHERE tc.table_schema = :schema_name
            AND tc.constraint_type = 'CHECK'
        """), {"schema_name": schema_name})
        
        for check in check_result:
            constraints[check[0]].append({
                'type': 'CHECK',
                'name': check[1],
                'definition': check[2]
            })
        
        unique_result = conn.execute(text("""
            SELECT
                tc.table_name,
                tc.constraint_name,
                string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = :schema_name
            AND tc.constraint_type = 'UNIQUE'
            GROUP BY tc.table_name, tc.constraint_name
        """), {"schema_name": schema_name})
        
        for unique in unique_result:
            constraints[unique[0]].append({
                'type': 'UNIQUE',
                'name': unique[1],
                'columns': unique[2]
            })
        
        return dict(constraints)
    
    def detect_alerts(self):
        """Detecta alertas automáticamente"""
        # Alertas de FK cross-schema sin constraint
        for schema_name, schema_data in self.results.items():
            if schema_name not in ['app', 'espn']:
                continue
            
            # Buscar referencias cross-schema en código
            for fk in schema_data.get('foreign_keys', []):
                if fk['foreign_schema'] != schema_name:
                    # FK cross-schema con constraint (OK)
                    continue
            
            # Buscar columnas que probablemente referencian otros esquemas
            for table_name, table_info in schema_data.get('tables', {}).items():
                for col_name, col_info in table_info.get('columns', {}).items():
                    # Detectar user_id, game_id que probablemente son FKs cross-schema
                    if col_name.endswith('_id') and col_name in ['user_id', 'game_id']:
                        # Verificar si hay FK constraint
                        has_fk = any(
                            fk['table'] == table_name and fk['column'] == col_name
                            for fk in schema_data.get('foreign_keys', [])
                        )
                        if not has_fk:
                            if col_name == 'user_id' and schema_name == 'espn':
                                self.alerts['high'].append({
                                    'type': 'FK_CROSS_SCHEMA_NO_CONSTRAINT',
                                    'schema': schema_name,
                                    'table': table_name,
                                    'column': col_name,
                                    'message': f'{schema_name}.{table_name}.{col_name} probablemente referencia app.user_accounts.id sin FK constraint',
                                    'impact': 'Riesgo de integridad referencial, datos huérfanos posibles'
                                })
                            elif col_name == 'game_id' and schema_name == 'espn':
                                # game_id en espn probablemente referencia espn.games (mismo esquema)
                                # pero verificar tipo
                                pass
        
        # Alertas de type mismatch
        self._detect_type_mismatches()
        
        # Alertas de tablas huérfanas
        self._detect_orphaned_tables()
        
        # Alertas de vistas que dependen de tablas DEPRECATED
        self._detect_deprecated_dependencies()
    
    def _detect_type_mismatches(self):
        """Detecta type mismatches críticos"""
        # Buscar game_id en diferentes tablas
        game_id_types = {}
        
        for schema_name, schema_data in self.results.items():
            for table_name, table_info in schema_data.get('tables', {}).items():
                for col_name, col_info in table_info.get('columns', {}).items():
                    if col_name == 'game_id':
                        key = f"{schema_name}.{table_name}.{col_name}"
                        game_id_types[key] = col_info['type']
        
        # Comparar tipos
        if len(set(game_id_types.values())) > 1:
            mismatches = []
            for key, dtype in game_id_types.items():
                mismatches.append(f"{key}: {dtype}")
            
            self.alerts['high'].append({
                'type': 'TYPE_MISMATCH',
                'column': 'game_id',
                'details': mismatches,
                'message': 'game_id tiene tipos diferentes en diferentes tablas',
                'impact': 'Errores en joins, posible pérdida de datos si hay overflow'
            })
    
    def _detect_orphaned_tables(self):
        """Detecta tablas huérfanas (sin referencias entrantes ni salientes)"""
        # Construir grafo de dependencias
        referenced_tables = set()
        referencing_tables = set()
        
        for schema_name, schema_data in self.results.items():
            for fk in schema_data.get('foreign_keys', []):
                ref_key = f"{fk['foreign_schema']}.{fk['foreign_table']}"
                ref_by_key = f"{schema_name}.{fk['table']}"
                referenced_tables.add(ref_key)
                referencing_tables.add(ref_by_key)
        
        # Encontrar tablas que no referencian ni son referenciadas
        for schema_name, schema_data in self.results.items():
            for table_name in schema_data.get('tables', {}).keys():
                table_key = f"{schema_name}.{table_name}"
                if table_key not in referenced_tables and table_key not in referencing_tables:
                    # Verificar si es una tabla de catálogo o configuración (OK)
                    if table_name not in ['bet_types', 'bet_statuses', 'roles', 'permissions']:
                        self.alerts['medium'].append({
                            'type': 'ORPHANED_TABLE',
                            'schema': schema_name,
                            'table': table_name,
                            'message': f'{table_key} no tiene referencias entrantes ni salientes',
                            'impact': 'Posible tabla no utilizada o falta de relaciones'
                        })
    
    def _detect_deprecated_dependencies(self):
        """Detecta dependencias en tablas DEPRECATED"""
        deprecated_tables = ['app.users', 'app.bets']
        
        for schema_name, schema_data in self.results.items():
            for view_name in schema_data.get('views', []):
                # Verificar si la vista depende de tablas deprecated
                # (esto requeriría parsear la definición de la vista)
                pass
            
            for fk in schema_data.get('foreign_keys', []):
                ref_key = f"{fk['foreign_schema']}.{fk['foreign_table']}"
                if ref_key in deprecated_tables:
                    self.alerts['high'].append({
                        'type': 'DEPRECATED_DEPENDENCY',
                        'schema': schema_name,
                        'table': fk['table'],
                        'depends_on': ref_key,
                        'message': f'{schema_name}.{fk["table"]} tiene FK a tabla DEPRECATED {ref_key}',
                        'impact': 'Requiere migración antes de eliminar tabla deprecated'
                    })
    
    def generate_json_output(self) -> str:
        """Genera salida JSON raw"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'schemas': self.results,
            'alerts': self.alerts
        }
        return json.dumps(output, indent=2, default=str)
    
    def generate_markdown_output(self) -> str:
        """Genera salida Markdown estructural"""
        md = []
        md.append("# Inspección Comprehensiva de Esquemas de Base de Datos\n")
        md.append(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for schema_name, schema_data in self.results.items():
            md.append(f"\n## Esquema: `{schema_name}`\n")
            
            tables = schema_data.get('tables', {})
            if not tables:
                md.append("*Esquema no existe o no tiene tablas*\n")
                continue
            
            md.append(f"**Total de tablas**: {len(tables)}\n")
            md.append("\n### Tablas\n")
            
            for table_name, table_info in sorted(tables.items()):
                md.append(f"\n#### `{table_name}`\n")
                md.append(f"- **Columnas**: {len(table_info.get('columns', {}))}")
                if table_info.get('primary_key'):
                    md.append(f"\n- **Primary Key**: `{table_info['primary_key']}`")
                if table_info.get('row_count') is not None:
                    md.append(f"\n- **Filas**: {table_info['row_count']:,}")
                
                # Columnas principales
                md.append("\n- **Columnas principales**:")
                for col_name, col_info in list(table_info.get('columns', {}).items())[:10]:
                    nullable = "NULL" if col_info['nullable'] else "NOT NULL"
                    md.append(f"  - `{col_name}`: {col_info['type']} {nullable}")
                if len(table_info.get('columns', {})) > 10:
                    md.append(f"  - ... y {len(table_info.get('columns', {})) - 10} más")
            
            # Foreign Keys
            fks = schema_data.get('foreign_keys', [])
            if fks:
                md.append("\n### Foreign Keys\n")
                for fk in fks[:20]:  # Limitar a 20
                    cross_schema = "⚠️ " if fk['foreign_schema'] != schema_name else ""
                    md.append(f"- {cross_schema}`{fk['table']}.{fk['column']}` → `{fk['foreign_schema']}.{fk['foreign_table']}.{fk['foreign_column']}`")
                if len(fks) > 20:
                    md.append(f"- ... y {len(fks) - 20} más")
        
        return "\n".join(md)
    
    def generate_alerts_output(self) -> str:
        """Genera salida de alertas clasificadas"""
        alerts_md = []
        alerts_md.append("# Alertas de Inspección de Esquemas\n")
        alerts_md.append(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        for severity in ['high', 'medium', 'low']:
            severity_alerts = self.alerts[severity]
            if not severity_alerts:
                continue
            
            severity_title = {
                'high': '🔴 Alto',
                'medium': '🟡 Medio',
                'low': '🟢 Bajo'
            }[severity]
            
            alerts_md.append(f"\n## {severity_title} Riesgo ({len(severity_alerts)} alertas)\n")
            
            for alert in severity_alerts:
                alerts_md.append(f"\n### {alert.get('type', 'UNKNOWN')}\n")
                alerts_md.append(f"**Mensaje**: {alert.get('message', 'N/A')}\n")
                if 'impact' in alert:
                    alerts_md.append(f"**Impacto**: {alert['impact']}\n")
                if 'schema' in alert:
                    alerts_md.append(f"**Esquema**: `{alert['schema']}`\n")
                if 'table' in alert:
                    alerts_md.append(f"**Tabla**: `{alert['table']}`\n")
                if 'details' in alert:
                    alerts_md.append("**Detalles**:\n")
                    for detail in alert['details']:
                        alerts_md.append(f"- {detail}\n")
        
        return "\n".join(alerts_md)
    
    def run(self):
        """Ejecuta la inspección completa"""
        print("=" * 60)
        print("🔍 INSPECCIÓN COMPREHENSIVA DE ESQUEMAS")
        print("=" * 60)
        print()
        
        # Inspeccionar esquemas
        print("📊 Inspeccionando esquemas...")
        for schema_name in self.schemas:
            print(f"  - {schema_name}...", end=" ")
            if schema_name in ['app']:
                engine = self.app_engine
            elif schema_name in ['espn']:
                engine = self.espn_engine
            else:
                # ml y premier_league usan la misma conexión que app
                engine = self.app_engine
            
            schema_data = self.inspect_schema(schema_name, engine)
            self.results[schema_name] = schema_data
            
            table_count = len(schema_data.get('tables', {}))
            print(f"✅ {table_count} tablas")
        
        print()
        print("🔍 Detectando alertas...")
        self.detect_alerts()
        
        total_alerts = sum(len(alerts) for alerts in self.alerts.values())
        print(f"  ✅ {total_alerts} alertas detectadas")
        print()
        
        # Generar salidas
        output_dir = Path(__file__).parent.parent / "data" / "schema_inspection"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON
        json_file = output_dir / f"inspection_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_json_output())
        print(f"📄 JSON: {json_file}")
        
        # Markdown
        md_file = output_dir / f"inspection_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_markdown_output())
        print(f"📄 Markdown: {md_file}")
        
        # Alertas
        alerts_file = output_dir / f"alerts_{timestamp}.md"
        with open(alerts_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_alerts_output())
        print(f"📄 Alertas: {alerts_file}")
        
        print()
        print("=" * 60)
        print("✅ Inspección completada")
        print("=" * 60)


if __name__ == "__main__":
    inspector = SchemaInspector()
    inspector.run()
