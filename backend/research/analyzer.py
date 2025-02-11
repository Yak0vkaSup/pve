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

@dataclass
class ExecutedOrder:
    index: int
    time: pd.Timestamp
    price: Decimal
    qty: Decimal
    side: str = "BUY"  # default side is BUY

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
    profit: Decimal = Decimal('0')
    return_pct: Decimal = Decimal('0')

class BacktestAnalyzer:
    def __init__(self, df):
        self.df = df.copy()
        self.trades: List[Trade] = []
        self.parse_trades()
        self.calculate_metrics()
        self.equity_curve = self.get_equity_curve()

    def parse_trades(self):
        df = self.df
        in_position = False
        entry_index = None
        executed_orders = []
        last_avg_price = None  # computed as Decimal

        # These columns indicate execution quantities.
        executed_order_cols = [col for col in df.columns if col.startswith('£order_executed_')]

        for index, row in df.iterrows():
            # Process executed orders (entry orders):
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
                        # Create a BUY order
                        executed_order = ExecutedOrder(
                            index=index,
                            time=row['date'],
                            price=order_price,
                            qty=qty_val,
                            side="BUY"
                        )
                        executed_orders.append(executed_order)
                        last_avg_price, _ = self.calculate_average_entry_price(executed_orders)

            # Check for an exit signal.
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
                    # Create an exit order and append it to executed orders.
                    exit_order = ExecutedOrder(
                        index=index,
                        time=row['date'],
                        price=exit_price,
                        qty=trade_qty,
                        side="SELL"
                    )
                    executed_orders.append(exit_order)
                    trade = Trade(
                        entry_index=entry_index,
                        exit_index=index,
                        entry_time=df.loc[entry_index, 'date'],
                        exit_time=row['date'],
                        entry_price=last_avg_price,
                        exit_price=exit_price,
                        qty=trade_qty,  # quantity from the exit signal
                        executed_orders=executed_orders.copy()
                    )
                    trade.profit, trade.return_pct = self.calculate_position_profit(
                        trade.entry_price, trade.qty, trade.exit_price)
                    self.trades.append(trade)
                # Reset trade variables.
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
        self.num_trades = len(self.trades)
        wins = sum(1 for trade in self.trades if trade.profit > Decimal('0'))
        self.win_rate = (wins / self.num_trades) * 100 if self.num_trades > 0 else 0
        self.sharpe_ratio = self.calculate_sharpe_ratio()
        self.max_drawdown = self.calculate_max_drawdown()

    def calculate_sharpe_ratio(self):
        returns = [Decimal(str(trade.return_pct)) / Decimal('100') for trade in self.trades]
        n = len(returns)
        if n > 1:
            total = sum(returns, Decimal('0'))
            mean_return = total / Decimal(n)
            diff_squares = [(r - mean_return) ** 2 for r in returns]
            variance = sum(diff_squares, Decimal('0')) / Decimal(n - 1)
            std_return = variance.sqrt() if variance > Decimal('0') else Decimal('0')
            sharpe_ratio = (mean_return / std_return) * (Decimal(n).sqrt()) if std_return != Decimal('0') else Decimal('0')
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
        initial_capital = Decimal('500.0')
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
                            exec_price = Decimal(str(row['close']))
                        except (InvalidOperation, ValueError, TypeError):
                            exec_price = Decimal('0')
                        total_cost = avg_entry_price * position_qty + exec_price * qty_val
                        position_qty += qty_val
                        avg_entry_price = total_cost / position_qty
            try:
                current_close = Decimal(str(row['close']))
            except (InvalidOperation, ValueError, TypeError):
                current_close = Decimal('0')
            unrealized_pnl = (current_close - avg_entry_price) * position_qty if position_qty > Decimal('0') else Decimal('0')
            realized_pnl = Decimal('0')
            exit_value = row.get('@exit', False)
            if pd.notna(exit_value) and exit_value not in [False, 'False', 0, 0.0, '0'] and position_qty > Decimal('0'):
                realized_pnl = unrealized_pnl
                position_qty = Decimal('0')
                avg_entry_price = Decimal('0')
            equity += realized_pnl
            total_equity = equity + unrealized_pnl
            df.at[index, 'equity'] = float(total_equity)
        self.df['equity'] = df['equity']
        return df['equity']

    def get_metrics(self):
        return {
            'Total PnL': float(self.total_pnl),
            'Number of Trades': self.num_trades,
            'Win Rate (%)': self.win_rate,
            'Sharpe Ratio': float(self.sharpe_ratio),
            'Max Drawdown (%)': self.max_drawdown,
        }

    def get_trades(self):
        return self.trades

def convert_timestamp(ts):
    try:
        return datetime.utcfromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception as e:
        return ts

def print_trade_details(analyzer):
    metrics = analyzer.get_metrics()
    print("GLOBAL METRICS:")
    print(f"  Total PnL:          {metrics['Total PnL']}")
    print(f"  Number of Trades:   {metrics['Number of Trades']}")
    print(f"  Win Rate (%):       {metrics['Win Rate (%)']}")
    print(f"  Sharpe Ratio:       {metrics['Sharpe Ratio']}")
    print(f"  Max Drawdown (%):   {metrics['Max Drawdown (%)']}\n")

    for idx, trade in enumerate(analyzer.get_trades(), start=1):
        trade_usdt = trade.entry_price * trade.qty
        print(f"TRADE {idx}:")
        print(f"  Entry Time:   {convert_timestamp(trade.entry_time)}")
        print(f"  Exit Time:    {convert_timestamp(trade.exit_time)}")
        print(f"  Entry Price:  {trade.entry_price} USDT")
        print(f"  Exit Price:   {trade.exit_price} USDT")
        print(f"  Trade Qty:    {trade.qty} coins")
        print(f"  Trade Qty:   {trade_usdt:.3f} USDT")
        print(f"  PnL:          {trade.profit:.3f} USDT")
        print(f"  Return (%):   {trade.return_pct:.3f}%")
        print(f"  # Orders:     {len(trade.executed_orders)}")
        print("  ORDERS:")
        for order_idx, order in enumerate(trade.executed_orders, start=1):
            order_usdt = order.price * order.qty
            print(f"    Order {order_idx}:")
            print(f"      Time:  {convert_timestamp(order.time)}")
            print(f"      Price: {order.price} USDT")
            print(f"      Qty:   {order.qty} coins")
            print(f"      Qty:  {order_usdt:.3f} USDT")
            print(f"      Side:  {order.side}")
        print()

if __name__ == '__main__':
    df = pd.read_csv('backtest.csv')
    analyzer = BacktestAnalyzer(df)
    analyzer.calculate_metrics()
    print_trade_details(analyzer)
