import csv, datetime, os, glob, re, itertools
from .. import utils

LINE_RE = re.compile("(\d\d?)\.(\d\d?)\.(\d\d\d\d)(.*?)([0-9.,-]+)\s*(€|EUR|E)")

def do_import(input_path, account):
    print("\t", input_path)
    entries = []
    with open(input_path, "r", encoding="UTF-8") as input_fp:
        if input_path.endswith(".csv"):
            reader = csv.DictReader(input_fp)
            for row in reader:
                if row["Datum"]:
                    d, m, y = row["Datum"].split(".")
                    date = datetime.date(int(y), int(m), int(d))
                    description = (row["Beschreibung"] + " " + row["Bemerkung"]).strip()
                    id = row["BuchungsID"]
                if not row["BuchungsID"]:
                    assert date
                    assert description
                    if row["Volle Kontobezeichnung"] != "Aktiva:Giro EasyBank":
                        entries.append(utils.Entry(
                            input_path,
                            account,
                            date,
                            description + " (" + id + ")",
                            -int(row["Wert numerisch"].replace(".", "").replace(",", "")),
                            "EUR"
                        ))
                    date = None
                    description = None
        else:
            for line in input_fp.readlines():
                line = line.strip()
                if line:
                    match = LINE_RE.match(line)
                    entries.append(utils.Entry(
                        input_path,
                        account,
                        datetime.date(int(match[3]), int(match[2]), int(match[1])),
                        re.sub(r"\s+", " ", match[4]),
                        -int(match[5].replace(".", "").replace(",", "")) * (1 if "," in match[5] else 100),
                        "EUR"))
    return entries

def main(pool, source, account, **kwargs):
    files = list(glob.glob(os.path.join(source, "*.txt")))
    files += list(glob.glob(os.path.join(source, "*.csv")))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, account) for f in files))))
