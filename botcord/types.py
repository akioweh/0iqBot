"""Typing Definitions for BotCord."""

from os import PathLike
from typing import Protocol, Union, runtime_checkable

__all__ = ['BasicTypes', 'ValueTypes', 'ConfigDict',
           'StrOrPath', 'FileDescriptor', 'SupportsWrite']

type BasicTypes = str | int | float | bool | None
type ValueTypes = BasicTypes | list[ValueTypes] | tuple[ValueTypes]
type ConfigDict = dict[str | int, Union[ValueTypes, ConfigDict]]

type StrOrPath = str | bytes | PathLike[str] | PathLike[bytes]
type FileDescriptor = StrOrPath | int


@runtime_checkable
class SupportsWrite[T](Protocol):  # copied-ish from typeshed
    def write(self, __s: T) -> object:
        ...
