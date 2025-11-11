-- Initial database setup for NBA Bets
-- This script runs when the PostgreSQL container is first created

-- Grant privileges on tesis database
GRANT ALL PRIVILEGES ON DATABASE tesis TO postgres;

-- Create nba_data database if it doesn't exist
SELECT 'CREATE DATABASE nba_data'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nba_data')\gexec

-- Grant privileges on nba_data database
GRANT ALL PRIVILEGES ON DATABASE nba_data TO postgres;
