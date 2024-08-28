from binance.um_futures import UMFutures
from binance.error import ClientError
import math
import time

# API credentials
api_key = 'EgeOoN241f4KMNgFQ6NjgfJWrwMQLf2YzQAdKyqc5HfTjJF63exDKf6t1m5dwjSy'
api_secret = 'KZnGfELRNQM5T9NHfcs1qK311hbVSdagotNtsFxZ3f7zCsC8aWUYpPi3trorEpuH'

# Initialize the UMFutures client
client = UMFutures(key=api_key, secret=api_secret)

# Trading parameters
symbol = 'XRPUSDT'
usdt_amount = 2.5
leverage = 20
take_profit_percent = 0.4
stop_loss_percent = 0.4

def get_symbol_info(symbol):
    exchange_info = client.exchange_info()
    for s in exchange_info['symbols']:
        if s['symbol'] == symbol:
            return s
    raise ValueError(f"Symbol {symbol} not found")

def round_step_size(quantity, step_size):
    precision = int(round(-math.log(step_size, 10), 0))
    return round(quantity, precision)

def get_open_orders(symbol):
    return client.get_orders(symbol=symbol)

def cancel_order(symbol, order_id):
    try:
        client.cancel_order(symbol=symbol, orderId=order_id)
    except ClientError as error:
        print(f"Error cancelling order: {error}")

def monitor_orders(symbol, tp_order_id, sl_order_id):
    while True:
        open_orders = get_open_orders(symbol)

        tp_order_open = any(order['orderId'] == tp_order_id for order in open_orders)
        sl_order_open = any(order['orderId'] == sl_order_id for order in open_orders)

        if not tp_order_open and sl_order_open:
            cancel_order(symbol, sl_order_id)
            print("Take profit triggered. Position closed.")
            break
        elif not sl_order_open and tp_order_open:
            cancel_order(symbol, tp_order_id)
            print("Stop loss triggered. Position closed.")
            break
        elif not tp_order_open and not sl_order_open:
            print("Both orders closed. Position may have been manually closed.")
            break

        time.sleep(3)  # Wait for 3 seconds before checking again

def place_short_trade():
    try:
        symbol_info = get_symbol_info(symbol)
        quantity_precision = next(filter(lambda f: f['filterType'] == 'LOT_SIZE', symbol_info['filters']))['stepSize']
        price_precision = next(filter(lambda f: f['filterType'] == 'PRICE_FILTER', symbol_info['filters']))['tickSize']

        client.change_leverage(symbol=symbol, leverage=leverage)

        ticker = client.ticker_price(symbol)
        entry_price = float(ticker['price'])

        quantity = (usdt_amount * leverage) / entry_price
        rounded_quantity = round_step_size(quantity, float(quantity_precision))

        take_profit_price = round_step_size(entry_price * (1 - take_profit_percent / 100), float(price_precision))
        stop_loss_price = round_step_size(entry_price * (1 + stop_loss_percent / 100), float(price_precision))

        order = client.new_order(
            symbol=symbol,
            side="SELL",
            type="MARKET",
            quantity=rounded_quantity
        )
        print(f"Market order placed: {order}")

        tp_order = client.new_order(
            symbol=symbol,
            side="BUY",
            type="TAKE_PROFIT_MARKET",
            timeInForce="GTC",
            quantity=rounded_quantity,
            stopPrice=take_profit_price,
            workingType="MARK_PRICE"
        )
        print(f"Take profit order placed: {tp_order}")

        sl_order = client.new_order(
            symbol=symbol,
            side="BUY",
            type="STOP_MARKET",
            timeInForce="GTC",
            quantity=rounded_quantity,
            stopPrice=stop_loss_price,
            workingType="MARK_PRICE"
        )
        print(f"Stop loss order placed: {sl_order}")

        monitor_orders(symbol, tp_order['orderId'], sl_order['orderId'])

    except ClientError as error:
        print(f"An error occurred: {error}")

if __name__ == "__main__":
    place_short_trade()
