from collections.abc import Coroutine
from concurrent.futures import ProcessPoolExecutor
from contextlib import suppress
from importlib import import_module
from os import getcwd
from signal import SIGINT, SIG_IGN, signal
from traceback import print_exception
from typing import Callable, Optional, ParamSpec, TypeVar

from aiohttp import ClientSession
from discord import Activity, Forbidden, Guild, HTTPException, Intents, Invite, Message, Status
from discord.ext import commands
from discord.ext.commands.errors import (CheckFailure, CommandNotFound, CommandOnCooldown, DisabledCommand,
                                         NoPrivateMessage, UserInputError)
from sys import platform as __platform__, stderr, stdout, version_info as __version_info__

from .configs import ConfigDict, load_configs, new_guild_config, save_config, save_guild_config
from .functions import *
from .utils.errors import protect
from .utils.extensions import get_all_extensions_from

# Fix to stop aiohttp spamming errors in stderr when closing because that is uglier
if __version_info__[0] == 3 and __version_info__[1] >= 8 and __platform__.startswith('win'):
    from asyncio import WindowsSelectorEventLoopPolicy, set_event_loop_policy
    set_event_loop_policy(WindowsSelectorEventLoopPolicy())


# Subprocess Error handling stuff
def _subprocess_initializer():
    signal(SIGINT, SIG_IGN)


# Typing pre-definitions
P = ParamSpec('P')
T = TypeVar('T')


class BotClient(commands.Bot):
    connect_init_ed: bool
    async_init_ed: bool
    latest_message: Optional[Message]
    aiohttp_session: Optional[ClientSession]
    process_pool: Optional[ProcessPoolExecutor]
    configs: ConfigDict
    guild_configs: dict[int, ConfigDict]
    prefix: list[str]
    guild_prefixes: dict[int, str]

    def __init__(self, **options):
        self.async_init_ed = False
        self.connect_init_ed = False

        global_configs, guild_configs = load_configs()
        prefix_check = BotClient.mentioned_or_in_prefix \
            if global_configs['bot']['reply_to_mentions'] else BotClient.in_prefix
        process_count = options.pop('multiprocessing', 0)
        self.__status = options.pop('status', None)
        self.__activity = options.pop('activity', None)
        super().__init__(**options,
                         activity=Activity(name='...Bot Initializing...', type=0),
                         status=Status('offline'),
                         command_prefix=prefix_check,
                         max_messages=global_configs['bot']['message_cache'],
                         intents=Intents.all())

        self.latest_message = None
        self.aiohttp_session = None
        self.process_pool = ProcessPoolExecutor(max_workers=process_count, initializer=_subprocess_initializer)

        self.configs = global_configs
        self.guild_configs = guild_configs
        self.prefix = global_configs['bot']['prefix']
        self.guild_prefixes = {c['guild']['id']: c['bot']['prefix'] for c in self.guild_configs.values()}

        exts = import_module(self.configs['bot']['extension_dir'], getcwd())
        self.load_extensions(exts)

    async def __init_async__(self) -> bool:
        """Used to initialize whatever that requires to run inside an event loop
        (called after the event loop has been initialized)"""
        if self.async_init_ed:
            return False
        self.async_init_ed = True
        self.aiohttp_session = ClientSession(loop=self.loop)

        log('Asynchronous Initialization Finished')
        return True

    async def __init_connect__(self) -> bool:
        """Used to initialized whatever that require a fully established discord connection
        (called after logged in and connected to Discord)"""
        if self.connect_init_ed:
            return False
        self.connect_init_ed = True

        with protect():
            await self.validate_guild_configs()
            self.save_guild_configs()

        await self.change_presence(activity=self.__activity, status=self.__status)
        log('Post-Connection Initialization Finished')
        return True

    def to_process(self, func: Callable[P, T], *args) -> Coroutine[None, P, T]:
        return self.loop.run_in_executor(self.process_pool, func, *args)

    def load_extensions(self, package):
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

    def guild_config(self, guild: Guild | int):
        if isinstance(guild, Guild):
            guild = guild.id
        if guild in self.guild_configs:
            return self.guild_configs[guild]
        raise FileNotFoundError(f'No Guild configs for{guild} found.')

    def ext_guild_config(self, ext: str, guild: Guild):
        if guild.id in self.guild_configs:
            config = self.guild_configs[guild.id]
            if ext in config['ext']:
                return config['ext'][ext]
        raise FileNotFoundError(f'No Extension configs for guild {guild} found.')

    async def logm(self, message, tag="Main", sep="\n", channel=None):
        stdout.write(f"[{time_str()}] [{tag}]: {message}" + sep)
        if not channel:
            channel = self.latest_message.channel
        try:
            await channel.send(message)
        except Forbidden:
            pass

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

    async def on_command(self, context):
        pass

    async def on_command_error(self, context, exception, *, fire_anyway=False):
        if not fire_anyway:  # Normally we don't do anything here if another handler catches the error
            if self.extra_events.get('on_command_error', None):
                return
            if hasattr(context.command, 'on_error'):
                return
            cog = context.cog
            # hasattr check is to see if the cog error handler has been overridden with a custom method
            if cog and hasattr(cog.cog_command_error.__func__, '__cog_special_method__'):
                return

        handled = False
        if isinstance(exception, (CommandNotFound, DisabledCommand, CheckFailure)) or (context.command is None):
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

        #  Additional logging for HTTP (networking) errors
        if isinstance(exception, HTTPException):
            log(f'An API Exception has occurred ({exception.code}): {exception.text}', tag='Error')
            context.reply(f'An API error occurred while executing the command. (API Error code: {exception.code})')

        if not handled:
            print(f'Ignoring exception in command {context.command}:', file=stderr)
            print_exception(type(exception), exception, exception.__traceback__, file=stderr)

    async def on_command_completion(self, context):
        pass

    async def load_commands(self):
        pass

    async def validate_guild_configs(self):
        for guild in self.guilds:
            # Create config for guild if it doesn't exist
            if guild.id not in self.guild_configs:
                self.guild_configs[guild.id] = self.create_guild_config(guild)

            # Update guild name and invite
            self.guild_configs[guild.id]['guild']['name'] = guild.name
            try:
                i0: list[Optional[Invite]] = await guild.invites()
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

    def create_guild_config(self, guild: Guild):
        if guild.id in self.guild_configs:
            raise FileExistsError(f'There already exists a config for guild {guild.id}')
        return new_guild_config(guild.id)

    def save_guild_configs(self):
        for guild, config in self.guild_configs.items():
            save_guild_config(config, guild)

    def run(self, *args, **kwargs):
        super().run(*args, *kwargs)
        self.__close_sync__()

    async def start(self, *args, **kwargs):
        await self.__init_async__()
        await super().start(*args, **kwargs)

    async def close(self):
        save_config(self.configs)
        self.save_guild_configs()
        await self.aiohttp_session.close()
        await super().close()

    async def __close_async__(self):  # todo: make the shutdown process automatically call this
        pass

    def __close_sync__(self):
        self.process_pool.shutdown(wait=True)

# End
