from random import sample
from typing import Final, TYPE_CHECKING

from discord.ext.commands import Context, command

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

    @command(aliases=['ms'])
    async def minesweeper(self, ctx: Context, width: int, height: int, mines: int):
        """Generates minesweeper board using spoilers."""
        # Checks to ensure valid input
        grids = width * height
        chars = grids * 7 + height - 1  # each square can take up to 7 unicode characters
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


def setup(bot: 'BotClient'):
    bot.add_cog(MineSweeper(bot))
