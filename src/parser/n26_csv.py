import csv, re, os, glob, itertools
from .. import utils

DATE_RE = re.compile(r'(\d\d\d\d)-(\d\d)-(\d\d)')

# "Date"      ,"Payee"      ,"Account number","Transaction type"  ,"Payment reference","Amount (EUR)","Amount (Foreign Currency)","Type Foreign Currency","Exchange Rate"
# "2022-01-02","OEBB Ticket",""              ,"MasterCard Payment","-"                ,"-1.1"        ,"-1.1"                     ,"EUR"                  ,"1.0"

def do_import(input_path, ledger_account, iban):
    print("\t", input_path)

    entries = []
    with open(input_path, "r", encoding="utf-8") as input_fp:
        reader = csv.DictReader(input_fp, delimiter=',')
        for row in reader:
            booking_date_str = row['Date']
            entry_date = utils.parse_date_ddmmyyyy(list(reversed(DATE_RE.match(booking_date_str).groups())))
            payee_str = row['Payee']
            reference_str = row['Payment reference'].strip()
            accountno_str = row['Account number'].strip()
            entry_desc = f'{payee_str}'
            if accountno_str != '':
                entry_desc += f' - {accountno_str}'
            if reference_str != '' and reference_str != '-':
                entry_desc += f' - {reference_str}'
            entry_amount = utils.parse_num_us(row['Amount (EUR)'])
            entry_currency = 'EUR'
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
