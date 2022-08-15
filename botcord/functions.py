"""All kinds of highly generic simple utility functions"""

from collections.abc import Generator
from datetime import datetime
from re import IGNORECASE, findall as _re_findall
from sys import stdout as __stdout__
from typing import Any, AnyStr, Iterable, Optional

from discord import Message

from .types import FileDescripor, SupportsWrite


def removeprefix(string: str, prefix: str | Iterable[str]) -> str:
    """Similar to ``str.removeprefix()`` in python 3.9,
    except it works for lower versions and can take a list of prefixes"""
    if isinstance(prefix, str):
        return string[(string.startswith(prefix) and len(prefix)):]
    elif isinstance(prefix, Iterable):
        for i in prefix:
            string = removeprefix(string, i)
        return string


def removesuffix(string: str, suffix: str | Iterable[str]) -> str:
    """Similar to ``str.removesuffix()`` in python 3.9,
    except it works for lower versions and can take a list of suffixes"""
    if isinstance(suffix, str):
        return string[:-len(suffix)] if string.endswith(suffix) else string
    elif isinstance(suffix, Iterable):
        for i in suffix:
            string = removesuffix(string, i)
        return string


def time_str() -> str:
    """returns a formatted string of the current time"""
    return datetime.now().strftime('%H:%M:%S')


def log(message: str, /, tag: str = 'Main', end: str = '\n', time: bool = True, *,
        file: SupportsWrite = __stdout__):
    """Logs messages to file (stdout by default).

    Format:
    ``[timestamp] [tag] message (ending)``

    :param str message: Message to write to file
    :param str tag: Tag to prefixed at the front of the message (while enclosed in "[]").
        Pass an empty string to disable.
    :param str end: string to append to the end of the output, defaults to newline (\n)
    :param bool time: Whether to prepend a local timestamp
    :param file: File-like object to write to, defaults to stdout
    """
    file.write((f'[{time_str()}] ' if time else '') +
               (f'[{tag}]: ' if tag else '') +
               f'{message}{end}')
    if hasattr(file, 'flush'):
        file.flush()


def to_int(obj: Any, *args, **kwargs) -> Optional[int]:
    """tries to cast an object to :class:`int` \n
    returns None if conversion fails"""
    try:
        return int(obj, *args, **kwargs)
    except (ValueError, TypeError):
        return None


def to_flt(obj: Any) -> Optional[float]:
    """tries to cast an object to :class:`float` \n
    returns None if conversion fails"""
    try:
        return float(obj)
    except (ValueError, TypeError):
        return None


def clean_return(string: str) -> str:
    """"cleans" a string's line returns \n
    ensures all linebreaks are ``\\n`` and strips away leading and trailing whitespaces"""
    return str(string).replace('\r\n', '\n').replace('\r', '\n').replace(' \n', '\n').strip()


def load_list(filepath: FileDescripor) -> list[str]:
    """loads a list of strings from a text file, items delimited by newlines"""
    with open(filepath, mode='r', encoding='utf-8') as file:
        return file.read().splitlines()


def save_list(filepath: FileDescripor, array: Iterable[AnyStr]):
    """saves a list of items as strings to a text file, delimited by newlines"""
    with open(filepath, mode='w', encoding='utf-8') as file:
        for item in array:
            file.write(clean_return(item).replace('\n', r'\n') + '\n')


