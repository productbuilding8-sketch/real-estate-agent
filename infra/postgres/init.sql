-- Extensions required by DealFlow AI
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Ensure the dealflow user has full access to the database
GRANT ALL PRIVILEGES ON DATABASE dealflow TO dealflow;
