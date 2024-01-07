import textract, datetime, re, glob, os, itertools
from .. import utils

HEADER1_RE = re.compile(r"^\s+KONTOAUSZUG.*?vom\s+(\d\d)\.(\d\d)\.(\d\d\d\d)")
HEADER2_RE = re.compile(r"^.*?(AT\d\d \d\d\d\d \d\d\d\d \d\d\d\d \d\d\d\d)\s+")
ENTRY_RE = re.compile(r"^(\s+(\d\d)\.(\d\d)\s+)(.*?)\s+(\d\d)\.(\d\d)\*?\s+([0-9.]+,\d\d)(-?)")
IGNORE_RE = re.compile(r"^[A-Z0-9]{30}/[A-Z0-9]{2}-[0-9]")
SUM_RE = re.compile(r"^\s+Neuer Kontostand zu Ihren Gunsten EUR\s+([0-9.]+,\d\d)")

def do_import(input_path, account, iban):
    print("\t", input_path)

    text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")
    entries = []

    report_date, account_iban, total = None, None, None
    description, date, amount, indent = None, None, None, None
    for line in text.splitlines():
        match = IGNORE_RE.match(line)
        if match or not line.strip():
            continue

        match = HEADER1_RE.match(line)
        if match and not report_date:
            report_date = datetime.date(int(match[3]), int(match[2]), int(match[1]))
        
        match = HEADER2_RE.match(line)
        if match and not account_iban:
            account_iban = match[1].replace(" ", "")
            assert account_iban == iban

        match = SUM_RE.match(line)
        if match and not total:
            total = int(match[1].replace(".", "").replace(",", ""))

        if indent:
            if line.startswith(" " * indent) and len(line) > indent and line[indent] != " ":
                description += line
            else:
                description = re.sub(r"\s+", " ", description)
                entries.append(utils.Entry(
                    input_path,
                    account,
                    date,
                    description,
                    amount,
                    "EUR"
                ))
                description, date, amount, indent = None, None, None, None

        match = ENTRY_RE.match(line)
        if match:
            date = datetime.date(report_date.year, int(match[3]), int(match[2]))
            if date > report_date:
                date = datetime.date(date.year - 1, date.month, date.day)
            description = match[4]
            amount = (-1 if match[8] else 1) * int(match[7].replace(".", "").replace(",", ""))
            indent = len(match[1])
    
    if indent:
        description = re.sub(r"\s+", " ", description)
        entries.append(utils.Entry(
            input_path,
            account,
            date,
            description,
            amount,
            "EUR"
        ))
    
    assert total is not None
    assert report_date is not None
    entries.append(utils.Assert(input_path, account, report_date, total, "EUR"))

    return entries
            
def main(pool, source, account, iban, **kwargs):
    files = glob.glob(os.path.join(source, "*.pdf"))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, account, iban) for f in files))))
