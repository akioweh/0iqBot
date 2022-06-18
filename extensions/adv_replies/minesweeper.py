from random import sample
from typing import TYPE_CHECKING

from discord.ext.commands import Context, command

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


class MineSweeper(Cog):
    E = {
        -1: '💥',
        0: '⬛',
        1: '1️⃣',
        2: '2️⃣',
        3: '3️⃣',
        4: '4️⃣',
        5: '5️⃣',
        6: '6️⃣',
        7: '7️⃣',
        8: '8️⃣',
        9: '9️⃣',
    }

    def __init__(self, bot):
        self.bot: BotClient = bot

    @command(aliases=['ms'])
    async def minesweeper(self, ctx: Context, width: int, height: int, mines: int):
        """
        Generates minesweeper board using spoilers.
        """
        grids = width * height
        if width <= 0 or height <= 0:
            await ctx.reply('stop tryna set invalid board sizes lol')
            return
        chars = grids * 7 + height - 1
        if chars > 2000:
            await ctx.reply('board is too big to fit within discord\'s 2000 character limit')
            return
        if mines > grids:
            await ctx.reply('bros tryna fit more mines than there are squares')
            return

        board_serial: list[int] = [0] * grids
        mine_cords: list[int] = sample(list(range(grids)), mines)
        for i in mine_cords:
            board_serial[i] = -1
            # update "bomb count" of neighboring squares
            for j in MineSweeper.neighbors(width, height, i):
                if board_serial[j] != -1:  # only increment bomb count if the square isn't a bomb lol
                    board_serial[j] += 1

        board_text = ''
        for i, j in enumerate(board_serial):
            if i % width == 0:
                board_text += '\n'
            board_text += f'||{MineSweeper.E[j]}||'
        board_text.lstrip('\n')

        print(board_text)
        await ctx.send(board_text)

    @staticmethod
    def neighbors(x: int, y: int, pos: int):
        up, down, left, right = False, False, False, False
        mid = True
        # up
        if pos - x >= 0:
            up = True
        # down
        if pos + x <= x * y - 1:
            down = True
        # left
        if pos % x != 0:
            left = True
        # right
        if pos % x != x - 1:
            right = True

        pos_bool = [left * up, mid * up, right * up, left * mid, mid * mid, right * mid, left * down, mid * down, right * down]
        pos_pos = [pos - 1 - x, pos - x, pos + 1 - x, pos - 1, pos, pos + 1, pos - 1 + x, pos + x, pos + 1 + x]
        neighbor_pos: list[int] = list(p for p, b in zip(pos_pos, pos_bool) if b)

        return neighbor_pos


def setup(bot: 'BotClient'):
    bot.add_cog(MineSweeper(bot))
