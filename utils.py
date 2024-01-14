from pprint import pformat
import re
import datetime
import collections
from fractions import Fraction
from decimal import Decimal
import sys

Entry = collections.namedtuple("Entry", ("source", "account", "date", "text", "amount", "currency"))
Assert = collections.namedtuple("Assert", ("source", "account", "date", "amount", "currency"))
Raw = collections.namedtuple("Raw", ("source", "date", "text", "lines"))

FormatArgs = collections.namedtuple("FormatArgs", ("decimal_separator"))
DEFAULT_FORMAT_ARGS = FormatArgs(decimal_separator=",")

def namedtuple_pformat(tuple, format_args):
    str = ""
    str += type(tuple).__name__
    str += "(\n"
    indent = 2
    fields = tuple._fields
    longest_field_len = max([len(field) for field in fields])
    for field in tuple._fields:
        padding = (longest_field_len - len(field)) + 1
        value = getattr(tuple, field)
        if type(value) == Fraction:
            value = format_number_exact(value, format_args, min_decimal=2)
        str += f"{' ' * indent}{field}{' ' * padding}= {pformat(value, compact=True, width=sys.maxsize)},\n"
    str += ")"
    return str


def write_booking(fp, booking, format_args):
    fp.write(f"{booking.date} {sanitize_description(booking.description)}\n")
    for line in booking.lines:
        line_str = None
        if line.amount is None:
            line_str = f"  {line.account}"
        else:
            line_str = f"  {line.account}  {format_exact(line.amount, line.commodity, format_args)}"
        fp.write(line_str + "\n")
    fp.write(f"\n")

def write_assert(fp, account, date, amount, commodity, format_args):
    fp.write(f"{date} ASSERT\n")
    fp.write(f"  {account}  =={format_exact(amount, commodity, format_args)}\n")
    fp.write(f"\n")

def format_exact(amount, commodity, format_args, min_decimal=None):
    # This is an hledger commodity with an exchange value, i.e., VGWL @@ 1234 EUR.
    if isinstance(commodity, tuple):
        dest, value, source = commodity
        return f"{format_exact(amount, dest, format_args, min_decimal)} @@ {format_exact(value, source, format_args, min_decimal)}"

    if min_decimal is None:
        if commodity == "EUR":
            min_decimal = 2
        else:
            min_decimal = 0

    result = format_number_exact(amount=amount, format_args=format_args, min_decimal=min_decimal)

    escaped_commodity = escape_commodity(commodity)

    return f"{result} {escaped_commodity}"

def format_number_exact(amount, format_args, min_decimal=0):
    if isinstance(amount, int):
        amount = Decimal(amount) / Decimal(100)
    else:
        amount = Decimal(amount.numerator) / Decimal(amount.denominator)
    
    sign, digits, exponent = amount.as_tuple()
    result = ""

    if sign == 1:
        result += "-"

    digits = "".join(str(d) for d in digits)
    if exponent < 0:
        if len(digits) < abs(exponent):
            digits = "0" * (abs(exponent) - len(digits)) + digits
        digits = digits[:exponent] + format_args.decimal_separator + digits[exponent:]
        if digits[0] == format_args.decimal_separator:
            digits = "0" + digits
        if len(digits[exponent:]) < min_decimal:
            digits += "0" * (min_decimal - len(digits[exponent:]))
    else:
        digits += "0" * exponent
        if min_decimal > 0:
            digits += format_args.decimal_separator + ("0" * min_decimal)
    result += digits

    return result

def escape_commodity(commodity):
    # > If the commodity name contains non-letters (spaces, numbers, or punctuation), you must always write it inside double quotes ("green apples", "ABC123").
    # https://hledger.org/1.32/hledger.html

    # This is not completely sound under various edge cases (e.g. quotes in the commodity names, ...)
    needs_quoting = not re.match(r"^[a-zA-Z]*$", commodity)
    if needs_quoting:
        return f'"{commodity}"'
    else:
        return commodity

def sanitize_description(text):
    return text.replace('\r\n', ' | ').replace('\r', ' | ').replace('\n', ' | ')

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

def parse_date_ddmmyyyy(ddmmyyyy):
    return datetime.date(year=int(ddmmyyyy[2]), month=int(ddmmyyyy[1]), day=int(ddmmyyyy[0]))

# We have learnt nothing from y2k
def parse_date_ddmmyy_without_century(statement_start_year, statement_end_year, ddmmyy):
    assert (statement_end_year - statement_start_year) in [0, 1], "Non consecutive statement years are not supported"
    statement_start_century = int(str(statement_start_year)[0:2])
    statement_start_yy = int(str(statement_start_year)[2:4])
    statement_end_yy = int(str(statement_end_year)[2:4])
    statement_end_century = int(str(statement_end_year)[0:2])
    yy = int(ddmmyy[2])
    mm = int(ddmmyy[1])
    dd = int(ddmmyy[0])
    yyyy = None
    if yy == statement_start_yy:
        yyyy = int(str(statement_start_century) + str(yy))
    elif yy == statement_end_yy:
        yyyy = int(str(statement_end_century) + str(yy))
    else:
        assert False, "Statement entry date was neither in start nor in end year"

    return datetime.date(year=yyyy, month=mm, day=dd)

def parse_num_us(str):
    return Fraction(str.replace(",", ""))

def parse_num_ch(str):
    return Fraction(str.replace("'", ""))

def parse_num_de(str):
    return Fraction(str.replace(".", "").replace(",", "."))

def parse_num_de_from_match(match):
    return parse_num_de(match[1])

def parse_num_str(str, decimal_separator=","):
    return Fraction(str.replace(decimal_separator, "."))