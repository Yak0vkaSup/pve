CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    username VARCHAR(255),
    usertoken UUID,
    auth_date TIMESTAMP,
    key VARCHAR(255),
    key_secret VARCHAR(255)
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