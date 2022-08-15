import sys
import traceback
from typing import ContextManager, Type


class protect(ContextManager):
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

    def __init__(self, *exceptions: Type[BaseException], compact: bool = False):
        """initializer with options

        :param exceptions: Variable number of exceptions to catch and protect from.
            If not specified, all exceptions are caught and protected
        :param compact: If true, prints shorter one-line error message without traceback
        """
        self.exceptions = exceptions
        self.compact = compact

    def __enter__(self):
        pass

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None,
                 exc_tb: Type[traceback.TracebackException] | None) -> bool:
        if exc_type is not None:
            # do not protect is exceptions argument is specified and this exception is not in it
            if self.exceptions and not issubclass(exc_type, self.exceptions):
                return False
            # protect from this error, and print traceback/error message
            if self.compact:
                print(f'{exc_type.__name__}: {exc_val}', file=sys.stderr)
            else:
                print(f'Exception ignored and resuming execution of the remaining program:', file=sys.stderr)
                traceback.print_exc()
        return True


__all__ = ['protect']
