import requests

from .utils import format_number_exact, parse_num_us, escape_commodity

QUERY_URL = "https://www.alphavantage.co/query"

def fetch(api_key, load, format_args):
	output = ""
	for value in load:
		type = value['type']

		if type == 'EQUITY':
			key = value['key']
			symbol = value['symbol']
			currency = value['currency']
			result = requests.get(QUERY_URL, params={
				"function": 'TIME_SERIES_DAILY',
				"symbol": symbol,
				"outputsize": "full",
				"apikey": api_key
			})
			result = result.json()
			for date, values in result["Time Series (Daily)"].items():
				price = parse_num_us(values['4. close'])
				output += f"P {date} {escape_commodity(key)} {format_number_exact(price, format_args, min_decimal=4)} {escape_commodity(currency)}\n"
		elif type == 'FX':
			from_symbol = value['from_symbol']
			to_symbol = value['to_symbol']
			result = requests.get(QUERY_URL, params={
				"function": 'FX_DAILY',
				"from_symbol": from_symbol,
				"to_symbol": to_symbol,
				"outputsize": "full",
				"apikey": api_key
			})
			result = result.json()
			for date, values in result["Time Series FX (Daily)"].items():
				price = parse_num_us(values['4. close'])
				output += f"P {date} {escape_commodity(from_symbol)} {format_number_exact(price, format_args, min_decimal=4)} {escape_commodity(to_symbol)}\n"
		else:
			assert False, "Unknown type"
	return output
