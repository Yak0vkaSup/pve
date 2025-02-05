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
    timeframe VARCHAR(20),
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

CREATE TABLE bots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'inactive',
    parameters JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT unique_bot_per_user UNIQUE (user_id, name)
);

CREATE TABLE bot_performance (
    id SERIAL PRIMARY KEY,
    bot_id INTEGER NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    profit FLOAT DEFAULT 0,
    equity FLOAT DEFAULT 0,
    trades_executed INTEGER DEFAULT 0,
    pnl FLOAT DEFAULT 0,
    drawdown FLOAT DEFAULT 0,
    UNIQUE(bot_id, timestamp)
);
