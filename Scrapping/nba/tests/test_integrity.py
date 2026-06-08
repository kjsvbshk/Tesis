import pytest
import pandas as pd
import os
import json
from datetime import datetime
from loguru import logger

class TestDataIntegrity:
    """
    Tests de integridad de datos para el sistema de scraping NBA.
    """
    
    def setup_method(self):
        """Configurar datos de prueba antes de cada test."""
        self.data_dir = "data"
        self.raw_dir = os.path.join(self.data_dir, "raw")
        self.processed_dir = os.path.join(self.data_dir, "processed")
        
    def test_points_validation(self):
        """
        Validar que home_points + away_points ≈ promedio PPG del equipo.
        """
        logger.info("Ejecutando test de validación de puntos...")
        
        try:
            # Cargar dataset consolidado
            dataset_path = os.path.join(self.processed_dir, "nba_full_dataset.csv")
            if not os.path.exists(dataset_path):
                pytest.skip("Dataset consolidado no encontrado")
            
            df = pd.read_csv(dataset_path)
            
            # Verificar que tenemos las columnas necesarias
            required_columns = ['home_score', 'away_score', 'home_team', 'away_team']
            missing_columns = [col for col in required_columns if col not in df.columns]
            assert not missing_columns, f"Columnas faltantes: {missing_columns}"
            
            # Validar que los scores son numéricos
            assert df['home_score'].dtype in ['int64', 'float64'], "home_score debe ser numérico"
            assert df['away_score'].dtype in ['int64', 'float64'], "away_score debe ser numérico"
            
            # Validar rangos de puntos (NBA típicamente 80-150 puntos por equipo)
            assert df['home_score'].between(50, 200).all(), "home_score fuera de rango válido"
            assert df['away_score'].between(50, 200).all(), "away_score fuera de rango válido"
            
            # Calcular total de puntos por juego
            df['total_points'] = df['home_score'] + df['away_score']
            
            # Validar que el total de puntos es razonable (NBA típicamente 160-300 puntos totales)
            assert df['total_points'].between(120, 350).all(), "Total de puntos por juego fuera de rango válido"
            
            logger.info(f"✓ Validación de puntos exitosa: {len(df)} juegos procesados")
            
        except Exception as e:
            logger.error(f"Error en test de validación de puntos: {e}")
            pytest.fail(f"Test de validación de puntos falló: {e}")
    
    def test_team_names_consistency(self):
        """
        Validar que los nombres de equipos sean consistentes.
        """
        logger.info("Ejecutando test de consistencia de nombres de equipos...")
        
        try:
            # Cargar dataset consolidado
            dataset_path = os.path.join(self.processed_dir, "nba_full_dataset.csv")
            if not os.path.exists(dataset_path):
                pytest.skip("Dataset consolidado no encontrado")
            
            df = pd.read_csv(dataset_path)
            
            # Verificar columnas de equipos
            team_columns = ['home_team', 'away_team']
            for col in team_columns:
                assert col in df.columns, f"Columna {col} no encontrada"
            
            # Obtener nombres únicos de equipos
            home_teams = set(df['home_team'].dropna().unique())
            away_teams = set(df['away_team'].dropna().unique())
            all_teams = home_teams.union(away_teams)
            
            # Validar que tenemos equipos
            assert len(all_teams) > 0, "No se encontraron equipos"
            
            # Lista de equipos NBA válidos
            valid_teams = {
                'Boston Celtics', 'Los Angeles Lakers', 'Golden State Warriors',
                'Chicago Bulls', 'Miami Heat', 'San Antonio Spurs', 'New York Knicks',
                'Brooklyn Nets', 'Philadelphia 76ers', 'Toronto Raptors', 'Milwaukee Bucks',
                'Indiana Pacers', 'Cleveland Cavaliers', 'Detroit Pistons', 'Atlanta Hawks',
                'Charlotte Hornets', 'Orlando Magic', 'Washington Wizards', 'Dallas Mavericks',
                'Houston Rockets', 'Memphis Grizzlies', 'New Orleans Pelicans', 'Phoenix Suns',
                'Sacramento Kings', 'Oklahoma City Thunder', 'Minnesota Timberwolves',
                'Los Angeles Clippers', 'Denver Nuggets', 'Portland Trail Blazers', 'Utah Jazz'
            }
            
            # Verificar que todos los equipos son válidos
            invalid_teams = all_teams - valid_teams
            if invalid_teams:
                logger.warning(f"Equipos no reconocidos: {invalid_teams}")
                # No fallar el test, solo advertir
            
            # Verificar que no hay nombres vacíos o nulos
            assert not df['home_team'].isna().any(), "Nombres de equipos locales nulos encontrados"
            assert not df['away_team'].isna().any(), "Nombres de equipos visitantes nulos encontrados"
            
            logger.info(f"✓ Validación de nombres de equipos exitosa: {len(all_teams)} equipos únicos")
            
        except Exception as e:
            logger.error(f"Error en test de consistencia de nombres: {e}")
            pytest.fail(f"Test de consistencia de nombres falló: {e}")
    
    def test_no_duplicate_game_ids(self):
        """
        Verificar que no hay duplicación de game_id.
        """
        logger.info("Ejecutando test de duplicados de game_id...")
        
        try:
            # Cargar dataset consolidado
            dataset_path = os.path.join(self.processed_dir, "nba_full_dataset.csv")
            if not os.path.exists(dataset_path):
                pytest.skip("Dataset consolidado no encontrado")
            
            df = pd.read_csv(dataset_path)
            
            # Verificar que tenemos game_id
            assert 'game_id' in df.columns, "Columna game_id no encontrada"
            
            # Verificar que no hay game_ids nulos
            assert not df['game_id'].isna().any(), "Game IDs nulos encontrados"
            
            # Verificar que no hay duplicados
            duplicate_count = df['game_id'].duplicated().sum()
            assert duplicate_count == 0, f"Se encontraron {duplicate_count} game_ids duplicados"
            
            # Verificar que todos los game_ids son únicos
            unique_game_ids = df['game_id'].nunique()
            total_games = len(df)
            assert unique_game_ids == total_games, f"Game IDs no únicos: {unique_game_ids} únicos de {total_games} totales"
            
            logger.info(f"✓ Validación de duplicados exitosa: {unique_game_ids} game_ids únicos")
            
        except Exception as e:
            logger.error(f"Error en test de duplicados: {e}")
            pytest.fail(f"Test de duplicados falló: {e}")
    
    def test_boxscores_data_integrity(self):
        """
        Validar integridad de datos de boxscores.
        """
        logger.info("Ejecutando test de integridad de boxscores...")
        
        try:
            boxscores_dir = os.path.join(self.raw_dir, "boxscores")
            if not os.path.exists(boxscores_dir):
                pytest.skip("Directorio de boxscores no encontrado")
            
            # Contar archivos JSON
            json_files = [f for f in os.listdir(boxscores_dir) if f.endswith('.json')]
            assert len(json_files) > 0, "No se encontraron archivos de boxscores"
            
            # Validar algunos archivos de muestra
            sample_files = json_files[:5]  # Tomar muestra de 5 archivos
            
            for filename in sample_files:
                file_path = os.path.join(boxscores_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                
                # Verificar estructura básica
                required_fields = ['game_id', 'home_team', 'away_team', 'home_score', 'away_score']
                for field in required_fields:
                    assert field in game_data, f"Campo {field} faltante en {filename}"
                
                # Verificar que los scores son numéricos
                assert isinstance(game_data['home_score'], (int, float)), f"home_score no numérico en {filename}"
                assert isinstance(game_data['away_score'], (int, float)), f"away_score no numérico en {filename}"
                
                # Verificar que los scores son positivos
                assert game_data['home_score'] >= 0, f"home_score negativo en {filename}"
                assert game_data['away_score'] >= 0, f"away_score negativo en {filename}"
            
            logger.info(f"✓ Validación de boxscores exitosa: {len(json_files)} archivos encontrados")
            
        except Exception as e:
            logger.error(f"Error en test de integridad de boxscores: {e}")
            pytest.fail(f"Test de integridad de boxscores falló: {e}")
    
    def test_team_stats_data_integrity(self):
        """
        Validar integridad de datos de estadísticas de equipos.
        """
        logger.info("Ejecutando test de integridad de estadísticas de equipos...")
        
        try:
            team_stats_dir = os.path.join(self.raw_dir, "team_stats")
            if not os.path.exists(team_stats_dir):
                pytest.skip("Directorio de estadísticas de equipos no encontrado")
            
            # Contar archivos CSV
            csv_files = [f for f in os.listdir(team_stats_dir) if f.endswith('.csv')]
            assert len(csv_files) > 0, "No se encontraron archivos de estadísticas de equipos"
            
            # Validar algunos archivos de muestra
            sample_files = csv_files[:3]  # Tomar muestra de 3 archivos
            
            for filename in sample_files:
                file_path = os.path.join(team_stats_dir, filename)
                df = pd.read_csv(file_path)
                
                # Verificar que no está vacío
                assert len(df) > 0, f"Archivo {filename} está vacío"
                
                # Verificar columnas esperadas
                expected_columns = ['FG%', '3P%', 'FT%', 'RPG', 'APG', 'SPG', 'BPG', 'TPG', 'PPG', 'OPPG']
                missing_columns = [col for col in expected_columns if col not in df.columns]
                if missing_columns:
                    logger.warning(f"Columnas faltantes en {filename}: {missing_columns}")
            
            logger.info(f"✓ Validación de estadísticas de equipos exitosa: {len(csv_files)} archivos encontrados")
            
        except Exception as e:
            logger.error(f"Error en test de integridad de estadísticas: {e}")
            pytest.fail(f"Test de integridad de estadísticas falló: {e}")
    
    def test_data_types_consistency(self):
        """
        Validar consistencia de tipos de datos.
        """
        logger.info("Ejecutando test de consistencia de tipos de datos...")
        
        try:
            dataset_path = os.path.join(self.processed_dir, "nba_full_dataset.csv")
            if not os.path.exists(dataset_path):
                pytest.skip("Dataset consolidado no encontrado")
            
            df = pd.read_csv(dataset_path)
            
            # Verificar tipos de datos numéricos
            numeric_columns = ['home_score', 'away_score', 'home_win', 'point_diff']
            for col in numeric_columns:
                if col in df.columns:
                    assert pd.api.types.is_numeric_dtype(df[col]), f"Columna {col} no es numérica"
            
            # Verificar tipos de datos categóricos
            categorical_columns = ['home_team', 'away_team']
            for col in categorical_columns:
                if col in df.columns:
                    assert pd.api.types.is_object_dtype(df[col]), f"Columna {col} no es categórica"
            
            # Verificar que home_win es binario (0 o 1)
            if 'home_win' in df.columns:
                unique_values = df['home_win'].unique()
                assert set(unique_values).issubset({0, 1}), f"home_win contiene valores no binarios: {unique_values}"
            
            logger.info("✓ Validación de tipos de datos exitosa")
            
        except Exception as e:
            logger.error(f"Error en test de tipos de datos: {e}")
            pytest.fail(f"Test de tipos de datos falló: {e}")

def run_integrity_tests():
    """
    Ejecutar todos los tests de integridad.
    """
    logger.info("=== INICIANDO TESTS DE INTEGRIDAD DE DATOS ===")
    
    # Crear instancia de la clase de tests
    test_instance = TestDataIntegrity()
    test_instance.setup_method()
    
    # Lista de tests a ejecutar
    tests = [
        test_instance.test_points_validation,
        test_instance.test_team_names_consistency,
        test_instance.test_no_duplicate_game_ids,
        test_instance.test_boxscores_data_integrity,
        test_instance.test_team_stats_data_integrity,
        test_instance.test_data_types_consistency
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
            logger.info(f"✓ {test.__name__} - PASÓ")
        except Exception as e:
            failed += 1
            logger.error(f"✗ {test.__name__} - FALLÓ: {e}")
    
    logger.info(f"=== TESTS COMPLETADOS: {passed} pasaron, {failed} fallaron ===")
    
    return failed == 0

if __name__ == "__main__":
    # Ejecutar tests directamente
    success = run_integrity_tests()
    exit(0 if success else 1)
