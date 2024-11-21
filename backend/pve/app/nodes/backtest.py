from datetime import datetime, timedelta
from pandas import read_csv
import plotly.graph_objects as go
import time
import decimal
from pybit.unified_trading import HTTP
from pybit.unified_trading import WebSocket
from plotly.subplots import make_subplots
import logging
import random

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("backtester.log"),
    logging.StreamHandler()
])

session = HTTP(testnet=False)


def get_date_delta_days_ago(delta):
    date_days_ago = datetime.now() - timedelta(delta)
    return date_days_ago.strftime('%Y-%m-%d')


class Position:
    def __init__(self, side):
        self.side = side
        self.pnl = 0.0
        self.qty = 0.0
        self.positionValue = 0.0

    @property
    def pnl_perc(self):
        return (self.pnl * 100 / self.positionValue) if self.positionValue != 0.0 else 0.0


class Bybit:
    def __init__(self, api_key, api_secret):
        self.session = HTTP(api_key=api_key, api_secret=api_secret, recv_window=20000)
        self.__ws = WebSocket(testnet=False, channel_type="linear")

    def get_positions(self, SYMBOL):
        positions = self.session.get_positions(category="linear", symbol=SYMBOL)
        if positions['retCode'] != 0:
            logging.critical("Error, can't get positions")
            return None

        long_position = Position("Buy")
        short_position = Position("Sell")

        for position in positions['result']['list']:
            try:
                side = position['side']
                pnl = float(position.get('unrealisedPnl', 0)) + float(position.get('curRealisedPnl', 0))
                qty = float(position['size'])
                positionValue = float(position['positionValue'])

                if side == 'Buy':  # Long position
                    long_position.pnl += pnl
                    long_position.qty += qty
                    long_position.positionValue += positionValue
                elif side == 'Sell':  # Short position
                    short_position.pnl += pnl
                    short_position.qty += qty
                    short_position.positionValue += positionValue
            except Exception as e:
                logging.warning(f"Error processing position, no open position, pnl = 0: {e}")
                continue  # position['unrealisedPnl'] == ""

        logging.info(
            f"Long Position: PnL={long_position.pnl}, Qty={long_position.qty}, Value={long_position.positionValue}")
        logging.info(
            f"Short Position: PnL={short_position.pnl}, Qty={short_position.qty}, Value={short_position.positionValue}")

        return long_position, short_position

    def entry(self, price, side, qty, order_type, SYMBOL, take_profit_price=0, stop_loss_price=0):
        position_idx = 1 if side == "Buy" else 2
        params = {
            "category": "linear",
            "symbol": SYMBOL,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "positionIdx": position_idx,
        }
        if order_type == "Limit":
            params["price"] = str(price)
        try:
            response = self.session.place_order(**params)
            logging.info(f"Placed {side} entry order for {SYMBOL}: Quantity = {qty}, Price = {price}")
            return True
        except Exception as e:
            logging.error(f"An error occurred while placing the entry order: {e}")
            return False

    def exit(self, side, qty, index, SYMBOL):
        position_idx = index
        params = {
            "category": "linear",
            "symbol": SYMBOL,
            "side": side,
            "orderType": "Market",
            "qty": qty,
            "positionIdx": position_idx,
            "reduceOnly": True,
        }
        try:
            response = self.session.place_order(**params)
            logging.info(f"Placed {side} exit order for {SYMBOL}: Quantity = {qty}")
            return True
        except Exception as e:
            logging.error(f"An error occurred while placing the exit order: {e}")
            return False

    def cancel_all_orders(self, SYMBOL):
        try:
            self.session.cancel_all_orders(
                category="linear",
                symbol=SYMBOL,
                settleCoin="USDT",
            )
            logging.info(f"Canceled all orders for {SYMBOL}")
        except Exception as e:
            logging.error(f"An error occurred while canceling the orders: {e}")

    def get_filled_orders(self, symbol):
        try:
            response = self.session.get_open_orders(
                category="linear",
                symbol=symbol,
                openOnly=1,  # Set to fetch recent closed status orders
                limit=100  # Adjust the limit as per your requirement
            )
            if response['retCode'] == 0:
                filled_orders = [order for order in response['result']['list'] if order['orderStatus'] == 'Filled']
                logging.info(f"Successfully fetched filled orders for {symbol}")
                return filled_orders
            else:
                logging.error(f"Failed to fetch orders: {response['retMsg']}")
                return []
        except Exception as e:
            logging.error(f"Error fetching filled orders: {e}")
            return []

    def fetch_steps(self, symbol):
        try:
            response = self.session.get_instruments_info(category="linear", symbol=symbol)
            if response['retCode'] == 0:
                for instrument in response['result']['list']:
                    if instrument['symbol'] == symbol:
                        step_size = decimal.Decimal(str(instrument['lotSizeFilter']['qtyStep']))
                        price_step = decimal.Decimal(str(instrument['priceFilter']['tickSize']))
                        logging.info(
                            f"Fetched step size and price step for {symbol}: qtyStep = {step_size}, priceStep = {price_step}")
                        return step_size, price_step
            else:
                logging.error(f"Failed to fetch step sizes: {response['retMsg']}")
        except Exception as e:
            logging.error(f"An error occurred while fetching the step sizes: {e}")
        return None, None

    def get_symbols_by_turnover(self, turnover):
        try:
            response = self.session.get_tickers(category="linear")

            if response['retCode'] == 0:
                logging.error("Failed to get tickers info")
                filtered_symbols = [ticker['symbol'] for ticker in response['result']['list'] if
                                    float(ticker['turnover24h']) > turnover]
                logging.info(
                    f"Symbols with turnover greater than {turnover}$: {filtered_symbols}, Total number: {len(filtered_symbols)}")
                return filtered_symbols
            else:
                logging.error(f"Failed to get tickers info: {response['retMsg']}")
        except Exception as e:
            logging.error(f"An error occurred while fetching tickers: {e}")
        return None

    def get_symbols_by_volume(self, volume):
        try:
            response = self.session.get_tickers(category="linear")
            if response['retCode'] == 0:
                logging.error("Failed to get tickers info")
                filtered_symbols = [ticker['symbol'] for ticker in response['result']['list'] if
                                    float(ticker['volume24h']) > volume]
                logging.info(
                    f"Symbols with volume greater than 100M: {filtered_symbols}, Total number: {len(filtered_symbols)}")
                return filtered_symbols
            else:
                logging.error(f"Failed to get tickers info: {response['retMsg']}")
        except Exception as e:
            logging.error(f"An error occurred while fetching tickers: {e}")
        return None


