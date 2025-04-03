from asyncio import CancelledError, Future, Task, all_tasks, gather, get_event_loop, iscoroutinefunction, run
from collections.abc import Callable, Container, Coroutine
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from importlib import import_module, invalidate_caches
from logging import Formatter, Handler
from os import getcwd, getenv
from signal import SIGINT, SIG_IGN, signal
from sys import exc_info, platform as __platform__, stderr as __stderr__, stdout as __stdout__
from threading import Thread
from traceback import print_exception
from types import ModuleType, TracebackType
from typing import Any, Final, Optional, Sequence

from aiohttp import ClientSession
from discord import Activity, Forbidden, Guild, HTTPException, Intents, Invite, Message, NotFound, Status
from discord.abc import Messageable, Snowflake
from discord.ext import commands
from discord.ext.commands import GroupMixin
from discord.ext.commands.errors import (CheckFailure, CommandNotFound, CommandOnCooldown, DisabledCommand,
                                         NoPrivateMessage, UserInputError)
from discord.utils import MISSING

from .configs import ConfigDict, load_configs, new_guild_config, save_config, save_guild_config
from .errors import ExtensionDisabledGuild
from .ext.commands import Cog, Cog as _Cog
from .functions import *
from .help import HelpCommand
from .types import SupportsWrite
from .utils import TaskKeeper, protect
from .utils.extensions import parent_package_path, walk_extensions

__all__ = ['BotClient']

# Fix to stop aiohttp spamming errors in stderr when closing because that is uglier
if __platform__.startswith('win'):
    from asyncio import WindowsSelectorEventLoopPolicy, set_event_loop_policy

    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


# Subprocess Error handling stuff...
# ignore Keyboard Interrupts and let the main process handle them
def _subprocess_initializer():
    signal(SIGINT, SIG_IGN)
    if __platform__.startswith('win'):
        from signal import SIGBREAK

        signal(SIGBREAK, SIG_IGN)


