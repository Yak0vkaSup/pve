# pve/app/vpl/tasks.py

from pve.app import celery, redis_client
import logging, json, pandas as pd
from pve.app.models.graph_model import Graph
from pve.app.vpl.nodes import process_graph
from pve.app.socketio_setup import socketio
from pve.app.utils.logger import SocketIOLogHandler
from pve.app.models.backtest_model import BacktestResult
from pve.app.models.analizer_model import AnalyzerResult
from pve.app.vpl.analyzer import BacktestAnalyzer

logger = logging.getLogger(__name__)

class RedisLogHandler(logging.Handler):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    def emit(self, record):
        log_entry = self.format(record)
        redis_client.publish(self.channel, log_entry)

class socket_logging:
    """Attach a SocketIOLogHandler to the ROOT logger for the duration."""
    def __init__(self, user_id):
        self.root = logging.getLogger()          # root logger
        self.handler = SocketIOLogHandler(user_id)

    def __enter__(self):
        self.root.setLevel(logging.INFO)         # ensure INFO+ passes
        self.root.addHandler(self.handler)

    def __exit__(self, exc_type, exc, tb):
        self.root.removeHandler(self.handler)

@celery.task(bind=True)
def process_graph_task(self, user_id, graph_name):
    # wrap the *entire* backtest in socket-logging
    with socket_logging(user_id):
        logger.info("Starting backtest for graph %s", graph_name)

        try:
            # Stage 1: Loading graph data (10%)
            socketio.emit('compilation_progress', {
                'status': 'progress',
                'progress': 10,
                'stage': 'Loading graph data...',
                'graph_name': graph_name
            }, to=str(user_id))

            graph_data = Graph.load(user_id, graph_name)
            if not graph_data:
                logger.error('Graph not found')
                socketio.emit('compilation_progress', {
                    'status': 'error',
                    'message': 'Graph not found',
                    'graph_name': graph_name
                }, to=str(user_id))
                return

            graph, start_date, end_date, symbol, timeframe = graph_data
            graph_json = json.dumps(graph) if isinstance(graph, dict) else graph

            # Stage 2: Preparing data (25%)
            socketio.emit('compilation_progress', {
                'status': 'progress',
                'progress': 25,
                'stage': f'Preparing data for {symbol} ({timeframe})...',
                'graph_name': graph_name
            }, to=str(user_id))

            # Stage 3: Processing graph (this is the main computation, 30-80%)
            socketio.emit('compilation_progress', {
                'status': 'progress',
                'progress': 30,
                'stage': 'Processing graph nodes...',
                'graph_name': graph_name
            }, to=str(user_id))

            # This will now fire INFO logs from process_graph, update_orders, nodes, etc.
            df, precision, min_move, orders, _ = process_graph(
                graph_json, start_date, end_date,
                symbol, timeframe,
                mode='backtest',
                api_key=None, api_secret=None,
                warmup_only=False,
                dataframe=None,
                state=None,
                incremental=False
            )

            # Stage 4: Processing results (85%)
            socketio.emit('compilation_progress', {
                'status': 'progress',
                'progress': 85,
                'stage': 'Processing results...',
                'graph_name': graph_name
            }, to=str(user_id))

            if df is not None:
                df['date'] = df['date'].astype('int64') // 10 ** 9
                columns_to_ignore = ['date', 'open', 'high', 'low', 'close', 'volume']
                ma_columns = [col for col in df.columns if col not in columns_to_ignore]
                df[ma_columns] = df[ma_columns].astype(object)
                df[ma_columns] = df[ma_columns].where(pd.notna(df[ma_columns]), None)
                data = df.to_dict('records')

                # Stage 5: Saving results (95%)
                socketio.emit('compilation_progress', {
                    'status': 'progress',
                    'progress': 95,
                    'stage': 'Saving results...',
                    'graph_name': graph_name
                }, to=str(user_id))

                socketio.emit('update_chart', {
                    'status': 'success',
                    'data': data,
                    'precision': precision,
                    'minMove': min_move,
                    'orders': orders
                }, to=str(user_id))

                BacktestResult.save(
                    user_id, graph_name, data, orders,
                    precision, min_move, symbol, timeframe,
                    start_date, end_date, graph_json
                )

                # Stage 6: Complete (100%)
                socketio.emit('compilation_progress', {
                    'status': 'completed',
                    'progress': 100,
                    'stage': 'Compilation completed successfully!',
                    'graph_name': graph_name
                }, to=str(user_id))

                logger.info("Backtest completed successfully for %s", graph_name)
            else:
                socketio.emit('compilation_progress', {
                    'status': 'error',
                    'message': 'No data generated from graph processing',
                    'graph_name': graph_name
                }, to=str(user_id))
                
        except Exception as e:
            # this logs full traceback, both to file and over SocketIO
            logger.exception("Error during backtest")
            socketio.emit('compilation_progress', {
                'status': 'error',
                'message': f'Compilation failed: {str(e)}',
                'graph_name': graph_name
            }, to=str(user_id))


