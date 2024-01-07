import csv, re, os, glob, itertools
from .. import utils

DATE_RE = re.compile(r'(\d\d\d\d)-(\d\d)-(\d\d)')

# "Date"      ;"Amount";"Original amount";"Original currency";"Exchange rate";"Description";"Subject";"Category" ;"Tags";"Wise";"Spaces"
# "2022-01-01";"-1.00" ;""               ;""                 ;""             ;"Migros"     ;         ;"household";""    ;"no"  ;"no"

def do_import(input_path, ledger_account, iban):
    print("\t", input_path)

    entries = []
    with open(input_path, "r", encoding="utf-8") as input_fp:
        reader = csv.DictReader(input_fp, delimiter=';')
        for row in reader:
            booking_date_str = row['Date']
            entry_date = utils.parse_date_ddmmyyyy(list(reversed(DATE_RE.match(booking_date_str).groups())))
            desc_str = row['Description']
            subject_str = row['Subject'].strip()
            entry_desc = f'{desc_str}'
            if subject_str != '':
                entry_desc += f' - {subject_str}'
            entry_amount = utils.parse_num_us(row['Amount'])
            entry_currency = 'CHF'
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
