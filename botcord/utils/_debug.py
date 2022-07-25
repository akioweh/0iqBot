# noinspection DuplicatedCode
from contextlib import suppress
from traceback import print_exception

from discord import Forbidden, HTTPException
from discord.ext.commands import (CheckFailure,
                                  CommandError,
                                  CommandNotFound,
                                  CommandOnCooldown,
                                  DisabledCommand,
                                  NoPrivateMessage,
                                  UserInputError)
from sys import stderr

from botcord import log


# noinspection DuplicatedCode
# noinspection PyUnusedLocal
async def on_command_error(context, exception: CommandError, *, fire_anyway=False):
    if context.command is None:
        log('WTF HOW IS context.command NONE?!', 'DEBUG')
    if not fire_anyway:  # Normally we don't do anything here if another handler catches the error
        if hasattr(context.command, 'on_error'):
            log(f'Skipping default error handling for {context.command.qualified_name}: it has its own error handler. '
                f'{type(exception)}: {exception}', tag='DEBUG')
            return
        cog = context.cog
        # hasattr check is to see if the cog error handler has been overridden with a custom method
        if cog and cog.has_error_handler():
            log(f'Skipping default error handling for {context.command.qualified_name}: its cog has an error handler. '
                f'{type(exception)}: {exception}', tag='DEBUG')
            return

    handled = False
    if isinstance(exception, (CommandNotFound, DisabledCommand, CheckFailure)):
        handled = True
    if isinstance(exception, NoPrivateMessage):
        await context.reply('This does not work in Direct Messages!', delete_after=10)
        handled = True
    if isinstance(exception, CommandOnCooldown):
        with suppress(Forbidden):
            await context.reply(f'Command is on cooldown. Please try again in {exception.retry_after} seconds.',
                                delete_after=10)
        handled = True
    if isinstance(exception, UserInputError):
        await context.reply('Invalid inputs.', delete_after=10)
        handled = True

    if handled:
        log(f'Ignoring trivial exception in command {context.command.qualified_name}: {type(exception)}: {exception}', tag='DEBUG')

    #  Additional logging for HTTP (networking) errors
    if isinstance(exception, HTTPException):
        log(f'An API Exception has occurred ({exception.code}): {exception.text}', tag='Error')
        context.reply(f'An API error occurred while executing the command. (API Error code: {exception.code})')

    if not handled:
        print(f'Ignoring exception in command {context.command}:', file=stderr)
        print_exception(type(exception), exception, exception.__traceback__, file=stderr)
