import re
from asyncio import TimeoutError
from typing import List, Optional, TYPE_CHECKING, Tuple, Union

from discord import Message

from botcord.ext.commands import Cog
from botcord.functions import log

if TYPE_CHECKING:
    from botcord import BotClient


def is_bj_message(message: Message) -> bool:
    if not message.author.id == 270904126974590976:
        return False
    if not message.embeds:
        return False
    try:
        embed = message.embeds[0].to_dict()
        if re.findall(r'(?<=\[`. )(\d|10|J|Q|K|A)(?=`])', embed['fields'][0]['value']):
            return True
    except (KeyError, ValueError, IndexError):
        pass
    return False


def parse_cards(string: str) -> List[Optional[Union[str, int]]]:
    results: List[Union[str, int]] = re.findall(r'(?<=\[`. )(\d|10|J|Q|K|A)(?=`])', string)
    if not results:
        log(f'Error in bj card parsing: No card found: \n{string}', tag='Error')
        return []

    for i in range(len(results)):
        if results[i] in 'JQK':
            results[i] = 10
        elif results[i] == 'A':
            results[i] = 0
        elif results[i] in '2345678910':
            results[i] = int(results[i])
        else:
            log(f'Error in bj card parsing: Unknown card {results[i]}', tag='Error')

    return results


def sum_cards(cards: list) -> Tuple[int, bool]:
    total = sum(cards)
    soft = False

    aces = cards.count(0)
    for i in range(aces):
        if total <= 10:
            total += 11
            soft = True
        else:  # total >= 11
            total += 1
    return total, soft


def best_move(player: int, soft: bool, dealer: int) -> str:
    if soft:
        if player >= 19:
            return 's'
        elif player == 18:
            if dealer >= 9:
                return 'h'
            else:  # dealer <= 8
                return 's'
        else:  # player <= 17
            return 'h'
    else:  # hard
        if player >= 17:
            return 's'
        elif 13 <= player <= 16:
            if dealer >= 7:
                return 'h'
            else:  # dealer <= 6
                return 's'
        elif player == 12:
            if dealer <= 3:
                return 'h'
            elif 4 <= dealer <= 6:
                return 's'
            else:  # dealer >= 7
                return 'h'
        else:  # player <= 11
            return 'h'


async def bj_assist(message: Message, response: Message = None):
    embed = message.embeds[0].to_dict()

    user_cards = parse_cards(embed['fields'][0]['value'])
    dealer_cards = parse_cards(embed['fields'][1]['value'])

    user_total, user_soft = sum_cards(user_cards)
    dealer_top = dealer_cards[0]
    msg = f'Your total: **`{"A+" + str(user_total - 11) if user_soft else user_total}`** | Dealer top card: **`{dealer_top}`** \nYou should: **{best_move(user_total, user_soft, dealer_top)}**'
    if response:
        edited = await response.edit(content=msg)
        return edited if edited else response
    else:
        return await message.channel.send(msg)


class BlackJackAssist(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot

    @Cog.listener('on_message')
    async def new_bj_session(self, bj_msg: Message):
        if is_bj_message(bj_msg):
            session_id = bj_msg.id
            assist_msg = None

            def bj_message_check(_, msg):
                return is_bj_message(msg) and msg.id == session_id

            for i in range(10):
                assist_msg = await bj_assist(bj_msg, assist_msg)
                try:
                    _, bj_msg = await self.bot.wait_for('message_edit', check=bj_message_check, timeout=20)
                except TimeoutError:
                    break


async def setup(bot: 'BotClient'):
    await bot.add_cog(BlackJackAssist(bot))
