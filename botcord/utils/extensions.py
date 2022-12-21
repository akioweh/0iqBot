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


def full_extension_path(module_name: str, in_package: ModuleType) -> str:
    """Returns the full path of a module relative to in_package, from a shortened name,
    such as that of just the module, without the parent packages.

    Checks to ensure everything exists and is valid.

    raises NameError if the name is too ambiguous to find only one
    specific module within in_package (two or more modules with the same name)

    raises ImportError if the name cannot be found or errors occur during imports"""

    matches: list[str] = [module for module in get_all_extensions_from(in_package) if module.endswith(module_name)]

    if not matches:
        raise ImportError(f'No module named {module_name} found in {in_package.__name__}')

    if len(matches) > 1:
        raise NameError(f'Module name {module_name} is too ambiguous to find only one module in {in_package.__name__} '
                        f'({len(matches)} matches found: [{", ".join(matches)}])')

    return matches[0]


def parent_package_path(module: ModuleType | str | object, root_package: ModuleType | str = None) -> str:
    """Returns the path of the package containing the given module

    Assumes that the argument is the path to a module if it is in string form

    If root_package is given, the path will be relative to that package

    Does not check if the module is actually a module or if the
    alleged parent package actually exists"""
    parent_path = None

    # ModuleType object with a convenient __package__ attribute
    if getattr(module, '__package__', None) is not None:
        parent_path = module.__package__

    # Object that should have a __module__ attribute that we then parse as string
    elif getattr(module, '__module__', None) is not None:
        parent_path = module.__module__.rpartition('.')[0]

    # String that we parse as a module path
    elif isinstance(module, str):
        parent_path = module.rpartition('.')[0]

    if parent_path is None:
        raise TypeError(f'Expected a ModuleType, an object with __module__ attribute, or a valid string, '
                        f'but got {type(module)}')

    if root_package is not None:  # trimming the path before root_package, so it becomes "relative"
        if isinstance(root_package, ModuleType):
            root_path = module.__name__.rpartition('.')[2]
        elif isinstance(root_package, str):
            root_path = root_package
        else:
            raise TypeError(f'Expected a ModuleType or a valid string for argument root_package, '
                            f'but got {type(root_package)}')

        return parent_path.partition(root_path)[2].lstrip('.')
    else:
        return parent_path


__all__ = ['get_all_extensions_from', 'full_extension_path', 'parent_package_path']
