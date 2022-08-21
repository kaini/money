import multiprocessing, os, shutil, datetime, configparser, importlib, re, collections, utils, sys, fetch_prices
from pprint import pprint

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

def parse_rules(base_path):
    rules = configparser.ConfigParser(delimiters=("=",))
    rules.read(os.path.join(base_path, "rules.ini"), encoding="UTF-8")

    result = []
    for rule, account in rules["DEFAULT"].items():
        parts = rule.split("$")
        if parts[0] == "text":
            result.append((lambda entry, regex=re.compile(parts[1], re.I | re.M | re.DOTALL): bool(regex.search(entry.text)), account))
        else:
            raise Exception("Unknown rule syntax " + rule)

    def fallback(entry):
        print(f"Warning: Had to apply fallback rule to entry: {utils.namedtuple_pformat(entry)}")
        return True
    result.append((fallback, "Unbekannt"))

    return result

def main():
    base_path = sys.argv[1]

    config = configparser.ConfigParser()
    config.read(os.path.join(base_path, "config.ini"), encoding="UTF-8")

    rules = parse_rules(base_path)

    parsers = init_parsers(base_path, config)
    
    commodity_prices = None
    if os.path.exists(os.path.join(base_path, "output", "prices.journal")):
        mtime = datetime.datetime.fromtimestamp(os.stat(os.path.join(base_path, "output", "prices.journal")).st_mtime)
        if datetime.datetime.now() - mtime < datetime.timedelta(days=2):
            with open(os.path.join(base_path, "output", "prices.journal"), "r", encoding="UTF-8") as fp:
                commodity_prices = fp.read()

    delete_output(base_path)
    output_files = dict()
    
    if not commodity_prices:
        print("[FETCHING PRICES]")
        alphavantage_api_key = config["prices"]["alphavantagekey"]
        price_load_entries = [[k, *v.split()] for k, v in config["prices"].items() if "." in k]
        equity_entries = [{'type': 'EQUITY', 'key': v[1], 'symbol': v[2], 'currency': v[3]} for v in price_load_entries if v[0].startswith("equity.")]
        fx_entries = [{'type': 'FX', 'from_symbol': v[1], 'to_symbol': v[2]} for v in price_load_entries if v[0].startswith("fx.")]
        commodity_prices = fetch_prices.fetch(alphavantage_api_key, equity_entries + fx_entries)
    with open(os.path.join(base_path, "output", "prices.journal"), "w", encoding="UTF-8") as fp:
        fp.write(commodity_prices)
    output_files[os.path.join("output", "prices.journal")] = datetime.date(1000, 1, 1)

    entries = collections.defaultdict(lambda: [])  # maps destination path to list of entries
    with multiprocessing.Pool() as pool:
        for name, parser in parsers.items():
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
                    for rule in rules:
                        if rule[0](entry):
                            break
                    else:
                        # This should be unreachable, because there is a fallback rule in rules.
                        assert False

                    # The rule could be a compound rule (using the + operator)
                    destination = []
                    for component in rule[1].split("+"):
                        component = component.strip()
                        parts = component.split("=")
                        if len(parts) == 1:
                            destination.append((parts[0].strip(), None, None))
                        else:
                            destination.append((parts[0].strip(), utils.parse_num_str(parts[1]), entry.currency))

                    utils.write_booking(fp, destination, entry.account, entry.date, entry.text, entry.amount, entry.currency)
                elif isinstance(entry, utils.Assert):
                    utils.write_assert(fp, entry.account, entry.date, entry.amount, entry.currency)
                elif isinstance(entry, utils.Raw):
                    utils.write_booking(fp, entry.lines[1:], entry.lines[0][0], entry.date, entry.text, entry.lines[0][1], entry.lines[0][2])
                else:
                    raise Exception("Unknown thing in entries: " + repr(entry))
                output_files[dest_file] = max(output_files[dest_file], entry.date)

    with open(os.path.join(base_path, "output", "root.journal"), "w", encoding="UTF-8") as fp:
        for output_file, date in sorted(output_files.items(), key=lambda i: i[1]):
            output_file = output_file[output_file.index("output") + 7:]
            fp.write("include " + output_file + "\n")


if __name__ == "__main__":
    main()
