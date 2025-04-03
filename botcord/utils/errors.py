import sys
import traceback
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Type

from botcord.types import SupportsWrite

__all__ = ['protect']


class protect(AbstractContextManager[None, bool]):
    """
    Context Manager used to suppress errors and print traceback/error message
    to stderr without propagating the errors (and halting the program).
    "Protects" whatever code that must execute after the context

    Similar to ``contextlib.suppress``, but prints information to stderr

    Example::

        with protect():
            # error prone code

        # protected code (always executes)

    """

    def __init__(
            self,
            *exceptions: Type[BaseException],
            compact: bool = False,
            name: str = '',
            stream: SupportsWrite[str] = sys.stderr
    ):
        """initializer with options

        :param exceptions: Variable number of exceptions to catch and protect from.
            If not specified, all exceptions are caught and protected
        :param compact: If true, prints shorter one-line error message without traceback
        :param name: A name that if given will be printed before the error message.
        :param stream: Stream to print error messages to.
            Default is ``sys.stderr``
        """
        self._exceptions = exceptions
        self._compact = compact
        self._name = name
        self._stream = stream

    def __enter__(self):
        pass

    def __exit__(
            self,
            exc_type: type | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None
    ) -> bool:
        if exc_type is not None:
            # if a specific list of exceptions is provided via the exceptions argument, only catch those
            if self._exceptions and not issubclass(exc_type, self._exceptions):
                return False
            # otherwise, protect from all exceptions.
            print(f'Exception ignored '
                  f'{f"at [{self._name}] " if self._name else ""}'
                  f'and resuming execution of the remaining program:',
                  file=self._stream)
            if self._compact:
                print(f'{exc_type.__name__}: {exc_val} \n', file=self._stream)
            else:
                print('', file=self._stream)  # extra space for readability
                traceback.print_exc(file=self._stream)
                print(f'(End of protect{f" [{self._name}] " if self._name else ""})', file=self._stream)
        return True
