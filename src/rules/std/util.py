import hashlib
import json

def entry_id(entry):
    entry_str = json.dumps({
        # account and source have been intentionally excluded as they are probably too unstable
        'date': f'{entry.date}',
        'text': entry.text,
        'amount': f'{entry.amount}',
        'currency': entry.currency,

    })
    return hashlib.sha256(entry_str.encode('utf-8')).hexdigest()[:8]