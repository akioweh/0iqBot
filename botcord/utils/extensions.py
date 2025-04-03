"""
Utility functions for managing bot extensions
"""

from collections.abc import Iterator
from importlib import import_module
from inspect import isfunction
from pkgutil import walk_packages
from types import ModuleType

__all__ = ['walk_extensions', 'resolve_extension_path', 'parent_package_path']


def walk_extensions(package: ModuleType) -> Iterator[str]:
    """
    Yields string namespaces of valid extensions within ``package``, to be imported separately

    An extension is a python module with some additional properties.

    A module is a valid extension if:
     - its (file) name does NOT start with ``_``
     - the module has a top-level function called ``setup``
     (which is automatically called when loading the extension with the Bot as the only parameter)
     - it is inside a package (a subpackage within the top package)
    """

    for module in walk_packages(package.__path__):
        if module.name.rpartition('.')[-1].startswith('_'):
            continue  # ignore private modules

        imported = import_module(module.name, package.__name__)
        if not isfunction(getattr(imported, 'setup', None)):
            continue  # ignore modules without a setup function

        yield module.name


def resolve_extension_path(module_name: str, in_package: ModuleType) -> str:
    """Returns the full path of a module relative to in_package, from a shortened name,
    such as that of just the module, without the parent packages.

    Checks to ensure everything exists and is valid.

    raises NameError if the name is too ambiguous to find only one
    specific module within in_package (two or more modules with the same name)

    raises ImportError if the name cannot be found or errors occur during imports"""

    matches = [
        module
        for module in walk_extensions(in_package)
        if module.endswith(module_name)
    ]

    if not matches:
        raise ImportError(f'No module named {module_name} found in {in_package.__name__}')

    if len(matches) > 1:
        raise NameError(f'Module name {module_name} is too ambiguous to find only one module in {in_package.__name__} '
                        f'({len(matches)} matches found: [{", ".join(matches)}])')

    return matches[0]


def parent_package_path(obj: ModuleType | str | type, root_package: ModuleType | str | None = None) -> str:
    """Determines the containing package of the given object,
    which should be a module, user-defined class, or a string representative of a module path.

    Note that string paths are not validated
    and are assumed to not be a package themselves.

    If given, ``root_package`` is removed as a prefix from the path.
    (And the path is checked to ensure it is a descendant of ``root_package``.)

    The result may be an empty string if the object is a top-level module
    or its parent is the root package itself.
    """

    if isinstance(obj, ModuleType):
        if obj.__spec__ is None:
            raise ValueError(f'Module object {obj}, {obj.__name__} does not have its __spec__ set; '
                             f'was it imported weirdly or is it the __main__ module?')
        if (parent_path := obj.__spec__.parent) is None:
            raise ValueError(f'Module object {obj}, {obj.__name__} does not have a parent; '
                             f'was it created dynamically?')
    else:
        if isinstance(obj, str):
            module_path = obj
        elif isinstance(obj, type):
            module_path = obj.__module__  # todo: don't think this is right as __module__ is just the file name?
        else:
            raise TypeError(f'Expected a ModuleType, str, or type for argument obj, '
                            f'but got {type(obj)}')
        parent_path = module_path.rpartition('.')[0]

    if root_package is not None:
        if isinstance(root_package, str):
            root_path = root_package
        elif isinstance(root_package, ModuleType):
            root_path = root_package.__name__
        else:
            raise TypeError(f'Expected a ModuleType or a valid string for argument root_package, '
                            f'but got {type(root_package)}')
        root_path += '.'
        if not parent_path.startswith(root_path):
            raise ValueError(f'Expected {parent_path} to start with {root_path}, but it does not.')

        parent_path = parent_path.removeprefix(root_path)

    return parent_path
