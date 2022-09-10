# How to start

1. Build the docker container in the folder `docker`.
2. Create an home directory. Put this directory under version control.
3. While the details of the file structure are up to you, I recommend the following setup.
    * *rules/\_\_init\_\_.py*: This file must exist and export a `make_converter` function which returns a converter.
        A converter is a function that takes an `Entry` and returns a corresponding `Booking`. Their respective definitions can be seen in the example below.

        Minimal example:
        ```python
        from rules.data import Booking, BookingLine

        def make_converter():
            def converter(entry):
                # entry.source - source file of the entry
                # entry.account - source account for the entry
                # entry.date - date of the entry
                # entry.text - text of the entry
                # entry.amount - amount of the entry: this is either an integer in the smallest currency unit, a Fraction object, or a Decimal object
                # entry.currency - the currency of the entry
                return Booking(date=entry.date, description=entry.text, lines=[
                    BookingLine(account=entry.account, amount=entry.amount, commodity=entry.currency),
                    BookingLine(account='Unknown', amount=None, commodity=None),
                ])
            return converter
        ```

    * *config.ini*: This file must exist and look like this:

        ```ini
        [DEFAULT]

        # optional formatting information
        [format]
        decimal_separator = ,

        [prices]
        alphavantagekey = XXXXXXXXXXXXXXXXXX
        equity.0 = IS_N IS3N.DEX EUR # hleder commodity <space> Alphavantage Key <space> currency of the price
        equity.1 = IBCZ IBCZ.DEX EUR
        equity.2 = VGWL VGWL.DEX EUR
        fx.0 = USD EUR
        fx.1 = CHF EUR

        [input.cash]
        parser = cash
        account = Aktiva:Bargeld

        [input.easybank_giro]
        parser = easybank_giro
        account = Aktiva:Giro EasyBank
        iban = AT999999999999999999

        [input.easybank_visa]
        parser = easybank_visa
        account = Fremdkapital:VISA EasyBank
        cardno = 999999999999999999

        [input.flatex]
        parser = flatex
        cash = Aktiva:Geldanlagen:Flatex:Kassa
        depot = Aktiva:Geldanlagen:Flatex:Depot
        fees = Aufwendungen:Sonstiges:Bankgebühren
        gains = Erträge:Zinsen und Dividenden
        exchange = Devisen:Flatex
        wkn.A1JX52 = VGWL
        wkn.A111X9 = IS_N
        wkn.A14YPA = IBCZ

        [input.santander]
        parser = santander
        account = Aktiva:Geldanlagen:Taggeld:Santander BestFlex
        iban = AT99999999999999999
        ```

        Each `input.*` section describes how the documents placed in `input/*/` should be processed. The `parser` key is the Python module that is going to be imported and called to handle the files. All other parameters are passed as-is to these modules.
    * A folder called `input`. This folder must exist and must be filled with the input documents, e.g., bank statements or CSV files in sub-folders. Each sub-folder can be processed by a singe input module.
    * A folder called `output`. This folder will be created is the output folder and will copy the structure of the input folder, except that all input documents will be replaced by hledger journals. `output/root.journal` is a hledger journal that imports all other journal files. **Do not edit files in this folder. It will be deleted and re-created on each run!**
    * While this is up to you, a `main.journal` with the following structure is recommended as entry point for hledger: (Hint: Set the environment variable `LEDGER_FILE` to its path.) The `docker_run.sh` script automatically sets `LEDGER_FILE` to `/dest/main.journal`.

        ```
        account Aktiva  ; type:Asset
        account Aktiva:...
        ...

        account Fremdkapital  ; type:Liability
        account Fremdkapital:...
        ...

        account Eigenkapital  ; type:Equity
        account Eigenkapital:...
        ...

        account Erträge  ; type:Revenue
        account Erträge:...
        ...

        account Aufwendungen  ; type:Expense
        account Aufwendungen:...
        ...

        account Buchungsfehler  ; type:Equity
        account Unbekannt  ; type:Equity

        account Devisen  ; type:Equity
        ...

        commodity 1.000,00 EUR  ; €
        commodity 1.000,0 VGWL  ; Vanguard FTSE All-World UCITS ETF
        ...

        include output/root.journal
        include special.journal  ; Used for special postings that have to be entered manually, e.g., your starting balances
        ```
    * Run scripts are provided for your convenience. The scripts are named `run_*.sh` and build and run the docker container.
      They must be executed in the project directory, otherwise the volume mounts will not work correctly.
      They all expect the destination directory (i.e. the directory containing the input data and `main.journal`) as their first argument e.g. `run_main.sh "$HOME/ledger"`.
      - `run_main.sh` executes `src/main.py` and runs the data import.
      - `run_bash.sh` spawns an interactive bash shell in the container.
      - `run_hledger.sh` runs the `hledger` command. Arguments are passed through.
      - `run_hledger_web.sh` starts an `hledger web` server.

# A typical workflow at the end of the month

1. Be sure that `git status` is clean.
2. Download new bank documents/CSV files and place them in their respective `input/*` folder. If needed, manually edit files in the `input` folder, e.g., for cash transactions.
3. Run `main.py`.
4. Use `git diff` and `main.py`'s output to check if everything new is correct. `hledger bal -sB` should add up to zero.
5. If not, edit `rules/__init__.py` and goto step 3.
6. `git commit` and enjoy your new reports.

Note that the Docker container does not contain hledger. I recommend to install it on your host operating system.

# FAQ

I am the only user of this software and - so far - I had no question more than once.
