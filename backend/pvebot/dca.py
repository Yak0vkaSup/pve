# dca.py
import decimal
import logging

logger = logging.getLogger(__name__)

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
        # Fetch step sizes and instrument info from cache
        instrument = self.bybit.get_instrument_info(self.symbol)
        if not instrument:
            logging.error("Failed to fetch instrument info.")
            return None, None, None

        step_size = decimal.Decimal(str(instrument['lotSizeFilter']['qtyStep']))
        tick_size = decimal.Decimal(str(instrument['priceFilter']['tickSize']))
        min_order_qty = decimal.Decimal(str(instrument['lotSizeFilter']['minOrderQty']))

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
        self.long_orders.clear()
        self.short_orders.clear()
        for i in range(self.num_orders):
            long_price = self.initial_price * (1 - (self.step_percentage / 100) * (i + 1))
            short_price = self.initial_price * (1 + (self.step_percentage / 100) * (i + 1))
            order_size = self.base_order_size * (self.martingale_factor ** i)

            adjusted_qty = round(order_size / self.step_size) * self.step_size
            adjusted_long_price = round(long_price / self.price_step) * self.price_step
            adjusted_short_price = round(short_price / self.price_step) * self.price_step

            self.long_orders.append(
                {'price': float(adjusted_long_price), 'qty': float(adjusted_qty), 'executed': False})
            self.short_orders.append(
                {'price': float(adjusted_short_price), 'qty': float(adjusted_qty), 'executed': False})

            logging.debug(
                f"Order {i + 1}: Long price = {adjusted_long_price}, Short price = {adjusted_short_price}, Qty = {adjusted_qty}")

    def place_long_orders(self):
        for order in self.long_orders:
            success = self.bybit.entry(price=order['price'],
                                       side='Buy',
                                       qty=order['qty'],
                                       order_type='Limit',
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
        total_usdt = decimal.Decimal("0.0")
        print(self.long_orders, 'pvepvepve')
        for order in self.long_orders:
            price = decimal.Decimal(str(order['price']))
            qty = decimal.Decimal(str(order['qty']))
            total_usdt += price * qty
        logging.info(f"Total USDT required for the full DCA grid: {total_usdt}")
        return float(total_usdt)

