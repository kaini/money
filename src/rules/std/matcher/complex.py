import re

from rules.std.util import entry_id

def is_regex_substr(regex):
    r = re.compile(regex, re.I | re.M | re.DOTALL)
    return lambda entry: bool(r.search(entry.text))

def is_id(id):
    return lambda entry: entry_id(entry) == id

def is_account(account):
    return lambda entry: entry.account == account

def is_date(date):
    return lambda entry: entry.date == date