# noinspection PyTypeChecker
class BotClient(commands.Bot):
    DEBUG: Final[bool]
    _async_init_ed: bool
    _connect_init_ed: bool
    _sync_shut: bool
    _async_shut: bool
    _running: bool
    thread: Thread | None
    _runner: Task | None
    latest_message: Message | None
    aiohttp_session: ClientSession | None
    task_keeper: TaskKeeper | None
    process_pool: ProcessPoolExecutor | None
    configs: ConfigDict  # type: Any # todo: more type gymnastics
    guild_configs: dict[int, ConfigDict]  # type: Any
    prefix: list[str]
    guild_prefixes: dict[int, str]
    cogs: dict[str, commands.Cog | _Cog]
    command_prefix: Callable[['BotClient', Message], Coroutine[Any, Any, list[str]]]  # type: ignore

    def __init__(self, **options) -> None:
        log('Performing Synchronous Initialization...', tag='INIT')

        # Flags
        self.DEBUG = getenv('DEBUG', 'false').lower() == 'true'
        self._async_init_ed = False
        self._connect_init_ed = False
        self._sync_shut = False
        self._async_shut = False
        self._running = False

        # Run-management stuff
        self.thread = None
        self._runner = None

        # Configuration stuff
        self.configs, self.guild_configs = load_configs()
        self.prefix = self.configs['bot']['prefix']
        self.guild_prefixes = {c['guild']['id']: c['bot']['prefix'] for c in self.guild_configs.values()}

        prefix_check = self.mentioned_or_in_prefix if self.configs['bot']['reply_to_mentions'] else self.in_prefix
        self._process_count = options.pop('multiprocessing', 0)

        # Init superclass with bot options
        self.__status = options.pop('status', None)
        self.__activity = options.pop('activity', None)
        # need suppression for now because the `command_prefix=prefix_check,` line
        # still triggers a false positive for the type checker
        # noinspection PyTypeChecker
        super().__init__(
            **options,
            activity=Activity(name='...Bot Initializing...', type=0),
            status=Status('offline'),
            command_prefix=prefix_check,
            help_command=HelpCommand(),
            max_messages=self.configs['bot']['message_cache'],
            intents=options.pop('intents', Intents.all())
        )

        # Additional utility stuff
        self.latest_message = None
        self.aiohttp_session = None
        self.task_keeper = None
        self.process_pool = None
        if self._process_count > 0:
            self.process_pool = ProcessPoolExecutor(max_workers=self._process_count,
                                                    initializer=_subprocess_initializer)

        # Extension stuff (actual loading had to be moved to async_init due to discord.py changes)
        self._ext_module = import_module(self.configs['bot']['extension_dir'], getcwd())
        self.ext_module_name = self._ext_module.__name__

        # Debug stuff
        if self.DEBUG:
            # noinspection PyProtectedMember
            from .utils._debug import on_command_error as debug_on_command_error
            self.on_command_error = debug_on_command_error  # type: ignore

        log('.......... Synchronous Initialization Finished', tag='INIT')

    async def setup_hook(self) -> None:
        pass

    async def __init_async__(self) -> bool:
        """Called after starting asyncio event loop.

        Used to initialize whatever that requires to run inside an event loop"""
        if self._async_init_ed:
            return False
        self._async_init_ed = True

        self.task_keeper = TaskKeeper(self.loop)
        self.task_keeper.start()

        # Load extensions
        log('Loading Extensions...', tag='Exts')
        await self.load_extensions_in(import_module('..builtins', self.__module__))  # loads builtin extensions
        n = await self.load_extensions_in(self._ext_module)  # loads custom extensions

        self.aiohttp_session = ClientSession(loop=self.loop)

        # call async initializers for any cogs that have them
        tasks = []
        corresponding_cogs = []  # for error handling
        for cog in self.cogs.values():
            if not hasattr(cog, '__init_async__'):
                continue
            if not iscoroutinefunction(cog.__init_async__):
                log(f'__init_async__ methods should be coroutine functions, '
                    f'but is {type(cog.__init_async__)} for cog {cog.__class__.__name__}', tag='Warn', file=__stderr__)
                continue
            tasks.append(cog.__init_async__())
            corresponding_cogs.append(cog)

        results = await gather(*tasks, return_exceptions=True)

        # print errors if any
        for result, cog in zip(results, corresponding_cogs):
            if isinstance(result, Exception):
                print(f'Ignoring exception while running __init_async__ for {cog.__class__.__name__}:', file=__stderr__)
                print_exception(type(result), result, result.__traceback__, file=__stderr__)

        log(f'Loaded {n} Extensions from [{self._ext_module.__name__}].', tag='Exts')

        log('.......... Asynchronous Initialization Finished.', tag='INIT')
        return True

    async def __init_connect__(self) -> bool:
        """
        Called after successful login and connection to Discord.
        (Can be called multiple times)

        Used to initialized whatever that require a fully established discord connection.
        """
        if self._connect_init_ed:
            return False
        self._connect_init_ed = True

        # Validate guild configs
        with protect(name='guild config validation'):
            await self.validate_guild_configs()
            self.save_guild_configs()

        # Set bot status to configured status (instead of offline during startup)
        await self.change_presence(activity=self.__activity, status=self.__status)

        log('Post-Connection Initialization Finished.', tag='Conn')
        return True

    def to_process[*Ts, T](self, func: Callable[[*Ts], T], *args: *Ts) -> Future[T]:
        """
        Converts a blocking/cpu-bound subroutine into an
        awaitable coroutine by running it in a process pool

        :param func: The function to run in a process pool
        :param args: The arguments to pass to func
        :return: A coroutine can be awaited to get the result of func(*args)
        """
        if self.process_pool is None:
            raise RuntimeError('No process pool was configured to initialize (pass non-zero process count to __init__'
                               'option with key "multiprocessing" to initialize a process pool)')
        return self.loop.run_in_executor(self.process_pool, func, *args)

    @property
    def ext_module(self) -> ModuleType:
        """**REimports** root extension package and returns it;
        runs synchronously..."""
        invalidate_caches()
        self._ext_module = import_module(self.configs['bot']['extension_dir'], getcwd())
        return self._ext_module

    async def load_extensions_in(self, package: ModuleType) -> int:
        """Load all valid extensions within a Python package.
        Recursively crawls through all subdirectories
        :return: the number of extensions loaded"""
        extensions = list(walk_extensions(package))
        results = await gather(*(self.load_extension(ext) for ext in extensions), return_exceptions=True)
        n = 0
        for result, ext in zip(results, extensions):
            if isinstance(result, Exception):
                print(f'Failed to load extension {ext}:', file=__stderr__)
                print_exception(type(result), result, result.__traceback__, file=__stderr__)
            else:
                n += 1

        return n

    @staticmethod
    async def blocked_check(ctx: commands.Context) -> bool:
        bot: 'BotClient' = ctx.bot
        if ctx.cog:
            cconf = getattr(ctx.cog, 'local_config', dict())
            cblocked = getattr(cconf, 'blocked_users', dict())
            if ctx.author.id in cblocked:
                return BotClient._blocked_check_helper(ctx, cblocked, scope='c')

        if ctx.guild:
            gconf = bot.guild_config(ctx.guild)
            gblocked = getattr(gconf, 'blocked_users', dict())
            if ctx.author.id in gblocked:
                return BotClient._blocked_check_helper(ctx, gblocked, scope='g')

        if 1:
            conf = bot.configs
            blocked = getattr(conf, 'blocked_users', dict())
            if ctx.author.id in blocked:
                return BotClient._blocked_check_helper(ctx, blocked, scope='a')

        return True

    @staticmethod
    def _blocked_check_helper(ctx: commands.Context, blocked_entries: Container[str], scope='a') -> bool:
        if scope not in ('a', 'g', 'c'):
            raise ValueError(f'Scope parameter must be either a, g, or c, not {scope}')

        if ctx.command is not None and ctx.command.name in blocked_entries:
            return False
        if any(i in blocked_entries for i in ctx.invoked_parents):
            return False
        if 'ALL' in blocked_entries:
            return False
        if scope in ('a', 'g') and ctx.cog is not None and ctx.cog.qualified_name in blocked_entries:
            return False
        if scope == 'a' and ctx.guild in blocked_entries:
            return False
        return True

    @staticmethod
    async def in_prefix(bot, message) -> list[str]:
        guild_id = getattr(message.guild, 'id', None)
        if (guild_id is not None) and (guild_id in bot.guild_prefixes):
            if bot.guild_prefixes[guild_id] and message.content.startswith(bot.guild_prefixes[guild_id]):
                return bot.guild_prefixes[guild_id]
        return bot.prefix

    @staticmethod
    async def mentioned_or_in_prefix(bot, message) -> list[str]:
        return commands.when_mentioned_or(*await BotClient.in_prefix(bot, message))(bot, message)

    async def logm(self, message: str, /, tag: str = 'Main', end: str = '\n', time: bool = True, *,
                   channel: Messageable | None = None, file: SupportsWrite[str] = __stdout__):
        """Logs a message to file and discord channel.

        same as functions.log but copies message to discord

        :param message: The message to log.
        :param tag: The tag to prefixed at the front of the message (while enclosed in "[]").
        :param end: The separator/ending character appended to the end of the message.
        :param time: Whether to prefix the message with the current time.
        :param channel: The discord channel to log to. If None, logs to channel of last received message.
        :param file: The file to log to. If None, logs to stdout.
        """
        log(message, tag, end, time, file=file)
        if channel is None:
            if self.latest_message is None:
                return
            channel = self.latest_message.channel
        with suppress(Forbidden, NotFound):
            await channel.send(message)

    async def on_ready(self):
        log(f"User Logged in as <{self.user}>", tag="Conn")
        await self.__init_connect__()

    async def on_connect(self):
        log(f"Discord Connection Established. <{self.user}>", tag="Conn")

    async def on_disconnect(self):
        log(f"Discord Connection Lost. <{self.user}>", tag="Conn")

    async def on_resume(self):
        log(f"Discord Connection Resumed. <{self.user}>", tag="Conn")

    async def on_message(self, message):
        self.latest_message = message
        self.dispatch('message_all', message)  # Custom event to trigger both on new messages and edits
        await super().on_message(message)

    async def on_message_edit(self, _, after):
        self.dispatch('message_all', after)  # Custom event to trigger both on new messages and edits

    async def on_member_update(self, before, after):
        # custom event dispatched when a Member has just completed membership verification/screening
        if before.pending and not after.pending:
            self.dispatch('verification_complete', after)

    async def on_error(self, event_method: str, /, *args, **kwargs):
        """Called when an event handler raises an exception.

        This method returns True if the exception was handled
        and None/False otherwise.
        (useful for cooperation between subclass methods)

        :param event_method: The name of the event that raised the exception (prefixed with "on_").
        :param args: The positional arguments (if any) that were passed to the event.
        :param kwargs: The keyword arguments (if any) that were passed to the event.
        """
        exc_type, exception, traceback = exc_info()

        if exc_type == ExtensionDisabledGuild:  # Can be raised outside a command, e.g. from an event listener
            return True

        print(f'Ignoring exception in event {event_method}:', file=__stderr__)
        print_exception(exc_type, exception, traceback)

    # noinspection DuplicatedCode
    # the "duplicated code" is from the debug version of this function which has extra logging
    # noinspection PyIncorrectDocstring
    async def on_command_error(self, context: commands.Context, exception: BaseException, *,
                               fire_anyway: bool = False):
        """Check discord.py docs for intended purpose and default behavior.

        This method returns True if the exception was handled
        and None/False otherwise.
        (useful for cooperation between subclass methods)

        :param fire_anyway: if False, will do nothing if another error handler should catch the error
            (a cog- or command- specific handler)
        """
        if not fire_anyway:  # Normally we don't do anything here if another handler catches the error
            if hasattr(context.command, 'on_error'):
                return True
            cog = context.cog
            # hasattr check is to see if the cog error handler has been overridden with a custom method
            if cog and cog.has_error_handler():
                return True

        handled = False
        if isinstance(exception, (CommandNotFound, DisabledCommand, CheckFailure,
                                  ExtensionDisabledGuild)) or (context.command is None):
            handled = True
        if isinstance(exception, NoPrivateMessage):
            with suppress(Forbidden):
                await context.reply('This does not work in Direct Messages!', delete_after=10)
            handled = True
        if isinstance(exception, CommandOnCooldown):
            with suppress(Forbidden):
                await context.reply(f'Command is on cooldown. Please try again in {exception.retry_after} seconds.',
                                    delete_after=10)
            handled = True
        if isinstance(exception, UserInputError):
            with suppress(Forbidden):
                await context.reply('Invalid inputs.', delete_after=10)
            handled = True

        #  Additional logging for HTTP (networking) errors
        if isinstance(exception, HTTPException):
            log(f'An API Exception has occurred ({exception.code}): {exception.text}', tag='Error')
            with suppress(Forbidden, NotFound):
                await context.reply(f'An API error occurred while executing the command. '
                                    f'(API Error code: {exception.code})')

        if handled:
            return True

        print(f'Ignoring exception in command {context.command}:', file=__stderr__)
        print_exception(type(exception), exception, exception.__traceback__, file=__stderr__)

    async def load_commands(self):
        pass

    async def does_trigger_command(self, message: Message) -> bool:
        """checks if the message starts with a valid prefix
        that *could* trigger a command on the bot"""
        return any(message.content.startswith(i) for i in await self.command_prefix(self, message))

    async def add_cog(
            self,
            cog: Cog,  # type: ignore
            /,
            *,
            override: bool = False,
            guild: Optional[Snowflake] = MISSING,
            guilds: Sequence[Snowflake] = MISSING,
    ) -> None:
        await super().add_cog(cog, override=override, guild=guild, guilds=guilds)

    async def validate_guild_configs(self) -> None:
        """
        "Validates" guild configs by updating any dynamic settings
        and ensuring proper format and required fields are present

        Automatically ran upon bot startup
        """
        guilds = self.guilds

        # ========== Basic Hard-Format Validation ========== #

        for guild in guilds:
            # ensure a config exists for each guild
            if guild.id not in self.guild_configs:
                self.guild_configs[guild.id] = self.create_guild_config(guild)
            # we actually don't need this here because the loading process does this
            # # ensure the config is properly formatted
            # else:
            #     temp_conf = default_guild()
            #     recursive_update(temp_conf, self.guild_configs[guild.id], allow_new=True)
            #     self.guild_configs[guild.id] = temp_conf  # recursive_update() updates the temp_conf in place

        # ========== Update Guild Invite Link ========== #

        # concurrently gather invites for speedups with multiple guilds
        tasks = [guild.invites() for guild in guilds]
        guild_invites: list[list[Invite] | BaseException] = await gather(*tasks, return_exceptions=True)

        for guild, invites in zip(guilds, guild_invites):
            self.guild_configs[guild.id]['guild']['name'] = guild.name
            i0 = invites
            if isinstance(i0, BaseException):
                if isinstance(i0, Forbidden):  # bot doesn't have permission to view invites
                    self.guild_configs[guild.id]['guild']['invite'] = None
                else:  # something went horribly wrong
                    raise i0
            elif i0:
                invite = i0[0]
                if i1 := [i for i in i0 if not i.revoked]:
                    invite = i1[0]
                    if i2 := [i for i in i1 if not (i.max_age and i.max_uses)]:
                        invite = i2[0]
                        if i3 := [i for i in i1 if not (i.max_age or i.max_uses)]:
                            invite = i3[0]
                            if i4 := [i for i in i2 if not i.temporary]:
                                invite = i4[0]
                                if i5 := [i for i in i3 if not i.temporary]:
                                    invite = i5[0]

                self.guild_configs[guild.id]['guild']['invite'] = invite.url

            else:
                self.guild_configs[guild.id]['guild']['invite'] = None

        # ========== Create Config Field for each Extension ========== #

        for guild in guilds:
            for ext_name, ext in self.extensions.items():
                ext_key = parent_package_path(ext, self.ext_module_name)
                if not ext_key:  # extensions not in the standard extension directory will have an empty key
                    continue
                if ext_key not in self.guild_configs[guild.id]['ext']:
                    self.guild_configs[guild.id]['ext'][ext_key] = {'enabled': False}  # default to disabled

        # # saves any changes made to file
        # self.save_guild_configs()

    def guild_config(self, guild: Guild | int) -> dict:
        """Returns the guild config for the given guild."""
        if isinstance(guild, Guild):
            guild = guild.id
        if guild in self.guild_configs:
            return self.guild_configs[guild]
        raise FileNotFoundError(f'No Guild configs for{guild} found.')

    def ext_guild_config(self, ext: str | ModuleType, guild: Guild) -> dict:
        """
        Get the per-guild config for an extension.

        :param ext: The extension module or name as a string
        :param guild: The guild to get the config for
        """
        if guild.id in self.guild_configs:
            config = self.guild_configs[guild.id]
            if isinstance(ext, ModuleType):
                ext = parent_package_path(ext, self.ext_module_name)

            if ext in config['ext']:
                return config['ext'][ext]

        raise FileNotFoundError(f'No Extension configs for guild {guild} found.')

    def create_guild_config(self, guild: Guild):
        """Creates a guild config for the given guild."""
        if guild.id in self.guild_configs:
            raise FileExistsError(f'There already exists a config for guild {guild.id}')
        return new_guild_config(guild.id)

    def save_guild_configs(self):
        """Saves (all) guild configs to file."""
        for guild_id, config in self.guild_configs.items():
            save_guild_config(config, guild_id)

    async def unload_extensions(self) -> int:
        """Unloads **ALL** loaded extensions & cogs
        returns number of extensions unloaded"""
        n = len(self.extensions)
        for extension in tuple(self.extensions.keys()):
            with protect(name='extension unloading: unload_extension'):
                await self.unload_extension(extension)

        n += len(self.cogs)
        for cog in tuple(self.cogs.keys()):
            with protect(name='extension unloading: remove_cog'):
                await self.remove_cog(cog)

        return n

    async def __close_connect__(self):
        """Called before connection to Discord is closed.
        Do Not Directly Call"""
        with suppress(AttributeError):
            # This can be raised when the bot is shut down without an established websocket (discord connection)
            # I.e. when the bot is requested to shut down without fully initializing.
            await self.change_presence(status=Status('offline'))

    async def __shutdown_async__(self):
        """Called before the asyncio event loop halts.
        Do Not Directly Call"""
        if self._async_shut:
            log('__shutdown_async__() called more than once', tag='Warning')
            return
        self._async_shut = True

        # Unload all extensions
        log('Unloading extensions...', tag='SHDN')
        with protect(name='extension unloading'):
            n = await self.unload_extensions()
            log(f'Unloaded {n} Extensions & Cogs.', tag='Exts')

        if self.task_keeper:
            self.task_keeper.stop()
        if self.aiohttp_session:
            await self.aiohttp_session.close()

        log('.......... Asynchronous Shutdown Finished.', tag='SHDN')

    def __shutdown_sync__(self):
        """Called before the blocking run() exits
        Do Not Directly Call"""
        if self._sync_shut:
            log('__shutdown_sync__() called more than once.', tag='Warning')
            return
        self._sync_shut = True

        log('Saving Configs...', tag='SHDN')
        with protect(name='shutdown global config saving'):
            save_config(self.configs)
        with protect(name='shutdown guild configs saving'):
            self.save_guild_configs()
        log('...... Configs Saved.', tag='SHDN')

        if self.process_pool is not None:
            self.process_pool.shutdown(wait=True, cancel_futures=True)

        log('.......... Synchronous Shutdown Finished.', tag='SHDN')

    def clear(self):
        """Resets all flags, clears all caches,
        and resets all states of the bot...
        hopefully, without missing anything"""
        self._async_init_ed = False
        self._connect_init_ed = False
        self._sync_shut = False
        self._async_shut = False
        self._running = False
        self._runner = None
        self.aiohttp_session = None
        self.task_keeper = None

        # the process pool and extensions have to be reinitialized because they get shut down/unloaded
        # and is only initialized in __init__, which we do not call again (obviously)
        # todo: move these to a better place
        if self._process_count > 0:
            self.process_pool = ProcessPoolExecutor(max_workers=self._process_count,
                                                    initializer=_subprocess_initializer)
        self.load_extensions_in(self._ext_module)

        # noinspection PyAttributeOutsideInit
        self._closed = False
        self._ready.clear()
        self._connection.clear()

    async def __aenter__(self):
        log('Performing Asynchronous Initialization...', tag='INIT')

        await self._async_setup_hook()
        with protect(name='async init'):
            await self.__init_async__()

        return self

    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
    ):
        if exc_type == CancelledError:
            log('Received Termination Signal (Task Cancellation).', tag='Runr')
        elif exc_type in (KeyboardInterrupt, SystemExit):
            log('Received Termination Signal (KeyboardInterrupt/SystemExit)', tag='Runr')
        elif exc_type is not None:
            print(f'Critical Exception occurred in Runner: {exc_type.__name__}: {exc_value}', file=__stderr__)
            print_exception(exc_type, exc_value, traceback)
        else:
            raise RuntimeError('Impossible. Unexpected __aexit__ call')

        log('Performing Asynchronous Shutdown...', tag='SHDN')

        if not self.is_closed():
            with protect(name='connection closing'):
                await self.__close_connect__()
            await super(GroupMixin, self).close()
            log('Discord Connection Closed.', tag='Conn')

        with protect(name='async shutdown'):
            await self.__shutdown_async__()

    def run(
            self,
            token: str,
            *,
            reconnect: bool = True,
            log_handler: Handler | None = MISSING,
            log_formatter: Formatter = MISSING,
            log_level: int = MISSING,
            root_logger: bool = False
    ):
        """Starts and runs the bot.

        -> Starts asyncio event loop

        -> Establishes connection with Discord and logs in

        -> (When stop signal detected)
        Closes connection with Discord

        -> Stops asyncio event loop

        Blocks for as long as the bot is running & not fully shut-down.
        Stop using KeyboardInterrupt.
        """
        if self._running:
            raise RuntimeError('Bot is already running.')
        self._running = True

        async def _runner():
            log('Asynchronous Runner Started...', tag='Runr')
            async with self:
                self._runner = get_event_loop().create_task(self.start(token, reconnect=reconnect))
                await self._runner  # main "blocking" entry point

        with protect(name='runner wrapper'):
            with suppress(KeyboardInterrupt, SystemExit, CancelledError):
                run(_runner())
        log('Asynchronous Runner Exited.', tag='Runr')

        log('Performing Synchronous Shutdown...', tag='SHDN')
        with protect(name='sync shutdown'):
            self.__shutdown_sync__()

    def run_threaded(self, token: str, *, reconnect: bool = True):
        """Starts and runs the bot,
        in a separate thread.

        Non-blocking. Stop bot with stop_threaded()"""
        if self.thread:
            raise RuntimeError('Bot is already running in a thread.')
        if self._running:
            raise RuntimeError('Bot is already running.')

        self.thread = Thread(target=self.run, name='Runner', args=(token,), kwargs={'reconnect': reconnect})
        self.thread.start()
        log('Bot started in a separate thread.', tag='MAIN')

    def stop_threaded(self):
        """Complete closure and shutdown of the bot,
        by signaling for run() to stop gracefully.

        Can be manually called to stop run_threaded()"""
        if not self.thread:
            raise RuntimeError('Tried to stop threaded running not but there are no threads.')

        if self._runner is None:  # not fully initialized yet
            log('Stopping Bot (During Init) in Runner Thread...', tag='MAIN')
            with protect(name='stop threaded force loop.stop() call'):
                self.loop.stop()
                for task in all_tasks(self.loop):
                    with suppress(CancelledError):
                        task.cancel()

        else:  # normal shutdown
            log('Stopping Bot in Runner Thread...', tag='MAIN')
            with protect(name='stop threaded runner.cancel() call'):
                self.loop.call_soon_threadsafe(self._runner.cancel, ())  # empty args because type checker dumb

        self.thread.join()
        log('........ Bot in Runner Thread Stopped.', tag='MAIN')
        self.thread = None
