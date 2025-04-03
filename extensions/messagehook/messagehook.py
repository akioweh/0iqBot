import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import Sequence, TYPE_CHECKING

from discord import AllowedMentions, Forbidden, ForumChannel, Guild, HTTPException, Member, NotFound, StageChannel, \
    TextChannel, Thread, User, VoiceChannel, Webhook
from discord.ext.commands import command
from discord.utils import MISSING

from botcord.ext.commands import Cog, Context
from botcord.types import WebhookMessagableChannel, WebhookPossessingChannel

if TYPE_CHECKING:
    from botcord import BotClient


# noinspection SpellCheckingInspection,DuplicatedCode
class MessageHook(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.mentions = AllowedMentions(everyone=False, users=True, roles=False)

    @command(name='send', aliases=['say'])
    async def _send_cmd(self, ctx: Context, *, text: str | None = None, delete: bool = True):
        if not text and not ctx.message.attachments:
            return
        if text is not None and len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer characters in length. (nitro abuse smh)', delete_after=5)
            return

        attachments = await asyncio.gather(*(item.to_file() for item in ctx.message.attachments))

        delete_task = asyncio.create_task(ctx.message.delete()) if delete else None

        with suppress(Forbidden):
            await ctx.send(content=text,
                           files=attachments,
                           reference=ctx.message.reference,  # type: ignore # what
                           allowed_mentions=self.mentions)
        if delete_task is not None:
            with suppress(Forbidden, NotFound):
                await delete_task

    @command(name='resend', aliases=['repost'])
    async def _resend_cmd(self, ctx: Context, *, text: str | None = None):
        await self._sendas_cmd(ctx, ctx.author, text=text)

    @command(name='sendas', aliases=['sayas'])
    async def _sendas_cmd(self, ctx: Context, user: User | Member, *, text: str | None = None, delete: bool = True):
        if not isinstance(ctx.channel, TextChannel | VoiceChannel | StageChannel | ForumChannel | Thread):
            await ctx.reply('This channel does not seem to support webhooks. ')
            return
        if not text and not ctx.message.attachments:
            return
        if text is not None and len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer characters in length. (nitro abuse smh)', delete_after=5)
            return

        attachments = await asyncio.gather(*(item.to_file() for item in ctx.message.attachments))

        delete_task = asyncio.create_task(ctx.message.delete()) if delete else None

        try:
            await MessageHook.send(ctx.channel, text, user.name, user.display_avatar.url, attachments, self.mentions)
        except Forbidden:
            with suppress(Forbidden):
                await ctx.reply('Missing Permissions', delete_after=5)
        except HTTPException as error:
            if error.code == 30007:
                await ctx.reply('All existing webhooks are unusable (please delete). '
                                'Failed to create new one: Maximum number of webhooks in this channel reached (10).')
        if delete_task is not None:
            with suppress(Forbidden, NotFound):
                await delete_task

    @command(name='cleanhooks')
    async def _cleanhooks_cmd(self, ctx: Context):
        if ctx.guild is None:
            return
        try:
            check = lambda hook: hook.name == 'MessageHook' or hook.user == ctx.bot.user
            deleted = await MessageHook.clean_hooks(ctx.guild, check)
            await ctx.reply(f'Deleted {deleted} webhooks.')
        except Forbidden:
            with suppress(Forbidden):
                await ctx.reply('Missing Permissions', delete_after=5)

    @staticmethod
    async def clean_hooks(guild: Guild, check: Callable[[Webhook], bool]) -> int:
        """Deletes all webhooks in a guild that match the given check function."""
        hooks = await guild.webhooks()
        hooks_to_delete = list(filter(check, hooks))
        if not hooks_to_delete:
            return 0

        await asyncio.gather(*(hook.delete() for hook in hooks_to_delete))
        return len(hooks_to_delete)

    @staticmethod
    async def send(chl: WebhookMessagableChannel,
                   content: str | None,
                   username: str,
                   avatar_url: str,
                   attachments: Sequence | None = None,
                   allowed_mentions: AllowedMentions = AllowedMentions.none()):
        """Sends a message to a channel with a webhook."""
        parent_channel: WebhookPossessingChannel | None = chl.parent if isinstance(chl, Thread) else chl
        if parent_channel is None:
            raise ValueError('Cannot find valid channel from chl.')

        hooks = await parent_channel.webhooks()
        valid_hook = None
        for hook in hooks:
            if hook.token:
                valid_hook = hook
                break
        if not valid_hook:
            valid_hook = await parent_channel.create_webhook(name='MessageHook', reason='MessageHook')

        await valid_hook.send(content=content or MISSING,
                              username=username,
                              avatar_url=avatar_url,
                              files=attachments or MISSING,
                              thread=chl if isinstance(chl, Thread) else MISSING,
                              allowed_mentions=allowed_mentions)


async def setup(bot: 'BotClient'):
    await bot.add_cog(MessageHook(bot))
