
import collections
import csv, re, utils, os, glob, itertools
from datetime import datetime
from email import feedparser

DATE_RE = re.compile(r'(\d\d\d\d)-(\d\d)-(\d\d)')
FOREX_COMM_RE = re.compile(f'Comm in (.*)')

Section = collections.namedtuple('Section', ['name', 'header', 'data'])

def do_import(input_path, cash_account, portfolio_account, exchange_account, fees_account, gains_account):
    print('\t', input_path)

    sections = []
    current_section = None
    with open(input_path, 'r', encoding='utf-8-sig') as input_fp:
        reader = csv.reader(input_fp, delimiter=',')
        for row in reader:
            name = row[0]
            type = row[1]
            fields = row[2:]

            if type == 'Header':
                if current_section is not None:
                    sections += [current_section]
                current_section = Section(name=name, header=['Name', 'Type'] + fields, data=[])
            elif type in ['Data', 'Total', 'SubTotal']:
                assert name == current_section.name
                current_section = current_section._replace(data=current_section.data + [[name, type] + fields])
            else:
                assert False, f'Unknown entry type: {type}'

    if current_section is not None:
        sections += [current_section]
    
    rows = [row for section in sections for row in parse_section_to_dicts(section)  ]

    entries = []
    entries += parse_deposits_withdrawals(
        input_path=input_path,
        account=cash_account,
        rows=rows,
    )
    entries += parse_trades(
        input_path=input_path,
        cash_account=cash_account,
        portfolio_account=portfolio_account,
        exchange_account=exchange_account,
        fees_account=fees_account,
        rows=rows,
    )
    entries += parse_dividends(
        input_path=input_path,
        cash_account=cash_account,
        gains_account=gains_account,
        rows=rows,
    )
    entries += parse_ending_asserts(
        input_path=input_path,
        cash_account=cash_account,
        portfolio_account=portfolio_account,
        rows=rows
    )

    return entries


def parse_ending_asserts(input_path, cash_account, portfolio_account, rows):
    def parse_period_date(str):
        return datetime.strptime(str, '%B %d, %Y').date()

    period_str = next((
        row['Field Value'] for row in rows if
            row['Name'] == 'Statement' and
            row['Type'] == 'Data' and
            row['Field Name'] == 'Period'
    ))
    period_start_str, period_end_str = period_str.split(' - ')
    period_start = parse_period_date(period_start_str)
    period_end = parse_period_date(period_end_str)

    entries = []
    ending_cash_rows = [
        row for row in rows if
            row['Name'] == 'Cash Report' and
            row['Type'] == 'Data' and
            row['Currency Summary'] == 'Ending Cash'
    ]
    for row in ending_cash_rows:
        currency = row['Currency']
        if currency == 'Base Currency Summary':
            continue

        amount = utils.parse_num_us(row['Total'])
        entry = utils.Assert(
            source=input_path,
            account=f'{cash_account}:{currency}',
            date=period_end,
            amount=amount,
            currency=currency,
        )
        entries.append(entry)

    open_position_rows = [
        row for row in rows if
            row['Name'] == 'Open Positions' and
            row['Type'] == 'Data' and
            row['Asset Category'] == 'Stocks' and
            row['DataDiscriminator'] == 'Summary'
    ]
    for row in open_position_rows:
        symbol = row['Symbol']
        quantity = utils.parse_num_us(row['Quantity'])

        entry = utils.Assert(
            source=input_path,
            account=f'{portfolio_account}:{symbol}',
            date=period_end,
            amount=quantity,
            currency=symbol,
        )
        entries.append(entry)

    return entries


