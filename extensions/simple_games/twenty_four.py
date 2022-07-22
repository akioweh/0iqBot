"""24 but twenty_four because python symbols can't start with a number"""

from fractions import Fraction
from operator import add, mul, sub, truediv
from random import randint
from typing import Final, Iterator, Optional, TYPE_CHECKING

import math
from discord import Message
from discord.ext.commands import Context, group

from botcord.ext.commands import Cog
from botcord.utils import MathParser

if TYPE_CHECKING:
    from botcord import BotClient


# noinspection SpellCheckingInspection
class TwentyFour(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.parser = MathParser(allowed_operations={add, mul, sub, truediv})

    @group(aliases=['24', 'tf'], invoke_without_command=True)
    async def twenty_four(self, ctx: Context):
        """
        The 24 number game thing.

        A question composes of four whole numbers
        The goal is to apply arithmetic operations between the four numbers
        to get an expression that equals 24.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(TwentyFour)

    @twenty_four.command(aliases=['q', 'generate'])
    async def new(self, ctx: Context):
        """Generate a 24-game question with valid solutions"""
        question = await self.bot.to_process(TwentyFour._new_q)  # subprocess offloading
        await ctx.reply(f'`{" ".join(str(i) for i in question)}`')

    @twenty_four.command(aliases=['reveal'], ignore_extra=False)
    async def solve(self, ctx: Context, a: int, b: int, c: int, d: int):
        """Find solutions to a 24-game question"""
        answers = await self.bot.to_process(TwentyFour.find_solutions, [a, b, c, d])  # subprocess offloading
        if answers:
            count = len(answers)
            await ctx.reply(f'`{answers[0]}`{f"... and {count - 1} more" if count > 1 else ""}')
        else:
            await ctx.reply('No Solution')

    @twenty_four.command(aliases=['answer'])
    async def submit(self, ctx: Context, *, answer: str):
        """Submit your answer to a 24-game question (by replying)
        and get feedback on whether it is correct or not"""
        if not ctx.message.reference:  # make sure the message has a reference
            await ctx.reply('Reply to the question you are submitting the answer for', delete_after=5)
            return
        if not isinstance(q_msg := ctx.message.reference.resolved, Message):  # make sure the reference isn't fucked up
            await ctx.reply('Can\'t resolve the refererred message', delete_after=5)
            return

        try:  # parse the question
            q = list(int(i) for i in q_msg.content.strip('`').split())
            if len(q) != 4 or any((not 0 <= i <= 9) for i in q):
                raise ValueError
        except ValueError:  # make sure the question is valid
            await ctx.reply('That doesn\'t seem like a valid 24-game question', delete_after=5)
            return

        if q_msg.author.id != self.bot.user.id:  # make sure the question was asked by the bot
            await ctx.reply('Can\'t submit an answer to a question that wasn\'t made by me', delete_after=5)
            return

        answer = answer.strip('`').strip()  # allow code block formatting

        try:
            if '_' in answer:  # Python allows _ in number literals, such as 4_3 (=43), but let's not allow that
                raise SyntaxError
            val = self.parser.parse(answer)  # safely evaluate the answer
        except SyntaxError:
            await ctx.reply('Invalid expression syntax.', delete_after=5)
        except TypeError:
            await ctx.reply('Invalid expression content.', delete_after=5)
        except ArithmeticError:
            await ctx.reply('Only four basic operations are allowed: + - * / \n'
                            '(and no leading minus because that\'s negation, not subtraction)', delete_after=5)
        else:  # expression equals 24, but we have more checks to do:
            try:  # verify that the answer is valid; uses all four numbers, and only once each
                operators = '+-*/'
                numbers = "".join(q_msg.content.strip("`").split())
                allowed_chars = operators + numbers
                if not all(i in allowed_chars for i in answer):
                    raise ValueError
                clean = answer.replace('(', '').replace(')', '').replace(' ', '')  # only keep numbers and operators
                # to make sure the four numbers are used legally, they must each appear once,
                # delimited from each other by an operator
                # the format of clean at this point should be 'xoxoxox' where x is a number and o is an operator
                if not len(clean) == 7:
                    raise ValueError
                if not all(clean[i] in operators for i in (1, 3, 5)):  # make sure the operators are in their positions
                    raise ValueError
                if not all(clean[i] in numbers for i in (0, 2, 4, 6)):  # make sure the numbers are in their positions
                    raise ValueError
                nums = clean[0] + clean[2] + clean[4] + clean[6]  # the digits only as a 4-long string
                if not all(i in nums for i in nums):  # make sure each number is used once and only once
                    raise ValueError

            except ValueError:
                await ctx.reply('That doesn\'t seem like a valid answer', delete_after=5)
                return

            else:
                if math.isclose(val, 24):  # not much of a skill issue
                    await ctx.reply(f'Correct answer. Took you `{ctx.message.created_at - q_msg.created_at}`')
                else:  # massive skill issue.
                    await ctx.reply(f'`{val}` is definitely not `24`; try harder.')

    # Computationally Intensive, lazy no brain implementation
    @staticmethod
    def _new_q() -> list[int]:
        q = [randint(0, 9) for _ in range(4)]
        possible = TwentyFour.has_solution(q)
        while not possible:
            q = [randint(0, 9) for _ in range(4)]
            possible = TwentyFour.has_solution(q)
        return q

    # Actual algorithms below
    OPS: Final = {mul: '*', sub: '-', add: '+',
                  lambda a, b: a / b if b != 0 else 9999999: '/'}  # special div to avoid division by zero

    # Computationally Intensive
    @staticmethod
    def has_solution(nums: list[int], target: int = 24) -> bool:
        if len(nums) == 1:
            if math.isclose(nums[0], target):
                return True

        for i in range(len(nums)):
            for j in range(len(nums)):
                if i != j:
                    for op in TwentyFour.OPS:
                        if nums[j]:
                            if TwentyFour.has_solution([op(nums[i], nums[j])] +
                                                       [nums[k] for k in range(len(nums)) if k not in (i, j)]):
                                return True

    # Computationally Intensive
    @staticmethod
    def _solve(num: list[Fraction], how: list, target: int) -> Iterator[Optional[str]]:
        if len(num) == 1:
            if num[0] == target:
                # hacky way to parse how into string
                yield str(how[0]).replace(',', '').replace("'", '').strip().removeprefix('(').removesuffix(')')
        else:
            for i, n1 in enumerate(num):
                for j, n2 in enumerate(num):
                    if i != j:  # for "every pair of two numbers in num":
                        for op in TwentyFour.OPS:  # do each of the operations...
                            # "Spectators" are the unchanged numbers (because we only operate on two at a time)
                            spectator_nums = [n for k, n in enumerate(num) if k != i and k != j]
                            spectator_hows = [h for k, h in enumerate(how) if k != i and k != j]

                            new_num = spectator_nums + [op(n1, n2)]  # Operate on two numbers
                            new_how = spectator_hows + [(how[i], TwentyFour.OPS[op], how[j])]

                            yield from TwentyFour._solve(new_num, new_how, target)

    # Computationally Intensive, driver function of _solve()
    @staticmethod
    def find_solutions(num: list[int], target: int = 24) -> list[Optional[str]]:
        frac = [Fraction(i) for i in num]
        return list(set(TwentyFour._solve(frac, num, target)))


def setup(bot):
    bot.add_cog(TwentyFour(bot))
