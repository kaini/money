import re
import datetime
import collections
from fractions import Fraction
from decimal import Decimal
from collections.abc import Iterable

Entry = collections.namedtuple("Entry", ("source", "account", "date", "text", "amount", "currency"))
Assert = collections.namedtuple("Assert", ("source", "account", "date", "amount", "currency"))
Raw = collections.namedtuple("Raw", ("source", "date", "text", "lines"))

def write_booking(fp, account2, account1, date, description, amount, commodity):
    if isinstance(account2, str):
        account2 = ((account2, None, None),)

    fp.write(f"{date} {description}\n")
    fp.write(f"  {account1}  {format_exact(amount, commodity)}\n")
    for subaccount, subamount, subcommodity in account2:
        if subamount is None:
            fp.write(f"  {subaccount}\n")
        else:
            fp.write(f"  {subaccount}  {format_exact(subamount, subcommodity)}\n")
    fp.write(f"\n")

def write_assert(fp, account, date, amount, commodity):
    fp.write(f"{date} ASSERT\n")
    fp.write(f"  {account}  =={format_exact(amount, commodity)}\n")
    fp.write(f"\n")

def format_exact(amount, commodity, min_decimal=None):
    # This is an hledger commodity with an exchange value, i.e., VGWL @@ 1234 EUR.
    if isinstance(commodity, tuple):
        dest, value, source = commodity
        return f"{format_exact(amount, dest, min_decimal)} @@ {format_exact(value, source, min_decimal)}"

    if isinstance(amount, int):
        amount = Decimal(amount) / Decimal(100)
    else:
        amount = Decimal(amount.numerator) / Decimal(amount.denominator)
    
    if min_decimal is None:
        if commodity == "EUR":
            min_decimal = 2
        else:
            min_decimal = 0

    sign, digits, exponent = amount.as_tuple()
    result = ""

    if sign == 1:
        result += "-"

    digits = "".join(str(d) for d in digits)
    if exponent < 0:
        if len(digits) < abs(exponent):
            digits = "0" * (abs(exponent) - len(digits)) + digits
        digits = digits[:exponent] + "," + digits[exponent:]
        if digits[0] == ",":
            digits = "0" + digits
        if len(digits[exponent:]) < min_decimal:
            digits += "0" * (min_decimal - len(digits[exponent:]))
    else:
        digits += "0" * exponent
        if min_decimal > 0:
            digits += "," + ("0" * min_decimal)
    result += digits

    return f"{result} {commodity}"

def format_date(date):
    return str(date)

def import_text(text, fields):
    result = dict()
    for name, (regex, parser) in fields.items():
        match = re.search(regex, text)
        if match:
            result[name] = parser(match)
        else:
            result[name] = None
    return collections.namedtuple("ImportResult", fields.keys())(**result)

def parse_date_dmy(match):
    return datetime.date(year=int(match[3]), month=int(match[2]), day=int(match[1]))

def parse_num_de(match):
    return Fraction(match[1].replace(".", "").replace(",", "."))

def parse_num_str(str):
    return Fraction(str.replace(",", "."))
