import pytest
import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture para directorio de datos de prueba."""
    return Path(__file__).parent.parent / "data"

@pytest.fixture(scope="session")
def raw_data_dir(test_data_dir):
    """Fixture para directorio de datos raw."""
    return test_data_dir / "raw"

@pytest.fixture(scope="session")
def processed_data_dir(test_data_dir):
    """Fixture para directorio de datos procesados."""
    return test_data_dir / "processed"

@pytest.fixture(scope="session")
def logs_dir():
    """Fixture para directorio de logs."""
    return Path(__file__).parent.parent / "logs"
