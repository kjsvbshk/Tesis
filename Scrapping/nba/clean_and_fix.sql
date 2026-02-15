DROP TABLE IF EXISTS espn.odds CASCADE;
TRUNCATE TABLE espn.standings;
TRUNCATE TABLE espn.team_stats;

-- Deduplicate nba_player_boxscores (keep first instance)
DELETE FROM espn.nba_player_boxscores
WHERE ctid NOT IN (
    SELECT min(ctid)
    FROM espn.nba_player_boxscores
    GROUP BY game_id, player_id
);
