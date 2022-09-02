import collections

Booking = collections.namedtuple("Booking", ("date", "description", "lines"))
BookingLine = collections.namedtuple("BookingLine", ("account", "amount", "commodity"))

def assert_is_booking(booking):
    if booking is not None:
        assert type(booking) is Booking, f'Expected Booking, but got {type(booking)} with value {booking}'