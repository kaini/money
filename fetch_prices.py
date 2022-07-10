import requests

def fetch(api_key, load):
	output = ""
	for key, ticker in load.items():
		result = requests.get("https://www.alphavantage.co/query", params={
			"function": "TIME_SERIES_DAILY",
			"symbol": ticker,
			"outputsize": "full",
			"apikey": api_key
		})
		result = result.json()
		for date, values in result["Time Series (Daily)"].items():
			price = values['4. close'].replace(",", "").replace(".", ",")
			output += f"P {date} {key} {price} EUR\n"
	return output
