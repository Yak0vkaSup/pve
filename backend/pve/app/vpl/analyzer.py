from datetime import datetime
import logging
from decimal import Decimal, InvalidOperation, getcontext
import pandas as pd
from dataclasses import dataclass, field
from typing import List

# Configure logging for this module
logger = logging.getLogger(__name__)

# Optionally set higher precision if needed
getcontext().prec = 12

# Bybit Derivatives fee rates (calibrated to match actual observed fees)
# Actual observed rates are lower than stated rates, likely due to VIP discounts
MAKER_FEE_RATE = Decimal('0.00036')
TAKER_FEE_RATE = Decimal('0.001')

@dataclass
class ExecutedOrder:
    index: int
    time: pd.Timestamp
    price: Decimal
    qty: Decimal
    side: str = "BUY"  # "BUY" or "SELL"
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
    fees: Decimal = Decimal('0')  # total fees for this trade
    profit: Decimal = Decimal('0')  # net profit (after fees)
    return_pct: Decimal = Decimal('0')
    funding_cost: Decimal = Decimal('0')  # funding cost for this trade
    opening_fees: Decimal = Decimal('0')  # fees for opening the position
    closing_fees: Decimal = Decimal('0')  # fees for closing the position

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def format_timedelta_full(td):
    days = td.days
    seconds = td.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    else:
        return f"{hours}h {minutes}m {seconds}s"

