import textract, datetime, re, os, glob, itertools
from fractions import Fraction
from .. import utils

FILENAME_RE = re.compile(r"^(\d\d\d\d)(\d\d)(\d\d)_")

def do_import(input_path, cash, depot, fees, gains, exchange, commodities, prices):
    if "kauffondszertifikate" in input_path.lower():
        text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")
        if "Wertpapierabrechnung Kauf Fonds/Zertifikate" in text:
            sell = False
        elif "Wertpapierabrechnung Verkauf Fonds/Zertifikate" in text:
            sell = True
        else:
            return []
        print("\t", input_path)

        values = utils.import_text(text, {
            "date": (r"Valuta\s+(\d\d)\.(\d\d)\.(\d\d\d\d)", utils.parse_date_dmy),
            "subject": (r"Nr\.([0-9/]+)\s+(?:Kauf|Verkauf).*\([A-Z0-9]+/([A-Z0-9]+)\)", lambda m: (re.sub(r"\s+", " ", m[0]), m[2], m[1])),
            "amount": (r"Ausgeführt\s+:\s+([0-9,.-]+) St\.", utils.parse_num_de_from_match),
            "value": (r"Kurswert\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
            "pcost": (r"Provision\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
            "ocost": (r"Eigene Spesen\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
            "fcost": (r"Fremde Spesen\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
            "tax": (r"Einbeh\. KESt\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
            "cash": (r"Endbetrag\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
        })
        fees_amount = values.pcost + values.ocost + values.fcost
        description, commodity, id = values.subject

        if sell:
            for i, entry in enumerate(prices[commodity]):
                if entry[0] == values.subject[2]:
                    break
            else:
                assert False
            buy_price = prices[commodity][i - 1][3] / prices[commodity][i - 1][2]
            gain = values.value - buy_price * values.amount

            lines = []
            lines.append((cash, values.cash, "EUR"))
            if fees_amount != 0:
                lines.append((fees, fees_amount, "EUR"))
            if values.tax and values.tax != 0:
                lines.append((gains, values.tax, "EUR"))
            if gain != 0:
                lines.append((gains, -gain, "EUR"))
            lines.append((depot + ":" + commodity, -values.amount, (commodities[commodity.lower()], buy_price * values.amount, "EUR")))
            lines.append((exchange + ":" + commodity, -buy_price * values.amount, "EUR"))
            lines.append((exchange + ":" + commodity, values.amount, (commodities[commodity.lower()], buy_price * values.amount, "EUR")))

            return [utils.Raw(input_path, values.date, description, lines)]
        else:
            lines = []
            lines.append((cash, values.cash, "EUR"))
            lines.append((exchange + ":" + commodity, -values.cash - fees_amount, "EUR"))
            lines.append((exchange + ":" + commodity, -values.amount, (commodities[commodity.lower()], -values.cash - fees_amount, "EUR")))
            lines.append((depot + ":" + commodity, values.amount, (commodities[commodity.lower()], -values.cash - fees_amount, "EUR")))
            if fees_amount != 0:
                lines.append((fees, fees_amount, "EUR"))
            return [utils.Raw(input_path, values.date, description, lines)]

    elif "fondsthesaurierung" in input_path.lower():
        print("\t", input_path)
        text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")
        values = utils.import_text(text, {
            "date": (r"Valuta\s+:\s+(\d\d)\.(\d\d)\.(\d\d\d\d)", utils.parse_date_dmy),
            "cost": (r"Endbetrag\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
            "subject": (r"Nr\.[0-9/]+.*?\)", lambda m: re.sub(r"\s+", " ", m[0])),
        })
        return [utils.Raw(input_path, values.date, "Thesaurierung " + values.subject, ((cash, values.cost, "EUR"), (gains, None, None)))]
    elif "kontoauszug" in input_path.lower():
        text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")
        if "Saldo vor Rechnungsabschluss" in text:
            print("\t", input_path)
            values = utils.import_text(text, {
                "date": (r"Rechnungsabschluss zum (\d\d)\.(\d\d)\.(\d\d\d\d)", utils.parse_date_dmy),
                "cost": (r"Rechnungsabschluss:\s+([0-9.,-]+) EUR", utils.parse_num_de_from_match),
                "sum": (r"Saldo nach Rechnungsabschluss.*?([0-9.,-]+) EUR", utils.parse_num_de_from_match),
            })
            result = []
            if values.cost != 0:
                result.append(utils.Raw(input_path, values.date, "Flatex Rechnungsabschluss", ((cash, values.cost, "EUR"), (fees, None, None))))
            result.append(utils.Assert(input_path, cash, values.date, values.sum, "EUR"))
            return result
        else:
            return []
    elif "fondsertragsausschuettung" in input_path.lower():
        print("\t", input_path)
        text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")
        values = utils.import_text(text, {
            "date": (r"Valuta\s+:\s+(\d\d)\.(\d\d)\.(\d\d\d\d)", utils.parse_date_dmy),
            "gain": (r"Endbetrag\s+:\s+([0-9.,-]+) EUR", utils.parse_num_de_from_match),
            "subject": (r"Nr\..*?\)", lambda m: re.sub(r"\s+", " ", m[0])),
        })
        if values.gain != 0:
            return [utils.Raw(input_path, values.date, values.subject, ((cash, values.gain, "EUR"), (gains, None, None)))]
        else:
            return []
    else:
        return []

def date_ok(filename):
    filematch = FILENAME_RE.match(os.path.basename(filename))
    if filematch:
        filedate = datetime.date(int(filematch[1]), int(filematch[2]), int(filematch[3]))
        return filedate >= datetime.date(2019, 1, 1)
    else:
        return False

def find_buy_sell(input_path):
    text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")
    
    if "Sammelabrechnung aus Sparplan" in text:
        return None
    sell = "verkauf" in input_path.lower()

    print("\t", input_path, "[PRE]")
    fields = utils.import_text(text, {
        "date": (r"Valuta\s+(\d\d)\.(\d\d)\.(\d\d\d\d)", utils.parse_date_dmy),
        "subject": (r"Nr\.([0-9/]+)\s+(?:Kauf|Verkauf).*\([A-Z0-9]+/([A-Z0-9]+)\)", lambda m: (m[1], m[2])),
        "amount": (r"Ausgeführt\s+:\s+([0-9,.-]+) St\.", utils.parse_num_de_from_match),
        "value": (r"Kurswert\s+:\s+([0-9,.-]+) EUR", utils.parse_num_de_from_match),
    })
    return (
        fields.subject[0],
        fields.subject[1],
        fields.date,
        (-1 if sell else 1) * fields.amount,
        None if sell else fields.value,
    )

def find_prices(pool, source):
    files = [f for f in glob.glob(os.path.join(source, "*.pdf")) if date_ok(f) and "kauffondszertifikate" in f.lower()]
    results = [r for r in pool.map(find_buy_sell, files) if r]
    results.sort(key=lambda r: (r[2], r[0]))

    prices = {
        "A111X9": [("init", datetime.date(2018, 12, 31), Fraction("290.346254"), Fraction("7060.88"))],
        "A14YPA": [("init", datetime.date(2018, 12, 31), Fraction("3002.703513"), Fraction("17222.79"))],
    }
    for id, subject, date, amount, value in results:
        if amount > 0:
            if subject not in prices:
                prices[subject] = [(id, date, amount, value)]
            else:
                last_id, last_date, last_amount, last_value = prices[subject][-1]
                prices[subject].append((id, date, last_amount + amount, last_value + value))
        else:
            last_id, last_date, last_amount, last_value = prices[subject][-1]
            prices[subject].append((id, date, last_amount + amount, last_value * (last_amount + amount) / last_amount))
    return prices

def main(pool, source, cash, depot, fees, gains, exchange, **kwargs):
    # Unfortunately, flatex does not have the buy price (or the gains) of a sale in its documents.
    # Therefore, I have to go through all buy/sell transactions first to find the commodities' buy-prices for each point in time.
    prices = find_prices(pool, source)
    commodities = dict((k[4:], v) for k, v in kwargs.items() if k.startswith("wkn."))
    files = [f for f in glob.glob(os.path.join(source, "*.pdf")) if date_ok(f)]
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, cash, depot, fees, gains, exchange, commodities, prices) for f in files))))
