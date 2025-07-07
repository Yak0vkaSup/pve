# app/vpl/nodes.py
import logging
import traceback
import pandas as pd
import json
import time
import threading
from flask import current_app
import asyncio
import telegram
import decimal
from pandas import Timestamp
from pybit.exceptions import FailedRequestError
from pybit.unified_trading import HTTP

from .utils import (
    fetch_data
)

default_category = 'linear'

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# Thread-local metaclass for per-bot isolation
# ----------------------------------------------------------------

class _NodeMeta(type):
    """A metaclass that keeps selected *class* attributes in thread-local
    storage so that multiple bots running in parallel threads don't overwrite
    each other's runtime state (orders, df, symbol, etc.).
    """

    _tls = threading.local()

    _thread_vars = {
        "orders":          lambda: [],
        "order_id_counter": lambda: 1,
        "df":              lambda: None,
        "symbol":          lambda: None,
        "instrument_specs": lambda: None,
        "mode":            lambda: "backtest",
        "api_key":         lambda: None,
        "api_secret":      lambda: None,
    }

    def _ensure(cls):
        """Initialise all thread-local variables if they are missing."""
        for name, factory in cls._thread_vars.items():
            if not hasattr(cls._tls, name):
                setattr(cls._tls, name, factory() if callable(factory) else factory)

    # ------------------------------------------------------------------
    # Provide transparent attribute access/assignment on the class itself
    # ------------------------------------------------------------------

    def __getattr__(cls, name):
        if name in cls._thread_vars:
            cls._ensure()
            return getattr(cls._tls, name)
        raise AttributeError(name)

    def __setattr__(cls, name, value):
        if name in cls._thread_vars:
            cls._ensure()
            setattr(cls._tls, name, value)
        else:
            super().__setattr__(name, value)

# ────────────────────────────────────────────────────────────────
# Core Node class (now uses the thread-local metaclass)          
# ----------------------------------------------------------------

class Node(metaclass=_NodeMeta):
    """Core VPL node. The runtime-specific attributes (orders, df, etc.) are
    now automatically isolated per thread so that each bot operates on its
    own independent state.
    """

    # ------------------------------------------------------------------

    def __init__(self, node_id, node_type, properties, inputs, outputs,
                 mode: str = 'backtest', api_key: str = None, api_secret: str = None):
        self.id = node_id
        self.type = node_type
        self.properties = properties
        self.inputs = inputs
        self.outputs = outputs
        self.input_values = {}
        self.output_values = {}
        self.input_connections = {}
        self.output_connections = {}
        self.bybit = None
        self.mode = mode if mode is not None else Node.mode
        if self.mode == 'live' and self.bybit is None:
            self.bybit = HTTP(
                api_key=api_key if api_key is not None else Node.api_key,
                api_secret=api_secret if api_secret is not None else Node.api_secret,
            )

    @classmethod
    def configure_runtime(cls, mode, api_key, api_secret):
        cls.mode = mode
        cls.api_key = api_key
        cls.api_secret = api_secret

    @classmethod
    def set_orders(cls, orders):
        cls.orders = orders

    @classmethod
    def get_orders(cls):
        return cls.orders

    @classmethod
    def set_df(cls, df):
        cls.df = df

    @classmethod
    def get_df(cls):
        return cls.df

    @classmethod
    def set_symbol(cls, symbol):
        cls.symbol = symbol

    @classmethod
    def get_symbol(cls):
        return cls.symbol


def retry(max_attempts=3, delays=None):
    if delays is None:
        delays = [1, 3, 6]
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except FailedRequestError as e:
                    # extract status code and any raw response the SDK gives us
                    code = getattr(e, 'status_code', '<unknown>')
                    resp  = getattr(e, 'response', None)
                    msg   = getattr(e, 'message', str(e))

                    # full context
                    logger.error(
                        f"{func.__name__} attempt #{attempt} → Fatal API error (no retry):\n"
                        f"  status_code: {code}\n"
                        f"  message:     {msg}\n"
                        f"  response:    {resp!r}\n"
                        f"  func args:   {args}\n"
                        f"  func kwargs: {kwargs}\n"
                        f"  full:        {str(e)}"
                        + traceback.format_exc()
                    )

                    # if client error, bubble up
                    if isinstance(code, int) and 400 <= code < 500:
                        raise
                    last_exc = e

                except Exception as e:
                    logger.warning(
                        f"{func.__name__} attempt #{attempt} failed with exception:\n"
                        f"{traceback.format_exc()}"
                    )
                    last_exc = e

                # back off
                if attempt < max_attempts:
                    time.sleep(delays[min(attempt-1, len(delays)-1)])

            logger.error(f"{func.__name__} failed after {max_attempts} attempts, last error:\n{traceback.format_exc()}")
            raise last_exc

        return wrapper
    return decorator

class GetOpenNode(Node):
    def execute(self, row):
        open_value = row.get('open', None)
        self.output_values['open'] = open_value

class GetCloseNode(Node):
    def execute(self, row):
        close_value = row.get('close', None)
        self.output_values['close'] = close_value

class GetHighNode(Node):
    def execute(self, row):
        high_value = row.get('high', None)
        self.output_values['high'] = high_value

class GetLowNode(Node):
    def execute(self, row):
        low_value = row.get('low', None)
        self.output_values['low'] = low_value

class GetVolumeNode(Node):
    def execute(self, row):
        volume_value = row.get('volume', None)
        self.output_values['volume'] = volume_value

class SetFloatNode(Node):
    def execute(self, row=None):
        float_value = self.properties.get('value', 1.0)
        self.output_values['Float'] = float_value

class SetIntegerNode(Node):
    def execute(self, row=None):
        integer_value = self.properties.get('value', 1)
        self.output_values['Integer'] = integer_value

class SetStringNode(Node):
    def execute(self, row=None):
        string_value = self.properties.get('value', '')
        self.output_values['String'] = string_value

class SetBoolNode(Node):
    def execute(self, row=None):
        bool_value = self.properties.get('value', False)
        self.output_values['Bool'] = bool_value

class IsNoneNode(Node):
    def execute(self, row=None):
        value = self.input_values.get(0)
        is_none = (value is None)
        self.output_values['None?'] = is_none
        #logger.info(f"IsNoneNode {self.id}: Value is None? {is_none}")
        return is_none

def adjust_quantity_value(requested_qty, min_qty, qty_step):
    requested_qty = decimal.Decimal(str(requested_qty))
    min_qty = decimal.Decimal(str(min_qty))
    qty_step = decimal.Decimal(str(qty_step))
    if requested_qty < min_qty:
        return min_qty
    steps = ((requested_qty - min_qty) / qty_step).to_integral_value(rounding=decimal.ROUND_FLOOR)
    adjusted = min_qty + steps * qty_step
    return adjusted.quantize(qty_step)

def adjust_price_value(requested_price, tick_size):
    requested_price = decimal.Decimal(str(requested_price))
    tick = decimal.Decimal(str(tick_size))
    adjusted = requested_price.quantize(tick, rounding=decimal.ROUND_HALF_EVEN)
    return adjusted

def adjust_order_parameters(requested_qty, requested_price, specs):
    adjusted_qty = adjust_quantity_value(requested_qty, specs["min_order_qty"], specs["qty_step"])
    adjusted_price = adjust_price_value(requested_price, specs["min_move"])
    
    # Use integers if qty_step is 1.0 or greater (indicates integer-only quantities)
    # For assets like BTC/ETH: qty_step = 0.001, 0.01 → use decimals
    # For assets like DOGE: qty_step = 1.0 → use integers  
    # For traditional instruments: qty_step = 1.0 or higher → use integers
    qty_step_decimal = specs["qty_step"]
    use_integer = (qty_step_decimal >= 1.0)
    
    return (
        int(adjusted_qty) if use_integer else float(adjusted_qty),
        float(adjusted_price)
    )

class CreateOrderNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs,
                 mode='backtest', api_key=None, api_secret=None):
        super().__init__(node_id, node_type, properties, inputs, outputs,
                         mode, api_key, api_secret)
        self.last_order = None

    @retry(max_attempts=3)
    def _api_place_order(self, **params):
        return self.bybit.place_order(**params)

    def execute(self, row=None):
        trigger = self.input_values.get(0)
        if trigger != 'GO':
            # propagate last ID even when no new order
            if self.last_order:
                self.output_values['ID'] = self.last_order['id']
            self.output_values['Exec'] = None
            return None

        direction = self.input_values.get(1)
        is_limit  = self.input_values.get(2)
        qty       = self.input_values.get(4)
        timestamp = row.get('date')
        if None in (direction, is_limit, qty):
            logger.error(f"CreateOrderNode {self.id}: Missing inputs")
            self.output_values['ID'] = None
            return None
        
        # ensure positive quantity
        if qty <= 0:
            qty = abs(qty)

        specs = Node.instrument_specs
        if specs is None:
            logger.error(f"CreateOrderNode {self.id}: No instrument specs for {Node.get_symbol()}, skipping live order")
            self.output_values['ID'] = None
            return None

        # adjust qty & price
        direction_text = "BUY" if direction else "SELL"
        if is_limit:
            price_in = self.input_values.get(3)
            adj_qty, adj_price = adjust_order_parameters(qty, price_in, specs)
            exec_time = None
        else:
            market_price = row.get('close')
            adj_qty, adj_price = adjust_order_parameters(qty, market_price, specs)
            exec_time = timestamp

        # create local order record
        ts = int(row.get('date').timestamp() * 1e3)  # e.g. 1682000000123
        seq = Node.order_id_counter  # small in‑memory counter
        link_id = f"local_{seq}_{ts}"  # local_1682000000123_0
        Node.order_id_counter = seq + 1

        order = {
            'id':         link_id,
            'remote_id':  None,
            'direction':  direction,
            'type':       'limit' if is_limit else 'market',
            'price':      adj_price,
            'quantity':   abs(adj_qty),
            'status':     'open',
            'time_created': timestamp,
            'time_executed': exec_time,
            'order_category' : 'normal'
        }

        Node.orders.append(order)
        self.last_order = order

        # send to Bybit if live
        if self.mode == 'live':
            params = {
                'category':   'linear',
                'symbol':     Node.get_symbol(),
                'side':       'Buy' if direction else 'Sell',
                'orderType':  'Limit' if is_limit else 'Market',
                'qty':        str(abs(adj_qty)),
                'orderLinkId': link_id,
            }
            if is_limit:
                params['price'] = str(adj_price)

            try:
                res = self._api_place_order(**params)
                logger.debug(f"[Bybit Response] {res!r}")
            except FailedRequestError as e:
                # already logged; mark order as error
                order['status'] = 'error'
                self.output_values['ID'] = None
                self.output_values['Exec'] = None
                return None

            # inspect Bybit response
            if res.get('retCode') == 0:
                oid = res['result']['orderId']
                order['remote_id']   = oid
                order['time_executed'] = exec_time
                order['status']      = 'open'
                logger.info(f"[LIVE ORDER CREATED] Node {self.id}: {direction_text} {order['type']} order - "
                           f"Symbol: {Node.get_symbol()}, Qty: {abs(adj_qty)}, Price: {adj_price}, "
                           f"Remote ID: {oid}, Local ID: {link_id}")
            else:
                order['status'] = 'error'
                msg = res.get('retMsg', '<no message>')
                logger.error(f"[LIVE ORDER FAILED] Node {self.id}: Place failed, retCode={res.get('retCode')} msg={msg}")

        # Log the order creation regardless of mode
        if self.mode == 'backtest':
            logger.info(f"[BACKTEST ORDER CREATED] Node {self.id}: {direction_text} {order['type']} order - "
                       f"Symbol: {Node.get_symbol()}, Qty: {abs(adj_qty)}, Price: {adj_price}, "
                       f"Local ID: {link_id}")


        if self.mode == 'live' and order.get('remote_id') is not None:
            self.output_values['ID'] = order['remote_id']
            self.output_values['Exec'] = 'GO'
        else:
            self.output_values['ID'] = order['id']
            self.output_values['Exec'] = 'GO'
        return order['id']

class CreateConditionalOrderNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs,
                 mode='backtest', api_key=None, api_secret=None):
        super().__init__(node_id, node_type, properties, inputs, outputs,
                         mode, api_key, api_secret)
        self.last_order = None

    @retry(max_attempts=3)
    def _api_place_conditional(self, **params):
        return self.bybit.place_order(**params)

    def execute(self, row=None):
        trigger = self.input_values.get(0)
        if trigger != 'GO':
            if self.last_order:
                self.output_values['ID'] = self.last_order['id']
            self.output_values['Exec'] = None
            return None

        direction     = self.input_values.get(1)
        trigger_price = self.input_values.get(2)
        qty           = self.input_values.get(3)
        timestamp     = row.get('date')
        if None in (direction, trigger_price, qty):
            logger.error(f"CreateConditionalOrderNode {self.id}: Missing inputs")
            self.output_values['ID'] = None
            return None
        
        # ensure positive quantity
        if qty <= 0:
            qty = abs(qty)

        specs = Node.instrument_specs
        if specs is None:
            logger.error(f"CreateConditionalOrderNode {self.id}: No instrument specs for {Node.get_symbol()}, skipping live order")
            self.output_values['ID'] = None
            return None

        # adjust qty & trigger price
        direction_text = "BUY" if direction else "SELL"
        adj_qty, adj_price = adjust_order_parameters(qty, trigger_price, specs)

        # create local order record with a single link_id
        ts = int(row.get('date').timestamp() * 1e3)  # e.g. 1682000000123
        seq = Node.order_id_counter  # small in‑memory counter
        link_id = f"local_{seq}_{ts}"  # local_1682000000123_0
        Node.order_id_counter = seq + 1

        order = {
            'id':           link_id,
            'remote_id':    None,
            'direction':    direction,
            'type':         'market',
            'price':        adj_price,
            'trigger_price': adj_price,
            'quantity':     abs(adj_qty),
            'status':       'open',
            'time_created': timestamp,
            'time_executed': None,
            'order_category': 'conditional',
        }

        Node.orders.append(order)
        self.last_order = order

        # send to Bybit if live
        if self.mode == 'live':
            params = {
                'category':         current_app.config.get('BYBIT_CATEGORY', default_category),
                'symbol':           Node.get_symbol(),
                'side':             'Buy' if direction else 'Sell',
                'orderType':        'Market',           # market conditional
                'qty':              str(abs(adj_qty)),
                'triggerPrice':     str(adj_price),
                'triggerDirection': 1 if direction else 2,
                'orderLinkId':      link_id,
            }

            try:
                res = self._api_place_conditional(**params)
            except FailedRequestError as e:
                order['status'] = 'error'
                logger.error(f"CreateConditionalOrderNode {self.id}: API error: {e}")
                self.output_values['ID'] = None
                self.output_values['Exec'] = None
                return None

            if res.get('retCode') == 0:
                oid = res['result']['orderId']
                order['remote_id'] = oid
                logger.info(f"[LIVE CONDITIONAL ORDER CREATED] Node {self.id}: {direction_text} conditional order - "
                           f"Symbol: {Node.get_symbol()}, Qty: {abs(adj_qty)}, Trigger Price: {adj_price}, "
                           f"Remote ID: {oid}, Local ID: {link_id}")
            else:
                order['status'] = 'error'
                msg = res.get('retMsg', '<no message>')
                logger.error(f"[LIVE CONDITIONAL ORDER FAILED] Node {self.id}: Failed retCode={res.get('retCode')} msg={msg}")

        # Log the order creation regardless of mode

        if self.mode == 'backtest':
            logger.info(f"[BACKTEST CONDITIONAL ORDER CREATED] Node {self.id}: {direction_text} conditional order - "
                       f"Symbol: {Node.get_symbol()}, Qty: {abs(adj_qty)}, Trigger Price: {adj_price}, "
                       f"Local ID: {link_id}")


        # outputs back to graph
        if self.mode == 'live' and order.get('remote_id') is not None:
            self.output_values['ID'] = order['remote_id']
            self.output_values['Exec'] = 'GO'
        else:
            self.output_values['ID'] = order['id']
            self.output_values['Exec'] = 'GO'
        return order['id']

class CancelOrderNode(Node):
    @retry(max_attempts=3)
    def _api_cancel_order(self, **params):
        return self.bybit.cancel_order(**params)

    def execute(self, row=None):
        trigger = self.input_values.get(0)
        local_id = self.input_values.get(1)
        if trigger != 'GO' or local_id is None or trigger is None:
            self.output_values['Exec'] = None
            return None
        order = next((o for o in Node.orders if o['id'] == local_id), None)
        if not order:
            self.output_values['Exec'] = None
            return None
        if self.mode == 'live':
            params = {
                'category': current_app.config.get('BYBIT_CATEGORY', default_category),
                'symbol': Node.get_symbol(),
                'orderLinkId': order['id'],
            }
            res = self._api_cancel_order(**params)
            if res.get('retCode') == 0:
                order['status'] = 'cancelled'
                order['time_executed'] = row.get('date')
                direction_text = "BUY" if order.get('direction') else "SELL"
                logger.info(f"[LIVE ORDER CANCELLED] Node {self.id}: {direction_text} order cancelled - "
                           f"Symbol: {Node.get_symbol()}, Local ID: {order['id']}, "
                           f"Remote ID: {order.get('remote_id', 'N/A')}")
            else:
                order['status'] = 'error'
                msg = res.get('retMsg', '<no message>')
                logger.error(f"[LIVE ORDER CANCEL FAILED] Node {self.id}: Cancel failed, "
                            f"retCode={res.get('retCode')} msg={msg}")
        else:
            order['status'] = 'cancelled'
            order['time_executed'] = row.get('date')
            direction_text = "BUY" if order.get('direction') else "SELL"
            logger.info(f"[BACKTEST ORDER CANCELLED] Node {self.id}: {direction_text} order cancelled - "
                       f"Symbol: {Node.get_symbol()}, Local ID: {order['id']}")
        self.output_values['Exec'] = 'GO'
        return True

