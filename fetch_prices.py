import requests
import time

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
				# Full is only available on the premium plan
				# Compact gives us 100 datapoints (~3 months)
				# Given that we keep old datapoints and merge them with the new ones, this should be good enough in practice (as long as we never need historical price data)
				"outputsize": "compact",
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

		# Sleep for 1s between loads, per the rate limits imposed on Alphavantage's free plan
		time.sleep(1)

	return output
