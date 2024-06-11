"""Typing Definitions for BotCord."""

from os import PathLike
from typing import ParamSpec, Protocol, TypeAlias, TypeVar, runtime_checkable

__all__ = ['BasicValues', 'BasicTypes', 'ConfigDict',
           'Param', 'T', 'T_contra',
           'StrOrPath', 'FileDescriptor', 'SupportsWrite']

# Poggers recursive type annotations lmao
BasicValues: TypeAlias = str | int | float | bool | None
BasicTypes: TypeAlias = BasicValues | list['BasicTypes'] | tuple['BasicTypes']
# Forward reference union operator | is weird xD (https://github.com/python/cpython/issues/90015)
ConfigDict: TypeAlias = dict[str | int, 'BasicTypes | ConfigDict']

Param: ParamSpec = ParamSpec('Param')  # need to explicitly annotate as ParamSpec or type checker complains...
T: 'T' = TypeVar('T')
T_contra: 'T_contra' = TypeVar('T_contra', contravariant=True)

StrOrPath: TypeAlias = str | bytes | PathLike[str] | PathLike[bytes]
FileDescriptor: TypeAlias = StrOrPath | int


@runtime_checkable
class SupportsWrite(Protocol[T_contra]):  # copied from typeshed
    def write(self, __s: T_contra) -> object:
        ...