def convert_timestamp_to_ms(ts):
    if isinstance(ts, pd.Timestamp):
        return int(ts.value // 10 ** 6)
    try:
        return int(float(ts) * 1000)
    except Exception:
        return None

class BacktestAnalyzer:
    def __init__(self, df, orders, symbol, initial_capital, precision, min_move):
        """
        df: DataFrame with market data.
        orders: List of orders (JSON/dict) – each must have:
                'time_executed' (or 'time_created'), 'price', 'quantity'
                and a 'direction' field (True for BUY, False for SELL).
        symbol: Symbol string.
        initial_capital: Decimal initial capital.
        precision: (optional) Number of decimal places for the price.
        min_move: (optional) The minimum price move.
        """
        self.df = df.copy()
        self.orders = orders
        self.symbol = symbol
        self.initial_capital = Decimal(initial_capital)
        self.precision = precision
        self.min_move = min_move
        self.trades: List[Trade] = []
        self.total_fees: Decimal = Decimal('0')
        self.total_funding_cost: Decimal = Decimal('0')
        self.parse_trades()
        self.calculate_metrics()
        self.equity_curve = self.get_equity_curve()  # Now a list of dicts.
        self.calculate_funding_costs()

    def parse_trades(self):
        """
        Position-based trade parsing that matches exchange behavior.
        Tracks net position and weighted average entry price.
        """
        # Sort orders by execution time
        sorted_orders = sorted(self.orders, key=lambda o: o.get('time_executed') or o.get('time_created'))
        
        # Position tracking variables
        position = Decimal('0')  # Net position (positive = long, negative = short)
        position_value = Decimal('0')  # Total value invested in current position
        position_fees = Decimal('0')  # Accumulated fees for current position
        position_start_time = None
        trades = []
        
        logger.info(f"Processing {len(sorted_orders)} orders for position-based analysis")
        
        for i, order in enumerate(sorted_orders):
            if order.get("status") != "executed":
                continue

            # Parse order data
            time = pd.to_datetime(order.get('time_executed') or order.get('time_created'))
            try:
                price = Decimal(str(order.get('price', '0')))
                if self.precision is not None:
                    price = price.quantize(Decimal('1.' + '0' * int(self.precision)))
                if self.min_move is not None:
                    min_move_decimal = Decimal(str(self.min_move))
                    price = (price // min_move_decimal) * min_move_decimal
            except:
                price = Decimal('0')

            try:
                qty = abs(Decimal(str(order.get('quantity', '0'))))
            except:
                qty = Decimal('0')
                
            # Determine signed quantity (positive for BUY, negative for SELL)
            is_buy = order.get("direction", True)
            signed_qty = qty if is_buy else -qty
            
            # Calculate fee - Bybit charges fees on both opening and closing positions
            order_type = order.get("type", "limit").lower()
            order_category = order.get("order_category", "normal")
            
            # Determine if order is maker or taker
            if order_type == "market" or order_category == "conditional":
                fee_rate = TAKER_FEE_RATE
            elif order_type == "limit":
                # For limit orders, check if price suggests maker or taker execution
                # This is a heuristic - limit orders that are aggressive (close to market price) 
                # are more likely to be taker orders
                current_close = None
                if hasattr(self, 'df') and not self.df.empty:
                    # Try to find the market price at order execution time
                    order_time = pd.to_datetime(order.get('time_executed') or order.get('time_created'))
                    df_at_time = self.df[self.df['date'] <= order_time.timestamp()]
                    if not df_at_time.empty:
                        current_close = float(df_at_time.iloc[-1]['close'])
                
                if current_close is not None:
                    price_diff_pct = abs(float(price) - current_close) / current_close * 100
                    # If order price is within 0.01% of market price, likely taker
                    if price_diff_pct < 0.01:
                        fee_rate = TAKER_FEE_RATE
                    else:
                        fee_rate = MAKER_FEE_RATE
                else:
                    # Default to maker rate if we can't determine market context
                    fee_rate = MAKER_FEE_RATE
            else:
                fee_rate = MAKER_FEE_RATE
                
            # Calculate notional value and fee
            notional = price * qty
            fee = round(notional * fee_rate, 4)
            
            # Store previous position for comparison
            prev_position = position
            prev_position_value = position_value
            prev_position_fees = position_fees
            
            # Update position
            position += signed_qty
            
            logger.debug(f"Order {i}: {order.get('id')} - {'BUY' if is_buy else 'SELL'} {qty} @ {price}")
            logger.debug(f"Position: {prev_position} -> {position}")
            
            # Check for position changes
            if prev_position == 0:
                # Opening new position
                position_value = price * abs(signed_qty)
                position_fees = round(fee, 4)
                position_start_time = time
                logger.debug(f"Opening new position: {position} @ {price}")
                
            elif position == 0:
                # Closing entire position
                closed_qty = abs(prev_position)
                avg_entry_price = round(prev_position_value / closed_qty, 4)
                
                # Bybit-style fee calculation: opening fees + closing fees
                opening_fees = round(prev_position_fees, 4)
                closing_fees = round(fee, 4)
                total_fees = round(opening_fees + closing_fees, 4)
                
                # Calculate profit based on position direction
                if prev_position > 0:  # Was long position
                    profit = round((round(price, 4) - avg_entry_price) * closed_qty - total_fees, 4)
                else:  # Was short position
                    profit = round((avg_entry_price - round(price, 4)) * closed_qty - total_fees, 4)
                
                return_pct = round((profit / prev_position_value * Decimal('100')) if prev_position_value != 0 else Decimal('0'), 2)
                
                trade = Trade(
                    entry_index=0,
                    exit_index=i,
                    entry_time=position_start_time,
                    exit_time=time,
                    entry_price=avg_entry_price,
                    exit_price=round(price, 4),
                    qty=closed_qty,
                    executed_orders=[],
                    fees=total_fees,
                    profit=profit,
                    return_pct=return_pct,
                    opening_fees=opening_fees,
                    closing_fees=closing_fees
                )
                trades.append(trade)
                
                logger.debug(f"Closed position: {closed_qty} @ {avg_entry_price} -> {round(price, 4)}")
                logger.debug(f"Opening fees: {opening_fees}, Closing fees: {closing_fees}, Total: {total_fees}")
                logger.debug(f"Profit: {profit}")
                
                # Reset position tracking
                position_value = Decimal('0')
                position_fees = Decimal('0')
                position_start_time = None
                
            elif (prev_position > 0 and position < 0) or (prev_position < 0 and position > 0):
                # Position reversal (close old + open new)
                closed_qty = abs(prev_position)
                avg_entry_price = round(prev_position_value / closed_qty, 4)
                
                # Bybit-style fee calculation for position reversal
                # The current order fee is split between closing old position and opening new position
                closing_portion = closed_qty / qty
                closing_fees = round(fee * closing_portion, 4)
                opening_fees = round(prev_position_fees, 4)
                total_close_fees = round(opening_fees + closing_fees, 4)
                
                # Calculate profit for closed portion
                if prev_position > 0:  # Was long position
                    close_profit = round((round(price, 4) - avg_entry_price) * closed_qty - total_close_fees, 4)
                else:  # Was short position
                    close_profit = round((avg_entry_price - round(price, 4)) * closed_qty - total_close_fees, 4)
                
                close_return_pct = round((close_profit / prev_position_value * Decimal('100')) if prev_position_value != 0 else Decimal('0'), 2)
                
                # Create trade for closed position
                trade = Trade(
                    entry_index=0,
                    exit_index=i,
                    entry_time=position_start_time,
                    exit_time=time,
                    entry_price=avg_entry_price,
                    exit_price=round(price, 4),
                    qty=closed_qty,
                    executed_orders=[],
                    fees=total_close_fees,
                    profit=close_profit,
                    return_pct=close_return_pct,
                    opening_fees=opening_fees,
                    closing_fees=closing_fees
                )
                trades.append(trade)
                
                logger.debug(f"Position reversal - Closed: {closed_qty} @ {avg_entry_price} -> {round(price, 4)}, profit: {close_profit}")
                
                # Start new position in opposite direction
                remaining_qty = abs(position)
                remaining_fee = round(fee * (1 - closing_portion), 4)
                position_value = price * remaining_qty
                position_fees = remaining_fee
                position_start_time = time
                
                logger.debug(f"Starting new position: {position} @ {round(price, 4)}")
                
            elif (prev_position > 0 and position > 0 and position > prev_position) or \
                 (prev_position < 0 and position < 0 and abs(position) > abs(prev_position)):
                # Adding to existing position in same direction
                add_qty = abs(signed_qty)
                position_value = prev_position_value + (price * add_qty)
                position_fees = round(prev_position_fees + fee, 4)
                
                logger.debug(f"Adding to position: {add_qty} @ {round(price, 4)}")
                
            elif (prev_position > 0 and position > 0 and position < prev_position) or \
                 (prev_position < 0 and position < 0 and abs(position) < abs(prev_position)):
                # Partial close of existing position
                closed_qty = abs(prev_position) - abs(position)
                avg_entry_price = round(prev_position_value / abs(prev_position), 4)
                
                # Calculate profit for closed portion
                if prev_position > 0:  # Long position
                    partial_profit = (round(price, 4) - avg_entry_price) * closed_qty
                else:  # Short position
                    partial_profit = (avg_entry_price - round(price, 4)) * closed_qty
                
                # Bybit-style fee calculation for partial close
                closing_ratio = closed_qty / abs(prev_position)
                allocated_opening_fees = round(prev_position_fees * closing_ratio, 4)
                closing_fees = round(fee, 4)
                total_fees = round(allocated_opening_fees + closing_fees, 4)
                partial_profit = round(partial_profit - total_fees, 4)
                
                partial_return_pct = round((partial_profit / (avg_entry_price * closed_qty) * Decimal('100')) if (avg_entry_price * closed_qty) != 0 else Decimal('0'), 2)
                
                trade = Trade(
                    entry_index=0,
                    exit_index=i,
                    entry_time=position_start_time,
                    exit_time=time,
                    entry_price=avg_entry_price,
                    exit_price=round(price, 4),
                    qty=closed_qty,
                    executed_orders=[],
                    fees=total_fees,
                    profit=partial_profit,
                    return_pct=partial_return_pct,
                    opening_fees=allocated_opening_fees,
                    closing_fees=closing_fees
                )
                trades.append(trade)
                
                logger.debug(f"Partial close: {closed_qty} @ {avg_entry_price} -> {round(price, 4)}, profit: {partial_profit}")
                
                # Update remaining position (reduce opening fees proportionally)
                remaining_ratio = abs(position) / abs(prev_position)
                position_value = prev_position_value * remaining_ratio
                position_fees = round(prev_position_fees * remaining_ratio, 4)
        
        logger.info(f"Created {len(trades)} trades from position tracking")
        self.trades = trades

    def calculate_metrics(self):
        self.total_pnl = sum(trade.profit for trade in self.trades)
        self.total_fees = sum(trade.fees for trade in self.trades)
        self.num_trades = len(self.trades)
        wins = sum(1 for trade in self.trades if trade.profit > Decimal('0'))
        self.win_rate = (wins / self.num_trades) * 100 if self.num_trades > 0 else 0
        self.sharpe_ratio = self.calculate_sharpe_ratio()
        self.max_drawdown = self.calculate_max_drawdown()
        if self.trades:
            durations = [pd.Timedelta(seconds=(trade.exit_time - trade.entry_time).total_seconds())
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
            sharpe_ratio = (mean_return / std_return) * (Decimal(n).sqrt()) if std_return != Decimal('0') else Decimal('0')
        else:
            sharpe_ratio = Decimal('0')
        return sharpe_ratio

    def calculate_max_drawdown(self):
        equity_points = self.get_equity_curve()  # a list of dicts with 'time' and 'equity'
        if not equity_points:
            return 0
        df_ec = pd.DataFrame(equity_points)
        cumulative_max = df_ec['equity'].cummax()
        drawdowns = (df_ec['equity'] - cumulative_max) / cumulative_max
        max_drawdown = drawdowns.min() * 100  # as percentage
        return abs(max_drawdown)

    def get_equity_curve(self):
        """
        Build an equity curve based on cumulative profit from closed trades.
        Returns a list of dictionaries with the timestamp (ISO format) and the equity value.
        """
        sorted_trades = sorted(self.trades, key=lambda t: t.exit_time)
        equity_points = []
        capital = self.initial_capital
        for trade in sorted_trades:
            capital += trade.profit
            equity_points.append({
                "time": trade.exit_time.isoformat(),
                "equity": float(capital)
            })
        return equity_points

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
        return round(funding_cost, 4)  # Round to 4 decimal places to match Bybit format

    def calculate_funding_costs(self):
        total_funding = Decimal('0')
        for trade in self.trades:
            try:
                fc = self.calculate_funding_cost_for_trade(trade)
                trade.funding_cost = fc
                total_funding += fc
            except Exception as e:
                logger.warning(f"Could not fetch funding for trade: {e}")
                trade.funding_cost = Decimal('0')
        self.total_funding_cost = round(total_funding, 4)  # Round total funding cost too

    def get_metrics(self):
        initial_capital = self.initial_capital
        final_equity = Decimal(str(self.equity_curve[-1]["equity"])) if self.equity_curve else initial_capital
        global_return_pct = ((final_equity - initial_capital) / initial_capital) * Decimal('100')
        first_date = pd.to_datetime(self.df['date'].iloc[0], unit='s') if 'date' in self.df.columns else None
        last_date = pd.to_datetime(self.df['date'].iloc[-1], unit='s') if 'date' in self.df.columns else None
        first_date_str = first_date.isoformat() if first_date is not None else None
        last_date_str = last_date.isoformat() if last_date is not None else None
        df_duration = (last_date - first_date) if (first_date and last_date) else None
        return {
            'Symbol': self.symbol,
            'Initial Capital': round(float(initial_capital), 2),
            'Final Capital': round(float(final_equity), 2),
            'First Date': first_date_str,
            'Last Date': last_date_str,
            'DF Duration': format_timedelta_full(df_duration) if df_duration is not None else None,
            'Total PnL': round(float(self.total_pnl), 2),
            'Total Fees': round(float(self.total_fees), 2),
            'Total Funding Cost': round(float(self.total_funding_cost), 2),
            'Number of Trades': self.num_trades,
            'Win Rate (%)': round(self.win_rate),
            'Sharpe Ratio': round(float(self.sharpe_ratio), 2),
            'Max Drawdown (%)': round(self.max_drawdown, 2),
            'Average Trade Duration': format_timedelta(self.avg_trade_duration),
            'Global Return (%)': round(float(global_return_pct), 2)
        }

    def get_trades(self):
        return self.trades

    def get_positions_summary(self):
        """
        Format trades like Bybit's closed positions display for easy comparison.
        Returns list of position dictionaries matching Bybit format.
        """
        positions = []
        for i, trade in enumerate(self.trades, 1):
            position_type = "Buy"  # All positions are "Buy" in Bybit display (direction shown by profit)
            
            # Format duration
            duration = trade.exit_time - trade.entry_time
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                duration_str = f"{hours}H {minutes}M"
            else:
                duration_str = f"{minutes}M {seconds}S"
            
            # Format profit with sign
            profit_str = f"+{trade.profit:.4f}" if trade.profit >= 0 else f"{trade.profit:.4f}"
            result = "Win" if trade.profit >= 0 else "Loss"
            
            # Calculate entry and exit values
            entry_value = float(trade.entry_price * trade.qty)
            exit_value = float(trade.exit_price * trade.qty)
            
            position = {
                "symbol": self.symbol,
                "qty": int(trade.qty),
                "entry_price": f"{trade.entry_price:.4f}",
                "exit_price": f"{trade.exit_price:.4f}",
                "side": position_type,
                "pnl": profit_str,
                "entry_value": f"{entry_value:.2f}",
                "exit_value": f"{exit_value:.2f}",
                "result": result,
                "opening_fees": f"{trade.opening_fees:.4f}",
                "closing_fees": f"{trade.closing_fees:.4f}",
                "total_fees": f"{trade.fees:.4f}",
                "funding": f"{trade.funding_cost:.4f}",
                "duration": duration_str,
                "entry_time": trade.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_time": trade.exit_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            positions.append(position)
        
        return positions

    def print_positions_like_bybit(self):
        """
        Print positions in Bybit-style format for easy comparison.
        """
        positions = self.get_positions_summary()
        
        print(f"\n=== {self.symbol} POSITIONS (Backtest) ===")
        print()
        
        for pos in positions:
            print(f"{pos['symbol']}")
            print(f"\t{pos['qty']}\t{pos['entry_price']}\t{pos['exit_price']}\t{pos['side']}\t{pos['pnl']}\t{pos['entry_value']}\t{pos['exit_value']}\t{pos['result']}\t{pos['opening_fees']}\t{pos['closing_fees']}\t{pos['funding']}\t{pos['duration']}\t{pos['entry_time']}\t{pos['exit_time']}")
            print()
        
        # Summary stats
        total_positions = len(positions)
        wins = sum(1 for p in positions if p['result'] == 'Win')
        losses = total_positions - wins
        win_rate = (wins / total_positions * 100) if total_positions > 0 else 0
        
        total_pnl = sum(float(p['pnl'].replace('+', '')) for p in positions)
        
        print("Summary")
        print(f"Total Positions: {total_positions}")
        print(f"Win Rate: {win_rate:.0f}% ({wins} Win/{losses} Loss)")
        print(f"Total P&L: {total_pnl:.2f} USD")
        print(f"Total Fees: {float(self.total_fees):.2f} USD")
        print(f"Average Trade Duration: {format_timedelta(self.avg_trade_duration)}")
        
        return positions

    def debug_vs_bybit(self, bybit_trades):
        """
        Debug method to compare our results with actual Bybit trades.
        bybit_trades: list of dicts with Bybit trade data
        """
        print("\n=== DETAILED COMPARISON: Backtest vs Bybit ===")
        print()
        
        # Sort both by quantity for easier matching
        our_trades = sorted(self.trades, key=lambda t: t.qty, reverse=True)
        bybit_sorted = sorted(bybit_trades, key=lambda t: abs(t.get('qty', 0)), reverse=True)
        
        total_pnl_diff = 0
        total_fee_diff = 0
        
        for i, (our_trade, bybit_trade) in enumerate(zip(our_trades, bybit_sorted)):
            bybit_qty = abs(bybit_trade.get('qty', 0))
            bybit_entry = float(bybit_trade.get('entry_price', 0))
            bybit_exit = float(bybit_trade.get('exit_price', 0))
            bybit_pnl = float(bybit_trade.get('pnl', 0))
            bybit_fee = float(bybit_trade.get('fee', 0))
            
            our_qty = float(our_trade.qty)
            our_entry = float(our_trade.entry_price)
            our_exit = float(our_trade.exit_price)
            our_pnl = float(our_trade.profit)
            our_fee = float(our_trade.fees)
            
            print(f"Trade {i+1} (Qty: {our_qty}):")
            print(f"  Entry Price:  Ours={our_entry:.6f}  Bybit={bybit_entry:.4f}  Diff={our_entry-bybit_entry:.6f}")
            print(f"  Exit Price:   Ours={our_exit:.6f}   Bybit={bybit_exit:.4f}   Diff={our_exit-bybit_exit:.6f}")
            print(f"  PnL:          Ours={our_pnl:.4f}      Bybit={bybit_pnl:.4f}      Diff={our_pnl-bybit_pnl:.4f}")
            print(f"  Fees:         Ours={our_fee:.6f}    Bybit={bybit_fee:.4f}    Diff={our_fee-bybit_fee:.6f}")
            print()
            
            total_pnl_diff += (our_pnl - bybit_pnl)
            total_fee_diff += (our_fee - bybit_fee)
        
        print(f"SUMMARY:")
        print(f"Total PnL Difference: {total_pnl_diff:.4f}")
        print(f"Total Fee Difference: {total_fee_diff:.6f}")
        print(f"Our Total PnL: {float(self.total_pnl):.4f}")
        print(f"Bybit Total PnL: {sum(float(t.get('pnl', 0)) for t in bybit_trades):.4f}")
        print(f"Our Total Fees: {float(self.total_fees):.6f}")
        print(f"Bybit Total Fees: {sum(float(t.get('fee', 0)) for t in bybit_trades):.6f}")

    def calibrate_fee_rates(self, bybit_trades):
        """
        Analyze actual Bybit trades to suggest optimal fee rates for backtest calibration.
        
        Args:
            bybit_trades: List of actual Bybit trades with structure:
                         [{'qty': X, 'entry_price': Y, 'exit_price': Z, 'opening_fee': A, 'closing_fee': B, ...}]
        
        Returns:
            dict: Suggested fee rates and analysis
        """
        if not bybit_trades:
            print("No Bybit trades provided for calibration")
            return None
            
        print("\n=== FEE RATE CALIBRATION ANALYSIS ===")
        print()
        
        opening_fee_rates = []
        closing_fee_rates = []
        
        for trade in bybit_trades:
            qty = abs(float(trade.get('qty', 0)))
            entry_price = float(trade.get('entry_price', 0))
            exit_price = float(trade.get('exit_price', 0))
            opening_fee = float(trade.get('opening_fee', 0))
            closing_fee = float(trade.get('closing_fee', 0))
            
            if qty > 0 and entry_price > 0 and exit_price > 0:
                # Calculate fee rates
                entry_notional = entry_price * qty
                exit_notional = exit_price * qty
                
                if entry_notional > 0:
                    opening_rate = opening_fee / entry_notional
                    opening_fee_rates.append(opening_rate)
                    
                if exit_notional > 0:
                    closing_rate = closing_fee / exit_notional
                    closing_fee_rates.append(closing_rate)
                    
                print(f"Trade: Qty={qty}, Entry={entry_price:.4f}, Exit={exit_price:.4f}")
                print(f"  Opening: {opening_fee:.4f} / {entry_notional:.2f} = {opening_rate:.6f} ({opening_rate*100:.4f}%)")
                print(f"  Closing: {closing_fee:.4f} / {exit_notional:.2f} = {closing_rate:.6f} ({closing_rate*100:.4f}%)")
                print()
        
        if opening_fee_rates and closing_fee_rates:
            avg_opening_rate = sum(opening_fee_rates) / len(opening_fee_rates)
            avg_closing_rate = sum(closing_fee_rates) / len(closing_fee_rates)
            avg_combined_rate = (avg_opening_rate + avg_closing_rate) / 2
            
            print("CALIBRATION RESULTS:")
            print(f"Average Opening Fee Rate: {avg_opening_rate:.6f} ({avg_opening_rate*100:.4f}%)")
            print(f"Average Closing Fee Rate: {avg_closing_rate:.6f} ({avg_closing_rate*100:.4f}%)")
            print(f"Average Combined Rate: {avg_combined_rate:.6f} ({avg_combined_rate*100:.4f}%)")
            print()
            print("RECOMMENDED SETTINGS:")
            print(f"MAKER_FEE_RATE = Decimal('{avg_combined_rate:.6f}')")
            print(f"TAKER_FEE_RATE = Decimal('{max(avg_opening_rate, avg_closing_rate):.6f}')")
            print()
            print("Add these lines to your analyzer.py file around line 15-16")
            
            return {
                'avg_opening_rate': avg_opening_rate,
                'avg_closing_rate': avg_closing_rate,
                'avg_combined_rate': avg_combined_rate,
                'suggested_maker_rate': avg_combined_rate,
                'suggested_taker_rate': max(avg_opening_rate, avg_closing_rate)
            }
        else:
            print("Could not calculate fee rates from provided data")
            return None

def convert_timestamp(ts):
    try:
        if isinstance(ts, pd.Timestamp):
            return ts.strftime('%Y-%m-%d %H:%M:%S UTC')
        return datetime.utcfromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception as e:
        return ts