class CancelAllOrderNode(Node):

    @retry(max_attempts=3)
    def _api_cancel_all(self, **params):
        """
        Wrap Bybit's cancel_all_orders in our retry decorator.
        This will retry on transient errors, but will raise immediately on 4xx.
        """
        return self.bybit.cancel_all_orders(**params)

    def execute(self, row=None):
        trigger = self.input_values.get(0)
        if trigger != 'GO':
            self.output_values['Exec'] = None
            return None

        # collect only the local orders we think are still open
        open_orders = [o for o in Node.orders if o['status'] == 'open']

        if self.mode == 'live' and open_orders:
            try:
                # attempt remote cancel via our retry‑wrapped method
                self._api_cancel_all(
                    category=current_app.config.get('BYBIT_CATEGORY', default_category),
                    symbol=Node.get_symbol()
                )
                logger.info(f"CancelAllOrderNode {self.id}: remote cancel_all_orders succeeded")
            except FailedRequestError as e:
                # if no remote orders (or other fatal 4xx), just log and proceed
                logger.warning(
                    f"CancelAllOrderNode {self.id}: remote cancel_all_orders failed after retries: {e}"
                )

        elif not open_orders:
            # nothing to cancel anywhere
            logger.info(f"CancelAllOrderNode {self.id}: no open orders to cancel, skipping.")

        # always mark our local opens as cancelled
        for o in open_orders:
            o['status'] = 'cancelled'
            o['time_executed'] = row.get('date')

        self.output_values['Exec'] = 'GO'
        return True

class ModifyOrderNode(Node):
    @retry(max_attempts=3)
    def _api_amend_order(self, **params):
        return self.bybit.amend_order(**params)

    def execute(self, row=None):
        trigger   = self.input_values.get(0)
        local_id  = self.input_values.get(1)
        new_price = self.input_values.get(2)
        new_qty   = self.input_values.get(3)

        if trigger != 'GO' or local_id is None:
            self.output_values['Exec'] = None
            return None

        order = next((o for o in Node.orders
                      if o['id'] == local_id and o['status'] == 'open'), None)
        if not order:
            self.output_values['Exec'] = None
            return None

        # ── keep originals for comparison ───────────────────────────
        old_price = order['price']
        old_qty   = order['quantity']

        adj_price = float(new_price) if new_price is not None else old_price
        adj_qty   = float(new_qty)  if new_qty   is not None else old_qty

        price_changed = adj_price != old_price
        qty_changed   = adj_qty   != old_qty

        # nothing really changes → pretend it succeeded
        if not price_changed and not qty_changed:
            logger.info(f"[ORDER MODIFY SKIPPED] Node {self.id}: No changes needed for order {local_id}")
            self.output_values.update({'ID': local_id, 'Exec': 'GO'})
            return local_id

        # live amend – send *only* the changed fields
        if self.mode == 'live':
            params = {
                'category': default_category,
                'symbol':   Node.get_symbol(),
                'orderLinkId': local_id,
            }
            if price_changed:
                params['price'] = str(adj_price)
            if qty_changed:
                params['qty'] = str(abs(adj_qty))

            try:
                res = self._api_amend_order(**params)
            except FailedRequestError as e:
                logger.error(f"ModifyOrderNode {self.id}: amend_order error {e}")
                order['status'] = 'error'
                self.output_values['Exec'] = None
                return None

            if res.get('retCode') != 0:
                order['status'] = 'error'
                msg = res.get('retMsg', '<no message>')
                logger.error(f"[LIVE ORDER MODIFY FAILED] Node {self.id}: Modify failed for order {local_id}, "
                            f"retCode={res.get('retCode')} msg={msg}")
                self.output_values['Exec'] = None
                return None
            else:
                logger.info(f"[LIVE ORDER MODIFIED] Node {self.id}: Order {local_id} modified - "
                           f"Symbol: {Node.get_symbol()}, "
                           f"Price: {old_price} → {adj_price if price_changed else 'unchanged'}, "
                           f"Qty: {old_qty} → {abs(adj_qty) if qty_changed else 'unchanged'}")

        # update local order *after* successful API call or in backtest
        order.setdefault('modifications', []).append({
            'time_modified': row.get('date'),
            'previous_price': old_price,
            'previous_quantity': old_qty
        })
        order['price']    = adj_price
        order['quantity'] = abs(adj_qty)
        '''
        if self.mode == 'backtest':
            logger.info(f"[BACKTEST ORDER MODIFIED] Node {self.id}: Order {local_id} modified - "
                       f"Symbol: {Node.get_symbol()}, "
                       f"Price: {old_price} → {adj_price if price_changed else 'unchanged'}, "
                       f"Qty: {old_qty} → {abs(adj_qty) if qty_changed else 'unchanged'}")
        '''
        self.output_values.update({'ID': local_id, 'Exec': 'GO'})
        return local_id



class GetLastOrderNode(Node):
    @retry(max_attempts=3)
    def _api_get_open(self, **params):
        return self.bybit.get_open_orders(**params)
    def execute(self, row=None):
        if not Node.orders:
            self.output_values.update({'ID': None, 'Long/Short': None, 'Normal/Conditional': None, 'Cancelled': None})
            return None
        last = Node.orders[-1]
        if self.mode == 'live':
            res = self._api_get_open(
                category=current_app.config.get('BYBIT_CATEGORY', default_category),
                symbol=Node.get_symbol(),
                orderLinkId=last['id'],
                limit=1
            )
            result = res.get('result', {})
            orders_list = result.get('list') or []
            if not orders_list:
                return None
            entry = orders_list[0]
            status = entry.get('orderStatus')
            if status == 'Cancelled':
                last['status'] = 'cancelled'
        self.output_values['ID'] = last['id']
        self.output_values['Long/Short'] = last.get('direction')
        self.output_values['Normal/Conditional'] = (last.get('type') == 'limit')
        is_cancelled = (last.get('status') == 'cancelled')
        self.output_values['Cancelled'] = is_cancelled
        
        # Log last order information
        direction_text = "BUY" if last.get('direction') else "SELL"
        order_type = last.get('type', 'unknown')
        status = last.get('status', 'unknown')
        logger.info(f"[LAST ORDER] Node {self.id}: {direction_text} {order_type} order {last['id']} - "
                   f"Symbol: {Node.get_symbol()}, Status: {status}, "
                   f"Price: {last.get('price')}, Qty: {last.get('quantity')}, "
                   f"Cancelled: {is_cancelled}")
        
        return last

class GetOrderNode(Node):
    @retry(max_attempts=3)
    def _api_get_orders(self, **params):
        return self.bybit.get_open_orders(**params)

    def execute(self, row=None):
        order_id = self.input_values.get(0)
        if order_id is None:
            return None
        if self.mode == 'live':
            res = self._api_get_orders(
                category=current_app.config.get('BYBIT_CATEGORY', default_category),
                symbol=Node.get_symbol(),
                orderLinkId=order_id,
                openOnly=0,
                limit=1
            )
            result = res.get('result', {})
            orders_list = result.get('list') or []
            if not orders_list:
                return None
            entry = orders_list[0]

            for order in Node.orders:
                if order['id'] == order_id:
                    self.output_values['ID'] = entry.get('orderLinkId')
                    self.output_values['Price'] = float(entry.get('price', 0))
                    self.output_values['Quantity'] = float(entry.get('qty', 0))
                    created_ms = int(entry.get('createdTime', 0))
                    diff = row.get('date').timestamp()*1000 - created_ms
                    current_time = row.get('date')
                    self.output_values['Created'] = diff/60000
                    is_executed = (entry.get('orderStatus') == 'Filled' and order.get('time_executed') == current_time)
                    is_open = (entry.get('orderStatus') in ('New', 'PartiallyFilled'))
                    self.output_values['Executed?'] = is_executed
                    self.output_values['Open?'] = is_open
                    
                    # Log order status information
                    direction_text = "BUY" if order.get('direction') else "SELL"
                    status = entry.get('orderStatus')
                    # logger.info(f"[LIVE ORDER STATUS] Node {self.id}: {direction_text} order {order_id} - "
                    #            f"Symbol: {Node.get_symbol()}, Status: {status}, "
                    #            f"Price: {float(entry.get('price', 0))}, Qty: {float(entry.get('qty', 0))}, "
                    #            f"Created: {diff/60000:.1f} min ago, "
                    #            f"Executed: {is_executed}, Open: {is_open}")
                    
                    return entry

        for order in Node.orders:
            current_time = row.get('date')
            created = order.get('time_created')
            if order['id'] == order_id:
                diff = current_time - Timestamp(created)
                minutes_diff = diff.total_seconds() / 60
                is_executed = (order.get('status') == 'executed' and order.get('time_executed') == current_time)
                is_open = (order['status'] == 'open')
                
                self.output_values['ID'] = order['id']
                self.output_values['Price'] = order['price']
                self.output_values['Quantity'] = order['quantity']
                self.output_values['Created'] = minutes_diff
                self.output_values['Executed?'] = is_executed
                self.output_values['Open?'] = is_open
                
                # Log order status information
                direction_text = "BUY" if order.get('direction') else "SELL"
                status = order.get('status')
                '''
                logger.info(f"[BACKTEST ORDER STATUS] Node {self.id}: {direction_text} order {order_id} - "
                           f"Symbol: {Node.get_symbol()}, Status: {status}, "
                           f"Price: {order['price']}, Qty: {order['quantity']}, "
                           f"Created: {minutes_diff:.1f} min ago, "
                           f"Executed: {is_executed}, Open: {is_open}")
                '''
                return order

