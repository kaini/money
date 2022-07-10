# How to start

1. Build the docker container in the folder `docker`.
2. Create an home directory. Put this directory under version control.
3. While the details of the file structure are up to you, I recommend the following setup.
    * *rules.ini*: This file must exist and look like this:

        ```text
        [DEFAULT]
        text$levis = Aufwendungen:Alltag:Kleidung
        text$hervis = Aufwendungen:Hobbies:Sonstiges
        text$hm.*voesendorf = Aufwendungen:Alltag:Kleidung
        text$wipark = Aufwendungen:Fahrtkosten:Auto:Maut und Parkgebühren
        text$marionnaud = Aufwendungen:Alltag:Lebensmittel und Einkäufe
        ```

        The key of each entry is a matcher, while the value of each entry is the account this should map to. Currently there is only one matcher, `text`, which is a case-insensitive regular expression contains operation.

        The value might either be an account, or, might be a list of accounts if the expense/income has to be split up. For example `text$p02-1685277-4365360 = Aufwendungen:Hobbies:Cello = 268,90 + Aufwendungen:Hobbies:Computer:Hardware` posts 268.90 EUR to `Aufwendungen:Hobbies:Cello` and the rest to `Aufwendungen:Hobbies:Computer:Hardware`.
    * *config.ini*: This file must exist and look like this:

        ```
        [DEFAULT]

        [prices]
        alphavantagekey = XXXXXXXXXXXXXXXXXX
        load.0 = IS_N IS3N.DEX  # hleder commodity <space> Alphavantage Key
        load.1 = IBCZ IBCZ.DEX
        load.2 = VGWL VGWL.DEX

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
    * While this is up to you, a `main.journal` with the following structure is recommended as entry point for hledger: (Hint: Set the environment variable `LEDGER_FILE` to its path.)

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

        commodity 1.000,00 EUR  ; €
        commodity 1.000,0 VGWL  ; Vanguard FTSE All-World UCITS ETF
        ...

        include output/root.journal
        include special.journal  ; Used for special postings that have to be entered manually, e.g., your starting balances
        ```
    * A small wrapper script to start `main.py` is handy. For example:
        ```
        docker run -it --rm -v x:\git\geld\haushaltsbuch:/code -v x:\git\geld\haushaltsbuch_home:/dest geld python3 /code/main.py /dest
        ```

# A typical workflow at the end of the month

1. Be sure that `git status` is clean.
2. Download new bank documents/CSV files and place them in their respective `input/*` folder. If needed, manually edit files in the `input` folder, e.g., for cash transactions.
3. Run `main.py`.
4. Use `git diff` and `main.py`'s output to check if everything new is correct. `hledger bal -sB` should add up to zero.
5. If not, edit `rules.ini` and goto step 3.
6. `git commit` and enjoy your new reports.

Note that the Docker container does not contain hledger. I recommend to install it on your host operating system.

# FAQ

I am the only user of this software and - so far - I had no question more than once.
