import pandas as pd

# Load consolidated dataset
df = pd.read_csv('data/processed/nba_full_dataset.csv')

print("="*80)
print("DATASET CONSOLIDADO - RESUMEN")
print("="*80)
print(f"\n📊 Total registros: {len(df)}")
print(f"📅 Rango de fechas: {df['fecha'].min()} a {df['fecha'].max()}")
print(f"📋 Columnas: {len(df.columns)}")

# Count by season (extract year from fecha)
df['year'] = pd.to_datetime(df['fecha']).dt.year
print(f"\n📈 Distribución por año:")
for year in sorted(df['year'].unique()):
    count = len(df[df['year'] == year])
    print(f"  {year}: {count} partidos")

# Check for nulls in critical columns
critical_cols = ['game_id', 'home_team', 'away_team', 'home_score', 'away_score']
print(f"\n✅ Verificación de columnas críticas:")
for col in critical_cols:
    nulls = df[col].isna().sum()
    print(f"  {col}: {nulls} nulos ({nulls/len(df)*100:.1f}%)")

# Check stats columns
stats_cols = ['home_fg_pct', 'home_3p_pct', 'home_ft_pct', 'home_reb', 'home_ast', 
              'away_fg_pct', 'away_3p_pct', 'away_ft_pct', 'away_reb', 'away_ast']
print(f"\n📊 Verificación de stats:")
for col in stats_cols[:5]:  # Just show first 5
    nulls = df[col].isna().sum()
    print(f"  {col}: {nulls} nulos ({nulls/len(df)*100:.1f}%)")

print(f"\n📋 Muestra de datos:")
print(df[['fecha', 'home_team', 'away_team', 'home_score', 'away_score', 'home_win']].head(3))

print("="*80)