class MANode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.prices = []
        self.window = None
        self.ma_series = []
        # State variables for different MA types
        self.ma_states = {}

    def execute(self, row=None):
        from .utils import (
            ma_sma, ma_ema, ma_dema, ma_tema, ma_wma, ma_hma, ma_rma, 
            ma_linreg, ma_trima, ma_kama, ma_alma, ma_fwma, ma_pwma, 
            ma_sinwma, ma_swma, ma_zlma, ma_ssf, ma_ssf3, ma_t3, 
            ma_vidya, ma_mcgd, ma_smma, ma_jma, ma_hwma
        )
        
        price = self.input_values.get(0)
        if self.window is None:
            self.window = self.input_values.get(1)
        if price is None or self.window is None:
            self.output_values['Float'] = None
            self.ma_series.append(None)
            return None

        self.prices.append(price)
        ma_type = self.properties.get('ma_type', 'ema')
        
        # Calculate the moving average based on type
        ma_value = None
        
        if ma_type == 'sma':
            ma_value = ma_sma(self.prices, self.window)
            
        elif ma_type == 'ema':
            prev_ema = self.ma_states.get('prev_ema')
            ma_value = ma_ema(price, self.window, prev_ema)
            self.ma_states['prev_ema'] = ma_value
            
        elif ma_type == 'dema':
            ema1_state = self.ma_states.get('ema1_state')
            ema2_state = self.ma_states.get('ema2_state')
            ma_value, ema1_state, ema2_state = ma_dema(self.prices, self.window, ema1_state, ema2_state)
            self.ma_states['ema1_state'] = ema1_state
            self.ma_states['ema2_state'] = ema2_state
            
        elif ma_type == 'tema':
            ema1_state = self.ma_states.get('ema1_state')
            ema2_state = self.ma_states.get('ema2_state')
            ema3_state = self.ma_states.get('ema3_state')
            ma_value, ema1_state, ema2_state, ema3_state = ma_tema(self.prices, self.window, ema1_state, ema2_state, ema3_state)
            self.ma_states['ema1_state'] = ema1_state
            self.ma_states['ema2_state'] = ema2_state
            self.ma_states['ema3_state'] = ema3_state
            
        elif ma_type == 'wma':
            ma_value = ma_wma(self.prices, self.window)
            
        elif ma_type == 'hma':
            hma_values = self.ma_states.get('hma_values')
            ma_value, hma_values = ma_hma(self.prices, self.window, hma_values)
            self.ma_states['hma_values'] = hma_values
            
        elif ma_type == 'rma':
            prev_rma = self.ma_states.get('prev_rma')
            ma_value = ma_rma(price, self.window, prev_rma)
            self.ma_states['prev_rma'] = ma_value
            
        elif ma_type == 'linreg':
            ma_value = ma_linreg(self.prices, self.window)
            
        elif ma_type == 'trima':
            trima_sma1 = self.ma_states.get('trima_sma1')
            ma_value, trima_sma1 = ma_trima(self.prices, self.window, trima_sma1)
            self.ma_states['trima_sma1'] = trima_sma1
            
        elif ma_type == 'kama':
            prev_kama = self.ma_states.get('prev_kama')
            ma_value = ma_kama(self.prices, self.window, prev_kama)
            self.ma_states['prev_kama'] = ma_value
            
        elif ma_type == 'alma':
            ma_value = ma_alma(self.prices, self.window)
            
        elif ma_type == 'fwma':
            ma_value = ma_fwma(self.prices, self.window)
            
        elif ma_type == 'pwma':
            ma_value = ma_pwma(self.prices, self.window)
            
        elif ma_type == 'sinwma':
            ma_value = ma_sinwma(self.prices, self.window)
            
        elif ma_type == 'swma':
            ma_value = ma_swma(self.prices, self.window)
            
        elif ma_type == 'zlma':
            zlma_ema = self.ma_states.get('zlma_ema')
            ma_value, zlma_ema = ma_zlma(self.prices, self.window, zlma_ema)
            self.ma_states['zlma_ema'] = zlma_ema
            
        elif ma_type == 'ssf':
            ssf_prev = self.ma_states.get('ssf_prev')
            ma_value, ssf_prev = ma_ssf(self.prices, self.window, ssf_prev)
            self.ma_states['ssf_prev'] = ssf_prev
            
        elif ma_type == 'ssf3':
            ssf3_prev = self.ma_states.get('ssf3_prev')
            ma_value, ssf3_prev = ma_ssf3(self.prices, self.window, ssf3_prev)
            self.ma_states['ssf3_prev'] = ssf3_prev
            
        elif ma_type == 't3':
            t3_states = self.ma_states.get('t3_states')
            ma_value, t3_states = ma_t3(price, self.window, t3_states)
            self.ma_states['t3_states'] = t3_states
            
        elif ma_type == 'vidya':
            prev_vidya = self.ma_states.get('prev_vidya')
            ma_value = ma_vidya(self.prices, self.window, prev_vidya)
            self.ma_states['prev_vidya'] = ma_value
            
        elif ma_type == 'mcgd':
            prev_mcgd = self.ma_states.get('prev_mcgd')
            ma_value = ma_mcgd(price, self.window, prev_mcgd)
            self.ma_states['prev_mcgd'] = ma_value
            
        elif ma_type == 'smma':
            prev_smma = self.ma_states.get('prev_smma')
            is_first = self.ma_states.get('smma_first', True)
            ma_value = ma_smma(price, self.window, prev_smma, is_first)
            self.ma_states['prev_smma'] = ma_value
            self.ma_states['smma_first'] = False
            
        elif ma_type == 'jma':
            jma_state = self.ma_states.get('jma_state')
            ma_value, jma_state = ma_jma(price, self.window, jma_state)
            self.ma_states['jma_state'] = jma_state
            
        elif ma_type == 'hwma':
            hwma_state = self.ma_states.get('hwma_state')
            ma_value, hwma_state = ma_hwma(price, hwma_state)
            self.ma_states['hwma_state'] = hwma_state
            
        else:
            # Default to SMA for unknown types
            ma_value = ma_sma(self.prices, self.window)
            
        self.output_values['Float'] = ma_value
        self.ma_series.append(ma_value)
        return ma_value

class RSINode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.prices = []
        self.window = None
        self.rsi_state = None

    def execute(self, row=None):
        from .utils import rsi_calculate
        
        price = self.input_values.get(0)
        if self.window is None:
            self.window = self.input_values.get(1)
        if price is None or self.window is None:
            self.output_values['Float'] = None
            return None

        self.prices.append(price)
        
        # Calculate RSI
        rsi_value, self.rsi_state = rsi_calculate(self.prices, self.window, self.rsi_state)
        
        self.output_values['Float'] = rsi_value
        return rsi_value

class SuperTrendNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.highs = []
        self.lows = []
        self.closes = []
        self.window = None
        self.supertrend_state = None

    def execute(self, row=None):
        from .utils import supertrend_calculate
        
        high = self.input_values.get(0)
        low = self.input_values.get(1)
        close = self.input_values.get(2)
        if self.window is None:
            self.window = self.input_values.get(3)
        
        if None in (high, low, close, self.window):
            self.output_values['Float'] = None
            return None

        # Get multiplier from properties (set by widget)
        multiplier = self.properties.get('multiplier', 3.0)

        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        
        # Calculate SuperTrend
        supertrend_value, self.supertrend_state = supertrend_calculate(
            self.highs, self.lows, self.closes, self.window, multiplier, self.supertrend_state
        )
        
        self.output_values['Float'] = supertrend_value
        return supertrend_value

class CrossOverNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.last_a = None
        self.last_b = None

    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"CrossOverNode {self.id}: One or both input values are None.")
            self.output_values['Condition'] = None
            self.last_a = a
            self.last_b = b
            return None

        if self.last_a is not None and self.last_b is not None:
            condition = (self.last_a < self.last_b) and (a > b)
        else:
            condition = False

        self.output_values['Condition'] = condition
        #logger.info(f"CrossOverNode {self.id}: Computed condition = {condition} (last_a={self.last_a}, last_b={self.last_b}, a={a}, b={b}).")

        self.last_a = a
        self.last_b = b
        return condition

class CrossUnderNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.last_a = None
        self.last_b = None

    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"CrossUnderNode {self.id}: One or both input values are None.")
            self.output_values['Condition'] = None
            self.last_a = a
            self.last_b = b
            return None

        if self.last_a is not None and self.last_b is not None:
            condition = (self.last_a > self.last_b) and (a < b)
        else:
            condition = False

        self.output_values['Condition'] = condition
        #logger.info(f"CrossUnderNode {self.id}: Computed condition = {condition} (last_a={self.last_a}, last_b={self.last_b}, a={a}, b={b}).")

        self.last_a = a
        self.last_b = b
        return condition

class GreaterNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"GreaterNode {self.id}: One or both input values are None.")
            self.output_values['Bool'] = None
            return None
        try:
            condition = a > b
            self.output_values['Bool'] = condition
            #logger.info(f"GreaterNode {self.id}: Computed condition {a} > {b} = {condition}.")
            return condition
        except Exception as e:
            logger.error(f"GreaterNode {self.id}: Error computing condition: {e}")
            self.output_values['Bool'] = None
            return None

class LessNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"LessNode {self.id}: One or both input values are None.")
            self.output_values['Bool'] = None
            return None
        try:
            condition = a < b
            self.output_values['Bool'] = condition
            #logger.info(f"LessNode {self.id}: Computed condition {a} < {b} = {condition}.")
            return condition
        except Exception as e:
            logger.error(f"LessNode {self.id}: Error computing condition: {e}")
            self.output_values['Bool'] = None
            return None

class EqualNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            logger.error(f"EqualNode {self.id}: One or both input values are None.")
            self.output_values['Bool'] = None
            return None
        try:
            condition = a == b
            self.output_values['Bool'] = condition
            #logger.info(f"EqualNode {self.id}: Computed condition {a} == {b} = {condition}.")
            return condition
        except Exception as e:
            logger.error(f"EqualNode {self.id}: Error computing condition: {e}")
            self.output_values['Bool'] = None
            return None

class AndNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"AndNode {self.id}: One or both input conditions are None.")
            self.output_values['Bool'] = None
            return None
        result = a and b
        self.output_values['Bool'] = result
        #logger.info(f"AndNode {self.id}: Computed {a} AND {b} = {result}.")
        return result

class OrNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"OrNode {self.id}: One or both input conditions are None.")
            self.output_values['Bool'] = None
            return None
        result = a or b
        self.output_values['Bool'] = result
        #logger.info(f"OrNode {self.id}: Computed {a} OR {b} = {result}.")
        return result

class NotNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        if a is None:
            #logger.error(f"NotNode {self.id}: Input condition is None.")
            self.output_values['Bool'] = None
            return None
        result = not a
        self.output_values['Bool'] = result
        #logger.info(f"NotNode {self.id}: Computed NOT {a} = {result}.")
        return result

class IfNode(Node):
    def execute(self, row=None):
        cond = self.input_values.get(0)
        if cond is None:
            #logger.error(f"IfNode {self.id}: Input condition is None.")
            self.output_values['True'] = None
            self.output_values['False'] = None
            return None
        if cond:
            self.output_values['True'] = "GO"
            self.output_values['False'] = None
            #logger.info(f"IfNode {self.id}: Condition evaluated True.")
        else:
            self.output_values['True'] = None
            self.output_values['False'] = "GO"
            #logger.info(f"IfNode {self.id}: Condition evaluated False.")
        return cond

class MultiplyFloatNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            #logger.error(f"MultiplyFloatNode {self.id}: One or both input values are None.")
            self.output_values['Float'] = None
            return None
        try:
            result = a * b
            self.output_values['Float'] = result
            #logger.info(f"MultiplyFloatNode {self.id}: {a} * {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"MultiplyFloatNode {self.id}: Error computing multiplication: {e}")
            self.output_values['Float'] = None
            return None

class DivideFloatNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            logger.error(f"DivideFloatNode {self.id}: One or both input values are None.")
            self.output_values['Float'] = None
            return None
        if b == 0:
            logger.error(f"DivideFloatNode {self.id}: Division by zero.")
            self.output_values['Float'] = None
            return None
        try:
            result = a / b
            self.output_values['Float'] = result
            #logger.info(f"DivideFloatNode {self.id}: {a} / {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"DivideFloatNode {self.id}: Error computing division: {e}")
            self.output_values['Float'] = None
            return None

class AddFloatNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            logger.error(f"AddFloatNode {self.id}: One or both input values are None.")
            self.output_values['Float'] = None
            return None
        try:
            result = a + b
            self.output_values['Float'] = result
            #logger.info(f"AddFloatNode {self.id}: {a} + {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"AddFloatNode {self.id}: Error computing addition: {e}")
            self.output_values['Float'] = None
            return None

class SubtractFloatNode(Node):
    def execute(self, row=None):
        a = self.input_values.get(0)
        b = self.input_values.get(1)
        if a is None or b is None:
            logger.error(f"SubtractFloatNode {self.id}: One or both input values are None.")
            self.output_values['Float'] = None
            return None
        try:
            result = a - b
            self.output_values['Float'] = result
            #logger.info(f"SubtractFloatNode {self.id}: {a} - {b} = {result}")
            return result
        except Exception as e:
            logger.error(f"SubtractFloatNode {self.id}: Error computing subtraction: {e}")
            self.output_values['Float'] = None
            return None

class ClipFloatNode(Node):
    def execute(self, row=None):
        min_val = self.input_values.get(0)
        max_val = self.input_values.get(1)
        value = self.input_values.get(2)
        
        if min_val is None or max_val is None or value is None:
            logger.error(f"ClipFloatNode {self.id}: One or more input values are None.")
            self.output_values['Float'] = None
            return None
        
        try:
            # Ensure min_val <= max_val
            if min_val > max_val:
                logger.warning(f"ClipFloatNode {self.id}: Min value ({min_val}) is greater than max value ({max_val}). Swapping values.")
                min_val, max_val = max_val, min_val
            
            # Clip the value
            clipped_value = max(min_val, min(max_val, value))
            self.output_values['Float'] = clipped_value
            #logger.info(f"ClipFloatNode {self.id}: Clipped {value} to range [{min_val}, {max_val}] = {clipped_value}")
            return clipped_value
        except Exception as e:
            logger.error(f"ClipFloatNode {self.id}: Error computing clip: {e}")
            self.output_values['Float'] = None
            return None

class LowestNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.values = []
        self.window = None

    def execute(self, row=None):
        value = self.input_values.get(0)
        if self.window is None:
            self.window = self.input_values.get(1)
        if value is None or self.window is None:
            self.output_values['Float'] = None
            return None

        self.values.append(value)
        
        # Keep only the last 'window' values for efficiency
        if len(self.values) > self.window:
            self.values.pop(0)
        
        # Calculate the minimum value in the current window
        if len(self.values) >= self.window:
            min_value = min(self.values)
        else:
            # Not enough values yet, return the minimum of what we have
            min_value = min(self.values) if self.values else None
        
        self.output_values['Float'] = min_value
        return min_value

class HighestNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.values = []
        self.window = None

    def execute(self, row=None):
        value = self.input_values.get(0)
        if self.window is None:
            self.window = self.input_values.get(1)
        if value is None or self.window is None:
            self.output_values['Float'] = None
            return None

        self.values.append(value)
        
        # Keep only the last 'window' values for efficiency
        if len(self.values) > self.window:
            self.values.pop(0)
        
        # Calculate the maximum value in the current window
        if len(self.values) >= self.window:
            max_value = max(self.values)
        else:
            # Not enough values yet, return the maximum of what we have
            max_value = max(self.values) if self.values else None
        
        self.output_values['Float'] = max_value
        return max_value

class SendMessageNode(Node):
    def execute(self):
        exec = self.input_values.get(0)
        message = self.input_values.get(1)  # Input message
        user_id = self.input_values.get(2)  # Input user ID

        if exec is None:
            logger.info(f"SendMessageNode {self.id}: Condition not met, stop of execution.")
            return

        if message is None or user_id is None:
            logger.error(f"SendMessageNode {self.id}: Message or UserID is None.")
            return

        try:
            # Retrieve the bot token from the app configuration
            bot_token = current_app.config['TELEGRAM_BOT_TOKEN']
            bot = telegram.Bot(bot_token)

            # Send the message to the user
            asyncio.run(bot.send_message(chat_id=user_id, text=message))
            logger.info(f"SendMessageNode {self.id}: Message successfully sent to user {user_id}.")
            self.output_values['Exec'] = True
        except Exception as e:
            logger.error(f"SendMessageNode {self.id}: Error sending message: {e}")
            self.output_values['Exec'] = None


