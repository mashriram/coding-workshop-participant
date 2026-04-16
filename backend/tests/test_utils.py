import importlib.util
import os

def load_module(service_name, module_name):
    # Get the file path
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", service_name, f"{module_name}.py"))
    spec = importlib.util.spec_from_file_location(f"{service_name}_{module_name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
