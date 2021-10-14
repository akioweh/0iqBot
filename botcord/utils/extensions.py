import importlib
import inspect
import pkgutil


def get_all_extensions_from(package):
    """"Only parameter should be reference to a package containing desired extensions"""

    def on_error(name):
        raise ImportError(name=name)

    for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}.", onerror=on_error):
        if module.name.rpartition('.')[-1].startswith("_"):
            continue

        imported = importlib.import_module(module.name)
        if not inspect.isfunction(getattr(imported, "setup", None)):
            continue

        yield module.name

# End