class GetPositionNode(Node):
    @retry(max_attempts=3)
    def _api_get_positions(self, **params):
        """
        Wrapper for Bybit get_positions with retry logic.
        """
        return self.bybit.get_positions(**params)

    def execute(self, row=None):
        """
        Compute unified (net) position from executed orders.
        A BUY order adds a positive quantity and a SELL order subtracts quantity.
        Offsetting is done in FIFO order regardless of the order sequence.

        Output:
            - 'Price': weighted average price of the open position (None if flat)
            - 'Quantity': net quantity (positive for long, negative for short)
            - 'Created': timestamp of the earliest order contributing to the open position
        """
        # Live mode: retrieve real-time position from Bybit
        if self.mode == 'live':
            try:
                res = self._api_get_positions(
                    category=current_app.config.get('BYBIT_CATEGORY', default_category),
                    symbol=Node.get_symbol(),
                )
            except FailedRequestError as e:
                logger.error(f"GetPositionNode: API error when fetching positions: {e}")
                return None
            if res.get('retCode') != 0:
                logger.error(f"GetPositionNode: API error retCode={res.get('retCode')} msg={res.get('retMsg')}")
                return None
            positions = res.get('result', {}).get('list', [])
            if not positions:
                self.output_values['Price'] = None
                self.output_values['Quantity'] = 0
                self.output_values['Created'] = None
                return self.output_values
            # Assume one position per symbol in one-way mode
            p = positions[0]
            size = float(p.get('size', 0))
            side = p.get('side', '').lower()  # 'Buy' or 'Sell'
            net_qty = size if side == 'buy' else -size
            avg_price = float(p.get('avgPrice')) if size != 0 else None
            created = pd.to_datetime(int(p.get('createdTime', 0)), unit='ms') if p.get('createdTime') else None

            self.output_values['Price'] = avg_price
            self.output_values['Quantity'] = net_qty
            self.output_values['Created'] = created
            
            # Log position information in live mode
            if net_qty != 0:
                position_type = "LONG" if net_qty > 0 else "SHORT"
                # logger.info(f"[LIVE POSITION] Node {self.id}: {position_type} position - "
                #            f"Symbol: {Node.get_symbol()}, Qty: {abs(net_qty)}, "
                #            f"Avg Price: {avg_price}, Created: {created}")
            #else:
            #    logger.info(f"[LIVE POSITION] Node {self.id}: FLAT position - Symbol: {Node.get_symbol()}")
            
            return self.output_values

        # Filter executed orders and sort by execution time (or creation time fallback)
        executed_orders = [o for o in Node.orders if o.get('status') == 'executed']
        sorted_orders = sorted(
            executed_orders,
            key=lambda o: pd.to_datetime(o.get('time_executed') or o.get('time_created'))
        )

        unmatched_entries = []

        # Process each order in time order and perform offsetting:
        for order in sorted_orders:
            qty = order.get('quantity')
            price = order.get('price')
            order_time = order.get('time_created')
            direction = order.get('direction')  # True = BUY, False = SELL
            remaining_qty = qty

            if direction is True:  # BUY order: try to offset an existing SELL entry (short position)
                while remaining_qty > 0 and unmatched_entries and unmatched_entries[0]['direction'] is False:
                    # Offset with the earliest unmatched SELL order
                    entry = unmatched_entries[0]
                    if entry['quantity'] > remaining_qty:
                        entry['quantity'] -= remaining_qty
                        remaining_qty = 0
                    else:
                        remaining_qty -= entry['quantity']
                        unmatched_entries.pop(0)
                # Any residual BUY quantity is added as a new unmatched BUY entry.
                if remaining_qty > 0:
                    unmatched_entries.append({
                        'quantity': remaining_qty,
                        'price': price,
                        'direction': True,
                        'time_created': order_time
                    })
            else:  # SELL order: try to offset an existing BUY entry (long position)
                while remaining_qty > 0 and unmatched_entries and unmatched_entries[0]['direction'] is True:
                    entry = unmatched_entries[0]
                    if entry['quantity'] > remaining_qty:
                        entry['quantity'] -= remaining_qty
                        remaining_qty = 0
                    else:
                        remaining_qty -= entry['quantity']
                        unmatched_entries.pop(0)
                # If there is residual SELL quantity, it becomes a new unmatched SELL entry.
                if remaining_qty > 0:
                    unmatched_entries.append({
                        'quantity': remaining_qty,
                        'price': price,
                        'direction': False,
                        'time_created': order_time
                    })

        # Calculate the net position.
        # BUY entries add, SELL entries subtract (we treat SELL as negative).
        net_quantity = sum(e['quantity'] if e['direction'] else -e['quantity']
                           for e in unmatched_entries)

        # Compute the weighted average price.
        if net_quantity != 0:
            weighted_price_sum = sum(e['quantity'] * e['price'] for e in unmatched_entries)
            avg_price = weighted_price_sum / abs(net_quantity)
        else:
            avg_price = None

        # Use the earliest creation time among unmatched entries as the "Created" time.
        created_time = min((e['time_created'] for e in unmatched_entries), default=None)

        # Set output values.
        self.output_values['Price'] = avg_price
        self.output_values['Quantity'] = net_quantity
        self.output_values['Created'] = created_time
        
        # Log position information
        '''
        if self.mode == 'backtest':
            if net_quantity != 0:
                position_type = "LONG" if net_quantity > 0 else "SHORT"
                logger.info(f"[BACKTEST POSITION] Node {self.id}: {position_type} position - "
                           f"Symbol: {Node.get_symbol()}, Qty: {abs(net_quantity)}, "
                           f"Avg Price: {avg_price}, Created: {created_time}")
            else:
                logger.info(f"[BACKTEST POSITION] Node {self.id}: FLAT position - Symbol: {Node.get_symbol()}")
        '''
        return self.output_values

class AddSignalNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.markers = []
        self.signal_name = properties.get("name", f"Signal_{node_id}")

    def execute(self, row=None):
        signal_value = self.input_values.get(0)
        name = self.input_values.get(1) or self.signal_name

        if row is None:
            return None

        try:
            marker_date = pd.to_datetime(row.get('date'))
        except Exception as e:
            logger.error(f"AddSignalNode {self.id}: Ошибка преобразования времени: {e}")
            return None

        if signal_value:
            marker = {
                "date": marker_date,  # сохраняем напрямую Timestamp
                "text": name,
                "position": "belowBar",  # например, под свечой
                "shape": "circle",
                "lineWidth": 2
            }
            self.markers.append(marker)
        self.output_values["Markers"] = self.markers
        return self.markers

class AddIndicatorNode(Node):
    def __init__(self, node_id, node_type, properties, inputs, outputs):
        super().__init__(node_id, node_type, properties, inputs, outputs)
        self.indicator_series = []
        self.indicator_name = properties.get("name", f"Indicator_{node_id}")

    def execute(self, row=None):
        """
        На каждом шаге узел получает входное числовое значение (float) и собирает серию.
        """
        value = self.input_values.get(0)
        name_input = self.input_values.get(1)
        if name_input:
            self.indicator_name = name_input

        if value is None:
            self.indicator_series.append(None)
        else:
            try:
                self.indicator_series.append(float(value))
            except Exception as e:
                logger.error(f"AddIndicatorNode {self.id}: Ошибка преобразования значения: {e}")
                self.indicator_series.append(None)

        self.output_values["Series"] = self.indicator_series
        return self.indicator_series

def update_orders(current_price, current_low_price, current_high_price, current_time):
    for order in Node.orders:
        if order.get('status') != 'open':
            continue
        order_category = order.get('order_category')
        order_type = order.get('type')
        direction = order.get('direction')
        if order_category == 'conditional':
            trigger_price = order.get('trigger_price')
            if trigger_price is None:
                order['status'] = 'executed'
                order['time_executed'] = current_time
                logger.info(f"[CONDITIONAL ORDER EXECUTED] {order.get('id')} immediately (no trigger_price).")
            else:
                if direction and current_high_price >= trigger_price:
                    order['status'] = 'executed'
                    order['time_executed'] = current_time
                    direction_text = "BUY" if direction else "SELL"
                    logger.info(f"[CONDITIONAL ORDER EXECUTED] {direction_text} conditional order {order.get('id')} executed: "
                               f"Symbol: {Node.get_symbol()}, current high {current_high_price} >= trigger {trigger_price}, "
                               f"Qty: {order.get('quantity')}")
                elif (not direction) and current_low_price <= trigger_price:
                    order['status'] = 'executed'
                    order['time_executed'] = current_time
                    direction_text = "BUY" if direction else "SELL"
                    logger.info(f"[CONDITIONAL ORDER EXECUTED] {direction_text} conditional order {order.get('id')} executed: "
                               f"Symbol: {Node.get_symbol()}, current low {current_low_price} <= trigger {trigger_price}, "
                               f"Qty: {order.get('quantity')}")

        else:  # normal orders
            direction_text = "BUY" if direction else "SELL"
            if order_type == 'market':
                order['status'] = 'executed'
                order['time_executed'] = current_time
                logger.info(f"[MARKET ORDER EXECUTED] {direction_text} market order {order.get('id')} executed immediately: "
                           f"Symbol: {Node.get_symbol()}, Price: {current_price}, Qty: {order.get('quantity')}")
            elif order_type == 'limit':
                order_price = order.get('price')
                if order_price is not None:
                    if direction and current_low_price <= order_price:
                        order['status'] = 'executed'
                        order['time_executed'] = current_time
                        logger.info(f"[LIMIT ORDER EXECUTED] {direction_text} limit order {order.get('id')} executed: "
                                   f"Symbol: {Node.get_symbol()}, current low {current_low_price} <= order price {order_price}, "
                                   f"Qty: {order.get('quantity')}")
                    elif (not direction) and current_high_price >= order_price:
                        order['status'] = 'executed'
                        order['time_executed'] = current_time
                        logger.info(f"[BACKTEST LIMIT ORDER EXECUTED] {direction_text} limit order {order.get('id')} executed: "
                                   f"Symbol: {Node.get_symbol()}, current high {current_high_price} >= order price {order_price}, "
                                   f"Qty: {order.get('quantity')}")

