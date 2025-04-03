import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import Sequence, TYPE_CHECKING

from discord import AllowedMentions, Forbidden, HTTPException, Member, NotFound, TextChannel, User, Webhook
from discord.ext.commands import Cog, Context, command
from discord.utils import MISSING

if TYPE_CHECKING:
    from botcord import BotClient


# noinspection SpellCheckingInspection,DuplicatedCode
class MessageHook(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.mentions = AllowedMentions(everyone=False, users=True, roles=False)

    @command(name='send', aliases=['say'])
    async def _send_cmd(self, ctx: Context, *, text: str = None, delete: bool = True):
        if text is None and ctx.message.attachments is None:
            return
        if len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer characters in length. (nitro abuse smh)', delete_after=5)
            return

        attachments = await asyncio.gather(*(item.to_file() for item in ctx.message.attachments))

        if delete:
            delete = asyncio.create_task(ctx.message.delete())
        with suppress(Forbidden):
            await ctx.send(content=text,
                           files=attachments,
                           reference=ctx.message.reference,
                           allowed_mentions=self.mentions)
        if delete:
            with suppress(Forbidden, NotFound):
                await delete

    @command(name='resend', aliases=['repost'])
    async def _resend_cmd(self, ctx: Context, *, text: str = None):
        # new discord.py typing annotations for @command are too complicated for PyCharm?!!!
        # noinspection PyTypeChecker
        await self._sendas_cmd(ctx, ctx.author, text=text)

    @command(name='sendas', aliases=['sayas'])
    async def _sendas_cmd(self, ctx: Context, user: User | Member, *, text: str = None, delete: bool = True):
        if text is None and ctx.message.attachments is None:
            return
        if len(text) > 2000:
            await ctx.reply('Messages must be 2000 or fewer characters in length. (nitro abuse smh)', delete_after=5)
            return

        attachments = await asyncio.gather(*(item.to_file() for item in ctx.message.attachments))

        if delete:
            delete = asyncio.create_task(ctx.message.delete())

        try:
            await MessageHook.send(ctx.channel, text, user.name, user.avatar.url, attachments, self.mentions)
        except Forbidden:
            with suppress(Forbidden):
                await ctx.reply('Missing Permissions', delete_after=5)
        except HTTPException as error:
            if error.code == 30007:
                await ctx.reply('All existing webhooks are unusable (please delete). '
                                'Failed to create new one: Maximum number of webhooks in this channel reached (10).')
        if delete:
            with suppress(Forbidden, NotFound):
                await delete

    @command(name='cleanhooks')
    async def _cleanhooks_cmd(self, ctx: Context):
        if not ctx.guild:
            return
        try:
            check = lambda hook: hook.name == 'MessageHook' or hook.user == ctx.bot.user
            deleted = await MessageHook.clean_hooks(ctx.channel, check)
            await ctx.reply(f'Deleted {deleted} webhooks.')
        except Forbidden:
            with suppress(Forbidden):
                await ctx.reply('Missing Permissions', delete_after=5)

    @staticmethod
    async def clean_hooks(chl: TextChannel, check: Callable[[Webhook], bool]) -> int:
        hooks: list[Webhook] | None = await chl.guild.webhooks()
        delete_ables = [hook for hook in hooks if check(hook)]
        if not delete_ables:
            return 0

        await asyncio.gather(*(hook.delete() for hook in delete_ables))
        return len(delete_ables)

    @staticmethod
    async def send(chl: TextChannel,
                   content: str,
                   username: str,
                   avatar_url: str,
                   attachments: Sequence = None,
                   allowed_mentions: AllowedMentions = AllowedMentions.none()):
        """Sends a message to a channel with a webhook."""
        hooks: list[Webhook] | None = await chl.webhooks()
        valid_hook: Webhook | None = None
        for hook in hooks:
            if hook.token:
                valid_hook = hook
                break

        if not valid_hook:
            valid_hook = await chl.create_webhook(name='MessageHook')

        await valid_hook.send(content=content,
                              username=username,
                              avatar_url=avatar_url,
                              files=attachments or MISSING,
                              allowed_mentions=allowed_mentions)


async def setup(bot: 'BotClient'):
    await bot.add_cog(MessageHook(bot))
