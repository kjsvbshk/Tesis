-- Initialize schemas for application database
-- This should be run after the database is created

-- Create app schema (for backend/frontend application data)
CREATE SCHEMA IF NOT EXISTS app;
GRANT ALL ON SCHEMA app TO neondb_owner;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO neondb_owner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO neondb_owner;

-- Grant schema privileges on public schema
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Enable UUID extension for future use
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Connect to nba_data database and create espn schema
\c nba_data;

-- Create espn schema
CREATE SCHEMA IF NOT EXISTS espn;
GRANT ALL ON SCHEMA espn TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA espn TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA espn TO postgres;

-- Grant schema privileges on public schema
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

