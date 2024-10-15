import re
# This code is meant for Blaze Markets, so all the symbols correspond to Blaze Markets symbols
# If you have a different broker, adjust the symbols_mapping an on line 28 to change it

def parse_complex_string(input_string):
    # Define regex patterns
    price_pattern = r'(\d+\.?\d*)'
    symbol_pattern = (r'\b(audusd|eurusd|gbpusd|usdcad|usdchf|usdjpy|audcad|audchf|audjpy|audnzd|cadchf|cadjpy|chfjpy|euraud|eurcad|eurchf|eurgbp|eurjpy|eurnzd|gbpaud|gbpcad|gbpchf|gbpjpy|gbpnzd|nzdcad|nzdchf|nzdjpy|nzdusd|gu|gold|oil|silver|nas|nasdaq|dxy|spx|dax|dow|bitcoin|btc)\b')
    price_exempt_symbols = ['XAUUSD', 'WTI', 'XAGUSG', 'US100', 'USDIDX', 'US500', 'GER30', 'US30', 'BTCUSD']
    position_pattern = r'\b(short|long)\b'

    # Extract components
    all_numbers = re.findall(price_pattern, input_string)
    symbol_match = re.search(symbol_pattern, input_string.lower())
    position_match = re.search(position_pattern, input_string.lower())

    # Error handling
    if len(all_numbers) < 2:
        print(all_numbers)
        raise ValueError("Not enough numbers found in the input string.")
    if not symbol_match:
        raise ValueError("No valid symbol found in the input string.")
    if not position_match:
        raise ValueError("No position (short/long) found in the input string.")

    # Process symbol
    symbol = symbol_match.group(1).upper()
    symbol_mapping = {
        "GOLD": "XAUUSD", "OIL": "WTI", "SILVER": "XAGUSD",
        "NAS": "US100", "NASDAQ": "US100", "DXY": "USDIDX",
        "SPX": "US500", "DAX": "GER30", "DOW": "US30",
        "BITCOIN": "BTCUSD", "BTC": "BTCUSD", "GU": "GBPUSD"
    }
    if symbol in symbol_mapping:
        symbol = symbol_mapping.get(symbol, symbol)

    # Process prices
    prices = all_numbers[:-1]
    processed_prices = []
    for price in prices:
        price_float = float(price)
        if price_float > 10000 and symbol not in price_exempt_symbols:
            price_float /= 100000
            processed_prices.append(f"{price_float:.5f}")
        else:
            processed_prices.append(f"{price_float}")

    # Process position and stop loss
    position = position_match.group(1).upper()
    sl = all_numbers[-1]
    sl_float = float(sl)
    if sl_float > 10000 and symbol not in price_exempt_symbols:
        sl_float /= 100000
    sl = sl_float


    # Generate output
    output = []
    for price in processed_prices:
        output.append(f"{price} {symbol} {position} {sl}")

    return "\n".join(output)

def replace_file_content(file_path, input_string):
    try:
        # Open the file in write mode
        with open(file_path, 'w') as file:
            # Write the input string to the file
            file.write(input_string)
        print(f'Successfully replaced content in {file_path}')
    except Exception as e:
        print(f'Error: {e}')
