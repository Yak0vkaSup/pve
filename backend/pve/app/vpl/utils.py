# app/vpl/utils.py
import pandas as pd
import pandas_ta as ta
from ..utils.database import get_db_connection
import logging
from functools import wraps
import pandas as pd
from typing import Union
import math


def calculate_ma(df, length, ma_type, calculate_on):
    ma_function = getattr(ta, ma_type)
    return ma_function(df[calculate_on], length, talib=True)

def fetch_data(symbol, start_date, end_date):
    conn = get_db_connection()
    if conn is None:
        return None
    query = f"""
        SELECT timestamp AS date, open, high, low, close, volume
        FROM candles
        WHERE symbol = '{symbol}' AND
              timestamp BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY timestamp;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    logging.info(f"Fetched data for {symbol} from {start_date} to {end_date}")
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df

def type_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        annotations = func.__annotations__
        for name, value in zip(annotations, args):
            expected_type = annotations.get(name)
            if expected_type and not isinstance(value, expected_type):
                raise TypeError(f"Argument '{name}' must be {expected_type}, got {type(value)}")
        return func(*args, **kwargs)
    return wrapper

@type_check
def get_open(df: pd.DataFrame) -> pd.Series:
    return df['open']

@type_check
def get_close(df: pd.DataFrame) -> pd.Series:
    return df['close']

@type_check
def get_high(df: pd.DataFrame) -> pd.Series:
    return df['high']

@type_check
def get_low(df: pd.DataFrame) -> pd.Series:
    return df['low']

@type_check
def get_volume(df: pd.DataFrame) -> pd.Series:
    return df['volume']

@type_check
def add_column(df: pd.DataFrame, column_name: str, column: pd.Series) -> pd.DataFrame:
    if column_name in df.columns:
        raise ValueError(f"Column '{column_name}' already exists in the DataFrame.")
    df[column_name] = column
    return df

@type_check
def delete_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")
    df.drop(columns=[column_name], inplace=True)
    return df

@type_check
def multiply_column(column: pd.Series, factor: Union[int, float]) -> pd.Series:
    return column * factor

@type_check
def ma(name: str, column: pd.Series, window: int) -> pd.Series:
    return ta.ma(name, column, length=window)


@type_check
def super_trend(high: pd.Series, low: pd.Series, close: pd.Series,  window: int) -> pd.Series:
    return ta.supertrend(high, low, close, window)

@type_check
def bollinger(close: pd.Series, window: int):
    return ta.bbands(close, window, talib=True)

@type_check
def rsi(close: pd.Series, window: int):
    return ta.rsi(close, window, talib=True)

@type_check
def true_range(high: pd.Series, low: pd.Series, close: pd.Series):
    return ta.true_range(high, low, close, talib=True)

# ============================================================================
# MOVING AVERAGE CALCULATIONS - Single input (price + length) -> Single output
# ============================================================================

def ma_sma(prices, window):
    """Simple Moving Average"""
    if len(prices) < window:
        return None
    return sum(prices[-window:]) / window

def ma_ema(price, window, prev_ema=None):
    """Exponential Moving Average"""
    alpha = 2.0 / (window + 1)
    if prev_ema is None:
        return price
    return alpha * price + (1 - alpha) * prev_ema

def ma_dema(prices, window, ema1_state=None, ema2_state=None):
    """Double Exponential Moving Average"""
    if len(prices) < 1:
        return None, None, None
    
    price = prices[-1]
    ema1 = ma_ema(price, window, ema1_state)
    ema2 = ma_ema(ema1, window, ema2_state)
    
    if ema1 is not None and ema2 is not None:
        dema = 2 * ema1 - ema2
        return dema, ema1, ema2
    return None, ema1, ema2

def ma_tema(prices, window, ema1_state=None, ema2_state=None, ema3_state=None):
    """Triple Exponential Moving Average"""
    if len(prices) < 1:
        return None, None, None, None
    
    price = prices[-1]
    ema1 = ma_ema(price, window, ema1_state)
    ema2 = ma_ema(ema1, window, ema2_state) if ema1 is not None else None
    ema3 = ma_ema(ema2, window, ema3_state) if ema2 is not None else None
    
    if all(x is not None for x in [ema1, ema2, ema3]):
        tema = 3 * ema1 - 3 * ema2 + ema3
        return tema, ema1, ema2, ema3
    return None, ema1, ema2, ema3

def ma_wma(prices, window):
    """Weighted Moving Average"""
    if len(prices) < window:
        return None
    weights = list(range(1, window + 1))
    weighted_sum = sum(p * w for p, w in zip(prices[-window:], weights))
    return weighted_sum / sum(weights)

def ma_hma(prices, window, hma_values=None):
    """Hull Moving Average"""
    if len(prices) < window:
        return None, hma_values
    
    if hma_values is None:
        hma_values = []
    
    half_period = max(1, window // 2)
    sqrt_period = max(1, int(math.sqrt(window)))
    
    if len(prices) < half_period:
        return None, hma_values
        
    wma_half = ma_wma(prices, half_period)
    wma_full = ma_wma(prices, window)
    
    if wma_half is None or wma_full is None:
        return None, hma_values
        
    raw_hma = 2 * wma_half - wma_full
    hma_values.append(raw_hma)
    
    if len(hma_values) >= sqrt_period:
        result = ma_wma(hma_values, sqrt_period)
        return result, hma_values
    return None, hma_values

def ma_rma(price, window, prev_rma=None):
    """Wilder's Moving Average (RMA)"""
    alpha = 1.0 / window
    if prev_rma is None:
        return price
    return alpha * price + (1 - alpha) * prev_rma

