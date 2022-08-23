
import csv, re, utils, os, glob, itertools

DATE_RE = re.compile(r'(\d\d)\.(\d\d)\.(\d\d\d\d)')

# 31.12.2019;"Some description";01.01.2020;1,23;EUR;31.12.2019 21:48:57:548
FIELDS = ['booking_date', 'desc', 'valuta_date', 'amount', 'currency', 'entry_timestamp']

def do_import(input_path, ledger_account, iban):
    print("\t", input_path)

    entries = []
    # The files contain BOMs, so get rid of them
    with open(input_path, "r", encoding="utf-8-sig") as input_fp:
        reader = csv.DictReader(input_fp, fieldnames=FIELDS, delimiter=';')
        for row in reader:
            booking_date_str = row['booking_date'].strip()
            entry_date = utils.parse_date_ddmmyyyy(DATE_RE.match(booking_date_str).groups())
            entry_desc = row['desc']
            entry_amount = utils.parse_num_de(row['amount'])
            entry_currency = row['currency']
            current_entry = utils.Entry(
                source=input_path,
                account=ledger_account,
                date=entry_date,
                text=entry_desc,
                amount=entry_amount,
                currency=entry_currency
            )

            entries.append(current_entry)

    return entries

def main(pool, source, account, iban, **kwargs):
    files = []
    files += glob.glob(os.path.join(source, "*.csv"))
    files += glob.glob(os.path.join(source, "*.CSV"))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, account, iban) for f in files))))
