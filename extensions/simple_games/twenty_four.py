"""24 but twenty_four because python symbols can't start with a number"""

from asyncio import CancelledError, Future, TimeoutError, ensure_future
from contextlib import suppress
from fractions import Fraction
from operator import add, mul, sub, truediv
from random import randint
from typing import Final, Iterator, Optional, TYPE_CHECKING

import math
from discord import Message
from discord.ext.commands import Context, group
from time import time

from botcord.ext.commands import Cog
from botcord.utils import MathParser

if TYPE_CHECKING:
    from botcord import BotClient


# noinspection SpellCheckingInspection
class TwentyFour(Cog):
    """
    The 24 number game thing.

    A question composes of four whole numbers
    The goal is to apply arithmetic operations between the four numbers to get an expression that equals 24.
    """

    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.parser = MathParser(allowed_operations={add, mul, sub, truediv})
        self.pending_games: dict[int, Future] = {}  # ids of question messages that aren't answerded yet and their waiting listeners

    def complete_game(self, q_msg_id: int):
        """remove the "game" from self.pending_games
        and cancels any listeners still waiting for an answer"""
        if q_msg_id in self.pending_games:
            with suppress(CancelledError):
                self.pending_games.pop(q_msg_id).cancel()

    @group(aliases=['24', 'tf'], invoke_without_command=True)
    async def twenty_four(self, ctx: Context):
        """
        The 24 number game thing.

        A question composes of four whole numbers
        The goal is to apply arithmetic operations between the four numbers to get an expression that equals 24.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(self.twenty_four)

    @twenty_four.command(aliases=['q', 'generate'])
    async def new(self, ctx: Context):
        """Generate a 24-game question with valid solutions"""
        question = await self.bot.to_process(TwentyFour._new_q)  # subprocess offloading
        q_msg: Message = await ctx.reply(f'`{" ".join(str(i) for i in question)}`')

        # annnnnnd, wait for an answer
        # the wait might be cancled from elsewhere, when the question is answered some other way,
        # so we check for that
        deadline: float = time() + 300  # a generous 5 minutes :)
        # also check for timeout here, just in case, to prevent infinite loops
        # also check for cancelation... again, just in case (im fucking losing this)
        while time() < deadline:
            answer_listener = self.bot.wait_for(
                    'message', check=lambda m: m.reference and m.reference.message_id == q_msg.id,  # only replies count
                    timeout=max(1., deadline - time())  # a persistent timeout across iterations
            )
            answer_listener = ensure_future(answer_listener)  # make sure we can cancel the listener
            self.pending_games[q_msg.id] = answer_listener
            try:
                answer_msg: Message = await answer_listener
            except TimeoutError:  # no response
                await q_msg.reply('No answer received within 5 minutes :(')
                break
            except CancelledError:  # question has been answered some other way
                break
            if answer_msg.author != ctx.author:
                await answer_msg.reply('You can\'t answer other people\'s questions!')
            else:  # valid reply (from OP), check the answer
                if any(answer_msg.content.startswith(i) for i in await self.bot.command_prefix(self.bot, answer_msg)):
                    continue  # ignore commands

                correct, response = self.check_answer(answer_msg.content, question)

                if correct is None:  # invalid answer
                    await answer_msg.reply(response, delete_after=5)
                elif not correct:  # incorrect answer
                    await answer_msg.reply(response)
                elif correct:  # correct answer
                    await answer_msg.reply(response.format(str(answer_msg.created_at - q_msg.created_at)))
                    break  # we can stop listening for answers now
        else:
            await q_msg.reply('No answer received within 5 minutes :(')

        self.complete_game(q_msg.id)

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
            q_nums = list(map(int, q_msg.content.strip('`').split()))
            if len(q_nums) != 4 or any((not 0 <= i <= 9) for i in q_nums):
                raise ValueError
        except ValueError:  # make sure the question is valid
            await ctx.reply('That doesn\'t seem like a valid 24-game question', delete_after=5)
            return

        if q_msg.author.id != self.bot.user.id:  # make sure the question was asked by the bot
            await ctx.reply('Can\'t submit an answer to a question that wasn\'t made by me', delete_after=5)
            return

        correct, response = self.check_answer(answer, q_nums)

        if correct is None:  # invalid answer
            await ctx.reply(response, delete_after=5)
        elif not correct:  # incorrect answer
            await ctx.reply(response)
        elif correct:  # correct answer
            await ctx.reply(response.format(str(ctx.message.created_at - q_msg.created_at)))

            self.complete_game(q_msg.id)  # cancel the command-less listener

    # @Cog.listener('on_message_all')
    # async def detect_submit_soooooper(self, message: Message):
    #     """tries to detect submissions to a 24-game question,
    #     without needing the user to reply to it and call the command"""
    #     # ~t~o~d~o~: implement 24-game answer detection without replying to the question message...
    #     pass
    #
    # in hindsight, probably not going to do this because deciding which question is the response for is ambiguous

    # ============= COMPUTATION FUNCTIONS ============= #

    def check_answer(self, answer: str, q_nums: list[int]) -> tuple[bool | None, str]:
        """checks if an answer is corret and provides a feedback message,
        returns tuple of (status, message)

        statuses:

        True = correct (is 24);
        False = incorrect (not 24);
        None = invalid answer (violates rules/invalid string)"""
        answer = answer.strip('`').strip()  # allow code block formatting

        try:
            if '_' in answer:  # Python allows _ in number literals, such as 4_3 (=43), but let's not allow that
                raise SyntaxError
            val = self.parser.parse(answer)  # safely evaluate the answer
        except SyntaxError:
            return None, 'Invalid expression syntax.'
        except TypeError:
            return None, 'Invalid expression content.'
        except ArithmeticError:
            return None, 'Only four basic operations are allowed: + - * / \n' \
                          '(and no leading minus because that\'s negation, not subtraction)'
        else:  # expression might already equal 24, but we have more checks to do:
            try:  # verify that the answer is valid; uses all four numbers, and only once each
                operators = '+-*/'
                numers = ''.join(map(str, q_nums))
                allowed_chars = operators + numers + '()'
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
                if not all(clean[i] in numers for i in (0, 2, 4, 6)):  # make sure the numbers are in their positions
                    raise ValueError
                nums = [clean[0], clean[2], clean[4], clean[6]]  # the digits only as a 4-long string
                for i in numers:  # make sure each number is used and used only once
                    nums.remove(i)

            except ValueError:
                return None, 'That doesn\'t seem like a valid answer'

            else:
                if math.isclose(val, 24):  # not much of a skill issue
                    return True, 'Correct answer. Took you `{}`'
                else:  # massive skill issue.
                    return False, f'`{val}` is definitely not `24`; try harder.'

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
    OPS: Final = {mul                                      : '*', sub: '-', add: '+',
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
