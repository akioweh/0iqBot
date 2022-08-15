"""Utility functions for managing bot extensions"""

from collections.abc import Generator
from importlib import import_module
from inspect import isfunction
from pkgutil import walk_packages
from types import ModuleType


def get_all_extensions_from(package: ModuleType) -> Generator[str, None, None]:
    """
    Only parameter should be reference to an imoprtlib package object containing desired extensions.
    Yields string namespaces of valid extensions within ``package``, to be imported separately

    An extension is a python module with some additional properties.

    A module is a valid extension if:
     - its (file) name does NOT start with ``_``
     - the module has a top-level function called ``setup``
     (which is automatically called when loading the extension with the Bot as the only parameter)
     - it is inside a package (a subpackage within the top package)
    """

    def on_error(name):
        raise ImportError(name=name)

    for module in walk_packages(package.__path__, package.__name__ + '.', onerror=on_error):
        if module.name.rpartition('.')[-1].startswith("_"):
            continue

        imported = import_module(module.name)
        if not isfunction(getattr(imported, 'setup', None)):
            continue

        yield module.name


__all__ = ['get_all_extensions_from']
