from rules.data import Booking, BookingLine

def to_account(to_account):
    assert type(to_account) is str
    return lambda entry: to_lines([BookingLine(account=to_account, amount=None, commodity=None)])(entry)

def to_lines(lines):
    def converter(entry):
        return Booking(date=entry.date, description=entry.text, lines=[
            BookingLine(entry.account, entry.amount, entry.currency),
        ] + lines)
    return converter