def parse_trades(input_path, cash_account, portfolio_account, fees_account, exchange_account, rows):
    rows = [row for row in rows if row['Name'] == 'Trades']
    entries = []
    for row in rows:
        type = row['Type']

        if type != 'Data':
            continue

        asset_category = row['Asset Category']
        data_discriminator = row['DataDiscriminator']
        currency = row['Currency']
        symbol = row['Symbol']
        date_time = row['Date/Time']
        date = parse_date(date_time.split(',')[0])
        quantity = utils.parse_num_us(row['Quantity'])
        proceeds = utils.parse_num_us(row['Proceeds'])
        
        desc = f'{asset_category} - {data_discriminator} - {symbol}'

        # TODO add support for sales, no exemplary data yet
        assert data_discriminator in ['Order'], f'Unsupported data discriminator: {data_discriminator}'
        
        entry = None
        if asset_category == 'Stocks':
            comm_amount = utils.parse_num_us(row['Comm/Fee'])

            from_account = f'{cash_account}:{currency}'
            to_account = f'{portfolio_account}:{symbol}'
            comm_account = f'{cash_account}:{currency}'

            lines = [
                (from_account, proceeds, currency),
                (f'{exchange_account}:{currency}', -proceeds, currency),

                (to_account, quantity, symbol),
                (f'{exchange_account}:{symbol}', -quantity, symbol),

                (comm_account, comm_amount, currency),
                (fees_account, -comm_amount, currency),
            ]
            entry = utils.Raw(input_path, date, desc, lines)
        elif asset_category == 'Forex':
            comm_key = next(k for k in row.keys() if FOREX_COMM_RE.match(k) is not None)
            comm_currency = FOREX_COMM_RE.match(comm_key).group(1)
            from_currency, to_currency = symbol.split('.')
            assert to_currency == currency
            comm_amount = utils.parse_num_us(row[comm_key])

            from_account = f'{cash_account}:{from_currency}'
            to_account = f'{cash_account}:{to_currency}'
            comm_account = f'{cash_account}:{comm_currency}'

            lines = [
                (from_account, quantity, from_currency),
                (f'{exchange_account}:{from_currency}', -quantity, from_currency),

                (to_account, proceeds, to_currency),
                (f'{exchange_account}:{to_currency}', -proceeds, to_currency),

                (comm_account, comm_amount, comm_currency),
                (fees_account, -comm_amount, comm_currency),
            ]
            entry = utils.Raw(input_path, date, desc, lines)
        else:
            assert False, f'Unsupported asset category: {asset_category}'

        entries.append(entry)
        
    return entries


def parse_dividends(input_path, cash_account, gains_account, rows):
    rows = [row for row in rows if row['Name'] == 'Dividends']
    entries = []
    for row in rows:
        type = row['Type']
        assert type == 'Data', f'Invalid row type: {type}'

        currency = row['Currency']
        if currency.startswith('Total'):
            continue

        desc = row['Description']
        amount = utils.parse_num_us(row['Amount'])
        date = parse_date(row['Date'])
        lines = [
            (f'{cash_account}:{currency}', amount, currency),
            (f'{gains_account}', -amount, currency),
        ]
        entry = utils.Raw(input_path, date, desc, lines)
        entries.append(entry)

    return entries


def parse_deposits_withdrawals(input_path, account, rows):
    rows = [row for row in rows if row['Name'] == 'Deposits & Withdrawals']
    entries = []

    for row in rows:
        currency = row['Currency']
        if currency.startswith('Total'):
            continue

        description = row['Description']
        settle_date = parse_date(row['Settle Date'])
        amount = utils.parse_num_us(row['Amount'])

        entry = utils.Entry(
            source=input_path,
            account=f'{account}:{currency}',
            date=settle_date,
            text=f'{description} - {currency}',
            amount=amount,
            currency=currency
        )

        entries.append(entry)
    return entries


def parse_section_to_dicts(section):
    dicts = []
    for row in section.data:
        d = { field: value for field, value in zip(section.header, row) }
        dicts.append(d)
    return dicts


def parse_date(str):
    return utils.parse_date_ddmmyyyy(list(reversed(DATE_RE.match(str).groups())))


def main(pool, source, cash_account, portfolio_account, exchange_account, fees_account, gains_account, **kwargs):
    files = []
    files += glob.glob(os.path.join(source, '*.csv'))
    files += glob.glob(os.path.join(source, '*.CSV'))
    return list(itertools.chain.from_iterable(pool.starmap(do_import, ((f, cash_account, portfolio_account, exchange_account, fees_account, gains_account) for f in files))))
