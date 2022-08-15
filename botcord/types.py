"""Typing Definitions for BotCord."""

from os import PathLike
from typing import ParamSpec, Protocol, TypeAlias, TypeVar

__all__ = ['BasicValues', 'BasicTypes', 'ConfigDict', 'Param', 'T', 'StrOrPath', 'FileDescripor', 'SupportsWrite']

# Poggers recursive type annotations lmao
BasicValues: TypeAlias = str | int | float | bool | None
BasicTypes: TypeAlias = BasicValues | list['BasicTypes'] | tuple['BasicTypes']
# Forward reference union operator | is weird xD (https://github.com/python/cpython/issues/90015)
ConfigDict: TypeAlias = dict[str | int, 'BasicTypes | ConfigDict']

Param: ParamSpec = ParamSpec('Param')  # need to explicitly annotate as ParamSpec or type checker complains...
T: 'T' = TypeVar('T')

StrOrPath: TypeAlias = str | bytes | PathLike[str] | PathLike[bytes]
FileDescripor: TypeAlias = StrOrPath | int


class SupportsWrite(Protocol):  # couldn't find this in any builtin definitions
    def write(self, s: str, *args, **kwargs):
        ...
