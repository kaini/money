import multiprocessing, os, shutil, datetime, importlib, collections
from . import utils, fetch_prices
from .rules.data import Booking, BookingLine, assert_is_booking
# Intentionally imported to re-export
from .utils import FormatArgs


def init_parsers(base_path, config):
    parsers = dict()
    for section in config.sections():
        if section.startswith("input."):
            parser_module = importlib.import_module("parser." + config[section].get("parser"))
            name = section[len("input."):]
            source = os.path.join(base_path, "input", name)
            parser = lambda pool, source=source, parser_module=parser_module, kwargs=dict(config[section]): parser_module.main(pool=pool, source=source, **kwargs)
            parsers[name] = parser
    return parsers

def delete_output(base_path):
    path = os.path.join(base_path, "output")
    if os.path.exists(path):
        shutil.rmtree(path)
    os.mkdir(path)

Config = collections.namedtuple("Config", (
    "inputs",
    "prices",
    "converter",
    "base_path",
    "format",
))

Input = collections.namedtuple("input", (
    "name",
    "parser",
))

Prices = collections.namedtuple("Prices", (
    "alphavantage_key",
    "equities",
    "forex",
))

def main(config):
    base_path = config.base_path
    format_args = config.format

    commodity_prices = ''
    should_fetch_commodity_prices = True
    prices_path_rel = os.path.join("output", "prices.journal")
    prices_path = os.path.join(base_path, prices_path_rel)
    if os.path.exists(prices_path):
        with open(prices_path) as fp:
            commodity_prices = fp.read()

        mtime = datetime.datetime.fromtimestamp(os.stat(prices_path).st_mtime)
        should_fetch_commodity_prices = datetime.datetime.now() - mtime > datetime.timedelta(days=2)

    delete_output(base_path)
    output_files = dict()
    
    if should_fetch_commodity_prices:
        print("Fetching prices")
        alphavantage_api_key = config.prices.alphavantage_key
        equity_entries = [{'type': 'EQUITY', 'key': v[0], 'symbol': v[1], 'currency': v[2]} for v in config.prices.equities]
        fx_entries = [{'type': 'FX', 'from_symbol': v[0], 'to_symbol': v[1]} for v in config.prices.forex]
        new_commodity_prices = fetch_prices.fetch(alphavantage_api_key, equity_entries + fx_entries, format_args)
        commodity_prices = merge_prices(existing_prices=commodity_prices, new_prices=new_commodity_prices)

    with open(prices_path, "w", encoding="UTF-8") as fp:
        fp.write(commodity_prices)
    output_files[prices_path_rel] = datetime.date(1000, 1, 1)

    entries = collections.defaultdict(lambda: [])  # maps destination path to list of entries
    with multiprocessing.Pool() as pool:
        for input in config.inputs:
            name, parser = input.name, input.parser
            print("Parsing", name)
            for entry in parser(pool):
                rest, filename = os.path.split(entry.source)
                rest, directory = os.path.split(rest)

                dot = filename.rfind(".")
                if dot >= 0:
                    filename = filename[:dot] + ".journal"

                destination = os.path.join(base_path, "output", directory, filename)
                entries[destination].append(entry)

    for dest_file, entries in entries.items():
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        with open(dest_file, "w", encoding="UTF-8") as fp:
            output_files[dest_file] = datetime.date(1000, 1, 1)
            for entry in entries:
                if isinstance(entry, utils.Entry):
                    booking = config.converter(entry)
                    if booking is None:
                        continue
                    assert_is_booking(booking)
                    utils.write_booking(fp, booking, format_args)
                elif isinstance(entry, utils.Assert):
                    utils.write_assert(fp, entry.account, entry.date, entry.amount, entry.currency, format_args)
                elif isinstance(entry, utils.Raw):
                    utils.write_booking(fp, Booking(date=entry.date, description=entry.text, lines = [
                        BookingLine(account=line[0], amount=line[1], commodity=line[2])
                        for line in entry.lines
                    ]), format_args)
                else:
                    raise Exception("Unknown thing in entries: " + repr(entry))
                output_files[dest_file] = max(output_files[dest_file], entry.date)

    with open(os.path.join(base_path, "output", "root.journal"), "w", encoding="UTF-8") as fp:
        for output_file, date in sorted(output_files.items(), key=lambda i: i[1]):
            output_file = output_file[output_file.index("output") + 7:]
            fp.write("include " + output_file + "\n")


def merge_prices(existing_prices, new_prices):
    parse_prices = lambda rows:  [r.split(' ') for r in rows.splitlines()]
    existing_rows = parse_prices(existing_prices)
    new_rows = parse_prices(new_prices)

    key_to_row = dict()
    for r in existing_rows + new_rows:
        _p, date, symbol_1, _price, symbol_2 = r
        key = (date, symbol_1, symbol_2)
        if key in key_to_row:
            val = key_to_row[key]
            if r != val:
                # Alphavantage reports the current day and the value can, of course, vary
                print(f'Warn: Merging prices - duplicate key {key} with mismatched value ({r} vs {val})')
        key_to_row[key] = r
    
    rows = [i[1] for i in sorted(key_to_row.items(), key=lambda i: i[0])]
    prices = '\n'.join([' '.join(r) for r in rows])
    return prices
