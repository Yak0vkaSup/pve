# bybit_api.py
import logging
import decimal
from pybit.unified_trading import HTTP, WebSocket

logger = logging.getLogger(__name__)

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
    def __init__(self, api_key, api_secret, testnet=False):
        self.session = HTTP(
            api_key=api_key, 
            api_secret=api_secret, 
            testnet=testnet, 
            recv_window=20000,
            timeout=10  # 10 second timeout for all API calls
        )
        self.__ws = WebSocket(testnet=testnet, channel_type="linear")
        self.instrument_info_cache = {}

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

                if side == 'Buy':
                    long_position.pnl += pnl
                    long_position.qty += qty
                    long_position.positionValue += positionValue
                elif side == 'Sell':
                    short_position.pnl += pnl
                    short_position.qty += qty
                    short_position.positionValue += positionValue
            except Exception as e:
                continue

        return long_position, short_position

    def get_pnl_history(self, symbol):
        """
        Fetches the closed PnL history for the given symbol.
        """
        try:
            response = self.session.get_closed_pnl(category="linear", symbol=symbol)
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logging.error(f"Failed to fetch PnL history: {response['retMsg']}")
                return []
        except Exception as e:
            logging.error(f"Error fetching PnL history: {e}")
            return []

    def get_trade_history(self, symbol):
        """
        Fetches recent execution records for a symbol.
        """
        try:
            response = self.session.get_executions(category="linear", symbol=symbol, limit=50)
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logging.error(f"Failed to fetch trade history: {response['retMsg']}")
                return []
        except Exception as e:
            logging.error(f"Error fetching trade history: {e}")
            return []

    def get_account_balance(self):
        """
        Fetches the account balance details.
        """
        try:
            response = self.session.get_wallet_balance(accountType="CONTRACT")
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logging.error(f"Failed to fetch account balance: {response['retMsg']}")
                return None
        except Exception as e:
            logging.error(f"Error fetching account balance: {e}")
            return None

    def get_risk_limit(self, symbol):
        """
        Retrieves the current risk limit for the given symbol.
        """
        try:
            response = self.session.get_risk_limit(category="linear", symbol=symbol)
            if response['retCode'] == 0:
                return response['result']['list']
            else:
                logging.error(f"Failed to fetch risk limit: {response['retMsg']}")
                return None
        except Exception as e:
            logging.error(f"Error fetching risk limit: {e}")
            return None

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
        # Ensure qty complies with exchange lot size
        try:
            step_size, _ = self.fetch_steps(SYMBOL)
            if step_size is not None:
                # Round DOWN to nearest step to avoid invalidQty errors
                from decimal import Decimal, ROUND_DOWN
                qty_dec = (Decimal(str(qty)).quantize(step_size, rounding=ROUND_DOWN))
                qty = float(qty_dec)
        except Exception:
            # If anything fails, just send the original qty and let the API validate
            pass

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
            if isinstance(response, dict) and response.get("retCode") != 0:
                logging.error(
                    f"Failed to place exit order for {SYMBOL}: retCode={response.get('retCode')} msg={response.get('retMsg')} params={params}"
                )
                return False
            logging.info(f"Placed {side} exit order for {SYMBOL}: Quantity = {qty}")
            return True
        except Exception as e:
            logging.error(f"An error occurred while placing the exit order: {e}")
            return False

    def cancel_all_orders(self, SYMBOL):
        try:
            response = self.session.cancel_all_orders(
                category="linear",
                symbol=SYMBOL,
                settleCoin="USDT",
            )
            if isinstance(response, dict) and response.get("retCode") != 0:
                logging.error(
                    f"Failed to cancel orders for {SYMBOL}: retCode={response.get('retCode')} msg={response.get('retMsg')}"
                )
            else:
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
    def get_instrument_info(self, symbol):
        if symbol in self.instrument_info_cache:
            return self.instrument_info_cache[symbol]
        else:
            try:
                response = self.session.get_instruments_info(category="linear", symbol=symbol)
                if response['retCode'] == 0:
                    for instrument in response['result']['list']:
                        if instrument['symbol'] == symbol:
                            self.instrument_info_cache[symbol] = instrument
                            return instrument
                else:
                    logging.error(f"Failed to fetch instrument info: {response['retMsg']}")
            except Exception as e:
                logging.error(f"An error occurred while fetching instrument info: {e}")
            return None

    def fetch_steps(self, symbol):
        instrument = self.get_instrument_info(symbol)
        if instrument:
            step_size = decimal.Decimal(str(instrument['lotSizeFilter']['qtyStep']))
            price_step = decimal.Decimal(str(instrument['priceFilter']['tickSize']))
            logging.info(
                f"Fetched step size and price step for {symbol}: qtyStep = {step_size}, priceStep = {price_step}")
            return step_size, price_step
        else:
            logging.error("Failed to fetch step size or tick size.")
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
