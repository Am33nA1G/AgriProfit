-- Setup script for AgriProfit database
-- Run this with: psql -U postgres -p 5433 -h localhost -f setup_db_user.sql

-- Create user if it doesn't exist
DO
$$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'agriprofit') THEN
      CREATE USER agriprofit WITH PASSWORD 'agriprofit';
   END IF;
END
$$;

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE agriprofit OWNER agriprofit'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agriprofit')\gexec

-- Grant all privileges
GRANT ALL PRIVILEGES ON DATABASE agriprofit TO agriprofit;

-- Connect to the agriprofit database
\c agriprofit;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO agriprofit;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agriprofit;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agriprofit;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO agriprofit;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO agriprofit;

\echo 'Database user agriprofit created successfully!'
