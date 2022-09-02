# A Converter is of type Entry -> Booking
# That is it receives an Entry and returns a Booking which will be written to the ledger

from rules.data import assert_is_booking


def c_seq(converters):
    def f(entry):
        for c in converters:
            result = c(entry)
            assert_is_booking(result)
            if result is not None:
                return result
        return None
    return f

def c_if(matcher, converter):
    return c_if_else(matcher, converter, c_const(None))

def c_if_else(matcher, c_true, c_false):
    def f(entry):
        if matcher(entry):
            r = c_true(entry)
        else:
            r = c_false(entry)
        assert_is_booking(r)
        return r
    return f

def c_const(booking):
    def f(_entry):
        assert_is_booking(booking)
        return booking
    return f