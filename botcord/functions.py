"""
All kinds of highly generic simple utility functions
"""

import re
from collections.abc import Generator, Mapping, MutableMapping
from datetime import datetime
from sys import stdout as __stdout__
from typing import Any, Iterable, Optional

from discord import Message

from .types import FileDescriptor, SupportsWrite

__all__ = ['time_str', 'log', 'to_int', 'to_flt', 'clean_return', 'load_list',
           'save_list', 'batch', 'contain_any', 'contain_all', 'contain_word', 'recursive_update', 'smart_time_s']


def time_str() -> str:
    """returns a formatted string of the current time"""
    return datetime.now().strftime('%H:%M:%S')


def log(message: str, /, tag: str = 'Main', end: str = '\n', time: bool = True, *,
        file: SupportsWrite[str] = __stdout__):
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


def load_list(filepath: FileDescriptor) -> list[str]:
    """loads a list of strings from a text file, items delimited by newlines"""
    with open(filepath, mode='r', encoding='utf-8') as file:
        return file.read().splitlines()


def save_list(filepath: FileDescriptor, array: Iterable[str]):
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
        splitted[-1] = splitted[-1].removesuffix(d)

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


def _contain_arg_helper(
        arg: Message | str, check: Iterable[str] | str, match_case: bool = False
) -> tuple[str, Iterable[str]]:
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
    return any(re.findall(rf'\b{i}\b', string, 0 if match_case else re.IGNORECASE) for i in items)


def recursive_update(base: MutableMapping, extra: Mapping, type_safe: bool = True, allow_new: bool = False) -> None:
    """Recursively updates base dictionary with extra data.

    **updates** ``base`` **IN PLACE**

    :param base: base dictionary to be updated
    :param extra: dictionary similar to ``base``, but with extra data
    :param type_safe: if True (default), will raise TypeError if a key in ``base`` and extra have different types.
    None values in ``base`` are allowed to be overwritten by any type.
    :param allow_new: if True, will allow new keys in extra to be added to ``base``. Default is False.
    """
    if not isinstance(base, MutableMapping):
        raise TypeError(f'base must be a MutableMapping, not {type(base).__name__}')
    if not isinstance(extra, Mapping):
        raise TypeError(f'extra must be a Mapping, not {type(extra).__name__}')

    for k, v_e in extra.items():
        if k in base:  # update key value
            v_b = base[k]
            t_b = type(v_b)
            t_e = type(v_e)

            if k in base and issubclass(t_b, Mapping) and issubclass(t_e, Mapping):  # if both are dicts, recurse
                recursive_update(v_b, v_e, type_safe, allow_new)
            else:  # otherwise, overwrite value
                if type_safe and v_b is not None and not (t_b == t_e or issubclass(t_e, t_b)):  # type mismatch
                    raise TypeError(f'Type mismatch while merging dicts: {t_b} != {t_e} at key "{k}"')
                base[k] = v_e

        else:  # create new key
            if not allow_new:
                raise KeyError(f'Key "{k}" not found in base dict')
            base[k] = v_e


def smart_time_s(seconds: int | float) -> str:
    """Formats time in seconds into a succinct word-based string.

    Formatting, if time is...:
        - =1 -> "1 second"
        - <60 -> "x seconds"
        - =60 -> "1 minute"
        - 60x -> "x minutes"
        - 60x + 1 -> "x minutes and 1 second"
        - 60x + y -> "x minutes and y seconds"

    If time is >= 3600, will also include hours.
    If time is >= 86400, will also include days.
    If time is >= 31556952, will also include years.
    If time is >= 31556952000, will also include centuries.

    If time is a ``float``, will include milliseconds (even if it is a whole number).
    """

    # break down the time into its components
    if isinstance(seconds, float):
        seconds = round(seconds, 3)  # round to the nearest millisecond
        ms = round(seconds * 1000 % 1000)
        seconds = int(seconds)
    else:
        ms = None
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365)
    centuries, years = divmod(years, 100)

    # build string
    output = ''
    if centuries:
        output += f'{centuries} {"century" if centuries == 1 else "centuries"}, '
    if years:
        output += f'{years} year{"" if years == 1 else "s"}, '
    if days:
        output += f'{days} day{"" if days == 1 else "s"}, '

    if hours:
        output += f'{hours} hour{"" if hours == 1 else "s"} '
    if minutes or (hours and ms is not None):
        output += f'{minutes} minute{"" if minutes == 1 else "s"} '
    if seconds or not output or ('minute' in output and ms is not None):
        output += f'{seconds} second{"" if seconds == 1 else "s"} '
    if ms is not None:
        output += f'{ms} millisecond{"" if ms == 1 else "s"} '

    # remove trailing comma and space
    output = output.rstrip(', ').strip()

    # add 'and' if long output
    if len(re.findall(r'\d+', output)) > 3:
        output = re.sub(r'(\d+)(\s\w+)$', r'and \1\2', output)

    return output
