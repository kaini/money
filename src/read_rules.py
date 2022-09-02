import utils
import importlib.machinery
import importlib.util
import sys

def read_rules(rules_file_path):
    module_name = 'user.rules'
    loader = importlib.machinery.SourceFileLoader(module_name, rules_file_path)
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    return module.make_converter()


#def parse_rules(base_path, format_args):
#    rules = configparser.ConfigParser(delimiters=("=",))
#    rules.read(os.path.join(base_path, "rules.ini"), encoding="UTF-8")
#
#    result = []
#    for rule, account in rules["DEFAULT"].items():
#        parts = rule.split("$")
#        if parts[0] == "text":
#            result.append((lambda entry, regex=re.compile(parts[1], re.I | re.M | re.DOTALL): bool(regex.search(entry.text)), account))
#        else:
#            raise Exception("Unknown rule syntax " + rule)
#
#    def fallback(entry):
#        print(f"Warning: Had to apply fallback rule to entry: {utils.namedtuple_pformat(entry, format_args)}")
#        return True
#    result.append((fallback, "Unbekannt"))
#
#    return result

#                    # The rule could be a compound rule (using the + operator)
#                    destination = []
#                    for component in rule[1].split("+"):
#                        component = component.strip()
#                        parts = component.split("=")
#                        if len(parts) == 1:
#                            destination.append((parts[0].strip(), None, None))
#                        else:
#                            destination.append((parts[0].strip(), utils.parse_num_str(parts[1], format_args.decimal_separator), entry.currency))