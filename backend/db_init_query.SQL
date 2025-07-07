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
    updated_at  TIMESTAMP,
    symbol VARCHAR(20),
    timeframe VARCHAR(20),
    start_date TIMESTAMP,
    end_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candles (
	id SERIAL PRIMARY KEY,
	symbol VARCHAR(20),
	timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	open DOUBLE PRECISION,
	high DOUBLE PRECISION,
	low DOUBLE PRECISION,
	close DOUBLE PRECISION,
	volume DOUBLE PRECISION,
	UNIQUE(symbol, timestamp)
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    graph_name VARCHAR(255) NOT NULL,
    backtest_data JSONB NOT NULL,
    orders JSONB NOT NULL,
    precision NUMERIC,
    min_move NUMERIC,
    symbol VARCHAR(20),
    timeframe VARCHAR(20),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    graph JSONB NOT NULL,
    analyzer_result_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analyzer_results (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    graph_name VARCHAR(255) NOT NULL,
    symbol VARCHAR(20),
    initial_capital NUMERIC,
    final_capital NUMERIC,
    first_date TIMESTAMP,
    last_date TIMESTAMP,
    df_duration INTERVAL,
    total_pnl NUMERIC,
    total_fees NUMERIC,
    total_funding_cost NUMERIC,
    num_trades INTEGER,
    win_rate NUMERIC,
    sharpe_ratio NUMERIC,
    max_drawdown NUMERIC,
    avg_trade_duration VARCHAR(50),
    global_return NUMERIC,
    equity_curve JSONB,         -- e.g. list of timestamp-equity pairs
    trades_details JSONB,       -- detailed trades info
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    id          SERIAL PRIMARY KEY,
    bot_id      INTEGER NOT NULL
                    UNIQUE
                    REFERENCES bots(id)
                    ON DELETE CASCADE,
    last_update TIMESTAMPTZ NOT NULL,
    orders      JSONB,
    df          JSONB,
    precision   NUMERIC,
    min_move    NUMERIC
);

CREATE TABLE bot_logs (
  id         SERIAL PRIMARY KEY,
  bot_id     INTEGER NOT NULL
                   REFERENCES bots(id)
                   ON DELETE CASCADE,
  timestamp  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  level      VARCHAR(10) NOT NULL,
  message    TEXT     NOT NULL
);