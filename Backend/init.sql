-- Initial database setup for NBA Bets
-- This script runs when the PostgreSQL container is first created

-- Create database if it doesn't exist (already created by POSTGRES_DB env var)
-- CREATE DATABASE nba_bets_db;

-- Create user if it doesn't exist (already created by POSTGRES_USER env var)
-- CREATE USER nba_user WITH PASSWORD 'nba_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tesis TO postgres;

-- Connect to the database
\c tesis;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Enable UUID extension for future use
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
