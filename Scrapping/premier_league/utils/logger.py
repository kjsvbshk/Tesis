import os
from loguru import logger
from datetime import datetime

def setup_logger():
    """
    Configurar logger con loguru según especificaciones:
    - Guardar logs diarios en logs/premier_league_scraper.log
    - Niveles: INFO (éxito), WARNING (fallos parciales), ERROR (fallos críticos)
    """
    # Crear directorio de logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    # Configurar formato de log
    log_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    
    # Configurar archivo de log diario
    log_file = f"logs/premier_league_scraper_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Remover handlers por defecto
    logger.remove()
    
    # Agregar handler para archivo con rotación diaria
    logger.add(
        log_file,
        format=log_format,
        level="INFO",
        rotation="1 day",
        retention="30 days",
        compression="zip"
    )
    
    # Agregar handler para consola
    logger.add(
        lambda msg: print(msg, end=""),
        format=log_format,
        level="INFO",
        colorize=True
    )
    
    return logger

# Configurar logger global
setup_logger()