def batch(msg: str, d: str = '\n', length: int = 2000, *, d2: str = ' ') -> Generator[str, None, None]:
    """
    "batches" a long string semi-intelligently into chunks no more than 2000 characters long \n
    useful to split a long essay into messages short enough to be sent over discord

    instead of chopping up between random words and characters, it tries to only split at linebreaks,
    or at least at word boundaries if a line is tooooo long \n
    if a word is too long, well then it will have to split it in the middle

    :param str msg: the entire long message
    :param str d: preferred separating character
    :param str d2: (keyword-only) secondary/backup separating character
    :param int length: maximum length of chunks, 2000 for standard discord, 4000 for discord nitro
    :return: (yields) a list of strings each under the length limit
    """
    splitted = [e + d for e in msg.split(d)]
    if splitted[-1] == d:
        splitted.pop()
    else:
        splitted[-1] = removesuffix(splitted[-1], d)

    cache = ''
    while splitted:
        if len(cache) + len(splitted[0]) <= length:
            cache += splitted.pop(0)
        elif cache:
            yield cache
            cache = ''
        else:  # if a split chunk is still larger than length
            long = splitted.pop(0)
            if d2 != '':  # try to split more aggressively using backup separator
                temp = list(batch(long, d2, length, d2=''))
            else:  # nothing more to do, just cut off between any character
                temp = list(long[i:i + length] for i in range(0, len(long), length))
            splitted = temp + splitted

    if cache:
        yield cache


def _contain_arg_helper(arg: Message | str, check: Iterable[str] | str, match_case: bool = False) -> [str,
                                                                                                      Iterable[str]]:
    items: Iterable[str] = [check] if isinstance(check, str) else check
    if isinstance(arg, Message):
        string = arg.content
    elif isinstance(arg, str):
        string = arg
    else:
        string = str(arg)
    if not match_case:
        string = string.lower()
        items = [i.lower() for i in items]
    return string, items


def contain_any(msg: Message | str, check: Iterable[str] | str, match_case: bool = False) -> bool:
    """
    Checks whether message contains [**any** of a list of strings / a string]

    if ``msg`` is :class:`discord.Message`, the message content as string is used

    :param Message | str msg: the main message to be checked for if it contains target substrings
    :param Iterable[str] | str check: a string or list of strings to check for containment inside msg
    :param bool match_case: whether to care about letter casing
    :return: result of check as a boolean
    :rtype: bool
    """
    string, items = _contain_arg_helper(msg, check, match_case)
    return any(str(i) in string for i in items)


def contain_all(msg: Message | str, check: Iterable[str] | str, match_case: bool = False) -> bool:
    """
    Checks whether message contains [**all** of a list of strings / a string]

    if ``msg`` is :class:`discord.Message`, the message content as string is used

    :param Message | str msg: the main message to be checked for if it contains target substrings
    :param Iterable[str] | str check: a string or list of strings to check for containment inside msg
    :param bool match_case: whether to care about letter casing
    :return: result of check as a boolean
    :rtype: bool
    """
    string, items = _contain_arg_helper(msg, check, match_case)
    return all(str(i) in string for i in items)


def contain_word(msg: Message | str, check: Iterable[str] | str, match_case: bool = False) -> bool:
    """
    Checks whether message contains [**any** of a list of words / a word]

    if ``msg`` is :class:`discord.Message`, the message content as string is used

    very similar to ``contain_any``, except it only matches a target when the ``check`` string
    is surrounded by whitespace in ``msg``

    :param Message | str msg: the main message to be checked for if it contains target substrings
    :param Iterable[str] | str check: a word or list of words to check for containment inside msg
    :param bool match_case: whether to care about letter casing
    :return: result of check as a boolean
    :rtype: bool
    """
    string, items = _contain_arg_helper(msg, check, match_case)
    return any(_re_findall(rf'\b{i}\b', string, 0 if match_case else IGNORECASE) for i in items)


def recursive_update(base: dict, extra: dict) -> None:
    """Recursively updates dictionary with extra data.

    **updates base IN PLACE**"""
    for k, v in extra.items():
        if k in base and isinstance(base[k], dict) and isinstance(extra[k], dict):
            recursive_update(base[k], extra[k])
        else:
            base[k] = extra[k]


__all__ = ['removesuffix', 'removeprefix', 'time_str', 'log', 'to_int', 'to_flt', 'clean_return', 'load_list',
           'save_list', 'batch', 'contain_any', 'contain_all', 'contain_word', 'recursive_update']
