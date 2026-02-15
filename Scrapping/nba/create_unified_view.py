"""
Crear vistas unificadas para facilitar el consumo de datos.
"""
import psycopg2
from load_data import Config

def create_views():
    print("🏗️ Creando vistas unificadas...")
    
    config = Config()
    try:
        conn = psycopg2.connect(**config.db_config)
        cur = conn.cursor()
        
        # Vista Unificada: Games + Player Boxscores
        # Une la información del partido (fecha, equipos) con stats detalladas de jugadores
        view_query = """
        CREATE OR REPLACE VIEW espn.unified_player_boxscores AS
        SELECT 
            -- Info del Juego (Origen: ESPN)
            g.game_id AS espn_game_id,
            g.fecha,
            g.home_team,
            g.away_team,
            g.home_score,
            g.away_score,
            
            -- Info del Mapping
            m.nba_id,
            
            -- Stats del Jugador (Origen: NBA)
            p.player_id,
            p.player_name,
            p.team_tricode,
            p.position,
            p.starter,
            p.minutes,
            p.pts,
            p.reb,
            p.ast,
            p.stl,
            p.blk,
            p.to_stat as turnovers,
            p.pf,
            p.plus_minus,
            p.fgm, p.fga, p.fg_pct,
            p.three_pm, p.three_pa, p.three_pct,
            p.ftm, p.fta, p.ft_pct,
            p.oreb, p.dreb
            
        FROM espn.games g
        JOIN espn.game_id_mapping m ON g.game_id::text = m.espn_id
        JOIN espn.nba_player_boxscores p ON m.nba_id = p.game_id;
        """
        
        cur.execute(view_query)
        conn.commit()
        print("✅ Vista 'espn.unified_player_boxscores' creada exitosamente.")
        
        # Verificar conteo usando la vista
        cur.execute("SELECT COUNT(*) FROM espn.unified_player_boxscores")
        count = cur.fetchone()[0]
        print(f"📊 Registros en vista unificada: {count}")
        
    except Exception as e:
        print(f"❌ Error creando vistas: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    create_views()
