import traceback

import sys


class protect:
    """
    Context Manager used to suppress errors and print traceback to stderr
    without halting program.
    Protects whatever that is within the context.

    Example::

        with protect():
            // protected code

    """
    def __init__(self, compact=False):
        self.compact = compact

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any((exc_type, exc_val, exc_tb)):
            if self.compact:
                print(exc_val, file=sys.stderr)
            else:
                print(f'Exception ingored and resuming execution of the remaining program:', file=sys.stderr)
                traceback.print_exc()
        return True


__all__ = ['protect']
