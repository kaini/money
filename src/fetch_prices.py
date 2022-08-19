import requests

QUERY_URL = "https://www.alphavantage.co/query"

def fetch(api_key, load):
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
				price = values['4. close'].replace(",", "").replace(".", ",")
				output += f"P {date} {key} {price} {currency}\n"
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
				price = values['4. close'].replace(",", "").replace(".", ",")
				output += f"P {date} {to_symbol} {price} {from_symbol}\n"
		else:
			assert False, "Unknown type"
	return output
