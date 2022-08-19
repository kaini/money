import textract, re, utils, os, glob, itertools


TABLE_HEADER_RE=re.compile(r"^\s*(Date)\s+(Text)\s+(Debit)\s+(Credit)\s+(Value)\s+(Balance)\s*$")
DATE_RE=re.compile(r"(\d\d)\.(\d\d).(\d\d)") # dd.mm.yy
FULL_DATE_RE=re.compile(r"(\d\d)\.(\d\d).(\d\d\d\d)") # dd.mm.yyyy
MONEY_RE=re.compile(r"(?:\d|'|\.)+") # 12'345.67
STATEMENT_TIME_RE=re.compile(fr"^\s*Detailed account extract ({FULL_DATE_RE.pattern}) to ({FULL_DATE_RE.pattern})\s+Page.*$")
IBAN_RE=re.compile(r"[A-Z]{2}\d{2} (?:\d{1,4} ?){4,}")
STATEMENT_IBAN_RE=re.compile(fr"^\s*IBAN\s+({IBAN_RE.pattern})\s*V?\s*$")
STATEMENT_CLOSING_BALANCE_RE=re.compile(fr"^\s*Closing balance\s+({MONEY_RE.pattern})\s*$")
ENTRY_HEADER_RE=re.compile(fr"^\s*({DATE_RE.pattern})\s+(.*?)\s+({MONEY_RE.pattern})\s+({DATE_RE.pattern})\s+({MONEY_RE.pattern})\s*$")
ENTRY_CONTENT_RE=re.compile(fr"^\s*(\S.*?)\s*$")
EMPTY_LINE_RE=re.compile(fr"^\s*$")


def do_import(input_path, ledger_account, iban):
    print("\t", input_path)

    entries = []
    text = textract.process(input_path, method='pdftotext', layout=True).decode("UTF-8")

    statement_closing_balance = None
    statement_start_date=None
    statement_end_date=None
    statement_iban = None
    current_entry = None
    debit_column_span = None
    for line in text.splitlines():
        statement_closing_balance_match = STATEMENT_CLOSING_BALANCE_RE.match(line)
        statement_iban_match = STATEMENT_IBAN_RE.match(line)
        statement_time_match = STATEMENT_TIME_RE.match(line)
        table_header_match = TABLE_HEADER_RE.match(line)
        entry_header_match = ENTRY_HEADER_RE.match(line)
        entry_content_match = ENTRY_CONTENT_RE.match(line)
        empty_line_match = EMPTY_LINE_RE.match(line)
        if statement_closing_balance_match is not None:
            assert statement_closing_balance is None
            statement_closing_balance = utils.parse_num_ch(statement_closing_balance_match.group(1))
        elif statement_iban_match is not None:
            assert statement_iban is None
            statement_iban = statement_iban_match.group(1).strip()
        elif statement_time_match is not None:
            new_statement_start_date = utils.parse_date_ddmmyyyy(statement_time_match.groups()[1:4])
            new_statement_end_date = utils.parse_date_ddmmyyyy(statement_time_match.groups()[5:8])
            if statement_start_date is not None or statement_end_date is not None:
                assert statement_start_date == new_statement_start_date
                assert statement_end_date == new_statement_end_date
            else:
                statement_start_date = new_statement_start_date
                statement_end_date = new_statement_end_date
        elif table_header_match is not None:
            debit_column_span = table_header_match.span(3)
            assert line[debit_column_span[0]:debit_column_span[1]] == "Debit"
        elif entry_header_match is not None:
            assert current_entry is None
            assert statement_start_date is not None
            assert statement_end_date is not None
            assert debit_column_span is not None
            groups = entry_header_match.groups()
            entry_date = utils.parse_date_ddmmyy_without_century(
                statement_start_year=statement_start_date.year,
                statement_end_year=statement_end_date.year,
                ddmmyy=groups[1:4]
            )
            entry_desc = groups[4].strip()
            entry_amount_span = entry_header_match.span(6)
            entry_amount = utils.parse_num_ch(entry_header_match.group(6))
            # We rely pretty strongly on the fact the the debit amount never moves outside the right-aligned debit column
            is_credit = entry_amount_span[1] > debit_column_span[1]
            if not is_credit:
                # It's a debit i.e. negative
                entry_amount = -entry_amount
            current_entry = utils.Entry(
                source=input_path,
                account=ledger_account,
                date=entry_date,
                text=entry_desc,
                amount=entry_amount,
                currency="CHF"
                )
        elif entry_content_match is not None:
            if current_entry is not None:
                current_entry = current_entry._replace(
                    text=current_entry.text + "\n" + entry_content_match.group(1).strip(),
                )
        elif empty_line_match is not None:
            if current_entry is not None:
                entries.append(current_entry)
                current_entry = None
                
    assert statement_iban == iban
    assert statement_closing_balance is not None
    assert statement_end_date is not None
    entries.append(utils.Assert(
        source=input_path,
        account=ledger_account,
        date=statement_end_date,
        amount=statement_closing_balance,
        currency="CHF"
    ))

    return entries

def main(pool, source, account, iban, **kwargs):
    files = []
    files += glob.glob(os.path.join(source, "*.pdf"))
    files += glob.glob(os.path.join(source, "*.PDF"))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, account, iban) for f in files))))
