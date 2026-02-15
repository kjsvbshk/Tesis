"""
Team slug mapping: ESPN team names → NBA.com slugs

NBA.com URLs use format: {away_slug}-vs-{home_slug}-{game_id}
Ejemplo: chi-vs-bos-0022500778
"""

TEAM_SLUG_MAP = {
    # Eastern Conference
    'Atlanta Hawks': 'atl',
    'Boston Celtics': 'bos',
    'Brooklyn Nets': 'bkn',
    'Charlotte Hornets': 'cha',
    'Chicago Bulls': 'chi',
    'Cleveland Cavaliers': 'cle',
    'Detroit Pistons': 'det',
    'Indiana Pacers': 'ind',
    'Miami Heat': 'mia',
    'Milwaukee Bucks': 'mil',
    'New York Knicks': 'ny',
    'Orlando Magic': 'orl',
    'Philadelphia 76ers': 'phi',
    'Toronto Raptors': 'tor',
    'Washington Wizards': 'wsh',
    
    # Western Conference
    'Dallas Mavericks': 'dal',
    'Denver Nuggets': 'den',
    'Golden State Warriors': 'gs',
    'Houston Rockets': 'hou',
    'Los Angeles Clippers': 'lac',
    'Los Angeles Lakers': 'lal',
    'Memphis Grizzlies': 'mem',
    'Minnesota Timberwolves': 'min',
    'New Orleans Pelicans': 'no',
    'Oklahoma City Thunder': 'okc',
    'Phoenix Suns': 'phx',
    'Portland Trail Blazers': 'por',
    'Sacramento Kings': 'sac',
    'San Antonio Spurs': 'sa',
    'Utah Jazz': 'utah'
}

def get_team_slug(team_name: str) -> str:
    """
    Obtener slug de NBA.com desde nombre de equipo ESPN
    
    Args:
        team_name: Nombre completo del equipo (ej: 'Chicago Bulls')
        
    Returns:
        Slug del equipo (ej: 'chi')
    """
    return TEAM_SLUG_MAP.get(team_name, team_name.lower().replace(' ', '-'))