@celery.task(bind=True)
def process_analyzer_task(self, user_id, backtest_id, initial_capital):
    logger = logging.getLogger('pve.app.analyzer')
    try:
        # Stage 1: Starting analysis (10%)
        socketio.emit('analyzer_progress', {
            'status': 'progress',
            'progress': 10,
            'stage': 'Loading backtest data...',
            'backtest_id': backtest_id
        }, to=str(user_id))

        # Load the saved backtest result using its unique ID.
        logger.info("Starting analysis")
        backtest_result = BacktestResult.load_by_id(backtest_id)
        if not backtest_result:
            logger.error("No backtest result found for backtest_id: %s", backtest_id)
            socketio.emit('analyzer_progress', {
                'status': 'error',
                'message': 'Backtest result not found',
                'backtest_id': backtest_id
            }, to=str(user_id))
            return

        # Stage 2: Processing data (30%)
        socketio.emit('analyzer_progress', {
            'status': 'progress',
            'progress': 30,
            'stage': 'Preparing analysis data...',
            'backtest_id': backtest_id
        }, to=str(user_id))

        data = backtest_result.get("backtest_data")
        df = pd.DataFrame(data)
        # if 'date' in df.columns:
        #     df['date'] = pd.to_datetime(df['date'], unit='s')

        symbol = backtest_result.get("symbol")
        orders = backtest_result.get("orders")
        graph_name = backtest_result.get("graph_name")
        precision = backtest_result.get("precision")
        min_move = backtest_result.get("min_move")

        # Stage 3: Calculating metrics (60%)
        socketio.emit('analyzer_progress', {
            'status': 'progress',
            'progress': 60,
            'stage': 'Calculating performance metrics...',
            'backtest_id': backtest_id
        }, to=str(user_id))

        analyzer = BacktestAnalyzer(df, orders, symbol, initial_capital, precision, min_move)
        analyzer.calculate_metrics()

        # Stage 4: Processing results (80%)
        socketio.emit('analyzer_progress', {
            'status': 'progress',
            'progress': 80,
            'stage': 'Processing trade details...',
            'backtest_id': backtest_id
        }, to=str(user_id))

        metrics = analyzer.get_metrics()
        equity_curve = analyzer.equity_curve  # Already a list of dictionaries
        trades_details = []

        for trade in analyzer.get_trades():
            # Calculate notional using entry_price and qty
            notional = float(trade.entry_price) * float(trade.qty)
            # Build the orders list including each order's details and notional.
            orders = []
            for order in trade.executed_orders:
                order_notional = float(order.price) * float(order.qty)
                order_dict = {
                    'time': str(order.time),
                    'price': float(order.price),
                    'qty': float(order.qty),
                    'side': order.side,
                    'fee': float(order.fee),
                    'notional': order_notional  # include order notional here
                }
                orders.append(order_dict)
            trade_dict = {
                'entry_time': str(trade.entry_time),
                'exit_time': str(trade.exit_time),
                'entry_price': float(trade.entry_price),
                'exit_price': float(trade.exit_price),
                'qty': float(trade.qty),
                'fees': float(trade.fees),
                'profit': float(trade.profit),
                'return_pct': float(trade.return_pct),
                'funding_cost': float(trade.funding_cost),
                'num_orders': len(trade.executed_orders),
                'notional': notional,  # include trade notional
                'orders': orders  # include orders details
            }
            trades_details.append(trade_dict)

        # Stage 5: Saving results (95%)
        socketio.emit('analyzer_progress', {
            'status': 'progress',
            'progress': 95,
            'stage': 'Saving analysis results...',
            'backtest_id': backtest_id
        }, to=str(user_id))

        # Save the analyzer results in SQL, linking them to the specific backtest record.
        analyzer_result_id = AnalyzerResult.save(
            user_id=user_id,
            graph_name=graph_name,
            symbol=symbol,
            metrics=metrics,
            equity_curve=equity_curve,
            trades_details=trades_details,
            backtest_id=backtest_id
        )
        BacktestResult.update_analyzer_result_id(backtest_id, analyzer_result_id)

        # Stage 6: Complete (100%)
        socketio.emit('analyzer_progress', {
            'status': 'completed',
            'progress': 100,
            'stage': 'Analysis completed successfully!',
            'backtest_id': backtest_id
        }, to=str(user_id))

        logger.info("Finished analysis")
    except Exception as e:
        logger.error("Error in process_analyzer_task: %s", str(e))
        socketio.emit('analyzer_progress', {
            'status': 'error',
            'message': f'Analysis failed: {str(e)}',
            'backtest_id': backtest_id
        }, to=str(user_id))

