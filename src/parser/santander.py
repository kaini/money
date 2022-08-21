import textract, datetime, re, utils, os, glob, itertools

RULES = [
    ("Zinsgutschrift", "Erträge:Zinsen und Dividenden"),
    ("Kapitalertragsteuer", "Erträge:Zinsen und Dividenden"),
    ("AT241420020012221798", "Aktiva:Geldanlagen:Taggeld:Santander BestFlex:Barverkehr Giro EasyBank"),
    ("10-00000-5560-2", "Aktiva:Geldanlagen:Festgeld:Santander BestFix 2019-05"),
]
DATE_HEADER_RE = re.compile(r"^\s+Kontostand per \d\d\.\d\d\.\d\d\d\d\s+Kontostand per (\d\d)\.(\d\d)\.(\d\d\d\d)")
IBAN_HEADER_RE = re.compile(r"^\s+IBAN: (.*?)\s*$")
SUM_RE = re.compile(r"^\s+€ -?[0-9.,]+\s+€ (-?[0-9.,]+)")
ENTRY_RE = re.compile(r"^\s+(\d\d)\.(\d\d)\.(\d\d\d\d)\s+(\d\d)\.(\d\d)\.(\d\d\d\d)\s+(-?[0-9.,]+)\s+(-?[0-9.,]+)\s+(.*?)\s*$")

def do_import(input_path, ledger_account, iban):
    print("\t", input_path)

    entries = []
    text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")

    report_date, account, total = None, None, None
    description, date, amount = None, None, None
    for line in text.splitlines():
        match = DATE_HEADER_RE.match(line)
        if match and not report_date:
            report_date = datetime.date(int(match[3]), int(match[2]), int(match[1]))
        
        match = IBAN_HEADER_RE.match(line)
        if match and not account:
            account = match[1]
            assert account == iban
        
        match = SUM_RE.match(line)
        if match and not total:
            total = int(match[1].replace(".", "").replace(",", ""))

        match = ENTRY_RE.match(line)
        if match:
            date = datetime.date(int(match[3]), int(match[2]), int(match[1]))
            description = match[9]
            amount = int(match[7].replace(".", "").replace(",", ""))
            if amount != 0:
                entries.append(utils.Entry(
                    input_path,
                    ledger_account,
                    date,
                    description,
                    amount,
                    "EUR"
                ))
                
    assert total is not None
    assert report_date is not None
    entries.append(utils.Assert(input_path, ledger_account, report_date, total, "EUR"))

    return entries

def main(pool, source, account, iban, **kwargs):
    files = glob.glob(os.path.join(source, "*.pdf"))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, account, iban) for f in files))))
