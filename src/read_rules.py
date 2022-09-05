import importlib.machinery
import importlib.util

def read_rules(rules_file_path):
    module_name = 'user.rules'
    loader = importlib.machinery.SourceFileLoader(module_name, rules_file_path)
    spec = importlib.util.spec_from_loader(module_name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)

    return module.make_converter()
