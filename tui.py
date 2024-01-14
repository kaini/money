import urwid, re, json, os
from thefuzz import process
from dataclasses import dataclass, asdict
from .rules.data import entry_id, Booking, BookingLine
from .utils import sanitize_description, format_exact

@dataclass
class TuiRule:
    rulenum: int

    id: int
    hash: str
    regex: str
    account: str

    dest_account: str

    def matches(self, entry):
        return (
            (not self.hash or entry_id(entry) == self.hash) and
            (not self.regex or re.search(self.regex, entry.text, re.IGNORECASE)) and
            (not self.account or entry.account == self.account)
        )

    def validate_or_raise(self):
        if self.regex is not None:
            re.compile(self.regex, re.IGNORECASE)

class SuggestionLine(urwid.WidgetWrap):
    def __init__(self):
        self._marker = urwid.Text("")
        self._text = urwid.Text("", wrap="ellipsis")
        self._score = urwid.Text("")
        self._layout = urwid.Columns([(2, urwid.AttrMap(self._marker, "em")), self._text, ("pack", self._score)])
        super().__init__(self._layout)
    
    def set_selected(self, selected):
        self._marker.set_text(">" if selected else "")

    def set_text(self, text, score=None):
        self._text.set_text(text)
        self._score.set_text("" if score is None else f"  ({int(score)})")

    def get_text(self):
        return self._text.get_text()[0]

class Suggestions(urwid.WidgetWrap):
    def __init__(self, suggest):
        self._suggest = suggest
        self._done = False

        self._input = urwid.Edit(wrap="clip")
        urwid.connect_signal(self._input, "postchange", self._on_change)

        self._lines = [SuggestionLine(), SuggestionLine(), SuggestionLine()]

        self._pile = urwid.Pile([urwid.AttrMap(self._input, "input"), *self._lines])
        super().__init__(self._pile)

        self._refresh_suggestions()
    
    def keypress(self, size, key):
        if key == "up" and not self._done:
            self.set_selected("up")
            return None
        elif key == "down" and not self._done:
            self.set_selected("down")
            return None
        elif key == "enter" and not self._done:
            if self.get_selected_suggestion():
                self._pile.contents = [(urwid.Text(self.get_selected_suggestion(), wrap="ellipsis"), ("weight", 1))]
                self._done = True
                urwid.emit_signal(self, "confirm")
            return None
        else:
            return super().keypress(size, key)

    def _on_change(self, widget, old_value):
        value = self._input.get_edit_text()
        if "=" in value and not value.startswith("="):
            self._input.set_edit_text("=")
        else:
            self._refresh_suggestions()

    def set_selected(self, i):
        if i == "up":
            self._selected = max(self._selected - 1, 0)
        elif i == "down":
            self._selected = min(self._selected + 1, len(self._lines) - 1)
        else:
            self._selected = i

        if self._lines[self._selected].get_text() == "":
            self._selected = 0
        
        for i, line in enumerate(self._lines):
            line.set_selected(i == self._selected)

    def get_selected_suggestion(self):
        return self._lines[self._selected].get_text()

    def reset(self):
        self._done = False
        self._pile.contents = [(urwid.AttrMap(self._input, "input"), ("weight", 1)), *((line, ("weight", 1)) for line in self._lines)]
        self._input.set_edit_text("")
        self._refresh_suggestions()

    def _refresh_suggestions(self):
        if self._input.get_edit_text().startswith("="):
            suggestions = [(self._input.get_edit_text()[1:], None)]
        else:
            suggestions = self._suggest(self._input.get_edit_text())
            if len(suggestions) > 3:
                suggestions = suggestions[:3]
        
        for i, line in enumerate(self._lines):
            if i < len(suggestions):
                suggestion = suggestions[i]
                line.set_text(suggestion[0], suggestion[1])
            else:
                line.set_text("")
        
        self.set_selected(0)

urwid.register_signal(Suggestions, ["confirm"])

