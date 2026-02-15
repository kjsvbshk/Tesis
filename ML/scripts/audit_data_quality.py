#!/usr/bin/env python3
"""
Script de Auditoría de Calidad de Datos - Fase 1.1
Valida calidad y coherencia de los datos en ml_ready_games
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from src.config import db_config


class DataQualityAuditor:
    """Auditor de calidad de datos para ml_ready_games"""
    
    def __init__(self):
        self.database_url = db_config.get_database_url()
        self.ml_schema = db_config.get_schema("ml")
        self.espn_schema = db_config.get_schema("espn")
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        self.issues = []
        self.stats = {}
        
    def log_issue(self, category, severity, message, details=None):
        """Registra un problema encontrado"""
        self.issues.append({
            'category': category,
            'severity': severity,  # 'critical', 'warning', 'info'
            'message': message,
            'details': details
        })
        
    def run_audit(self):
        """Ejecuta todas las verificaciones de calidad"""
        print("=" * 70)
        print("🔍 AUDITORÍA DE CALIDAD DE DATOS - Fase 1.1")
        print("=" * 70)
        print(f"Tabla: {self.ml_schema}.ml_ready_games")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Cargar datos
        print("📥 Cargando datos...")
        df = self._load_data()
        if df is None or len(df) == 0:
            print("❌ No se pudieron cargar datos o la tabla está vacía")
            return
        
        print(f"   ✅ {len(df)} registros cargados")
        print()
        
        # Ejecutar verificaciones
        self._check_game_id_uniqueness(df)
        self._check_temporal_integrity(df)
        self._check_null_values(df)
        self._check_outliers(df)
        self._check_team_alignment(df)
        self._check_score_consistency(df)
        self._check_target_variable(df)
        self._check_feature_coverage(df)
        
        # Generar reporte
        self._generate_report(df)
        
    def _load_data(self):
        """Carga datos de ml_ready_games"""
        try:
            query = f"""
                SELECT *
                FROM {self.ml_schema}.ml_ready_games
                ORDER BY fecha
            """
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            print(f"❌ Error al cargar datos: {e}")
            return None
    
    def _check_game_id_uniqueness(self, df):
        """Verifica unicidad de game_id"""
        print("1️⃣  Verificando unicidad de game_id...")
        
        duplicates = df[df.duplicated(subset=['game_id'], keep=False)]
        
        if len(duplicates) > 0:
            self.log_issue(
                'uniqueness',
                'critical',
                f'Encontrados {len(duplicates)} game_ids duplicados',
                duplicates[['game_id', 'fecha', 'home_team', 'away_team']].to_dict('records')
            )
            print(f"   ❌ CRÍTICO: {len(duplicates)} game_ids duplicados")
        else:
            print(f"   ✅ Todos los game_ids son únicos ({len(df)} registros)")
        
        self.stats['total_games'] = len(df)
        self.stats['unique_game_ids'] = df['game_id'].nunique()
        print()
    
    def _check_temporal_integrity(self, df):
        """Valida integridad temporal"""
        print("2️⃣  Verificando integridad temporal...")
        
        # Convertir fecha a datetime si no lo es
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        # Verificar fechas nulas
        null_dates = df['fecha'].isnull().sum()
        if null_dates > 0:
            self.log_issue(
                'temporal',
                'critical',
                f'{null_dates} registros con fecha nula'
            )
            print(f"   ❌ CRÍTICO: {null_dates} fechas nulas")
        
        # Verificar rango de fechas
        min_date = df['fecha'].min()
        max_date = df['fecha'].max()
        date_range = (max_date - min_date).days
        
        print(f"   📅 Rango de fechas: {min_date.date()} a {max_date.date()}")
        print(f"   📊 Período: {date_range} días")
        
        # Verificar fechas futuras
        today = pd.Timestamp.now()
        future_dates = df[df['fecha'] > today]
        if len(future_dates) > 0:
            self.log_issue(
                'temporal',
                'warning',
                f'{len(future_dates)} registros con fechas futuras',
                future_dates[['game_id', 'fecha']].to_dict('records')
            )
            print(f"   ⚠️  ADVERTENCIA: {len(future_dates)} fechas futuras")
        
        # Detectar gaps temporales grandes (>7 días sin partidos)
        df_sorted = df.sort_values('fecha')
        date_diffs = df_sorted['fecha'].diff()
        large_gaps = date_diffs[date_diffs > timedelta(days=7)]
        
        if len(large_gaps) > 0:
            print(f"   ⚠️  {len(large_gaps)} gaps temporales >7 días detectados")
            self.log_issue(
                'temporal',
                'info',
                f'{len(large_gaps)} gaps temporales significativos (>7 días)'
            )
        else:
            print(f"   ✅ Sin gaps temporales significativos")
        
        self.stats['min_date'] = str(min_date.date())
        self.stats['max_date'] = str(max_date.date())
        self.stats['date_range_days'] = date_range
        print()
    
    def _check_null_values(self, df):
        """Detecta valores nulos por columna"""
        print("3️⃣  Detectando valores nulos...")
        
        null_counts = df.isnull().sum()
        null_pcts = (null_counts / len(df) * 100).round(2)
        
        # Columnas críticas que NO deben tener nulos
        critical_cols = ['game_id', 'fecha', 'home_team', 'away_team', 
                        'home_score', 'away_score', 'home_win']
        
        critical_nulls = False
        for col in critical_cols:
            if col in null_counts and null_counts[col] > 0:
                self.log_issue(
                    'nulls',
                    'critical',
                    f'Columna crítica {col} tiene {null_counts[col]} nulos ({null_pcts[col]}%)'
                )
                print(f"   ❌ CRÍTICO: {col} tiene {null_counts[col]} nulos ({null_pcts[col]}%)")
                critical_nulls = True
        
        if not critical_nulls:
            print(f"   ✅ Columnas críticas sin nulos")
        
        # Reportar nulos en features (esperado para algunas)
        feature_cols = [col for col in df.columns if col not in critical_cols]
        cols_with_nulls = null_counts[null_counts > 0]
        
        if len(cols_with_nulls) > 0:
            print(f"   📊 Columnas con valores nulos:")
            for col, count in cols_with_nulls.items():
                pct = null_pcts[col]
                severity = 'warning' if pct > 50 else 'info'
                symbol = '⚠️ ' if pct > 50 else '   '
                print(f"   {symbol}- {col}: {count} ({pct}%)")
                
                if pct > 50:
                    self.log_issue(
                        'nulls',
                        severity,
                        f'{col} tiene {pct}% de valores nulos'
                    )
        
        self.stats['null_summary'] = null_pcts[null_pcts > 0].to_dict()
        print()
    
    def _check_outliers(self, df):
        """Identifica outliers estadísticos"""
        print("4️⃣  Identificando outliers...")
        
        # Columnas numéricas para verificar
        numeric_cols = ['home_score', 'away_score', 'point_diff']
        
        outliers_found = False
        for col in numeric_cols:
            if col not in df.columns or df[col].isnull().all():
                continue
            
            # Calcular estadísticas
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr
            
            outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
            
            if len(outliers) > 0:
                outliers_found = True
                pct = (len(outliers) / len(df) * 100).round(2)
                print(f"   ⚠️  {col}: {len(outliers)} outliers ({pct}%)")
                print(f"       Rango esperado: [{lower_bound:.1f}, {upper_bound:.1f}]")
                
                # Mostrar ejemplos extremos
                if len(outliers) <= 5:
                    for _, row in outliers.iterrows():
                        print(f"       Game {row['game_id']}: {row[col]}")
                
                self.log_issue(
                    'outliers',
                    'warning',
                    f'{col} tiene {len(outliers)} outliers ({pct}%)',
                    outliers[['game_id', 'fecha', col]].head(5).to_dict('records')
                )
        
        if not outliers_found:
            print(f"   ✅ No se detectaron outliers significativos")
        
        print()
    
    def _check_team_alignment(self, df):
        """Confirma alineación equipo local vs visitante"""
        print("5️⃣  Verificando alineación local vs visitante...")
        
        # Verificar que home_team != away_team
        same_team = df[df['home_team'] == df['away_team']]
        if len(same_team) > 0:
            self.log_issue(
                'alignment',
                'critical',
                f'{len(same_team)} partidos donde home_team == away_team',
                same_team[['game_id', 'fecha', 'home_team', 'away_team']].to_dict('records')
            )
            print(f"   ❌ CRÍTICO: {len(same_team)} partidos con mismo equipo local/visitante")
        else:
            print(f"   ✅ Todos los partidos tienen equipos diferentes")
        
        # Verificar equipos únicos
        unique_teams = set(df['home_team'].unique()) | set(df['away_team'].unique())
        print(f"   📊 Equipos únicos encontrados: {len(unique_teams)}")
        
        # Verificar balance home/away por equipo
        home_counts = df['home_team'].value_counts()
        away_counts = df['away_team'].value_counts()
        
        # Equipos con desbalance significativo (>20% diferencia)
        imbalanced = []
        for team in unique_teams:
            home_games = home_counts.get(team, 0)
            away_games = away_counts.get(team, 0)
            total = home_games + away_games
            if total > 0:
                home_pct = home_games / total
                if home_pct < 0.3 or home_pct > 0.7:
                    imbalanced.append((team, home_games, away_games, home_pct))
        
        if imbalanced:
            print(f"   ⚠️  {len(imbalanced)} equipos con desbalance home/away >20%")
            for team, home, away, pct in imbalanced[:5]:
                print(f"       {team}: {home} home, {away} away ({pct*100:.1f}% home)")
        else:
            print(f"   ✅ Balance razonable de partidos home/away")
        
        self.stats['unique_teams'] = len(unique_teams)
        print()
    
    def _check_score_consistency(self, df):
        """Valida consistencia de scores"""
        print("6️⃣  Validando consistencia de scores...")
        
        # Verificar scores negativos
        negative_scores = df[(df['home_score'] < 0) | (df['away_score'] < 0)]
        if len(negative_scores) > 0:
            self.log_issue(
                'scores',
                'critical',
                f'{len(negative_scores)} partidos con scores negativos',
                negative_scores[['game_id', 'home_score', 'away_score']].to_dict('records')
            )
            print(f"   ❌ CRÍTICO: {len(negative_scores)} scores negativos")
        else:
            print(f"   ✅ Sin scores negativos")
        
        # Verificar scores extremadamente altos (>200 puntos)
        high_scores = df[(df['home_score'] > 200) | (df['away_score'] > 200)]
        if len(high_scores) > 0:
            print(f"   ⚠️  {len(high_scores)} partidos con scores >200 puntos")
            self.log_issue(
                'scores',
                'warning',
                f'{len(high_scores)} partidos con scores muy altos (>200)'
            )
        
        # Verificar scores extremadamente bajos (<50 puntos)
        low_scores = df[(df['home_score'] < 50) | (df['away_score'] < 50)]
        if len(low_scores) > 0:
            print(f"   ⚠️  {len(low_scores)} partidos con scores <50 puntos")
        
        # Verificar consistencia home_win vs scores
        if 'home_win' in df.columns:
            df_clean = df.dropna(subset=['home_score', 'away_score', 'home_win'])
            expected_home_win = (df_clean['home_score'] > df_clean['away_score'])
            inconsistent = df_clean[df_clean['home_win'] != expected_home_win]
            
            if len(inconsistent) > 0:
                self.log_issue(
                    'scores',
                    'critical',
                    f'{len(inconsistent)} registros con home_win inconsistente con scores',
                    inconsistent[['game_id', 'home_score', 'away_score', 'home_win']].to_dict('records')
                )
                print(f"   ❌ CRÍTICO: {len(inconsistent)} registros con home_win inconsistente")
            else:
                print(f"   ✅ home_win consistente con scores")
        
        # Estadísticas de scores
        print(f"   📊 Estadísticas de scores:")
        print(f"       Home score promedio: {df['home_score'].mean():.1f}")
        print(f"       Away score promedio: {df['away_score'].mean():.1f}")
        print(f"       Point diff promedio: {df['point_diff'].mean():.1f}")
        
        self.stats['avg_home_score'] = float(df['home_score'].mean())
        self.stats['avg_away_score'] = float(df['away_score'].mean())
        print()
    
    def _check_target_variable(self, df):
        """Verifica integridad de la variable objetivo"""
        print("7️⃣  Verificando variable objetivo (home_win)...")
        
        if 'home_win' not in df.columns:
            self.log_issue(
                'target',
                'critical',
                'Columna home_win no existe'
            )
            print(f"   ❌ CRÍTICO: Columna home_win no existe")
            return
        
        # Verificar valores nulos
        null_target = df['home_win'].isnull().sum()
        if null_target > 0:
            pct = (null_target / len(df) * 100).round(2)
            self.log_issue(
                'target',
                'critical',
                f'home_win tiene {null_target} valores nulos ({pct}%)'
            )
            print(f"   ❌ CRÍTICO: {null_target} valores nulos ({pct}%)")
        else:
            print(f"   ✅ Sin valores nulos en home_win")
        
        # Verificar distribución
        value_counts = df['home_win'].value_counts()
        total = len(df) - null_target
        
        if total > 0:
            home_wins = value_counts.get(True, 0)
            away_wins = value_counts.get(False, 0)
            home_win_pct = (home_wins / total * 100).round(2)
            
            print(f"   📊 Distribución:")
            print(f"       Home wins: {home_wins} ({home_win_pct}%)")
            print(f"       Away wins: {away_wins} ({100-home_win_pct:.2f}%)")
            
            # Verificar desbalance extremo
            if home_win_pct < 40 or home_win_pct > 60:
                self.log_issue(
                    'target',
                    'warning',
                    f'Desbalance en home_win: {home_win_pct}% home wins'
                )
                print(f"   ⚠️  Desbalance detectado (esperado ~50-56%)")
            else:
                print(f"   ✅ Balance razonable (esperado ~50-56%)")
            
            self.stats['home_win_pct'] = float(home_win_pct)
        
        print()
    
    def _check_feature_coverage(self, df):
        """Verifica cobertura de features"""
        print("8️⃣  Verificando cobertura de features...")
        
        feature_cols = [
            'home_ppg_last5', 'away_ppg_last5',
            'home_net_rating_last10', 'away_net_rating_last10',
            'home_rest_days', 'away_rest_days',
            'home_injuries_count', 'away_injuries_count',
            'implied_prob_home', 'implied_prob_away'
        ]
        
        coverage = {}
        for col in feature_cols:
            if col in df.columns:
                non_null = df[col].notna().sum()
                pct = (non_null / len(df) * 100).round(2)
                coverage[col] = pct
                
                symbol = '✅' if pct > 90 else '⚠️ ' if pct > 50 else '❌'
                print(f"   {symbol} {col}: {pct}% cobertura")
                
                if pct < 50:
                    self.log_issue(
                        'features',
                        'warning',
                        f'{col} tiene baja cobertura ({pct}%)'
                    )
        
        self.stats['feature_coverage'] = coverage
        print()
    
    def _generate_report(self, df):
        """Genera reporte final"""
        print("=" * 70)
        print("📋 RESUMEN DE AUDITORÍA")
        print("=" * 70)
        print()
        
        # Contar problemas por severidad
        critical = [i for i in self.issues if i['severity'] == 'critical']
        warnings = [i for i in self.issues if i['severity'] == 'warning']
        info = [i for i in self.issues if i['severity'] == 'info']
        
        print(f"Total de registros: {len(df)}")
        print(f"Problemas encontrados:")
        print(f"  ❌ Críticos: {len(critical)}")
        print(f"  ⚠️  Advertencias: {len(warnings)}")
        print(f"  ℹ️  Informativos: {len(info)}")
        print()
        
        if critical:
            print("🚨 PROBLEMAS CRÍTICOS:")
            for issue in critical:
                print(f"   - {issue['message']}")
            print()
        
        if warnings:
            print("⚠️  ADVERTENCIAS:")
            for issue in warnings[:10]:  # Mostrar máximo 10
                print(f"   - {issue['message']}")
            if len(warnings) > 10:
                print(f"   ... y {len(warnings) - 10} más")
            print()
        
        # Guardar reporte detallado
        self._save_report(df)
        
        # Conclusión
        if len(critical) == 0:
            print("✅ RESULTADO: Dataset aprobado para continuar a Fase 1.2")
        else:
            print("❌ RESULTADO: Se deben corregir problemas críticos antes de continuar")
        
        print("=" * 70)
        print()
    
    def _save_report(self, df):
        """Guarda reporte detallado en archivo"""
        report_dir = Path(__file__).parent.parent / "reports"
        report_dir.mkdir(exist_ok=True)
        
        report_path = report_dir / "data_quality_audit.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Reporte de Auditoría de Calidad de Datos\n\n")
            f.write(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Tabla**: `{self.ml_schema}.ml_ready_games`\n\n")
            f.write(f"**Total de registros**: {len(df)}\n\n")
            
            f.write("## Resumen Ejecutivo\n\n")
            critical = [i for i in self.issues if i['severity'] == 'critical']
            warnings = [i for i in self.issues if i['severity'] == 'warning']
            
            f.write(f"- ❌ Problemas críticos: {len(critical)}\n")
            f.write(f"- ⚠️  Advertencias: {len(warnings)}\n\n")
            
            if len(critical) == 0:
                f.write("✅ **Estado**: Dataset aprobado para Fase 1.2\n\n")
            else:
                f.write("❌ **Estado**: Requiere correcciones antes de continuar\n\n")
            
            f.write("## Estadísticas Generales\n\n")
            for key, value in self.stats.items():
                f.write(f"- **{key}**: {value}\n")
            f.write("\n")
            
            if critical:
                f.write("## Problemas Críticos\n\n")
                for issue in critical:
                    f.write(f"### {issue['message']}\n\n")
                    f.write(f"- **Categoría**: {issue['category']}\n")
                    if issue['details']:
                        f.write(f"- **Detalles**: {issue['details']}\n")
                    f.write("\n")
            
            if warnings:
                f.write("## Advertencias\n\n")
                for issue in warnings:
                    f.write(f"- {issue['message']}\n")
                f.write("\n")
        
        print(f"📄 Reporte guardado en: {report_path}")


def main():
    """Función principal"""
    auditor = DataQualityAuditor()
    auditor.run_audit()


if __name__ == "__main__":
    main()
