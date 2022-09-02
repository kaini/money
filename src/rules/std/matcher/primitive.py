# A Matcher is of type Entry -> Bool and decides if an entry should match
# Some converter factory methods take a matcher as an argument

def is_any(matchers):
    return lambda entry: any([m(entry) for m in matchers])

def is_all(matchers):
    return lambda entry: all([m(entry) for m in matchers])