class DCA:
    def __init__(self, initial_price, order_size_usdt, step_percentage, num_orders, martingale_factor, bybit_instance,
                 symbol):
        self.initial_price = decimal.Decimal(str(initial_price))
        self.step_percentage = decimal.Decimal(str(step_percentage))
        self.num_orders = num_orders
        self.martingale_factor = decimal.Decimal(str(martingale_factor))
        self.bybit = bybit_instance
        self.symbol = symbol

        # Fetch step size and price step
        self.step_size, self.price_step, self.base_order_size = self.fetch_steps_and_validate(order_size_usdt)
        if not self.step_size or not self.price_step or not self.base_order_size:
            raise ValueError("Failed to fetch valid steps or order size constraints for DCA.")

        # Orders will be calculated here
        self.long_orders = []
        self.short_orders = []
        self.long_avg_price = None
        self.short_avg_price = None

    def fetch_steps_and_validate(self, order_size_usdt):
        """
        Fetch step sizes and validate order constraints.
        Adjust order size if it doesn't meet the minimum requirements.
        """
        step_size, tick_size = self.bybit.fetch_steps(self.symbol)
        if not step_size or not tick_size:
            logging.error("Failed to fetch step size or tick size.")
            return None, None, None

        step_size = decimal.Decimal(str(step_size))
        tick_size = decimal.Decimal(str(tick_size))

        response = self.bybit.session.get_instruments_info(category="linear", symbol=self.symbol)
        if response['retCode'] != 0:
            logging.error(f"Failed to fetch instrument info for {self.symbol}: {response['retMsg']}")
            return None, None, None

        min_order_qty = decimal.Decimal(str(response['result']['list'][0]['lotSizeFilter']['minOrderQty']))
        base_order_size = decimal.Decimal(str(order_size_usdt)) / self.initial_price

        if base_order_size < min_order_qty:
            logging.warning(f"Adjusting order size to meet minimum order quantity: {min_order_qty}")
            base_order_size = min_order_qty

        if base_order_size < min_order_qty:
            logging.error("Adjusted order size is still below the minimum requirement.")
            return None, None, None

        # Align order size with step size
        base_order_size = (base_order_size // step_size) * step_size
        logging.info(f"Validated base order size: {base_order_size}")

        return step_size, tick_size, base_order_size

    def adjust_qty_to_step(self, qty):
        if self.step_size:
            return (decimal.Decimal(str(qty)) // self.step_size) * self.step_size
        return qty

    def adjust_price_to_step(self, price):
        if self.price_step:
            return (decimal.Decimal(str(price)) // self.price_step) * self.price_step
        return price

    def calculate_orders(self):
        """
        Calculate DCA orders based on the initial price, step percentage, and other parameters.
        """
        for i in range(self.num_orders):
            long_price = self.initial_price * (1 - (self.step_percentage / 100) * (i + 1))
            short_price = self.initial_price * (1 + (self.step_percentage / 100) * (i + 1))
            order_size = self.base_order_size * (self.martingale_factor ** i)

            adjusted_qty = round(order_size / self.step_size) * self.step_size
            adjusted_long_price = round(long_price / self.price_step) * self.price_step
            adjusted_short_price = round(short_price / self.price_step) * self.price_step

            self.long_orders.append({'price': float(adjusted_long_price), 'qty': float(adjusted_qty)})
            self.short_orders.append({'price': float(adjusted_short_price), 'qty': float(adjusted_qty)})

            logging.debug(
                f"Order {i + 1}: Long price = {adjusted_long_price}, Short price = {adjusted_short_price}, Qty = {adjusted_qty}")

    def place_long_orders(self):
        for order in self.long_orders:
            success = self.bybit.entry(price=order['price'], side='Buy', qty=order['qty'], order_type='Limit',
                                       SYMBOL=self.symbol)
            if success:
                logging.info(f"Placed long DCA order: Price = {order['price']}, Quantity = {order['qty']}")
            else:
                logging.error(f"Error in placing long orders")

    def place_short_orders(self):
        for order in self.short_orders:
            success = self.bybit.entry(price=order['price'], side='Sell', qty=order['qty'], order_type='Limit',
                                       SYMBOL=self.symbol)
            if success:
                logging.info(f"Placed short DCA order: Price = {order['price']}, Quantity = {order['qty']}")
            else:
                logging.error(f"Error in placing long orders")

    def get_orders(self, position_type):
        """
        Retrieve long or short orders.
        """
        if position_type == 'long':
            return self.long_orders
        elif position_type == 'short':
            return self.short_orders
        else:
            raise ValueError("position_type must be 'long' or 'short'")

    def calculate_grid_average_price(self, position_type):
        orders = self.get_orders(position_type)
        total_qty = sum(order['qty'] for order in orders)
        if total_qty == 0:
            logging.info("No orders to calculate the average price.")
            return None, None
        total_cost = sum(order['price'] * order['qty'] for order in orders)
        average_price = total_cost / total_qty
        if position_type == 'long':
            self.long_avg_price = average_price
        elif position_type == 'short':
            self.short_avg_price = average_price
        adjusted_total_qty = self.adjust_qty_to_step(total_qty)
        adjusted_average_price = average_price
        logging.info(f"Grid Average Price ({position_type.capitalize()}): {average_price}")
        return adjusted_average_price, adjusted_total_qty

    def calculate_total_usdt_for_longs(self):
        """
        Calculate the total USDT required for the DCA grid (long orders).
        """
        total_usdt = sum(order['price'] * order['qty'] for order in self.long_orders)
        logging.info(f"Total USDT required for the full DCA grid: {total_usdt}")
        return total_usdt


def calculate_average_entry_price(executed_orders):
    logging.debug("Calculating average entry price. Executed orders: %s", executed_orders)
    total_qty = sum(order['order']['qty'] for order in executed_orders)
    if total_qty == 0:
        logging.debug("Total quantity is 0. Returning None for average price and quantity.")
        return None, None
    total_cost = sum(order['order']['price'] * order['order']['qty'] for order in executed_orders)
    average_price = total_cost / total_qty
    logging.debug("Calculated average price: %f, Total quantity: %f", average_price, total_qty)
    return average_price, total_qty


def backtest(df, entries, symbol, bybit, config):
    logging.debug("Backtest started with config: %s", config)
    start_time = time.time()
    in_position = False
    current_dca_orders = []
    all_dca_orders = []
    current_executed_orders = []  # Current executed orders
    all_executed_orders = []  # All executed orders
    current_executed_prices = set()  # Set to store executed order prices
    all_avg_entry_prices = []  # All average entry prices
    current_avg_entry_prices = []  # Current average entry prices
    all_profits = []  # All profits
    plot_segments = []
    last_avg_price = None  # Last average price
    last_total_qty = 0  # Last quantity
    num_orders = None
    entry_candle_index = None
    plot_start_index = None

    # Add entry, exit, and order executed columns initialized to False
    df['entry'] = False
    df['@exit'] = False
    df['_signal_'] = entries

    for i in range(config['num_orders']):
        df[f'£order_executed_{i + 1}'] = False

    for index, row in df.iterrows():
        if index == df.index[0]:
            continue
        yo = row['_signal_']

        # Entry condition
        if yo and not in_position:
            logging.debug("Entry condition met at index %s. YO: %s, Close price: %f", index, yo, row['close'])

            entry_price = row['close']
            in_position = True
            plot_start_index = index
            usdt_size = config['first_order_size_usdt']
            order = int(usdt_size / row['close'])
            logging.debug("Initializing DCA with entry price: %f, USDT size: %f, Calculated order size: %d",
                          entry_price, usdt_size, order)

            try:
                dca = DCA(
                    initial_price=entry_price,
                    order_size_usdt=config['first_order_size_usdt'],
                    step_percentage=config['step_percentage'],
                    num_orders=config['num_orders'],
                    martingale_factor=config['martingale_factor'],
                    bybit_instance=bybit,
                    symbol=symbol,
                )
                dca.calculate_orders()

                logging.debug(
                    f"Calculated DCA orders: Long Orders = {dca.long_orders}, Short Orders = {dca.short_orders}")
                current_dca_orders = dca.get_orders('long')  # Example: Using long orders for this test
                df.at[index, 'entry'] = True
                logging.debug("DCA orders calculated. Long orders: %s, Short orders: %s", dca.long_orders,
                              dca.short_orders)

                dca.calculate_orders()

                # Calculate total USDT required for the DCA grid and log
                total_usdt_required = dca.calculate_total_usdt_for_longs()

                # for dataviz
                entry_candle_index = index
                num_orders = dca.num_orders
                all_dca_orders.extend(current_dca_orders)

            except ValueError as e:
                logging.error(f"Failed to initialize DCA: {e}")
                continue


        elif in_position:
            order_executed = False
            for i, order in enumerate(current_dca_orders):
                if row['close'] <= order['price'] and order['price'] not in current_executed_prices:
                    order_executed = True
                    df.at[index, f'£order_executed_{i + 1}'] = True
                    logging.debug(f"Order executed at {order['price']} for quantity {order['qty']}")

                    current_executed_orders.append({'order': order, 'index': index})
                    all_executed_orders.append({'order': order, 'index': index})
                    current_executed_prices.add(order['price'])

                    last_avg_price, last_total_qty = calculate_average_entry_price(current_executed_orders)

                    current_avg_entry_prices.append({'price': last_avg_price, 'index': index})
                    all_avg_entry_prices.append({'price': last_avg_price, 'index': index})

            if not order_executed and last_avg_price is not None:
                current_avg_entry_prices.append({'price': last_avg_price, 'index': index})
                all_avg_entry_prices.append({'price': last_avg_price, 'index': index})

            # Exit if no orders executed in the last `candles_to_close` candles
            if (df.index.get_loc(index) - df.index.get_loc(entry_candle_index)) >= config[
                'candles_to_close'] and not current_executed_orders:
                logging.debug(
                    f"No orders executed in the last {config['candles_to_close']} candles, closing position at index {index}")
                in_position = False
                plot_end_index = index
                plot_segments.append((plot_start_index, plot_end_index))
                current_dca_orders = []
                current_executed_orders = []
                current_executed_prices = set()
                current_avg_entry_prices = []
                last_avg_price = None
                last_total_qty = 0

                # Mark exit as True
                df.at[index, '@exit'] = True

            # Calculate position profit
            if last_avg_price is not None:
                absolute_profit, percentage_profit = calculate_position_profit(last_avg_price, last_total_qty,
                                                                               row['close'])
                all_profits.append(
                    {'absolute_profit': absolute_profit, 'percentage_profit': percentage_profit, 'index': index})

                # Exit condition based on profit target
                if percentage_profit >= config['profit_target']:
                    logging.info(f"Exiting position at index {index} with profit {percentage_profit:.2f}%")
                    in_position = False
                    plot_end_index = index
                    plot_segments.append((plot_start_index, plot_end_index))
                    current_dca_orders = []
                    current_executed_orders = []
                    current_executed_prices = set()
                    current_avg_entry_prices = []
                    last_avg_price = None
                    last_total_qty = 0

                    # Mark exit as True
                    df.at[index, '@exit'] = True

    end_time = time.time()
    logging.info(f"Backtest time taken: {end_time - start_time:.2f} seconds")
    print(df.head(50))
    df.drop('_signal_', axis=1, inplace=True)
    df.drop('entry', axis=1, inplace=True)

    # all_profits_pve = plot_orders(df, all_dca_orders, all_executed_orders, all_avg_entry_prices, all_profits, symbol,
    #                               plot_segments, num_orders)

    return df


def calculate_position_profit(avg_price, total_qty, current_price):
    absolute_profit = (current_price - avg_price) * total_qty
    percentage_profit = (absolute_profit / (avg_price * total_qty)) * 100
    return absolute_profit, percentage_profit


def plot_orders(df, all_dca_orders, executed_orders, avg_entry_prices, profits, symbol, plot_segments, num_orders):
    # Создаем фигуру с двумя графиками, при этом второй график будет меньше по высоте
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.7, 0.3],  # Устанавливаем высоту графиков
                        subplot_titles=(f'{symbol} Price and Orders', 'Position Profit'))

    # Первый график: цена и ордера
    fig.add_trace(go.Scatter(x=df.index, y=df['close'], mode='lines', name='Close Price'), row=1, col=1)

    order_index = 0
    for segment in plot_segments:
        segment_df = df.loc[segment[0]:segment[1]]

        # Plot only the relevant orders for this segment
        segment_orders = all_dca_orders[order_index:order_index + num_orders]
        for order in segment_orders:
            fig.add_trace(go.Scatter(x=[segment_df.index[0], segment_df.index[-1]], y=[order['price'], order['price']],
                                     mode='lines',
                                     name=f'Buy Order @ {order["price"]}'), row=1, col=1)

        # Move to the next set of orders for the next segment
        order_index += num_orders

        for executed in executed_orders:
            if segment[0] <= executed['index'] <= segment[1]:
                order = executed['order']
                execution_index = executed['index']
                fig.add_trace(go.Scatter(x=[execution_index], y=[order['price']], mode='markers',
                                         name=f'Executed Order @ {order["price"]} for qty {order["qty"]}',
                                         marker=dict(color='green', size=10)), row=1, col=1)

    if avg_entry_prices:
        for segment in plot_segments:
            segment_avg_prices = [price for price in avg_entry_prices if segment[0] <= price['index'] <= segment[1]]
            if segment_avg_prices:
                ladder_x = []
                ladder_y = []

                for i in range(len(segment_avg_prices)):
                    current = segment_avg_prices[i]
                    previous = segment_avg_prices[i - 1] if i > 0 else current
                    ladder_x.extend([previous['index'], current['index']])
                    ladder_y.extend([previous['price'], current['price']])

                fig.add_trace(go.Scatter(x=ladder_x, y=ladder_y, mode='lines', name='Average Entry Price',
                                         line=dict(color='red', width=2)), row=1, col=1)

    # Второй график: прибыль позиции
    all_indexes = []
    all_profits = []
    if profits:
        cumulative_percentage_profit = 0

        for segment in plot_segments:
            segment_profits = [profit['percentage_profit'] for profit in profits if
                               segment[0] <= profit['index'] <= segment[1]]
            segment_indexes = [profit['index'] for profit in profits if segment[0] <= profit['index'] <= segment[1]]

            if segment_profits:
                cumulative_segment_profit = [cumulative_percentage_profit + p for p in segment_profits]
                cumulative_percentage_profit = cumulative_segment_profit[-1]

                all_indexes.extend(segment_indexes)
                all_profits.extend(cumulative_segment_profit)

        fig.add_trace(
            go.Scatter(x=all_indexes, y=all_profits, mode='lines', name='Cumulative Position Profit',
                       line=dict(color='green', width=2)), row=2, col=1)
    # fig.add_trace(
    #     go.Scatter(x=df.index, y=df['rsi21'], mode='lines', name='RSI',
    #                line=dict(color='green', width=2)), row=2, col=1)

    # profit_x = [profit['index'] for profit in profits]
    # profit_y = [profit['percentage_profit'] for profit in profits]
    #
    # fig.add_trace(
    #     go.Scatter(x=profit_x, y=profit_y, mode='lines', name='Cumulative Position Profit',
    #                line=dict(color='green', width=2)), row=2, col=1)

    # Настраиваем внешний вид графиков
    fig.update_layout(
        title=f'DCA Orders and Profit for {symbol}',
        xaxis_title='Date',
        yaxis_title='Price',
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(font=dict(size=12)),
        xaxis2_title='Date',
        yaxis2_title='Profit %',
        height=1080  # Общая высота фигуры
    )

    fig.show()

    return all_profits


def random_search(df, symbol, bybit, n_iter=100):
    best_config = None
    best_profit = float('-inf')

    for _ in range(n_iter):
        config = {
            'profit_target': round(random.uniform(0.5, 3.0), 1),
            'first_order_size_usdt': int(random.uniform(10, 10)),
            'step_percentage': round(random.uniform(0.3, 3.0), 1),
            'num_orders': int(random.randint(10, 25)),
            'martingale_factor': round(random.uniform(1.1, 2.0), 2),
            'candles_to_close': int(random.randint(30, 80))
        }

        total_profit = 0
        profits = backtest(df, symbol, bybit, config)
        if profits is not None and len(profits) > 0:
            total_profit += profits[-1]
        else:
            print(f"Warning: No profits returned for symbol {symbol} with config {config}")

        if total_profit > best_profit:
            best_profit = total_profit
            best_config = config

        print(
            f"Iteration {_ + 1}/{n_iter} - Current Profit: {total_profit} - Best Profit: {best_profit} Config: {config}", )

    return best_config, best_profit

if __name__ == '__main__':
    api_key = ""
    api_secret = ""
    bybit = Bybit(api_key, api_secret)

    df = read_csv('out.csv', )
    df = df.fillna(value=0)

    config = {
        'profit_target': 1,
        'first_order_size_usdt': 10,
        'step_percentage': 0.5,
        'num_orders': 3,
        'martingale_factor': 1.25,
        'candles_to_close': 3000}

    pve = backtest(df, df['$Alert'], 'BTCUSDT',  bybit, config)
    for col in pve.columns:
        print(col)

    print(pve.head(50))