class RuleWindow(urwid.WidgetWrap):
    def __init__(self):
        types = []
        
        self._type_single = urwid.RadioButton(types, "Apply to this entry only", state=True)
        urwid.connect_signal(self._type_single, "postchange", self._change)

        self._type_rule = urwid.RadioButton(types, "Create rule")
        urwid.connect_signal(self._type_rule, "postchange", self._change)
        urwid.connect_signal(self._type_rule, "postchange", self._focus_regex)
        self._regex = urwid.Edit(("default", "Regular expression: "))
        urwid.connect_signal(self._regex, "postchange", self._change)
        self._only_from_account = urwid.CheckBox("", state=True)
        urwid.connect_signal(self._only_from_account, "postchange", self._change)
        
        self._regex_widget = urwid.Padding(urwid.AttrMap(self._regex, "input"), left=2, right=2)
        self._settings_box = urwid.Pile([
            self._type_single,
            urwid.Text(""),
            self._type_rule,
            self._regex_widget,
            urwid.Padding(self._only_from_account, left=2, right=2)
        ], focus_item=self._type_rule)
                
        super().__init__(urwid.Filler(self._settings_box, valign="top"))

    def set_entry(self, entry):
        self._entry = entry
        self._only_from_account.set_label(f"Only from {entry.account}")
        self._type_single.set_state(True)
        self._regex.set_edit_text("")
        self._only_from_account.set_state(True)
        self._settings_box.focus = self._type_rule

    def get_rule(self):
        rule = TuiRule(
            rulenum=None,
            id=None,
            hash=entry_id(self._entry) if self._type_single.get_state() else None,
            regex=self._regex.get_edit_text() if self._type_rule.get_state() and self._regex.get_edit_text() else None,
            account=self._entry.account if self._type_rule.get_state() and self._only_from_account.get_state() else None,
            dest_account=None
        )
        try:
            rule.validate_or_raise()
            return rule
        except Exception as e:
            return "Error in rule expression: " + str(e)

    def _change(self, *args, **kwargs):
        urwid.emit_signal(self, "postchange", self.get_rule())

    def _focus_regex(self, widget, old_value):
        if self._type_rule.get_state():
            self._settings_box.focus = self._regex_widget

urwid.register_signal(RuleWindow, ["postchange"])

class BookingWindow(urwid.WidgetWrap):
    def __init__(self, format_args, suggest):
        self._format_args = format_args

        self._source_line = urwid.Text("", wrap="ellipsis")
        self._booking_header = urwid.Text("", wrap="ellipsis")

        self._source_account_text = urwid.Text("", wrap="ellipsis")
        self._source_account_amount = urwid.Text("")
        source_account = urwid.Columns([
            ("weight", 1, urwid.Padding(self._source_account_text, left=2, right=2)),
            ("pack", self._source_account_amount),
        ])

        self._dest_account = Suggestions(suggest)
        urwid.connect_signal(self._dest_account, "confirm", lambda: urwid.emit_signal(self, "confirm"))

        pile = urwid.Pile([
            self._source_line,
            urwid.Text(""),
            self._booking_header,
            source_account,
            urwid.Padding(self._dest_account, left=2, right=16),
        ])
        layout = urwid.Filler(pile, valign="top")
        super().__init__(layout)
    
    def set_entry(self, entry):
        self._source_line.set_text(f"From {entry.source}:")
        self._booking_header.set_text(f"{entry.date}  {sanitize_description(entry.text)}")
        self._source_account_text.set_text(entry.account)
        self._source_account_amount.set_text(format_exact(entry.amount, entry.currency, self._format_args))
        self._dest_account.reset()
    
    def get_selected(self):
        return self._dest_account.get_selected_suggestion()

urwid.register_signal(BookingWindow, ["confirm"])

class PreviewWindow(urwid.WidgetWrap):
    def __init__(self):
        self._list_walker = urwid.SimpleListWalker([])
        self._list_box = urwid.ListBox(self._list_walker)
        super().__init__(self._list_box)

    def refresh(self, unassigned, rule):
        self._list_walker.clear()
        if isinstance(rule, str):
            self._list_walker.append(urwid.Text(rule))
        else:
            self._list_walker.append(urwid.Text("--- first line ---", align="center", wrap="ellipsis"))
            for entry in unassigned:
                if rule.matches(entry):
                    self._list_walker.append(urwid.Text(f"{entry.date}  {sanitize_description(entry.text)}", wrap="ellipsis"))
            self._list_walker.append(urwid.Text("--- last line ---", align="center", wrap="ellipsis"))