def ma_linreg(prices, window):
    """Linear Regression Moving Average"""
    if len(prices) < window:
        return None
    
    y_values = prices[-window:]
    x_values = list(range(len(y_values)))
    n = len(x_values)
    
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x * x for x in x_values)
    
    if n * sum_x2 - sum_x * sum_x == 0:
        return None
        
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
    intercept = (sum_y - slope * sum_x) / n
    
    return slope * (n - 1) + intercept

def ma_trima(prices, window, trima_sma1=None):
    """Triangular Moving Average"""
    if len(prices) < window:
        return None, trima_sma1
        
    if trima_sma1 is None:
        trima_sma1 = []
    
    half_period = (window + 1) // 2
    
    if len(prices) >= half_period:
        sma1 = ma_sma(prices, half_period)
        if sma1 is not None:
            trima_sma1.append(sma1)
            
            if len(trima_sma1) >= half_period:
                result = ma_sma(trima_sma1, half_period)
                return result, trima_sma1
    return None, trima_sma1

def ma_kama(prices, window, prev_kama=None):
    """Kaufman's Adaptive Moving Average"""
    if len(prices) < window + 1:
        return prices[-1] if len(prices) == 1 else None
        
    price = prices[-1]
    
    # Calculate Efficiency Ratio
    if len(prices) >= window + 1:
        change = abs(price - prices[-(window + 1)])
        volatility = sum(abs(prices[i] - prices[i-1]) for i in range(-window, 0))
        er = change / volatility if volatility != 0 else 0
    else:
        er = 0
        
    # Smoothing Constants
    fastest_sc = 2.0 / (2 + 1)
    slowest_sc = 2.0 / (30 + 1)
    sc = (er * (fastest_sc - slowest_sc) + slowest_sc) ** 2
    
    if prev_kama is None:
        return price
    else:
        return prev_kama + sc * (price - prev_kama)

def ma_alma(prices, window, sigma=6.0, offset=0.85):
    """Arnaud Legoux Moving Average"""
    if len(prices) < window:
        return None
        
    m = offset * (window - 1)
    s = window / sigma
    
    weights = []
    norm = 0
    for i in range(window):
        weight = math.exp(-((i - m) ** 2) / (2 * s ** 2))
        weights.append(weight)
        norm += weight
        
    if norm == 0:
        return None
        
    weighted_sum = sum(p * w for p, w in zip(prices[-window:], weights))
    return weighted_sum / norm

