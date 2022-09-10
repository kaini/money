import collections
import hashlib
import json

Booking = collections.namedtuple("Booking", ("date", "description", "lines"))
BookingLine = collections.namedtuple("BookingLine", ("account", "amount", "commodity"))

def assert_is_booking(booking):
    if booking is not None:
        assert type(booking) is Booking, f'Expected Booking, but got {type(booking)} with value {booking}'

def entry_id(entry):
    entry_str = json.dumps({
        # account and source have been intentionally excluded as they are probably too unstable
        'date': f'{entry.date}',
        'text': entry.text,
        'amount': f'{entry.amount}',
        'currency': entry.currency,

    })
    return hashlib.sha256(entry_str.encode('utf-8')).hexdigest()[:8]