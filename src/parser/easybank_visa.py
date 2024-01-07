import textract, datetime, re, os, glob, itertools
from .. import utils

HEADER1_RE = re.compile(r"^\s+Abrechnung.*?per\s+(\d\d)\.(\d\d)\.(\d\d\d\d)")
HEADER2_RE = re.compile(r"^\s+zu Kartennummer\s+([0-9*]{4} [0-9*]{4} [0-9*]{4} [0-9*]{4}).*")
ENTRY_RE = re.compile(r"^\s+(\d\d)\.(\d\d)\s+(.*?)\s+([0-9.]+,\d\d)(-?)\s*$")
IGNORE_RE = re.compile(r"^[A-Z0-9]{30}/[A-Z0-9]{2}-[0-9]")
SUM_RE = re.compile(r"^\s+.*Gesamtbetrag.*\s+([0-9.]+,\d\d)(-?)")

def do_import(input_path, account, cardno):
    print("\t", input_path)

    cardno_stars = cardno[:6] + "******" + cardno[-4:]

    entries = []
    text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")

    report_date, account_cardno, total = None, None, None
    description, date, amount = None, None, None
    for line in text.splitlines():
        match = IGNORE_RE.match(line)
        if match or not line.strip():
            continue

        match = HEADER1_RE.match(line)
        if match and not report_date:
            report_date = datetime.date(int(match[3]), int(match[2]), int(match[1]))
        
        match = HEADER2_RE.match(line)
        if match and not account_cardno:
            account_cardno = match[1].replace(" ", "")
            assert account_cardno == cardno or account_cardno == cardno_stars
        
        match = SUM_RE.match(line)
        if match and not total:
            total = -(-1 if match[2] else 1) * int(match[1].replace(".", "").replace(",", ""))

        match = ENTRY_RE.match(line)
        if match:
            date = datetime.date(report_date.year, int(match[2]), int(match[1]))
            if date > report_date:
                date = datetime.date(date.year - 1, date.month, date.day)
            description = re.sub(r"\s+", " ", match[3])
            amount = -(-1 if match[5] else 1) * int(match[4].replace(".", "").replace(",", ""))
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
    entries.append(utils.Assert(
        input_path,
        account,
        date,
        total,
        "EUR"
    ))

    return entries

def main(pool, source, account, cardno, **kwargs):
    files = glob.glob(os.path.join(source, "*.pdf"))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, account, cardno) for f in files))))
