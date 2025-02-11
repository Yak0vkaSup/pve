import logging
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List

# Configure logging for this module
logger = logging.getLogger(__name__)

@dataclass
class ExecutedOrder:
    index: int
    time: pd.Timestamp
    price: float
    qty: float

@dataclass
class Trade:
    entry_index: int
    exit_index: int
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    qty: float
    executed_orders: List[ExecutedOrder] = field(default_factory=list)
    profit: float = 0.0
    return_pct: float = 0.0

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
        last_avg_price = None
        last_total_qty = 0

        # Determine all executed order columns
        executed_order_cols = [col for col in df.columns if col.startswith('£order_executed_')]

        for index, row in df.iterrows():
            # Check for Executed Orders
            for qty_col in executed_order_cols:
                price_col = 'order_' + qty_col.split('_')[-1]
                qty = row.get(qty_col, 0)
                price = row.get(price_col, np.nan)
                if qty and not pd.isna(qty) and float(qty) > 0:
                    if not in_position:
                        # We enter position when the first order is executed
                        entry_index = index
                        in_position = True
                        executed_orders = []
                        last_avg_price = None
                        last_total_qty = 0
                        # logger.debug(f"Entered position at index {entry_index}")

                    # Create an ExecutedOrder instance
                    executed_order = ExecutedOrder(
                        index=index,
                        time=row['date'],
                        price=price,
                        qty=float(qty),
                    )
                    executed_orders.append(executed_order)

                    # Update average price and total quantity
                    last_avg_price, last_total_qty = self.calculate_average_entry_price(executed_orders)
                    # logger.debug(f"Index {index}: Executed order at price {price}, quantity {qty}")
                    # logger.debug(f"Index {index}: Updated average price {last_avg_price}, total quantity {last_total_qty}")

            # Check for Exit Signal
            if in_position:
                exit_signal = row.get('@exit', False)
                # logger.debug(f"Index {index}: Exit signal = {exit_signal}")
                if exit_signal:
                    in_position = False
                    if executed_orders:
                        # Create a Trade instance
                        trade = Trade(
                            entry_index=entry_index,
                            exit_index=index,
                            entry_time=df.loc[entry_index, 'date'],
                            exit_time=row['date'],
                            entry_price=last_avg_price,
                            exit_price=row['close'],
                            qty=last_total_qty,
                            executed_orders=executed_orders.copy(),  # Copy to avoid reference issues
                        )
                        # Calculate profit and return percentage
                        trade.profit, trade.return_pct = self.calculate_position_profit(
                            trade.entry_price, trade.qty, trade.exit_price)
                        self.trades.append(trade)
                        # logger.debug(f"Trade recorded: {trade}")
                    else:
                        print()
                        # logger.info(f"No orders executed between entry at index {entry_index} and exit at index {index}. Trade skipped.")
                    # Reset variables after exiting position
                    entry_index = None
                    executed_orders = []
                    last_avg_price = None
                    last_total_qty = 0

    def calculate_average_entry_price(self, executed_orders):
        total_qty = sum(order.qty for order in executed_orders)
        if total_qty == 0:
            return None, 0
        total_cost = sum(order.price * order.qty for order in executed_orders)
        avg_price = total_cost / total_qty
        return avg_price, total_qty

    def calculate_position_profit(self, avg_price, total_qty, exit_price):
        if avg_price is None or total_qty == 0:
            return 0, 0
        absolute_profit = (exit_price - avg_price) * total_qty
        percentage_profit = (absolute_profit / (avg_price * total_qty)) * 100
        return absolute_profit, percentage_profit

    def calculate_metrics(self):
        self.total_pnl = sum(trade.profit for trade in self.trades)
        self.num_trades = len(self.trades)
        wins = sum(1 for trade in self.trades if trade.profit > 0)
        self.win_rate = (wins / self.num_trades) * 100 if self.num_trades > 0 else 0
        self.sharpe_ratio = self.calculate_sharpe_ratio()
        self.max_drawdown = self.calculate_max_drawdown()

    def calculate_sharpe_ratio(self):
        returns = [trade.return_pct / 100 for trade in self.trades]
        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)
            sharpe_ratio = (mean_return / std_return) * np.sqrt(len(returns)) if std_return != 0 else 0
        else:
            sharpe_ratio = 0
        return sharpe_ratio

    def calculate_max_drawdown(self):
        equity_curve = self.get_equity_curve()
        if not equity_curve.empty:
            cumulative_max = equity_curve.cummax()
            drawdowns = (equity_curve - cumulative_max) / cumulative_max
            max_drawdown = drawdowns.min() * 100  # As percentage
        else:
            max_drawdown = 0
        return abs(max_drawdown)

    def get_equity_curve(self):
        df = self.df.copy()
        initial_capital = 500.0  # Starting capital
        df['equity'] = initial_capital
        equity = initial_capital
        position_qty = 0.0
        avg_entry_price = 0.0

        for index, row in df.iterrows():
            date = row['date']

            # Check for executed orders
            for qty_col in [col for col in df.columns if col.startswith('£order_executed_')]:
                price_col = 'order_' + qty_col.split('_')[-1]
                qty = row.get(qty_col, 0)
                price = row.get(price_col, np.nan)
                if qty and float(qty) > 0:
                    total_cost = avg_entry_price * position_qty + price * qty
                    position_qty += qty
                    avg_entry_price = total_cost / position_qty

            # Update equity based on current position
            if position_qty > 0:
                # Unrealized PnL
                unrealized_pnl = (row['close'] - avg_entry_price) * position_qty
            else:
                unrealized_pnl = 0

            # Realized PnL is added when we exit a position
            realized_pnl = 0
            exit_signal = row.get('@exit', False)
            if exit_signal and position_qty > 0:
                realized_pnl = unrealized_pnl
                position_qty = 0
                avg_entry_price = 0

            equity += realized_pnl
            total_equity = equity + unrealized_pnl
            df.at[index, 'equity'] = total_equity

        # Store equity curve
        self.df['equity'] = df['equity']
        equity_curve = df['equity']
        return equity_curve

    def get_metrics(self):
        return {
            'Total PnL': self.total_pnl,
            'Number of Trades': self.num_trades,
            'Win Rate (%)': self.win_rate,
            'Sharpe Ratio': self.sharpe_ratio,
            'Max Drawdown (%)': self.max_drawdown,
        }

    def get_trades(self):
        return self.trades
