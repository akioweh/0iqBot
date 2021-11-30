import re
import time
from typing import TYPE_CHECKING

from discord import Embed, Message

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


# noinspection PyShadowingBuiltins
def print_(*_):
    pass


X = {
    'Rep_Lin_Dec': 0.01,

    'Rep_Grw_Mlt': 2.0,
    'Rep_Grw_Scl': 4.,

    'Msg_Len_Mlt': 1.0,
    'Msg_Len_Scl': 1500,

    'Msg_Men_Mlt': 5.0,
    'Msg_Men_Scl': 10.,

    'Msg_Att_Mlt': 3.0,
    'Msg_Att_Scl': 8.0,

    'Msg_Chr_Mlt': 2.0,
    'Msg_Chr_Scl': 300,
}


class Reputation:
    def __init__(self):
        self._score = 0
        self._history = []
        self._last_time = time.time()

    @property
    def score(self):
        offset = (time.time() - self._last_time) * X['Rep_Lin_Dec']
        if offset > abs(self._score):
            self._score = 0.0
        elif self._score > 0:
            self._score -= offset
        elif self._score < 0:
            self._score += offset
        # print(f'offset of {offset} from {time.time() - self._last_time}')
        self._last_time = time.time()
        return self._score

    @score.setter
    def score(self, value):
        if not (-100 < value < 100):
            print(f'setting an extreme score of {value}')
        self._score = value
        print(f'current score: {self._score}')

    @property
    def history(self):
        return self._history

    def add_history(self, msg):
        self._history.append(msg)
        if len(self._history) > 10:
            self._history = self._history[:10]


class AntiSpam(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.reputations = {}

    @Cog.listener()
    async def on_message_all(self, msg: Message):
        if msg.author.bot:
            return
        if not msg.guild:
            return

        if msg.author not in self.reputations:
            self.reputations[msg.author] = Reputation()

        await self.process_msg(msg)

    # noinspection PyProtectedMember
    async def process_msg(self, msg: Message):
        log = ''
        log += f'{msg.author.mention} sent [this]({msg.jump_url}) in {msg.channel.mention} \n' \
               f'Contents: \n{msg.content} \n\n Attachments: \n{msg.attachments} \n\n'

        tracker = self.reputations[msg.author]

        msg_ascii = msg.content.encode('ascii', 'ignore').decode()
        non_asciis = len(msg.content) - len(msg_ascii)
        mentions = len(re.findall(r'<(:\w+:|@|#|@&)\d{18}>', msg.content))

        log += f'`Non-ASCII:` `{"{:<4}".format(non_asciis)}` \n'
        log += f'`Mentions :` `{"{:<4}".format(mentions)}` \n'

        msg_len = len(msg.content)
        msg_men = len(msg.mentions) + len(msg.role_mentions)
        msg_att = len(msg.attachments)
        msg_chr = non_asciis + mentions

        if msg.reference and msg.reference.cached_message and msg.reference.cached_message.author in msg.mentions:
            log += f'ReplyPinged {len(msg.mentions)} - 1 \n'
            msg_men -= 1

        scr_len = sigmoidy(msg_len, X['Msg_Len_Scl'], X['Msg_Len_Mlt'])  # Message Text Length
        scr_men = paraboly(msg_men, X['Msg_Men_Scl'], X['Msg_Men_Mlt'])  # Message User/Role Mentions
        scr_att = sigmoidy(msg_att, X['Msg_Att_Scl'], X['Msg_Att_Mlt'])  # Message Attachments
        scr_chr = sigmoidy(msg_chr, X['Msg_Chr_Scl'], X['Msg_Chr_Mlt'])  # Special Characters

        log += f'`Msg_Len  :` `{"{:<4}".format(msg_len)}` `=>` `{"{:.4f}".format(scr_len)}` \n' \
               f'`Msg_Men  :` `{"{:<4}".format(msg_men)}` `=>` `{"{:.4f}".format(scr_men)}` \n' \
               f'`Msg_Att  :` `{"{:<4}".format(msg_att)}` `=>` `{"{:.4f}".format(scr_att)}` \n' \
               f'`Msg_Chr  :` `{"{:<4}".format(msg_chr)}` `=>` `{"{:.4f}".format(scr_chr)}` \n\n'

        raw_score = - sum((scr_len, scr_men, scr_att, scr_chr))

        rep_mlt = sigmoidy(abs(tracker.score), X['Rep_Grw_Scl'], X['Rep_Grw_Mlt']) + 1
        score = rep_mlt * raw_score
        log += f'`Tot_Raw  :` `{raw_score}` \n' \
               f'`Final    :` `{round(rep_mlt, 3)}` * `{round(raw_score, 3)}` = **`{round(score, 3)}`** \n\n'

        tracker._score += score
        log += f'`Rep_Scr  :` `{tracker._score}` \n'

        print(log)

        # if tracker._score <= -5:
        await self.temp_log(msg, log)

    # noinspection PyProtectedMember
    async def temp_log(self, msg: Message, log: str):
        chl = self.bot.get_channel(914032751433371709)
        if not chl:
            print('didnt find log channel for antispam')
            return
        tracker = self.reputations[msg.author]

        embed_data = {
            "type"       : "rich",
            "title"      : f"AntiSpam Flagged `{msg.author.name}` | Score: `{round(tracker._score, 5)}`",
            "description": log,
            "color"      : 16711680
        }

        embed_obj = Embed.from_dict(embed_data)
        await chl.send(embed=embed_obj)


def sigmoidy(x, in_max=1., out_max=1.):
    return (1 / (1 + 15.7 ** (-3 * (x / in_max) + 1.5))) * out_max if x != 0 else 0


def paraboly(x, in_max=1., out_max=1.):
    return min((1.1 * (x / in_max) + 0.3) ** 2.1 - 0.04, (x / in_max) + 1) * out_max if x != 0 else 0


def setup(bot: 'BotClient'):
    bot.add_cog(AntiSpam(bot))
