import contextlib
import importlib.machinery
import importlib.util
import os
import sys

def read_rules(rules_path):
    module_name = 'rules.user'
    # We have to add the rules directory to the python path to allow for simple submodule imports in the rules module
    syspath = [rules_path] + sys.path
    with override_sys_path(syspath):
        spec = importlib.util.spec_from_file_location(module_name, os.path.join(rules_path, '__init__.py'), submodule_search_locations=[rules_path])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    return module.make_converter()


@contextlib.contextmanager
def override_sys_path(path):
    old_path = sys.path
    try:
        sys.path = path
        yield
    finally:
        sys.path = old_path