def build_connections(links_data, nodes):
    for link in links_data:
        link_id, origin_id, origin_slot, target_id, target_slot, link_type = link
        origin_node = nodes[origin_id]
        target_node = nodes[target_id]

        # Map the connection
        target_node.input_connections[target_slot] = (origin_node, origin_slot)

        # Log the connection
        logger.debug(
            f"Connecting Node {origin_id} Output Slot {origin_slot} ('{origin_node.outputs[origin_slot]['name']}') "
            f"to Node {target_id} Input Slot {target_slot}")

        # Map the output links as well
        if origin_slot not in origin_node.output_connections:
            origin_node.output_connections[origin_slot] = []
        origin_node.output_connections[origin_slot].append((target_node, target_slot))

def build_graph(nodes):
    graph = {}
    in_degree = {}
    for node_id in nodes:
        graph[node_id] = []
        in_degree[node_id] = 0

    for node in nodes.values():
        for targets in node.output_connections.values():
            for target_node, _ in targets:
                graph[node.id].append(target_node.id)
                in_degree[target_node.id] += 1
    return graph, in_degree

def topological_sort(nodes, graph, in_degree):
    sorted_nodes = []
    queue = [node_id for node_id in nodes if in_degree[node_id] == 0]

    while queue:
        node_id = queue.pop(0)
        sorted_nodes.append(node_id)

        for neighbor in graph[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_nodes) != len(nodes):
        raise Exception("Graph has a cycle!")
    return sorted_nodes


def execute_stateful(sorted_ids, nodes):
    outputs = []
    df = Node.get_df()
    # Convert DataFrame to a list of dictionaries to avoid the slow iterrows
    rows = df.to_dict(orient='records')
    for row in rows:
        current_price = row.get('close')
        current_low_price = row.get('low')
        current_high_price = row.get('high')
        current_time = row.get('date')

        # Update orders only once per row
        update_orders(current_price, current_low_price, current_high_price, current_time)

        # For each node, update input values from connected outputs
        for nid in sorted_ids:
            node = nodes[nid]
            #logger.debug(f"▶ Node {nid} ({node.type}) inputs: {node.input_values}")
            for slot, origin, out_name in node.input_conn_list:
                node.input_values[slot] = origin.output_values.get(out_name)
            node.execute(row)
            #logger.debug(f"  ↳ Node {nid} outputs: {node.output_values!r}")

        # Cache output_values per node for this row
        out_row = {nid: nodes[nid].output_values.copy() for nid in sorted_ids}
        outputs.append(out_row)
    return outputs


def get_precision_and_min_move_local(symbol, json_filepath="bybit_instruments_info.json"):
    """
    Reads the local JSON file (downloaded from Bybit) and extracts the
    precision and minimum move for the given symbol using the same algorithm.
    """
    try:
        with open(json_filepath, "r") as f:
            data = json.load(f)
        if data.get("retCode") == 0 and data.get("result", {}).get("list"):
            instrument_list = data["result"]["list"]
            # Look for the instrument info matching the symbol (case-insensitive)
            instrument_info = next(
                (inst for inst in instrument_list if inst.get("symbol", "").upper() == symbol.upper()), None
            )
            if instrument_info:
                tick_size = decimal.Decimal(str(instrument_info['priceFilter']['tickSize']))
                price_scale = int(instrument_info.get('priceScale', 2))
                if tick_size:
                    precision = abs(tick_size.as_tuple().exponent)
                    min_move = float(tick_size)
                else:
                    precision = price_scale
                    min_move = 1 / (10 ** price_scale)
                return int(precision), min_move
            else:
                logger.error(f"Symbol '{symbol}' not found in local JSON data.")

                return None, None
        else:
            logger.error("Invalid JSON data structure or error code in JSON file.")
            return None, None
    except Exception as e:
        logger.error(f"Error reading local JSON file: {e}")
        return None, None

def fetch_and_save_bybit_instruments_info(json_filepath="bybit_instruments_info.json"):
    """
    Calls Bybit's API to get the instruments info and saves the JSON
    response to a local file.
    """
    session = HTTP(testnet=False)
    try:
        # You can remove the symbol parameter here if you wish to get info for all symbols.
        response = session.get_instruments_info(category="linear")
        with open(json_filepath, "w") as f:
            json.dump(response, f, indent=4)
        logger.info(f"Successfully fetched and saved instruments info to '{json_filepath}'.")
    except Exception as e:
        logger.error(f"Error fetching instruments info from Bybit: {e}")


