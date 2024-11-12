SET timezone = 'UTC';

CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    username VARCHAR(255),
    usertoken UUID,
    auth_date TIMESTAMP,
    last_auth TIMESTAMP
);

CREATE TABLE user_graphs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    graph_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP,
    symbol VARCHAR(20),
    start_date TIMESTAMP,
    end_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candles (
	id SERIAL PRIMARY KEY,
	symbol VARCHAR(20),
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	open NUMERIC,
	high NUMERIC,
	low NUMERIC,
	close NUMERIC,
	volume NUMERIC,
	UNIQUE(symbol, timestamp)
);
