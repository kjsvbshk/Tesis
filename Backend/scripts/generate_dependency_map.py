#!/usr/bin/env python3
"""
Genera mapa de dependencias entre esquemas y tablas
Visualización usando Mermaid
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.core.config import settings


class DependencyMapper:
    """Genera mapa de dependencias"""
    
    def __init__(self):
        self.app_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        self.espn_engine = create_engine(settings.NBA_DATABASE_URL, pool_pre_ping=True)
        self.dependencies = []  # List of (from_schema, from_table, to_schema, to_table, has_constraint)
        self.tables_by_schema = defaultdict(set)
    
    def collect_dependencies(self):
        """Recolecta todas las dependencias"""
        schemas = [
            ('app', self.app_engine),
            ('espn', self.espn_engine),
            ('ml', self.app_engine),
            ('premier_league', self.app_engine)
        ]
        
        for schema_name, engine in schemas:
            try:
                with engine.connect() as conn:
                    conn.execute(text(f"SET search_path TO {schema_name}, public"))
                    conn.commit()
                    
                    # Verificar si existe
                    exists = conn.execute(text("""
                        SELECT EXISTS(
                            SELECT 1 FROM information_schema.schemata 
                            WHERE schema_name = :schema
                        )
                    """), {"schema": schema_name}).scalar()
                    
                    if not exists:
                        continue
                    
                    # Obtener tablas
                    tables_result = conn.execute(text("""
                        SELECT table_name
                        FROM information_schema.tables 
                        WHERE table_schema = :schema
                        AND table_type = 'BASE TABLE'
                    """), {"schema": schema_name})
                    
                    for row in tables_result:
                        self.tables_by_schema[schema_name].add(row[0])
                    
                    # Obtener foreign keys
                    fk_result = conn.execute(text("""
                        SELECT
                            tc.table_name,
                            ccu.table_schema AS foreign_schema,
                            ccu.table_name AS foreign_table
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = :schema
                    """), {"schema": schema_name})
                    
                    for fk in fk_result:
                        self.dependencies.append((
                            schema_name,
                            fk[0],
                            fk[1],
                            fk[2],
                            True  # has_constraint
                        ))
                    
                    # Detectar referencias lógicas (sin constraint)
                    # Buscar columnas que probablemente son FKs
                    for table_name in self.tables_by_schema[schema_name]:
                        cols_result = conn.execute(text("""
                            SELECT column_name, data_type
                            FROM information_schema.columns
                            WHERE table_schema = :schema
                            AND table_name = :table
                            AND column_name LIKE '%_id'
                        """), {"schema": schema_name, "table": table_name})
                        
                        for col in cols_result:
                            col_name = col[0]
                            # Verificar si ya tiene FK constraint
                            has_fk = any(
                                d[0] == schema_name and d[1] == table_name and d[3] == col_name.replace('_id', 's')
                                for d in self.dependencies
                            )
                            
                            if not has_fk and col_name in ['user_id', 'game_id', 'bet_id']:
                                # Referencia lógica probable
                                if col_name == 'user_id' and schema_name == 'espn':
                                    self.dependencies.append((
                                        schema_name,
                                        table_name,
                                        'app',
                                        'user_accounts',
                                        False  # no constraint
                                    ))
            except Exception as e:
                print(f"WARNING: Error procesando {schema_name}: {e}", file=sys.stderr)
    
    def generate_mermaid(self) -> str:
        """Genera diagrama Mermaid"""
        mermaid = []
        mermaid.append("graph TB")
        
        # Agrupar por esquema
        schema_nodes = {}
        for schema_name, tables in self.tables_by_schema.items():
            schema_nodes[schema_name] = []
            for table in sorted(tables):
                node_id = f"{schema_name}_{table}".replace('.', '_')
                schema_nodes[schema_name].append((node_id, table))
        
        # Crear subgrafos por esquema
        for schema_name, nodes in schema_nodes.items():
            if not nodes:
                continue
            mermaid.append(f"    subgraph {schema_name.replace('_', '')}[\"{schema_name}\"]")
            for node_id, table_name in nodes:
                mermaid.append(f"        {node_id}[\"{table_name}\"]")
            mermaid.append("    end")
        
        # Agregar dependencias
        for from_schema, from_table, to_schema, to_table, has_constraint in self.dependencies:
            from_id = f"{from_schema}_{from_table}".replace('.', '_')
            to_id = f"{to_schema}_{to_table}".replace('.', '_')
            
            if has_constraint:
                mermaid.append(f"    {from_id} -->|FK| {to_id}")
            else:
                mermaid.append(f"    {from_id} -.->|logical| {to_id}")
        
        return "\n".join(mermaid)
    
    def generate_report(self) -> str:
        """Genera reporte de dependencias"""
        report = []
        report.append("# Mapa de Dependencias entre Esquemas\n")
        report.append("\n## Diagrama Mermaid\n")
        report.append("```mermaid")
        report.append(self.generate_mermaid())
        report.append("```\n")
        
        report.append("\n## Dependencias Cross-Schema\n")
        cross_schema = [
            d for d in self.dependencies
            if d[0] != d[2]  # from_schema != to_schema
        ]
        
        if cross_schema:
            for from_schema, from_table, to_schema, to_table, has_constraint in cross_schema:
                constraint_marker = "[FK]" if has_constraint else "[Logical - no constraint]"
                report.append(f"- `{from_schema}.{from_table}` → `{to_schema}.{to_table}` {constraint_marker}")
        else:
            report.append("No hay dependencias cross-schema detectadas.\n")
        
        report.append("\n## Tablas Huérfanas\n")
        # Tablas sin dependencias entrantes ni salientes
        all_tables = set()
        referenced_tables = set()
        referencing_tables = set()
        
        for from_schema, from_table, to_schema, to_table, _ in self.dependencies:
            all_tables.add((from_schema, from_table))
            all_tables.add((to_schema, to_table))
            referenced_tables.add((to_schema, to_table))
            referencing_tables.add((from_schema, from_table))
        
        orphaned = []
        for schema_name, tables in self.tables_by_schema.items():
            for table in tables:
                table_key = (schema_name, table)
                if table_key not in referenced_tables and table_key not in referencing_tables:
                    # Excluir catálogos
                    if table not in ['bet_types', 'bet_statuses', 'roles', 'permissions']:
                        orphaned.append((schema_name, table))
        
        if orphaned:
            for schema_name, table in orphaned:
                report.append(f"- `{schema_name}.{table}`")
        else:
            report.append("No hay tablas huérfanas detectadas.\n")
        
        return "\n".join(report)
    
    def run(self):
        """Ejecuta el mapeo"""
        print("=" * 60)
        print("MAPEO DE DEPENDENCIAS")
        print("=" * 60)
        print()
        
        print("Recolectando dependencias...")
        self.collect_dependencies()
        print(f"  OK: {len(self.dependencies)} dependencias encontradas")
        print()
        
        # Generar reporte
        output_dir = Path(__file__).parent.parent / "data" / "schema_inspection"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report_file = output_dir / f"dependency_map_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"Reporte: {report_file}")
        print()
        print("=" * 60)
        print("Mapa de dependencias generado")
        print("=" * 60)


if __name__ == "__main__":
    mapper = DependencyMapper()
    mapper.run()
