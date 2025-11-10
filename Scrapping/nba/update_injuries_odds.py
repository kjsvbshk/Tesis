#!/usr/bin/env python3
"""
Script para actualizar Injuries y Odds de forma fácil y rápida.

Por defecto, solo actualiza los archivos CSV/JSON en data/raw/.
Para actualizar también la base de datos, usa la opción --load-db.

Uso:
    python update_injuries_odds.py              # Actualiza ambos (solo archivos)
    python update_injuries_odds.py --injuries   # Solo injuries (solo archivos)
    python update_injuries_odds.py --odds       # Solo odds (solo archivos)
    python update_injuries_odds.py --load-db    # Actualiza ambos y carga a DB
    python update_injuries_odds.py --injuries --load-db  # Injuries y carga a DB
    python update_injuries_odds.py --odds --load-db      # Odds y carga a DB
"""

import sys
import argparse
from datetime import datetime
from loguru import logger

# Configurar logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO"
)

def update_injuries():
    """Actualizar reportes de lesiones."""
    try:
        logger.info("=" * 60)
        logger.info("ACTUALIZANDO REPORTES DE LESIONES")
        logger.info("=" * 60)
        
        from espn.injuries_scraper import scrape_current_injuries
        
        scrape_current_injuries()
        
        logger.info("✓ Reportes de lesiones actualizados exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error al actualizar reportes de lesiones: {e}")
        return False

def update_odds():
    """Actualizar cuotas de apuestas."""
    try:
        logger.info("=" * 60)
        logger.info("ACTUALIZANDO CUOTAS DE APUESTAS")
        logger.info("=" * 60)
        
        from espn.odds_scraper import scrape_current_odds
        
        scrape_current_odds()
        
        logger.info("✓ Cuotas de apuestas actualizadas exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error al actualizar cuotas de apuestas: {e}")
        return False

def load_to_database():
    """Cargar injuries y odds a la base de datos."""
    try:
        logger.info("=" * 60)
        logger.info("CARGANDO DATOS A BASE DE DATOS")
        logger.info("=" * 60)
        
        # Importar y ejecutar el sistema de carga
        from load_data import Config, DataAnalyzer, RelationshipDetector, DDLGenerator, DataLoader
        
        # Cargar configuración
        config = Config()
        
        # Analizar solo injuries y odds
        analyzer = DataAnalyzer(config)
        metadata = {}
        
        # Analizar solo las tablas que necesitamos
        analyzer._analyze_injuries()
        analyzer._analyze_odds()
        
        if 'injuries' in analyzer.metadata:
            metadata['injuries'] = analyzer.metadata['injuries']
        if 'odds' in analyzer.metadata:
            metadata['odds'] = analyzer.metadata['odds']
        
        if not metadata:
            logger.warning("No se encontraron datos para cargar")
            return False
        
        # Detectar relaciones
        detector = RelationshipDetector(metadata)
        relationships = detector.detect_relationships()
        
        # Generar DDL
        ddl_generator = DDLGenerator(metadata, relationships, config.schema)
        ddl_statements = ddl_generator.generate_ddl()
        
        # Cargar datos
        loader = DataLoader(config, metadata)
        loader.connect()
        loader.execute_ddl(ddl_statements)
        
        # Cargar solo injuries y odds
        for table_name, table_meta in metadata.items():
            logger.info(f"Cargando {table_name}...")
            
            # Obtener conteo antes de cargar
            count_before = loader._count_records(table_name)
            
            if table_meta['source_type'] == 'csv':
                loader._load_from_csv(table_name, table_meta)
            elif table_meta['source_type'] == 'json':
                loader._load_from_json(table_name, table_meta)
            
            # Verificar carga
            count_after = loader._count_records(table_name)
            new_records = count_after - count_before
            logger.info(f"  ✓ {table_name}: {count_after} registros totales ({new_records} nuevos)")
        
        loader.disconnect()
        
        logger.info("✓ Datos cargados a la base de datos exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error al cargar datos a la base de datos: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Actualizar Injuries y Odds de NBA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python update_injuries_odds.py              # Actualiza ambos
  python update_injuries_odds.py --injuries   # Solo injuries
  python update_injuries_odds.py --odds      # Solo odds
  python update_injuries_odds.py --load-db   # Actualiza y carga a DB
        """
    )
    
    parser.add_argument(
        '--injuries',
        action='store_true',
        help='Actualizar solo reportes de lesiones'
    )
    
    parser.add_argument(
        '--odds',
        action='store_true',
        help='Actualizar solo cuotas de apuestas'
    )
    
    parser.add_argument(
        '--load-db',
        action='store_true',
        help='Cargar datos a la base de datos después de actualizar'
    )
    
    args = parser.parse_args()
    
    # Si no se especifica ninguno, actualizar ambos
    update_both = not args.injuries and not args.odds
    
    start_time = datetime.now()
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("ACTUALIZACION DE INJURIES Y ODDS - NBA")
    logger.info("=" * 60)
    logger.info(f"Inicio: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    results = {
        'injuries': None,
        'odds': None
    }
    
    # Actualizar injuries
    if update_both or args.injuries:
        results['injuries'] = update_injuries()
        logger.info("")
    
    # Actualizar odds
    if update_both or args.odds:
        results['odds'] = update_odds()
        logger.info("")
    
    # Cargar a base de datos si se solicita
    db_loaded = None
    if args.load_db:
        db_loaded = load_to_database()
        logger.info("")
    
    # Resumen final
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("=" * 60)
    logger.info("RESUMEN DE ACTUALIZACION")
    logger.info("=" * 60)
    
    if results['injuries'] is not None:
        status = "✓ EXITOSO" if results['injuries'] else "✗ FALLIDO"
        logger.info(f"Injuries: {status}")
    
    if results['odds'] is not None:
        status = "✓ EXITOSO" if results['odds'] else "✗ FALLIDO"
        logger.info(f"Odds: {status}")
    
    if db_loaded is not None:
        status = "✓ EXITOSO" if db_loaded else "✗ FALLIDO"
        logger.info(f"Base de datos: {status}")
    
    logger.info(f"Tiempo total: {duration.total_seconds():.2f} segundos")
    logger.info(f"Fin: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    logger.info("")
    
    # Retornar código de salida apropiado
    if results['injuries'] is False or results['odds'] is False or (db_loaded is False):
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

