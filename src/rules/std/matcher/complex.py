import re

def on_regex_substr(regex):
    r = re.compile(regex, re.I | re.M | re.DOTALL)
    return lambda entry: bool(r.search(entry.text))