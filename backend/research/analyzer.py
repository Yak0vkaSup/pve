from datetime import datetime
import logging
from decimal import Decimal, InvalidOperation, getcontext
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List

# Configure logging for this module
logger = logging.getLogger(__name__)

# Optionally set higher precision if needed
getcontext().prec = 12

# Define fee rates (using Decimal for precision)
MAKER_FEE_RATE = Decimal('0.0002')  # 0.0200%
TAKER_FEE_RATE = Decimal('0.00055')  # 0.0550%


@dataclass
class ExecutedOrder:
    index: int
    time: pd.Timestamp
    price: Decimal
    qty: Decimal
    side: str = "BUY"  # default side is BUY
    fee: Decimal = Decimal('0')  # fee charged for this order


@dataclass
class Trade:
    entry_index: int
    exit_index: int
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: Decimal
    exit_price: Decimal
    qty: Decimal
    executed_orders: List[ExecutedOrder] = field(default_factory=list)
    fees: Decimal = Decimal('0')  # total fees for this trade (trading fees)
    profit: Decimal = Decimal('0')  # net profit (after fees)
    return_pct: Decimal = Decimal('0')
    funding_cost: Decimal = Decimal('0')  # funding cost for this trade


def format_timedelta(td):
    """Format a timedelta as 'Hh Mm Ss' (without days if zero)."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


def format_timedelta_full(td):
    """Format a timedelta as 'Dd Hh Mm Ss' if days > 0, else 'Hh Mm Ss'."""
    days = td.days
    seconds = td.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    else:
        return f"{hours}h {minutes}m {seconds}s"


def convert_timestamp_to_ms(ts):
    """Convert a timestamp (pd.Timestamp or numeric) to milliseconds."""
    if isinstance(ts, pd.Timestamp):
        return int(ts.value // 10 ** 6)
    try:
        return int(float(ts) * 1000)
    except Exception:
        return None


class BacktestAnalyzer:
    def __init__(self, df, symbol, initial_capital):
        self.df = df.copy()
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.trades: List[Trade] = []
        self.total_fees: Decimal = Decimal('0')
        self.total_funding_cost: Decimal = Decimal('0')
        self.parse_trades()
        self.calculate_metrics()
        self.equity_curve = self.get_equity_curve()
        # After basic metrics are calculated, add funding info.
        self.calculate_funding_costs()

    def parse_trades(self):
        df = self.df
        in_position = False
        entry_index = None
        executed_orders = []
        last_avg_price = None  # computed as Decimal

        executed_order_cols = [col for col in df.columns if col.startswith('£order_executed_')]

        for index, row in df.iterrows():
            for flag_col in executed_order_cols:
                exec_flag_value = row.get(flag_col, False)
                if exec_flag_value not in [False, 'False', 0, 0.0, '0']:
                    try:
                        qty_val = Decimal(str(exec_flag_value))
                    except (InvalidOperation, ValueError, TypeError):
                        qty_val = Decimal('0')
                    order_col = 'order_' + flag_col.split('_')[-1]
                    try:
                        order_price = Decimal(str(row.get(order_col, 0)))
                    except (InvalidOperation, ValueError, TypeError):
                        order_price = Decimal('0')
                    if qty_val > Decimal('0'):
                        if not in_position:
                            entry_index = index
                            in_position = True
                            executed_orders = []
                            last_avg_price = None
                        fee = order_price * qty_val * MAKER_FEE_RATE
                        executed_order = ExecutedOrder(
                            index=index,
                            time=row['date'],
                            price=order_price,
                            qty=qty_val,
                            side="BUY",
                            fee=fee
                        )
                        executed_orders.append(executed_order)
                        last_avg_price, _ = self.calculate_average_entry_price(executed_orders)
            exit_value = row.get('@exit', False)
            if in_position and pd.notna(exit_value) and exit_value not in [False, 'False', 0, 0.0, '0']:
                in_position = False
                try:
                    trade_qty = Decimal(str(exit_value))
                except (InvalidOperation, ValueError, TypeError):
                    trade_qty = Decimal('0')
                if executed_orders and trade_qty > Decimal('0'):
                    try:
                        exit_price = Decimal(str(row['close']))
                    except (InvalidOperation, ValueError, TypeError):
                        exit_price = Decimal('0')
                    exit_fee = exit_price * trade_qty * TAKER_FEE_RATE
                    exit_order = ExecutedOrder(
                        index=index,
                        time=row['date'],
                        price=exit_price,
                        qty=trade_qty,
                        side="SELL",
                        fee=exit_fee
                    )
                    executed_orders.append(exit_order)
                    total_trade_fee = sum(order.fee for order in executed_orders)
                    raw_profit, _ = self.calculate_position_profit(last_avg_price, trade_qty, exit_price)
                    net_profit = raw_profit - total_trade_fee
                    return_pct = (net_profit / (last_avg_price * trade_qty) * Decimal('100')
                                  if last_avg_price * trade_qty != Decimal('0') else Decimal('0'))
                    trade = Trade(
                        entry_index=entry_index,
                        exit_index=index,
                        entry_time=df.loc[entry_index, 'date'],
                        exit_time=row['date'],
                        entry_price=last_avg_price,
                        exit_price=exit_price,
                        qty=trade_qty,
                        executed_orders=executed_orders.copy(),
                        fees=total_trade_fee,
                        profit=net_profit,
                        return_pct=return_pct
                    )
                    self.trades.append(trade)
                entry_index = None
                executed_orders = []
                last_avg_price = None

    def calculate_average_entry_price(self, executed_orders):
        try:
            total_qty = sum(Decimal(str(order.qty)) for order in executed_orders if order.side == "BUY")
        except InvalidOperation:
            total_qty = sum(Decimal(str(order.qty)) for order in executed_orders if order.side == "BUY")
        if total_qty == Decimal('0'):
            return None, Decimal('0')
        try:
            total_cost = sum(Decimal(str(order.price)) * Decimal(str(order.qty))
                             for order in executed_orders if order.side == "BUY")
        except InvalidOperation:
            total_cost = sum(Decimal(str(order.price)) * Decimal(str(order.qty))
                             for order in executed_orders if order.side == "BUY")
        avg_price = total_cost / total_qty
        return avg_price, total_qty

    def calculate_position_profit(self, avg_price, total_qty, exit_price):
        try:
            avg_price_dec = Decimal(str(avg_price))
            total_qty_dec = Decimal(str(total_qty))
            exit_price_dec = Decimal(str(exit_price))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0'), Decimal('0')
        if avg_price_dec == Decimal('0') or total_qty_dec == Decimal('0'):
            return Decimal('0'), Decimal('0')
        absolute_profit = (exit_price_dec - avg_price_dec) * total_qty_dec
        percentage_profit = (absolute_profit / (avg_price_dec * total_qty_dec)) * Decimal('100')
        return absolute_profit, percentage_profit

    def calculate_metrics(self):
        self.total_pnl = sum(trade.profit for trade in self.trades)
        self.total_fees = sum(trade.fees for trade in self.trades)
        self.num_trades = len(self.trades)
        wins = sum(1 for trade in self.trades if trade.profit > Decimal('0'))
        self.win_rate = (wins / self.num_trades) * 100 if self.num_trades > 0 else 0
        self.sharpe_ratio = self.calculate_sharpe_ratio()
        self.max_drawdown = self.calculate_max_drawdown()
        if self.trades:
            durations = [pd.Timedelta(seconds=float(trade.exit_time - trade.entry_time))
                         for trade in self.trades]
            total_ns = sum(td.value for td in durations)
            avg_duration = pd.Timedelta(total_ns // len(durations), unit='ns')
        else:
            avg_duration = pd.Timedelta(0)
        self.avg_trade_duration = avg_duration

    def calculate_sharpe_ratio(self):
        returns = [Decimal(str(trade.return_pct)) / Decimal('100') for trade in self.trades]
        n = len(returns)
        if n > 1:
            total = sum(returns, Decimal('0'))
            mean_return = total / Decimal(n)
            diff_squares = [(r - mean_return) ** 2 for r in returns]
            variance = sum(diff_squares, Decimal('0')) / Decimal(n - 1)
            std_return = variance.sqrt() if variance > Decimal('0') else Decimal('0')
            sharpe_ratio = (mean_return / std_return) * (Decimal(n).sqrt()) if std_return != Decimal('0') else Decimal(
                '0')
        else:
            sharpe_ratio = Decimal('0')
        return sharpe_ratio

    def calculate_max_drawdown(self):
        equity_curve = self.get_equity_curve()
        if not equity_curve.empty:
            cumulative_max = equity_curve.cummax()
            drawdowns = (equity_curve - cumulative_max) / cumulative_max
            max_drawdown = drawdowns.min() * 100  # percentage
        else:
            max_drawdown = 0
        return abs(max_drawdown)

    def get_equity_curve(self):
        df = self.df.copy()
        initial_capital = self.initial_capital
        df['equity'] = float(initial_capital)
        equity = initial_capital
        position_qty = Decimal('0')
        avg_entry_price = Decimal('0')
        for index, row in df.iterrows():
            for flag_col in [col for col in df.columns if col.startswith('£order_executed_')]:
                exec_flag_value = row.get(flag_col, False)
                if exec_flag_value not in [False, 'False', 0, 0.0, '0']:
                    order_col = 'order_' + flag_col.split('_')[-1]
                    try:
                        qty_val = Decimal(str(row.get(flag_col, 0)))
                    except (InvalidOperation, ValueError, TypeError):
                        qty_val = Decimal('0')
                    if qty_val > Decimal('0'):
                        try:
                            order_price = Decimal(str(row.get(order_col, row['close'])))
                        except (InvalidOperation, ValueError, TypeError):
                            order_price = Decimal('0')
                        fee = order_price * qty_val * MAKER_FEE_RATE
                        equity -= fee
                        total_cost = avg_entry_price * position_qty + order_price * qty_val
                        position_qty += qty_val
                        avg_entry_price = total_cost / position_qty
            try:
                current_close = Decimal(str(row['close']))
            except (InvalidOperation, ValueError, TypeError):
                current_close = Decimal('0')
            unrealized_pnl = (current_close - avg_entry_price) * position_qty if position_qty > Decimal(
                '0') else Decimal('0')
            realized_pnl = Decimal('0')
            exit_value = row.get('@exit', False)
            if pd.notna(exit_value) and exit_value not in [False, 'False', 0, 0.0, '0'] and position_qty > Decimal('0'):
                try:
                    trade_qty = Decimal(str(exit_value))
                except (InvalidOperation, ValueError, TypeError):
                    trade_qty = Decimal('0')
                exit_price = current_close
                fee = exit_price * trade_qty * TAKER_FEE_RATE
                equity -= fee
                realized_pnl = (exit_price - avg_entry_price) * trade_qty - fee
                position_qty = Decimal('0')
                avg_entry_price = Decimal('0')
            equity += realized_pnl
            total_equity = equity + unrealized_pnl
            df.at[index, 'equity'] = float(total_equity)
        self.df['equity'] = df['equity']
        return df['equity']

    def fetch_funding_history(self, start_ms, end_ms):
        from pybit.unified_trading import HTTP
        session = HTTP()
        response = session.get_funding_rate_history(
            category="linear",
            symbol=self.symbol,
            startTime=start_ms,
            endTime=end_ms,
            limit=200
        )
        if response.get("retCode") == 0:
            return response["result"]["list"]
        else:
            logger.error(f"Funding history error: {response.get('retMsg')}")
            return []

    def calculate_funding_cost_for_trade(self, trade):
        start_ms = convert_timestamp_to_ms(trade.entry_time)
        end_ms = convert_timestamp_to_ms(trade.exit_time)
        events = self.fetch_funding_history(start_ms, end_ms)
        funding_cost = Decimal('0')
        notional = trade.entry_price * trade.qty
        for event in events:
            rate = Decimal(event.get("fundingRate", "0"))
            funding_cost += notional * rate
        return funding_cost

    def calculate_funding_costs(self):
        total_funding = Decimal('0')
        for trade in self.trades:
            fc = self.calculate_funding_cost_for_trade(trade)
            trade.funding_cost = fc
            total_funding += fc
        self.total_funding_cost = total_funding

    def get_metrics(self):
        initial_capital = self.initial_capital
        final_equity = Decimal(str(self.equity_curve.iloc[-1])) if not self.equity_curve.empty else initial_capital
        global_return_pct = ((final_equity - initial_capital) / initial_capital) * Decimal('100')
        # Since your date column is in seconds, use unit='s'
        first_date = pd.to_datetime(self.df['date'].iloc[0], unit='s')
        last_date = pd.to_datetime(self.df['date'].iloc[-1], unit='s')
        df_duration = last_date - first_date
        return {
            'Symbol': self.symbol,
            'Initial Capital': float(initial_capital),
            'Final Capital': float(final_equity),
            'First Date': first_date,
            'Last Date': last_date,
            'DF Duration': format_timedelta_full(df_duration),
            'Total PnL': float(self.total_pnl),
            'Total Fees': float(self.total_fees),
            'Total Funding Cost': float(self.total_funding_cost),
            'Number of Trades': self.num_trades,
            'Win Rate (%)': self.win_rate,
            'Sharpe Ratio': float(self.sharpe_ratio),
            'Max Drawdown (%)': self.max_drawdown,
            'Average Trade Duration': format_timedelta(self.avg_trade_duration),
            'Global Return (%)': float(global_return_pct)
        }

    def get_trades(self):
        return self.trades


def convert_timestamp(ts):
    try:
        if isinstance(ts, pd.Timestamp):
            return ts.strftime('%Y-%m-%d %H:%M:%S UTC')
        # Assuming ts is in seconds
        return datetime.utcfromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception as e:
        return ts


def print_trade_details(analyzer):
    metrics = analyzer.get_metrics()
    # Print global metrics / test summary first.
    print("TEST SUMMARY:")
    print(f"  Symbol:                 {metrics['Symbol']}")
    print(f"  Initial Capital:        {metrics['Initial Capital']} USDT")
    print(f"  Final Capital:          {round(metrics['Final Capital'], 2)} USDT")
    print(f"  First Date:             {convert_timestamp(metrics['First Date'])}")
    print(f"  Last Date:              {convert_timestamp(metrics['Last Date'])}")
    print(f"  DF Duration:            {metrics['DF Duration']}\n")
    print("GLOBAL METRICS:")
    print(f"  Global Return (%):      {round(metrics['Global Return (%)'], 2)}%")
    print(f"  Total PnL:              {round(metrics['Total PnL'], 2)} USDT")
    print(f"  Total Fees Paid:        {round(metrics['Total Fees'], 2)} USDT")
    print(f"  Total Funding Paid:     {round(metrics['Total Funding Cost'], 2)} USDT")
    print(f"  Number of Trades:       {metrics['Number of Trades']}")
    print(f"  Win Rate (%):           {metrics['Win Rate (%)']}")
    print(f"  Sharpe Ratio:           {round(metrics['Sharpe Ratio'], 2)}")
    print(f"  Max Drawdown (%):       {round(metrics['Max Drawdown (%)'], 2)}")
    print(f"  Average Trade Duration: {metrics['Average Trade Duration']}\n")

    print("TRADE DETAILS:")
    for idx, trade in enumerate(analyzer.get_trades(), start=1):
        trade_usdt = trade.entry_price * trade.qty
        trade_duration = pd.Timedelta(seconds=float(trade.exit_time - trade.entry_time))
        formatted_duration = format_timedelta(trade_duration)
        print(f"TRADE {idx}:")
        print(f"  Entry Time:       {convert_timestamp(trade.entry_time)}")
        print(f"  Exit Time:        {convert_timestamp(trade.exit_time)}")
        print(f"  Trade Duration:   {formatted_duration}")
        print(f"  Entry Price:      {trade.entry_price} USDT")
        print(f"  Exit Price:       {trade.exit_price} USDT")
        print(f"  Trade Qty:        {trade.qty} coins")
        print(f"  Trade Notional:   {trade_usdt:.3f} USDT")
        print(f"  Fees:             {trade.fees:.6f} USDT")
        print(f"  Net PnL:          {trade.profit:.3f} USDT")
        print(f"  Total Return (%): {trade.return_pct:.3f}%")
        print(f"  Funding Paid:     {trade.funding_cost:.6f} USDT")
        print(f"  # Orders:         {len(trade.executed_orders)}")
        print("  ORDERS:")
        for order_idx, order in enumerate(trade.executed_orders, start=1):
            order_usdt = order.price * order.qty
            print(f"    Order {order_idx}:")
            print(f"      Time:      {convert_timestamp(order.time)}")
            print(f"      Price:     {order.price} USDT")
            print(f"      Qty:       {order.qty} coins")
            print(f"      Notional:  {order_usdt:.3f} USDT")
            print(f"      Side:      {order.side}")
            print(f"      Fee:       {order.fee:.6f} USDT")
        print()


if __name__ == '__main__':
    df = pd.read_csv('hohoho.csv')
    symbol = '1000TOSHIUSDT'
    initial_capital = Decimal('100.0')
    analyzer = BacktestAnalyzer(df, symbol, initial_capital)
    analyzer.calculate_metrics()
    print_trade_details(analyzer)