class MainWindow(urwid.WidgetWrap):
    def __init__(self, format_args, unassigned, assigned, rules, extra_accounts):
        self._unassigned_original_len = len(unassigned)
        self._unassigned = list(sorted(unassigned, key=lambda e: e.date))

        self._accounts = set(extra_accounts)
        self._texts = dict()
        for entry, booking in sorted(assigned.items(), key=lambda i: i[0].date):
            for line in booking.lines:
                self._accounts.add(line.account)
                if entry.text not in self._texts and line.account != entry.account:
                    self._texts[entry.text] = line.account
        self._accounts = list(sorted(self._accounts))

        self._rules = rules

        self._progress_text = urwid.Text("", align="center")
        header = self._progress_text

        self._booking = BookingWindow(format_args, self._suggest)
        urwid.connect_signal(self._booking, "confirm", self._on_booking_confirm)

        self._rule = RuleWindow()
        urwid.connect_signal(self._rule, "postchange", self._on_rule_change)

        self._preview = PreviewWindow()

        self._booking_body = urwid.LineBox(self._booking, title="Booking", bline="", trcorner="┬")
        self._rule_body = urwid.LineBox(self._rule, title="Rule", tlcorner="├", trcorner="┤", brcorner="┴")
        preview_body = urwid.LineBox(self._preview, title="Preview", lline="", tlcorner="─", blcorner="─")

        self._left_pile = urwid.Pile([self._booking_body, self._rule_body])
        self._frame_body = urwid.Columns([self._left_pile, preview_body])

        self._shortcuts = urwid.Text([
            ("em", "UP"), "/", ("em", "DOWN"), "/", ("em", "ENTER"), " Select suggestion  ",
            ("em", "^X"), " Confirm entry  ",
            ("em", "^N"), " Skip entry  ",
            ("em", "^C"), " Save and quit",
        ], wrap="ellipsis");
        footer = self._shortcuts

        frame = urwid.Frame(self._frame_body, header=header, footer=footer)

        super().__init__(frame)

        self._jump_to_entry()
    
    def keypress(self, size, key):
        if key == "ctrl x":
            selected = self._booking.get_selected()
            if not selected:
                return None
            rule = self._rule.get_rule()
            if isinstance(rule, str):
                return None
            if not rule.matches(self._unassigned[0]):
                return None

            if selected not in self._accounts:
                self._accounts.append(selected)
                self._accounts.sort()
            self._texts[self._unassigned[0].text] = selected
            
            self._unassigned = [u for u in self._unassigned if not rule.matches(u)]

            rule.rulenum = (max(rule.rulenum for rule in self._rules) if self._rules else 0) + 1
            rule.dest_account = selected
            self._rules.append(rule)
            
            self._jump_to_entry()
        elif key == "ctrl n":
            self._unassigned = self._unassigned[1:]
            self._jump_to_entry()
        else:
            return super().keypress(size, key)

    def _jump_to_entry(self):
        if len(self._unassigned) == 0:
            raise urwid.ExitMainLoop()

        done = self._unassigned_original_len - len(self._unassigned)
        self._progress_text.set_text(f"TUI Rules {done + 1}/{self._unassigned_original_len} ({int(done / self._unassigned_original_len * 100)}%)")

        self._booking.set_entry(self._unassigned[0])
        self._rule.set_entry(self._unassigned[0])
        self._preview.refresh(self._unassigned, self._rule.get_rule())
        self._left_pile.focus = self._booking_body
        self._frame_body.set_focus(self._left_pile)
        self._w.focus_position = "body"
    
    def _on_booking_confirm(self):
        self._left_pile.focus = self._rule_body

    def _on_rule_change(self, rule):
        self._preview.refresh(self._unassigned, rule)

    def _suggest(self, value):
        if value == "":
            scores = list(process.extractWithoutOrder(self._unassigned[0].text, self._texts.keys()))
            scores.sort(key=lambda s: s[1], reverse=True)
            best = []
            for text, score in scores:
                if len(best) >= 3:
                    break
                account = self._texts[text]
                already_in_best = False
                for acc, _ in best:
                    if acc == account:
                        already_in_best = True
                        break
                if not already_in_best:
                    best.append((account, score))
            return best
        else:
            # Second part of the if is to avoid a thefuzz warning.
            if len(self._accounts) > 0 and len(process.default_processor(value)) > 0:
                return process.extract(value, self._accounts, limit=3)
            else:
                return []

def configure(*, format, rules_path, extra_accounts_path=None):
    """
    Returns a tuple of a converter and unassigned_handler. If you want to use custom rules
    as well, call the returned converter in your converter (at the end). Otherwise you can
    use the converter as an argument to money.main.

    extra_accounts_path is an optional path to a file where hledger account statements are
    parsed in order to pre-fill the suggested accounts. This is useful if you have no
    classified entries yet. A useful path is probably your main.journal file.
    """
    extra_accounts = []
    if extra_accounts_path:
        with open(extra_accounts_path, "r") as fp:
            for match in re.findall(r"^\s*account\s+([^;\r\n]*[^;\s]).*$", fp.read(), re.MULTILINE | re.IGNORECASE):
                extra_accounts.append(match)

    if os.path.exists(rules_path):
        with open(rules_path, "r", encoding="UTF-8") as fp:
            rules = [TuiRule(**rule) for rule in json.load(fp)]
    else:
        rules = []
        with open(rules_path, "w", encoding="UTF-8") as fp:
            json.dump(rules, fp)

    def unassigned_handler(unassigned, assigned):
        palette = [
            (None, "default", "default"),
            ("em", "default,bold", "default"),
            ("input", "default,bold,underline", "default"),
            ("focus", "default,standout", "default"),
        ]
        try:
            urwid.MainLoop(MainWindow(format, unassigned, assigned, rules, extra_accounts), palette=palette).run()
        except KeyboardInterrupt:
            pass

        with open(rules_path, "w", encoding="UTF-8") as fp:
            json.dump([asdict(rule) for rule in rules], fp, indent=2)

    def converter(entry):
        for rule in rules:
            if rule.matches(entry):
                lines = [
                    BookingLine(account=entry.account, amount=entry.amount, commodity=entry.currency),
                    BookingLine(account=rule.dest_account, amount=None, commodity=None),
                ]
                return Booking(date=entry.date, description=f"{sanitize_description(entry.text)} (rule #{rule.rulenum})", lines=lines)
        return None

    return converter, unassigned_handler
