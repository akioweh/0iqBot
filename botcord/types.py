"""Typing Definitions for BotCord."""

from typing import ParamSpec, Protocol, TypeAlias, TypeVar

__all__ = ['SupportsWrite', 'ConfigDict', 'BasicTypes', 'BasicValues', 'Param', 'T']

# Poggers recursive type annotations lmao
BasicValues: TypeAlias = str | int | float | bool | None
BasicTypes: TypeAlias = BasicValues | list['BasicTypes'] | tuple['BasicTypes']
# Forward reference union operator | is weird xD (https://github.com/python/cpython/issues/90015)
ConfigDict: TypeAlias = dict[str | int, 'BasicTypes | ConfigDict']

Param: ParamSpec = ParamSpec('Param')  # need to explicitly annotate as ParamSpec or type checker complains...
T: 'T' = TypeVar('T')


class SupportsWrite(Protocol):
    def write(self, s: str, *args, **kwargs):
        ...