def ma_fwma(prices, window):
    """Fibonacci Weighted Moving Average"""
    if len(prices) < window:
        return None
        
    # Generate Fibonacci sequence
    fib = [1, 1]
    while len(fib) < window:
        fib.append(fib[-1] + fib[-2])
        
    weights = fib[:window]
    weighted_sum = sum(p * w for p, w in zip(prices[-window:], weights))
    return weighted_sum / sum(weights)

def ma_pwma(prices, window):
    """Pascal's Weighted Moving Average"""
    if len(prices) < window:
        return None
        
    # Generate Pascal's triangle weights
    def pascal_triangle_row(n):
        row = [1]
        for i in range(n):
            row.append(row[i] * (n - i) // (i + 1))
        return row
        
    weights = pascal_triangle_row(window - 1)
    weighted_sum = sum(p * w for p, w in zip(prices[-window:], weights))
    return weighted_sum / sum(weights)

def ma_sinwma(prices, window):
    """Sine Weighted Moving Average"""
    if len(prices) < window:
        return None
        
    weights = [math.sin(math.pi * (i + 1) / (window + 1)) for i in range(window)]
    weighted_sum = sum(p * w for p, w in zip(prices[-window:], weights))
    return weighted_sum / sum(weights)

def ma_swma(prices, window):
    """Symmetric Weighted Moving Average"""
    if len(prices) < window:
        return None
        
    # Create symmetric triangle weights
    if window % 2 == 1:
        mid = window // 2
        weights = list(range(1, mid + 2)) + list(range(mid, 0, -1))
    else:
        mid = window // 2
        weights = list(range(1, mid + 1)) + list(range(mid, 0, -1))
        
    weighted_sum = sum(p * w for p, w in zip(prices[-window:], weights))
    return weighted_sum / sum(weights)

def ma_zlma(prices, window, zlma_ema=None):
    """Zero Lag Moving Average"""
    if len(prices) < window:
        return None, zlma_ema
        
    lag = (window - 1) // 2
    if len(prices) < lag + 1:
        return None, zlma_ema
        
    # Calculate EMA
    price = prices[-1]
    ema_val = ma_ema(price, window, zlma_ema)
    
    if ema_val is None:
        return None, zlma_ema
        
    # Zero lag calculation
    if len(prices) > lag:
        result = ema_val + (prices[-1] - prices[-(lag + 1)])
        return result, ema_val
    return ema_val, ema_val

def ma_ssf(prices, window, ssf_prev=None):
    """Ehlers Super Smoother Filter"""
    if len(prices) < 3:
        return prices[-1], [prices[-1], prices[-1]] if ssf_prev is None else ssf_prev
        
    if ssf_prev is None:
        ssf_prev = [prices[-1], prices[-1]]
        
    price = prices[-1]
    pi = 3.14159
    sqrt2 = 1.414
    
    a1 = math.exp(-sqrt2 * pi / window)
    b1 = 2 * a1 * math.cos(sqrt2 * pi / window)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1 - c2 - c3
    
    if ssf_prev[0] is None:
        ssf_prev = [price, price]
        return price, ssf_prev
        
    result = c1 * (price + prices[-2]) / 2 + c2 * ssf_prev[0] + c3 * ssf_prev[1]
    ssf_prev[1] = ssf_prev[0]
    ssf_prev[0] = result
    return result, ssf_prev

def ma_ssf3(prices, window, ssf3_prev=None):
    """Ehlers 3-Pole Super Smoother Filter"""
    if len(prices) < 4:
        return prices[-1], [prices[-1], prices[-1], prices[-1]] if ssf3_prev is None else ssf3_prev
        
    if ssf3_prev is None:
        ssf3_prev = [prices[-1], prices[-1], prices[-1]]
        
    price = prices[-1]
    pi = 3.14159
    sqrt3 = 1.732
    
    a1 = math.exp(-pi * sqrt3 / window)
    b1 = 2 * a1 * math.cos(1.738 * pi / window)
    c4 = a1 * a1
    c3 = -a1 * a1 * a1
    c2 = 3 * a1 + 2 * a1 * a1 * math.cos(1.738 * pi / window)
    c1 = 1 - c2 - c3 - c4
    
    if ssf3_prev[0] is None:
        ssf3_prev = [price, price, price]
        return price, ssf3_prev
        
    result = c1 * price + c2 * ssf3_prev[0] + c3 * ssf3_prev[1] + c4 * ssf3_prev[2]
    ssf3_prev[2] = ssf3_prev[1]
    ssf3_prev[1] = ssf3_prev[0]
    ssf3_prev[0] = result
    return result, ssf3_prev

def ma_t3(price, window, t3_states=None, a=0.7):
    """T3 Moving Average"""
    if t3_states is None:
        t3_states = {'e1': None, 'e2': None, 'e3': None, 'e4': None, 'e5': None, 'e6': None}
    
    # T3 requires 6 EMA calculations
    t3_states['e1'] = ma_ema(price, window, t3_states['e1'])
    t3_states['e2'] = ma_ema(t3_states['e1'] if t3_states['e1'] is not None else price, window, t3_states['e2'])
    t3_states['e3'] = ma_ema(t3_states['e2'] if t3_states['e2'] is not None else price, window, t3_states['e3'])
    t3_states['e4'] = ma_ema(t3_states['e3'] if t3_states['e3'] is not None else price, window, t3_states['e4'])
    t3_states['e5'] = ma_ema(t3_states['e4'] if t3_states['e4'] is not None else price, window, t3_states['e5'])
    t3_states['e6'] = ma_ema(t3_states['e5'] if t3_states['e5'] is not None else price, window, t3_states['e6'])
    
    if all(x is not None for x in t3_states.values()):
        c1 = -a**3
        c2 = 3 * a**2 + 3 * a**3
        c3 = -6 * a**2 - 3 * a - 3 * a**3
        c4 = 1 + 3 * a + a**3 + 3 * a**2
        
        result = c1 * t3_states['e6'] + c2 * t3_states['e5'] + c3 * t3_states['e4'] + c4 * t3_states['e3']
        return result, t3_states
    return None, t3_states

def ma_vidya(prices, window, prev_vidya=None):
    """Variable Index Dynamic Average"""
    if len(prices) < window + 1:
        return prices[-1] if len(prices) == 1 else None
        
    price = prices[-1]
    
    # Calculate CMO (Chande Momentum Oscillator)
    if len(prices) >= window + 1:
        ups = []
        downs = []
        for i in range(-window, 0):
            change = prices[i] - prices[i-1]
            if change > 0:
                ups.append(change)
            else:
                downs.append(abs(change))
                
        sum_ups = sum(ups)
        sum_downs = sum(downs)
        cmo = (sum_ups - sum_downs) / (sum_ups + sum_downs) if (sum_ups + sum_downs) != 0 else 0
    else:
        cmo = 0
        
    # Calculate VIDYA
    alpha = abs(cmo) * 2.0 / (window + 1)
    
    if prev_vidya is None:
        return price
    else:
        return alpha * price + (1 - alpha) * prev_vidya

def ma_mcgd(price, window, prev_mcgd=None):
    """McGinley Dynamic"""
    if prev_mcgd is None:
        return price
        
    # McGinley Dynamic formula
    k = window
    if prev_mcgd != 0:
        factor = (price / prev_mcgd - 1) * (price / prev_mcgd) ** 4
        return prev_mcgd + factor * (price - prev_mcgd) / (k * factor + 1)
    else:
        return price

def ma_smma(price, window, prev_smma=None, is_first=False):
    """Smoothed Moving Average"""
    if prev_smma is None or is_first:
        return price
    else:
        return (prev_smma * (window - 1) + price) / window

def ma_jma(price, window, jma_state=None, phase=0):
    """Jurik Moving Average (simplified implementation)"""
    if jma_state is None:
        jma_state = {'e0': price, 'e1': price, 'e2': price}
        return price, jma_state
        
    beta = 0.45 * (window - 1) / (0.45 * (window - 1) + 2)
    alpha = beta
    
    jma_state['e0'] = (1 - alpha) * price + alpha * jma_state['e0']
    jma_state['e1'] = (price - jma_state['e0']) * (1 - beta) + beta * jma_state['e1']
    jma_state['e2'] = jma_state['e0'] + phase * jma_state['e1']
    
    return jma_state['e2'], jma_state

def ma_hwma(price, hwma_state=None, alpha=0.2, beta=0.1):
    """Holt-Winter Moving Average (simplified)"""
    if hwma_state is None:
        hwma_state = {'level': price, 'trend': 0}
        return price, hwma_state
        
    prev_level = hwma_state['level']
    prev_trend = hwma_state['trend']
    
    hwma_state['level'] = alpha * price + (1 - alpha) * (prev_level + prev_trend)
    hwma_state['trend'] = beta * (hwma_state['level'] - prev_level) + (1 - beta) * prev_trend
    
    return hwma_state['level'], hwma_state

# ============================================================================
# RSI CALCULATION
# ============================================================================

def rsi_calculate(prices, window, rsi_state=None):
    """RSI (Relative Strength Index) calculation"""
    if len(prices) < 2:
        return None, rsi_state
        
    if rsi_state is None:
        rsi_state = {'gains': [], 'losses': [], 'avg_gain': None, 'avg_loss': None}
    
    # Calculate price change
    current_price = prices[-1]
    prev_price = prices[-2]
    change = current_price - prev_price
    
    # Separate gains and losses
    gain = max(change, 0)
    loss = max(-change, 0)
    
    rsi_state['gains'].append(gain)
    rsi_state['losses'].append(loss)
    
    # Keep only the last 'window' values
    if len(rsi_state['gains']) > window:
        rsi_state['gains'] = rsi_state['gains'][-window:]
        rsi_state['losses'] = rsi_state['losses'][-window:]
    
    # Need at least 'window' periods to calculate RSI
    if len(rsi_state['gains']) < window:
        return None, rsi_state
    
    # Calculate average gain and loss
    if rsi_state['avg_gain'] is None:
        # First calculation - simple average
        rsi_state['avg_gain'] = sum(rsi_state['gains']) / window
        rsi_state['avg_loss'] = sum(rsi_state['losses']) / window
    else:
        # Subsequent calculations - Wilder's smoothing
        alpha = 1.0 / window
        rsi_state['avg_gain'] = alpha * gain + (1 - alpha) * rsi_state['avg_gain']
        rsi_state['avg_loss'] = alpha * loss + (1 - alpha) * rsi_state['avg_loss']
    
    # Calculate RSI
    if rsi_state['avg_loss'] == 0:
        rsi_value = 100.0
    else:
        rs = rsi_state['avg_gain'] / rsi_state['avg_loss']
        rsi_value = 100.0 - (100.0 / (1 + rs))
    
    return rsi_value, rsi_state

# ============================================================================
# SUPERTREND CALCULATION
# ============================================================================

def supertrend_calculate(highs, lows, closes, window, multiplier=3.0, supertrend_state=None):
    """SuperTrend calculation"""
    if len(highs) < 2 or len(lows) < 2 or len(closes) < 2:
        return None, supertrend_state
    
    if supertrend_state is None:
        supertrend_state = {
            'tr_values': [],
            'atr': None,
            'trend': 1,
            'supertrend': None,
            'upper_band': None,
            'lower_band': None
        }
    
    # Calculate True Range
    high = highs[-1]
    low = lows[-1]
    close = closes[-1]
    prev_close = closes[-2]
    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = max(tr1, tr2, tr3)
    
    supertrend_state['tr_values'].append(tr)
    
    # Keep only the last 'window' values
    if len(supertrend_state['tr_values']) > window:
        supertrend_state['tr_values'] = supertrend_state['tr_values'][-window:]
    
    # Calculate ATR
    if len(supertrend_state['tr_values']) < window:
        return None, supertrend_state
    
    if supertrend_state['atr'] is None:
        # First ATR calculation - simple average
        supertrend_state['atr'] = sum(supertrend_state['tr_values']) / window
    else:
        # Subsequent calculations - Wilder's smoothing
        alpha = 1.0 / window
        supertrend_state['atr'] = alpha * tr + (1 - alpha) * supertrend_state['atr']
    
    # Calculate HL2 (median price)
    hl2 = (high + low) / 2
    
    # Calculate bands
    upper_band = hl2 + multiplier * supertrend_state['atr']
    lower_band = hl2 - multiplier * supertrend_state['atr']
    
    # Final upper and lower bands (with trend filtering)
    if supertrend_state['upper_band'] is None or upper_band < supertrend_state['upper_band'] or prev_close > supertrend_state['upper_band']:
        final_upper_band = upper_band
    else:
        final_upper_band = supertrend_state['upper_band']
    
    if supertrend_state['lower_band'] is None or lower_band > supertrend_state['lower_band'] or prev_close < supertrend_state['lower_band']:
        final_lower_band = lower_band
    else:
        final_lower_band = supertrend_state['lower_band']
    
    supertrend_state['upper_band'] = final_upper_band
    supertrend_state['lower_band'] = final_lower_band
    
    # Determine SuperTrend value and direction
    if supertrend_state['supertrend'] is None:
        # First calculation
        if close <= final_lower_band:
            supertrend_state['supertrend'] = final_upper_band
            supertrend_state['trend'] = -1
        else:
            supertrend_state['supertrend'] = final_lower_band
            supertrend_state['trend'] = 1
    else:
        # Subsequent calculations
        if supertrend_state['trend'] == 1 and close < final_lower_band:
            supertrend_state['supertrend'] = final_upper_band
            supertrend_state['trend'] = -1
        elif supertrend_state['trend'] == -1 and close > final_upper_band:
            supertrend_state['supertrend'] = final_lower_band
            supertrend_state['trend'] = 1
        else:
            # Keep current trend
            if supertrend_state['trend'] == 1:
                supertrend_state['supertrend'] = final_lower_band
            else:
                supertrend_state['supertrend'] = final_upper_band
    
    return supertrend_state['supertrend'], supertrend_state

symbols_db = ['1000000MOGUSDT', '1000BONKUSDT', '1000FLOKIUSDT', '1000NEIROCTOUSDT', '1000PEPEUSDT', '1000XUSDT', 'AAVEUSDT', 'ACTUSDT', 'ADAUSDT', 'APEUSDT', 'APTUSDT', 'ARBUSDT', 'ATOMUSDT', 'AVAXUSDT', 'BANUSDT', 'BCHUSDT', 'BNBUSDT', 'BOMEUSDT', 'BRETTUSDT', 'BTCPERP', 'BTCUSDT', 'CATIUSDT', 'CRVUSDT', 'DEGENUSDT', 'DOGEUSDT', 'DOGSUSDT', 'DOTUSDT', 'DRIFTUSDT', 'EIGENUSDT', 'ENAUSDT', 'ETCUSDT', 'ETHFIUSDT', 'ETHUSDT', 'FTMUSDT', 'GALAUSDT', 'GOATUSDT', 'GRASSUSDT', 'HBARUSDT', 'INJUSDT', 'JUPUSDT', 'KASUSDT', 'LDOUSDT', 'LINKUSDT', 'LTCUSDT', 'MEWUSDT', 'MOODENGUSDT', 'NEARUSDT', 'NEIROETHUSDT', 'NOTUSDT', 'OMUSDT', 'ONDOUSDT', 'OPUSDT', 'ORDIUSDT', 'PNUTUSDT', 'POLUSDT', 'POPCATUSDT', 'RENDERUSDT', 'SEIUSDT', 'SHIB1000USDT', 'SLERFUSDT', 'SOLUSDT', 'STRKUSDT', 'STXUSDT', 'SUIUSDT', 'TAOUSDT', 'TIAUSDT', 'TONUSDT', 'TROYUSDT', 'UNIUSDT', 'WIFUSDT', 'WLDUSDT', 'XLMUSDT', 'XRPUSDT']