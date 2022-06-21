from random import sample
from typing import Final, Optional, TYPE_CHECKING

from discord import Message
from discord.ext.commands import CommandError, Context, MissingRequiredArgument, group

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


class MineSweeper(Cog):
    EMOJI: Final = {
        -1: '💥',
        0 : '⬛',
        1 : '1️⃣',
        2 : '2️⃣',
        3 : '3️⃣',
        4 : '4️⃣',
        5 : '5️⃣',
        6 : '6️⃣',
        7 : '7️⃣',
        8 : '8️⃣',
    }

    def __init__(self, bot):
        self.bot: BotClient = bot

    @group(aliases=['ms'],
           usage='<width> <height> [mines] OR\n'
                 'iq [minesweeper|ms] <size>',
           invoke_without_command=True)
    async def minesweeper(self, ctx: Context, width: int, height: int, mines: Optional[int] = None):
        """Generates minesweeper board using spoilers.
        When number of mines is unspecified, around 11% of the size is used."""
        # Checks to ensure valid input
        grids = width * height
        chars = grids * 7 + height - 1  # each square can take up to 7 unicode characters
        if mines is None:
            mines = grids // 9
        if width <= 0 or height <= 0:
            await ctx.reply('Board size is invalid.')
            return
        if chars > 2000:
            await ctx.reply('Board is too big to fit within discord\'s 2000 character limit.')
            return
        if mines > grids:
            await ctx.reply('There are more mines than squares on the board.')
            return

        board: list[int] = [0] * grids
        mine_pos_s: list[int] = sample(list(range(grids)), mines)
        for mine_pos in mine_pos_s:
            board[mine_pos] = -1  # -1 signifies bomb
            # increment "bomb count" of neighboring squares
            for n_pos in MineSweeper.neighbors(width, height, mine_pos):
                if board[n_pos] != -1:  # only increment bomb count if the square isn't a bomb lol
                    board[n_pos] += 1

        board_text = ''
        for pos, value in enumerate(board):
            if pos % width == 0:  # Add newlines to make the board appear 2D in text
                board_text += '\n'
            board_text += f'||{MineSweeper.EMOJI[value]}||'
        board_text.lstrip('\n')

        # try to send using a webhook for custom pfp
        for c in self.bot.commands:
            if c.qualified_name == 'sendas':  # cross-extension dependency
                fake_user = lambda: None
                setattr(fake_user, 'name', 'MineSweeper Bot')
                setattr(fake_user, 'avatar_url', 'https://ih1.redbubble.net/image.395422632.9241/bg,ffffff-flat,750x,075,f-pad,750x750,ffffff.u2.jpg')
                await c(ctx, fake_user, text=board_text, delete=False)
                break
        else:  # backup in case message hook dependency doesn't exist
            await ctx.send(board_text)

    @staticmethod
    def neighbors(x: int, y: int, pos: int) -> list[int]:
        # middle - up - down - left - right
        mi: bool = True
        up: bool = pos - x >= 0
        dn: bool = pos + x <= x * y - 1
        lt: bool = pos % x != 0
        rt: bool = pos % x != x - 1

        pos_valid: list[bool] = [lt * up, mi * up, rt * up, lt * mi, False, rt * mi, lt * dn, mi * dn, rt * dn]
        pos_list: list[int] = [pos - x - 1, pos - x, pos - x + 1, pos - 1, pos, pos + 1, pos + x - 1, pos + x,
                               pos + x + 1]
        neighbor_pos: list[int] = list(pos for pos, valid in zip(pos_list, pos_valid) if valid)
        return neighbor_pos

    @minesweeper.error
    async def try_to_handle_goddam_dynamic_syntax(self, ctx: Context, error):
        """This junk here tries to allow the minesweeper command to accept an argument format
        with only one argument, ``size``, which generates a square board (with the default 11% bombs) \n
        Annoyingly, I have to take care of this alongside the other two- and three- argument cases \n
        I tried to make it super robust but that required lots of complicated checks and chaining logic"""
        try:
            # If error not due to supplying only one integer argument,
            # skip rest of codeblock (by raising exception)
            # then call default error handler because we do not deal with anything else
            if not isinstance(error, MissingRequiredArgument):
                raise CommandError()
            if not (len(ctx.args) == 3 and ctx.args[0] == self and isinstance(ctx.args[1], Context)):
                raise CommandError()
            size = ctx.args[2]  # 1st is self, 2nd is ctx
            if not isinstance(size, int):
                raise CommandError()

            await ctx.invoke(self.minesweeper, size, size)

        except CommandError as e:
            if not e.args:  # normally it is a blank CommandError raised from above
                e = error
                # but if e has content then it must be raised from the above ctx.invoke
                # then it is unexpected and should be passed on (not overwrite it with original error)
            await ctx.bot.on_command_error(ctx, e, fire_anyway=True)

    @minesweeper.command()
    async def reveal(self, ctx: Context):
        """Reveals a minesweeper board by removing all spoilers"""
        if not (ctx.message.reference and isinstance(ctx.message.reference.resolved, Message)):
            await ctx.reply('Reply to the minesweeper board you want to reveal.', delete_after=5)
            return
        board = ctx.message.reference.resolved.content
        if not ('||⬛||' in board or '||💥||' in board) or ' ' in board:
            await ctx.reply('That doesn\'t seem like a valid minesweeper board.')
            return
        revealed = board.replace('||', '')
        await ctx.reply(revealed)


def setup(bot: 'BotClient'):
    bot.add_cog(MineSweeper(bot))