def resample_df(df, timeframe):
    timeframe_map = {
        "1min": "1T",
        "3min": "3T",
        "5min": "5T",
        "15min": "15T",
        "30min": "30T",
        "1h": "1H",
    }
    if timeframe not in timeframe_map:
        raise ValueError(f"Invalid timeframe: {timeframe}")
    if timeframe != "1min":
        df = df.resample(timeframe_map[timeframe], label='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        }).dropna()
    return df

def build_nodes(nodes_data):
    nodes = {}
    for node_data in nodes_data:
        node_id = node_data['id']
        node_type = node_data['type']
        properties = node_data.get('properties', {})
        inputs = node_data.get('inputs', [])
        outputs = node_data.get('outputs', [])

        if node_type == 'get/open':
            node = GetOpenNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/close':
            node = GetCloseNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/high':
            node = GetHighNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/low':
            node = GetLowNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'get/volume':
            node = GetVolumeNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'math/multiply_float':
            node = MultiplyFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/add_float':
            node = AddFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/subtract_float':
            node = SubtractFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/divide_float':
            node = DivideFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/clip_float':
            node = ClipFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/lowest':
            node = LowestNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'math/highest':
            node = HighestNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'set/float':
            node = SetFloatNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/string':
            node = SetStringNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/integer':
            node = SetIntegerNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'set/bool':
            node = SetBoolNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'indicators/ma':
            node = MANode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'indicators/rsi':
            node = RSINode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'indicators/super_trend':
            node = SuperTrendNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'tools/add_indicator':
            node = AddIndicatorNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'tools/add_signal':
            node = AddSignalNode(node_id, node_type, properties, inputs, outputs)


        elif node_type == 'compare/cross_over':
            node = CrossOverNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'compare/cross_under':
            node = CrossUnderNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'compare/equal':
            node = EqualNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'compare/smaller':
            node = LessNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'compare/greater':
            node = GreaterNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'logic/and':
            node = AndNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'logic/or':
            node = OrNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'logic/not':
            node = NotNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'logic/if':
            node = IfNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'trade/cancel_all_order':
            node = CancelAllOrderNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/cancel_order':
            node = CancelOrderNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/create_conditional_order':
            node = CreateConditionalOrderNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/create_order':
            node = CreateOrderNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/get_position':
            node = GetPositionNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/get_order':
            node = GetOrderNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/get_last_order':
            node = GetLastOrderNode(node_id, node_type, properties, inputs, outputs)

        elif node_type == 'telegram/send_message':
            node = SendMessageNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/is_none':
            node = IsNoneNode(node_id, node_type, properties, inputs, outputs)
        elif node_type == 'trade/modify_order':
            node = ModifyOrderNode(node_id, node_type, properties, inputs, outputs)

        else:
            logger.error(f"Unknown node type: {node_type}")
            node = Node(node_id, node_type, properties, inputs, outputs)

        nodes[node_id] = node
    return nodes

def get_instrument_specs(symbol, json_filepath="bybit_instruments_info.json"):
    try:
        with open(json_filepath, "r") as f:
            data = json.load(f)
        if data.get("retCode") == 0 and data.get("result", {}).get("list"):
            instrument_list = data["result"]["list"]
            instrument_info = next(
                (inst for inst in instrument_list if inst.get("symbol", "").upper() == symbol.upper()),
                None
            )
            if instrument_info:
                # Price specifications
                tick_size = decimal.Decimal(str(instrument_info['priceFilter']['tickSize']))
                price_scale = int(instrument_info.get('priceScale', 2))
                if tick_size:
                    precision = abs(tick_size.as_tuple().exponent)
                    min_move = float(tick_size)
                else:
                    precision = price_scale
                    min_move = 1 / (10 ** price_scale)
                # Quantity specifications from lotSizeFilter:
                lot_size_filter = instrument_info.get("lotSizeFilter", {})
                # Set a safe default if missing or zero:
                min_order_qty = decimal.Decimal(lot_size_filter.get("minOrderQty", "1"))
                qty_step = decimal.Decimal(lot_size_filter.get("qtyStep", "1"))
                # Prevent zero min_order_qty:
                if min_order_qty == 0:
                    min_order_qty = decimal.Decimal("1")
                return {
                    "precision": precision,
                    "min_move": min_move,
                    "min_order_qty": min_order_qty,
                    "qty_step": qty_step
                }
            else:
                logger.error(f"Symbol '{symbol}' not found in local JSON data.")
                return None
        else:
            logger.error("Invalid JSON data structure or error code in JSON file.")
            return None
    except Exception as e:
        logger.error(f"Error reading local JSON file: {e}")
        return None

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _max_lookback(nodes_json: list) -> int:
    """Return the largest rolling-window size used by any indicator node.

    Besides checking common property names (length / period / window), we also
    look at the second input slot (index 1) which, in LiteGraph-generated JSON,
    often stores the default window length (e.g. {"inputs":[{"name":"float"},
    {"name":"window","value":100}]}). This allows a correct lookback even when
    the parameter is supplied via the UI rather than the *properties* dict.
    """
    w_max = 1

    for n in nodes_json:
        node_type = n.get("type", "")
        if not (node_type.startswith("indicators/") or node_type in ("math/lowest", "math/highest")):
            continue

        window_val = None
        props = n.get("properties", {})
        # check common property keys first
        for key in ("length", "period", "window"):
            if key in props and props[key] is not None:
                window_val = props[key]
                break

        # fallback – inspect the 2nd input slot's default value (LiteGraph)
        if window_val is None:
            inputs = n.get("inputs", [])
            if len(inputs) > 1:
                slot1 = inputs[1]
                window_val = slot1.get("value")  # may be None if linked

        # guard – convert to int safely, defaulting to 1
        try:
            w = int(window_val) if window_val is not None else 1
        except (ValueError, TypeError):
            w = 1

        # if still 1, attempt to scan *any* numeric property values as fallback
        if w == 1 and props:
            for v in props.values():
                try:
                    iv = int(v)
                    if iv > 1:
                        w = max(w, iv)
                except (ValueError, TypeError):
                    continue

        # final fallback: scan all input slot default values
        if w == 1 and inputs:
            for inp in inputs:
                if isinstance(inp, dict):
                    val = inp.get("value")
                else:
                    # litegraph sometimes stores as [name, type, {obj}]; value may be 3rd element
                    val = inp[2].get("value") if len(inp) > 2 and isinstance(inp[2], dict) else None
                try:
                    iv = int(val)
                    if iv > 1:
                        w = max(w, iv)
                except (ValueError, TypeError):
                    continue

        w_max = max(w_max, w)
    
    # ── 2) gather constants declared by set/integer nodes ─────────────
    for n in nodes_json:
        if n.get("type") == "set/integer":
            try:
                v = int(n.get("properties", {}).get("value"))
                w_max = max(w_max, v)
            except (ValueError, TypeError):
                continue

    logger.debug("[_max_lookback] computed lookback=%s", w_max)
    return w_max


def _parse_graph_json(graph_json: str) -> dict:
    """Unwrap the optional 'graph' envelope and return the raw graph dict."""
    data = json.loads(graph_json)
    if 'graph' in data:
        data = data['graph']
    return data


def _prepare_dataframe(symbol: str, start_date, end_date, timeframe: str):
    """Fetch candles, resample and return a clean dataframe."""
    df = fetch_data(symbol, start_date, end_date)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df = resample_df(df, timeframe)
    df.reset_index(inplace=True)
    return df


def _initialise_node_runtime(df, symbol, *, reset_state: bool = True):
    """Bind dataframe + symbol to Node runtime.
       When reset_state=False – keep orders / counters between calls."""
    Node.set_df(df)
    Node.set_symbol(symbol)

    if reset_state:
        Node.orders = []
        Node.order_id_counter = 0

    if Node.instrument_specs is None:
        Node.instrument_specs = get_instrument_specs(symbol)


def _build_dag(graph_dict):
    """Return {id:Node}, execution order list."""
    nodes = build_nodes(graph_dict['nodes'])
    build_connections(graph_dict['links'], nodes)

    for node in nodes.values():           # cache static mapping once
        node.input_conn_list = [
            (slot, origin, origin.outputs[origin_slot]['name'])
            for slot, (origin, origin_slot) in node.input_connections.items()
        ]

    g, indeg = build_graph(nodes)
    order = topological_sort(nodes, g, indeg)
    logger.info("Execution order: %s", order)
    return nodes, order


def _postprocess_orders(final_df):
    """Convert timestamp columns to isoformat and log all orders."""
    orders = Node.orders

    for o in orders:
        '''
        logger.info("dir:%s qty:%s price:%s type:%s status:%s",
                    o['direction'], o['quantity'], o['price'],
                    o['type'], o['status'])
        '''
        for key in ('time_created', 'time_executed', 'time_cancelled'):
            if key in o and isinstance(o[key], pd.Timestamp):
                o[key] = o[key].isoformat()

        for m in o.get('modifications', []):
            if 'time_modified' in m and isinstance(m['time_modified'],
                                                   pd.Timestamp):
                m['time_modified'] = m['time_modified'].isoformat()
    return orders


def _add_indicator_and_signal_cols(nodes, final_df):
    """
    Attach extra columns produced by
      • tools/add_indicator   (numeric series)
      • tools/add_signal      (string markers)
    so that their length always matches `final_df`, even when we are
    running incrementally and only the last bars are passed in.
    """
    for node in nodes.values():

        # ───────────────────── indicators ───────────────────────────
        if node.type == 'tools/add_indicator':
            col = node.properties.get("name", f"Indicator_{node.id}")
            if node.input_values.get(1) is not None:           # runtime rename
                col = node.input_values[1]

            series_full = getattr(node, "indicator_series", [])
            if not series_full:
                continue                                        # nothing yet

            # tail-slice so the length exactly equals the dataframe length
            series = series_full[-len(final_df):]
            if len(series) < len(final_df):                     # pad left
                series = [None] * (len(final_df) - len(series)) + series

            final_df[col] = series
            #logger.info("Added indicator column '%s' (node %s)", col, node.id)

        # ───────────────────── signals / markers ────────────────────
        elif node.type == 'tools/add_signal':
            col = node.properties.get("name", f"Signal_{node.id}")
            if node.input_values.get(1) is not None:
                col = "$" + node.input_values[1]
            if not col.startswith("$"):
                col = "$" + col

            markers = getattr(node, "markers", [])
            series = [None] * len(final_df)

            # only inspect the most recent `len(final_df)` markers
            date_col = final_df['date']
            for m in markers[-len(final_df):]:
                dt = m.get('date')
                if dt is None:
                    continue
                idx = date_col[date_col == dt].index
                for i in idx:
                    series[i] = col

            final_df[col] = series
            logger.info("Added signal column '%s' (node %s)", col, node.id)

def _apply_runtime(nodes):
    for n in nodes.values():
        if n.mode != Node.mode: 
            n.mode = Node.mode
        if n.mode == 'live' and n.bybit is None:
            n.bybit = HTTP(api_key=Node.api_key,
                           api_secret=Node.api_secret)

# ---------------------------------------------------------------------------
# main entry – same signature / same behaviour
# ---------------------------------------------------------------------------

def process_graph(graph_json,
                  start_date, end_date,
                  symbol, timeframe,
                  mode='backtest',
                  api_key=None, api_secret=None,
                  warmup_only=True,
                  dataframe=None,
                  state=None,
                  incremental=False):
    logger.info("Starting graph processing")
    t0 = time.time()

    # 1) configure runtime
    Node.configure_runtime(mode, api_key, api_secret)
    graph_dict = _parse_graph_json(graph_json)

    # 2) warm‑up only: return lookback
    if warmup_only:
        lookback = _max_lookback(graph_dict['nodes'])
        logger.info("Max lookback (%d candles)", lookback)
        return None, None, None, lookback

    # 3) prepare your full history DataFrame
    df = dataframe if dataframe is not None else _prepare_dataframe(symbol, start_date, end_date, timeframe)

    # 4) initialise Node state (but don't wipe it out on incremental)
    _initialise_node_runtime(df, symbol, reset_state=not incremental)

    # 5) build or restore the DAG structure
    if incremental and state and 'nodes' in state:
        nodes, exec_order = state['nodes'], state['exec_order']
    else:
        nodes, exec_order = _build_dag(graph_dict)
        state = {'nodes': nodes, 'exec_order': exec_order}
    _apply_runtime(nodes)

    # 6) dispatch candles through the nodes
    if incremental:
        last = df.to_dict(orient='records')[-1]
        update_orders(last['close'], last['low'], last['high'], last['date'])
        for nid in exec_order:
            node = nodes[nid]
            for slot, origin, name in node.input_conn_list:
                node.input_values[slot] = origin.output_values.get(name)
            node.execute(last)
    else:
        execute_stateful(exec_order, nodes)

    # 7) collect outputs
    final_df = Node.get_df()
    orders   = _postprocess_orders(final_df)
    _add_indicator_and_signal_cols(nodes, final_df)

    # 8) housekeeping & return
    #final_df.to_csv('test_out3.csv', index=False)
    precision, min_move = get_precision_and_min_move_local(symbol)

    # Fail fast if instrument specifications are missing
    if precision is None or min_move is None:
        raise ValueError(f"Instrument specs not found for symbol '{symbol}'. Aborting graph processing.")

    #logger.debug("Fetched precision:%s min_move:%s", precision, min_move)
    #malogger.info("Orders: %s", orders)
    logger.info("Processing finished (%d ms)", int((time.time()-t0)*1000))

    if incremental:
        return final_df, precision, min_move, orders, state
    else:
        return final_df, precision, min_move, orders, state