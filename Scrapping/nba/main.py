from espn.espn_scraper import run_scraper
from loguru import logger
import schedule
import time
import os
from datetime import datetime

# Configurar logging rotativo
logger.add(
    "logs/scraper_{time}.log", 
    rotation="1 week",
    retention="1 month",
    compression="zip",
    level="INFO"
)

def job():
    """
    Tarea programada de scraping diario.
    """
    logger.info("=== INICIANDO SCRAPING NBA DIARIO ===")
    start_time = datetime.now()
    
    try:
        # Ejecutar scraping completo
        success = run_scraper(limit=100)
        
        if success:
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"=== SCRAPING COMPLETADO EXITOSAMENTE ✅ ===")
            logger.info(f"Duración total: {duration}")
        else:
            logger.error("=== SCRAPING FALLÓ ❌ ===")
            
    except Exception as e:
        logger.error(f"=== ERROR CRÍTICO EN SCRAPING: {e} ===")
        # Aquí se puede agregar notificación por email/Discord

def run_scheduler():
    """
    Ejecutar scheduler principal.
    """
    logger.info("=== INICIANDO SCHEDULER NBA SCRAPER ===")
    logger.info("Scraping programado diariamente a las 03:00")
    
    # Programar tarea diaria
    schedule.every().day.at("03:00").do(job)
    
    # Ejecutar bucle principal
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
        except KeyboardInterrupt:
            logger.info("=== SCHEDULER DETENIDO POR USUARIO ===")
            break
        except Exception as e:
            logger.error(f"Error en scheduler: {e}")
            time.sleep(300)  # Esperar 5 minutos antes de reintentar

if __name__ == "__main__":
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    # Ejecutar scheduler
    run_scheduler()
