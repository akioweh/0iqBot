import re
from asyncio import TimeoutError
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from discord import Message, Reaction, TextChannel, User
from discord.ext.commands import Context, check_any, command

from botcord.checks import guild_owner_or_perms, has_global_perms
from botcord.ext.commands import Cog
from botcord.functions import batch

if TYPE_CHECKING:
    from botcord import BotClient

A_UPPERCASE = ord('A')
ALPHABET_SIZE = 26
# noinspection SpellCheckingInspection R = r'^\s+|\s+$|(\|\|.*?\|\|)|(\s*((<:\w+:\d{18}>)|(\u00a9|\u00ae|[
# noinspection SpellCheckingInspection \u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[
# noinspection SpellCheckingInspection \ud000-\udfff]))\s*)+$'


class LetterCounting(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.config_init(__file__)
        if 'channels' not in self.config:
            self.config['channels'] = list()
        if 'regex' not in self.config:
            self.config['regex'] = ''
        self.delete_queue = []

    @staticmethod
    def _decompose(number):
        while number:
            number, remainder = divmod(number - 1, ALPHABET_SIZE)
            yield remainder

    @staticmethod
    def base_10_to_alphabet(number: int) -> str:
        """Convert a decimal number to its base alphabet representation"""
        return ''.join(
                chr(A_UPPERCASE + part)
                for part in LetterCounting._decompose(number)
        )[::-1]

    @staticmethod
    def base_alphabet_to_10(letters: str) -> int:
        """Convert an alphabet number to its decimal representation"""
        return sum(
                (ord(letter) - A_UPPERCASE + 1) * ALPHABET_SIZE ** i
                for i, letter in enumerate(reversed(letters.upper()))
        )

    async def _errors_in(self, chl: TextChannel, *, limit: int = None, oldest_first: bool = True, **kwargs):
        if not isinstance(chl, TextChannel):
            raise TypeError(f'chl parameter must be a TextChannel, not {type(chl)}')
        expected = 1
        async for msg in chl.history(limit=limit, oldest_first=oldest_first, **kwargs):
            if not isinstance(msg, Message):
                continue
            content = re.sub(self.config['regex'], '', msg.content)
            num = LetterCounting.base_alphabet_to_10(content)
            if num == expected:
                expected += 1
            else:
                yield msg

    async def _remove_errors_in(self, chl: TextChannel, after_t: Optional[datetime] = None, errors: List[Message] = None):
        if not isinstance(chl, TextChannel):
            raise TypeError(f'chl parameter must be a TextChannel, not {type(chl)}')
        errors = [i async for i in self._errors_in(chl, after=after_t)] if errors is None else errors
        await chl.purge(check=lambda m: m in errors)

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.channel.id not in self.config['channels']:
            return
        if message.author.id == self.bot.user.id:
            return

        prev = None
        async for msg in message.channel.history(before=message.created_at, limit=100):
            if msg.id not in self.delete_queue:
                prev = msg
                break
        new_num = LetterCounting.base_alphabet_to_10(message.content.strip().strip('|'))
        prev_num = LetterCounting.base_alphabet_to_10(prev.content.strip().strip('|')) if prev else 0
        if new_num - 1 != prev_num:
            self.delete_queue.append(message.id)
            await message.delete()
            self.delete_queue.remove(message.id)

    @command()
    @check_any(guild_owner_or_perms(administrator=True), has_global_perms(owner=True))
    async def find_errors(self, ctx: Context, chl: Optional[TextChannel] = None):
        channel = chl if chl is not None else ctx.channel
        await ctx.message.delete()
        count = 0
        msg = ''
        async for err in self._errors_in(channel):
            msg += f'{getattr(err, "jump_url", "")}\n'
            count += 1
            if count > 50:
                await ctx.send('More than 50 errors found... showing oldest 50.')
                break

        if msg.strip('\n'):
            msg = '**__Errors:__** \n' + msg
            for i in batch(msg):
                await ctx.send(i)
        else:
            await ctx.send('No errors found.', delete_after=5)

    @command()
    @check_any(guild_owner_or_perms(administrator=True), has_global_perms(owner=True))
    async def remove_errors(self, ctx: Context, chl: Optional[TextChannel] = None):
        if chl is None:
            return
        errors = [i async for i in self._errors_in(chl)]
        if not errors:
            await ctx.reply(f'No errors found in {chl.mention}.', delete_after=5)
            return
        target: Message = await ctx.reply(f'Are you SURE that you want to delete {len(errors)} messages from {chl.mention}???', delete_after=8)

        def check(r: Reaction, u: User):
            if u == ctx.author and target == r.message:
                if str(r.emoji) == '👍':
                    return True
                if str(r.emoji) == '👎':
                    raise TimeoutError
            return False

        try:
            await target.add_reaction('👍')
            await target.add_reaction('👎')
            await self.bot.wait_for('reaction_add', check=check, timeout=5)
        except TimeoutError:
            await ctx.send('Canceled.', delete_after=3)
        else:
            msg = await ctx.reply('Deleting...')
            await self._remove_errors_in(chl, errors=errors)
            await msg.edit(content='Operation Completed.')


def setup(bot):
    bot.add_cog(LetterCounting(bot))
