from asyncio import CancelledError, Task, TimeoutError, all_tasks, gather, iscoroutinefunction, wait_for
from collections.abc import Coroutine
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from importlib import import_module
from os import getcwd, getenv
from signal import SIGINT, SIGTERM, SIG_IGN, signal
from sys import exc_info, platform as __platform__, stderr as __stderr__, stdout as __stdout__
from traceback import print_exception
from types import ModuleType
from typing import Callable, Final, Optional

from aiohttp import ClientSession
from discord import Activity, Forbidden, Guild, HTTPException, Intents, Invite, Message, NotFound, Status, TextChannel
from discord.ext import commands
from discord.ext.commands.errors import (CheckFailure, CommandNotFound, CommandOnCooldown, DisabledCommand,
                                         NoPrivateMessage, UserInputError)

from .configs import ConfigDict, default_guild, load_configs, new_guild_config, save_config, save_guild_config
from .errors import ExtensionDisabledGuild
from .functions import *
from .types import Param, SupportsWrite, T
from .utils.errors import protect
from .utils.extensions import get_all_extensions_from

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


class BotClient(commands.Bot):
    _connect_init_ed: bool
    _async_init_ed: bool
    latest_message: Optional[Message]
    aiohttp_session: Optional[ClientSession]
    process_pool: Optional[ProcessPoolExecutor]
    configs: ConfigDict
    guild_configs: dict[int, ConfigDict]
    prefix: list[str]
    guild_prefixes: dict[int, str]

    def __init__(self, **options):
        # Flags
        self.DEBUG: Final = getenv('DEBUG', 'false').lower() == 'true'
        self._async_init_ed = False
        self._connect_init_ed = False

        # Configuration stuff
        self.configs, self.guild_configs = load_configs()
        self.prefix = self.configs['bot']['prefix']
        self.guild_prefixes = {c['guild']['id']: c['bot']['prefix'] for c in self.guild_configs.values()}

        prefix_check = self.mentioned_or_in_prefix \
            if self.configs['bot']['reply_to_mentions'] else self.in_prefix
        process_count = options.pop('multiprocessing', 0)

        # Init superclass with bot options
        self.__status = options.pop('status', None)
        self.__activity = options.pop('activity', None)
        super().__init__(**options,
                         activity=Activity(name='...Bot Initializing...', type=0),
                         status=Status('offline'),
                         command_prefix=prefix_check,
                         max_messages=self.configs['bot']['message_cache'],
                         intents=Intents.all())

        # Additional utility stuff
        self.latest_message = None
        self.aiohttp_session = None
        self.process_pool = None
        if process_count != 0:
            self.process_pool = ProcessPoolExecutor(max_workers=process_count, initializer=_subprocess_initializer)

        # Extension stuff
        exts = import_module(self.configs['bot']['extension_dir'], getcwd())
        self.load_extensions(exts)

        # Debug stuff
        if self.DEBUG:
            # noinspection PyProtectedMember
            from .utils._debug import on_command_error as debug_on_command_error
            self.on_command_error = debug_on_command_error

        log('Synchronous Initialization Finished', tag='Init')

    async def __init_async__(self) -> bool:
        """Called after starting asyncio event loop.

        Used to initialize whatever that requires to run inside an event loop"""
        if self._async_init_ed:
            return False
        self._async_init_ed = True

        self.aiohttp_session = ClientSession(loop=self.loop)

        # call async initializers for any cogs that have them
        tasks = []
        for cog in self.cogs.values():
            if not hasattr(cog, '__init_async__'):
                continue
            if not iscoroutinefunction(cog.__init_async__):
                log(f'__init_async__ methods should be coroutine functions, '
                    f'but is {type(cog.__init_async__)} for cog {cog.__class__.__name__}', tag='Warn', file=__stderr__)
                continue
            tasks.append(cog.__init_async__())

        await gather(*tasks)

        log('Asynchronous Initialization Finished', tag='Init')
        return True

    async def __init_connect__(self) -> bool:
        """Called after successful connection and login to Discord.

        Used to initialized whatever that require a fully established discord connection.

        (Can be called multiple times)"""
        if self._connect_init_ed:
            return False
        self._connect_init_ed = True

        # Validate guild configs
        with protect():
            await self.validate_guild_configs()
            self.save_guild_configs()

        # Set bot status to configured status (instead of offline during startup)
        await self.change_presence(activity=self.__activity, status=self.__status)

        log('Post-Connection Initialization Finished', tag='Connection')
        return True

    def to_process(self, func: Callable[Param, T], *args) -> Coroutine[None, Param, T]:
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

    def load_extensions(self, package: ModuleType):
        """Load all valid extensions within a Python package.
        Recursively crawls through all subdirectories"""
        extensions = get_all_extensions_from(package)
        for extension in extensions:
            self.load_extension(extension)

    @staticmethod
    async def blocked_check(ctx: commands.Context):
        if ctx.cog:
            cconf = getattr('config', ctx.cog, dict())
            cblocked = getattr(cconf, 'blocked_users', dict())
            if ctx.author.id in cblocked:
                return BotClient._blocked_check_helper(ctx, cblocked, scope='c')

        if ctx.guild:
            bot: 'BotClient' = ctx.bot
            gconf = bot.guild_config(ctx.guild)
            gblocked = getattr(gconf, 'blocked_users', dict())
            if ctx.author.id in gblocked:
                return BotClient._blocked_check_helper(ctx, gblocked, scope='g')

        if 1:
            bot: 'BotClient' = ctx.bot
            conf = bot.configs
            blocked = getattr(conf, 'blocked_users', dict())
            if ctx.author.id in conf['blocked_users']:
                return BotClient._blocked_check_helper(ctx, blocked, scope='a')

        return True

    @staticmethod
    def _blocked_check_helper(ctx: commands.Context, blocked_entries: list, scope='a'):
        if scope not in ('a', 'g', 'c'):
            raise ValueError(f'Scope parameter must be either a, g, or c, not {scope}')
        if ctx.command.name in blocked_entries:
            return False
        if any(i.name in blocked_entries for i in ctx.invoked_parents):
            return False
        if 'ALL' in blocked_entries:
            return False
        if scope in ('a', 'g') and ctx.cog.qualified_name in blocked_entries:
            return False
        if scope == 'a' and ctx.guild in blocked_entries:
            return False
        return True

    @staticmethod
    async def in_prefix(bot, message):
        guild_id = getattr(message.guild, 'id', None)
        if (guild_id is not None) and (guild_id in bot.guild_prefixes):
            if bot.guild_prefixes[guild_id] and message.content.startswith(bot.guild_prefixes[guild_id]):
                return bot.guild_prefixes[guild_id]
        return bot.prefix

    @staticmethod
    async def mentioned_or_in_prefix(bot, message):
        return commands.when_mentioned_or(*await BotClient.in_prefix(bot, message))(bot, message)

    async def logm(self, message: str, /, tag: str = 'Main', end: str = '\n', time: bool = True, *,
                   channel: Optional[TextChannel] = None, file: SupportsWrite = __stdout__):
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
        if channel is None and self.latest_message is None:
            return
        channel = channel or self.latest_message.channel
        with suppress(Forbidden, NotFound):
            await channel.send(message)

    async def on_ready(self):
        log(f"User Logged in as <{self.user}>", tag="Connection")
        await self.__init_connect__()

    async def on_connect(self):
        log(f"Discord Connection Established. <{self.user}>", tag="Connection")

    async def on_disconnect(self):
        log(f"Discord Connection Lost. <{self.user}>", tag="Connection")

    async def on_resume(self):
        log(f"Discord Connection Resumed. <{self.user}>", tag="Connection")

    async def on_typing(self, channel, user, when):
        pass

    async def on_message(self, message):
        self.latest_message = message
        self.dispatch('message_all', message)  # Custom event to trigger both on new messages and edits
        await super().on_message(message)

    async def on_message_delete(self, message):
        pass

    async def on_message_edit(self, _, after):
        self.dispatch('message_all', after)  # Custom event to trigger both on new messages and edits

    async def on_reaction_add(self, reaction, user):
        pass

    async def on_reaction_remove(self, reaction, user):
        pass

    async def on_reaction_clear(self, message, reactions):
        pass

    async def on_reaction_clear_emoji(self, reaction):
        pass

    async def on_private_channel_create(self, channel):
        pass

    async def on_private_channel_delete(self, channel):
        pass

    async def on_private_channel_update(self, before, after):
        pass

    async def on_private_channel_pins_update(self, channel, last_pin):
        pass

    async def on_guild_channel_create(self, channel):
        pass

    async def on_guild_channel_delete(self, channel):
        pass

    async def on_guild_channel_update(self, before, after):
        pass

    async def on_guild_channel_pins_update(self, channel, last_ping):
        pass

    async def on_guild_integrations_update(self, guild):
        pass

    async def on_webhooks_update(self, channel):
        pass

    async def on_member_join(self, member):
        pass

    async def on_member_remove(self, member):
        pass

    async def on_member_update(self, before, after):
        # custom event dispatched when a Member has just completed membership verification/screening
        if before.pending and not after.pending:
            self.dispatch('verification_complete', after)

    async def on_verification_complete(self, member):  # custom event from above
        pass

    async def on_user_update(self, before, after):
        pass

    async def on_guild_join(self, guild):
        pass

    async def on_guild_remove(self, guild):
        pass

    async def on_guild_update(self, before, after):
        pass

    async def on_guild_role_create(self, role):
        pass

    async def on_guild_role_delete(self, role):
        pass

    async def on_guild_role_update(self, before, after):
        pass

    async def on_guild_emojis_update(self, guild, before, after):
        pass

    async def on_guild_available(self, guild):
        pass

    async def on_guild_unavailable(self, guild):
        pass

    async def on_voice_state_update(self, member, before, after):
        pass

    async def on_member_ban(self, guild, user):
        pass

    async def on_member_unban(self, guild, user):
        pass

    async def on_invite_create(self, invite):
        pass

    async def on_invite_delete(self, invite):
        pass

    async def on_group_join(self, channel, user):
        pass

    async def on_group_remove(self, channel, user):
        pass

    async def on_relationship_add(self, relationship):
        pass

    async def on_relationship_remove(self, relationship):
        pass

    async def on_relationship_update(self, before, after):
        pass

    async def on_error(self, event_name: str, *args, **kwargs):
        """Called when an event handler raises an exception.

        This method returns True if the exception was handled
        and None/False otherwise.
        (useful for cooperation between subclass methods)

        :param event_name: The name of the event that raised the exception (prefixed with "on_").
        :param args: The positional arguments (if any) that were passed to the event.
        :param kwargs: The keyword arguments (if any) that were passed to the event.
        """
        exc_type, exception, traceback = exc_info()

        if exc_type == ExtensionDisabledGuild:  # Can be raised outside a command, e.g. from an event listener
            return True

        print(f'Ignoring exception in event {event_name}:', file=__stderr__)
        print_exception(exc_type, exception, traceback)

    async def on_command(self, context: commands.Context):
        pass

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

    async def on_command_completion(self, context):
        pass

    async def load_commands(self):
        pass

    async def does_trigger_command(self, message: Message) -> bool:
        """checks if the message starts with a valid prefix
        that *could* trigger a command on the bot"""
        return any(message.content.startswith(i) for i in await self.command_prefix(self, message))

    async def validate_guild_configs(self):
        """"Validates" guild configs by updating any dynamic settings
        and ensuring proper format and required fields are present

        Currently just updates the guild invite in the configs"""
        guilds = self.guilds

        # ========== Basic Hard-Format Validation ========== #

        for guild in guilds:
            # ensure a config exists for each guild
            if guild.id not in self.guild_configs:
                self.guild_configs[guild.id] = self.create_guild_config(guild)
            # ensure the config is properly formatted
            else:
                temp_conf = default_guild()
                recursive_update(temp_conf, self.guild_configs[guild.id])
                self.guild_configs[guild.id] = temp_conf  # recursive_update() updates the temp_conf in place

        # ========== Update Guild Invite Link ========== #

        # concurrently gather invites for speedups with multiple guilds
        tasks = []
        for guild in guilds:
            tasks.append(guild.invites())
        guild_invites = await gather(*tasks)

        for guild, invites in zip(guilds, guild_invites):
            self.guild_configs[guild.id]['guild']['name'] = guild.name
            try:
                i0: list[Optional[Invite]] = invites
            except Forbidden:
                i0 = []
            if i0:
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

        # ========== Create Config Field for each Extension ========== #

        for guild in guilds:
            for ext_name in self.extensions.keys():
                if ext_name not in self.guild_configs[guild.id]['ext']:
                    self.guild_configs[guild.id]['ext'][ext_name] = {'enabled': False}  # default to disabled

        # saves any changes made to file
        self.save_guild_configs()

    def guild_config(self, guild: Guild | int) -> dict:
        """Returns the guild config for the given guild."""
        if isinstance(guild, Guild):
            guild = guild.id
        if guild in self.guild_configs:
            return self.guild_configs[guild]
        raise FileNotFoundError(f'No Guild configs for{guild} found.')

    def ext_guild_config(self, ext: str, guild: Guild) -> dict:
        """
        Get the per-guide config for an extension.

        :param ext: The extension name as a string
        :param guild: The guild to get the config for
        """
        if guild.id in self.guild_configs:
            config = self.guild_configs[guild.id]
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

    async def close(self):
        """Do Not Override"""
        await self.__close_connect__()
        await super().close()

    async def __close_connect__(self):
        """Called before connection to Discord is closed."""
        await self.change_presence(status=Status('offline'))
        log('Closing connection to Discord...', tag='Connection')

    async def __shutdown_async__(self):
        """Called before the asyncio event loop halts."""
        log('Closing aiohttp session...', tag='Shutdown')
        await self.aiohttp_session.close()
        log('Aiohttp session closed.', tag='Shutdown')

    def __shutdown_sync__(self):
        """Called before blocking run() call exits"""
        log('Saving Configs...', tag='Shutdown')
        save_config(self.configs)
        self.save_guild_configs()
        log('All Configs saved.', tag='Shutdown')
        if self.process_pool is not None:
            log('Shutting down process pool...', tag='Shutdown')
            self.process_pool.shutdown(wait=True, cancel_futures=True)
            log('Process pool shut down.', tag='Shutdown')

    def _cancel_asyncio_tasks(self):
        """Cancels **ALL** running and scheduled asyncio tasks.
        Therefore, this method must not be a coroutine
        as it would recursively cancel itself."""
        tasks: set[Task]
        # Get all still-running tasks
        if not (tasks := {t for t in all_tasks(loop=self.loop) if not t.done()}):
            return
        # Try HARD to cancel ALL tasks ASAP
        log(f'Cancelling {len(tasks)} lingering tasks...', tag='Shutdown')
        if self.DEBUG:
            for task in tasks:
                print(task)

        async def safe_canceller(t: Task):
            with protect():
                if t.cancelled():
                    return None
                if t.done():
                    return t.result() or t.exception()
                t.cancel()
                return await t

        try:
            self.loop.run_until_complete(  # coros wrapped in Task to stop DeprecationWarning
                    wait_for(gather(*[self.loop.create_task(safe_canceller(t)) for t in tasks], return_exceptions=True),
                             timeout=10)
            )
        except TimeoutError:
            log('Timed out waiting for lingering tasks to cancel (!!!)', tag='Shutdown')
            pass
        except CancelledError:
            log('Got cancelled while waiting on the cancelled to get cancelled...', tag='WTF')

        log('All lingering tasks cancelled.', tag='Shutdown')

    def shut_async_loop(self):
        """Completely and forcibly stops and closes the asyncio event loop.
        Catastrophic if called in the middle of an active connection."""
        with protect():
            self.loop.run_until_complete(self.__shutdown_async__())

        log('Closing asyncio event loop...', tag='Shutdown')
        with protect():
            self._cancel_asyncio_tasks()
        with protect():
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())

        self.loop.close()
        log('Asyncio event loop closed.', tag='Shutdown')

    async def start(self, token: str, *, bot: bool = True, reconnect: bool = True):
        """Do Not Override"""
        await self.login(token, bot=bot)
        await self.connect(reconnect=reconnect)

    def run(self, token: str, *, bot: bool = True, reconnect: bool = True):
        """Starts and runs the bot.

        -> Starts asyncio event loop

        -> establishes connection with Discord and logs in

        -> (When stop signal detected)
        closes connection with Discord

        -> Shuts down asyncio event loop

        Blocks for as long as the bot is running & not fully shut-down."""

        async def run_loop():  # runs the Discord Connection
            try:
                await self.start(token, bot=bot, reconnect=reconnect)
            except CancelledError:
                # this is here because the task canceller will try to cancel this too,
                # but we can stop it gracefully and close the Discord connection
                log('Ignoring Cancellation and proceeding to close Discord connection.', tag='Runner')
            except KeyboardInterrupt:
                log('KeyboardInterrupt detected', tag='Runner')
            finally:
                if not self.is_closed():
                    await self.close()
                log('Discord Connection Closed.', tag='Runner')

        def close_loop(*_, **__):  # shuts down asyncio event loop
            self.shut_async_loop()

        with suppress(NotImplementedError):  # unix only
            self.loop.add_signal_handler(SIGINT, close_loop)
            self.loop.add_signal_handler(SIGTERM, close_loop)

        # initialize bot stuff
        with protect():
            self.loop.run_until_complete(self.__init_async__())

        run_: Task = self.loop.create_task(run_loop())

        try:
            self.loop.run_until_complete(run_)
        except (KeyboardInterrupt, EOFError):
            log('Received signal to terminate bot and event loop.')
        finally:
            close_loop()

        with protect():
            self.__shutdown_sync__()

        if not run_.cancelled():  # this should um... return exceptions (I think?)
            return run_.result()


__all__ = ['BotClient']
