"""
AntiSpam V1
2022-06-16
"""

import asyncio
import re
import time
from contextlib import suppress
from typing import Final, Iterable, Optional, TYPE_CHECKING

from discord import Embed, Forbidden, Member, Message
from discord.ext.commands import Context, group

from botcord.errors import ExtensionDisabledGuild
from botcord.ext.commands import Cog, guild_admin_or_perms
from botcord.utils.errors import protect

if TYPE_CHECKING:
    from botcord import BotClient

# Antispam score calculation fine-tuning parameters.
# Passed into non-linear functions. These numbers govern the behavior of antispam.
X = {
    'Rep_Lin_Dec': 0.01,  # Reputation passive reset rate towards 0 (points-per-second)

    'Rep_Grw_Mlt': 2.0,  # Reputation score growth multiplier
    'Rep_Grw_Scl': 4.,  # Reputation score growth scale

    'Msg_Len_Mlt': 1.0,  # Message length multiplier
    'Msg_Len_Scl': 1500,  # Message length scale

    'Msg_Men_Mlt': 5.0,  # Mention count multiplier
    'Msg_Men_Scl': 10.,  # Mention count scale

    'Msg_Att_Mlt': 3.0,  # Attachment count multiplier
    'Msg_Att_Scl': 8.0,  # Attachment count scale

    'Msg_Chr_Mlt': 2.0,  # Special character (non-ascii & special Discord objects) count multiplier
    'Msg_Chr_Scl': 300,  # Special character count scale
}


class Tracker:
    def __init__(self, member: Member, score: float = 0.0, mute_role_id=819097920368148501):
        self.member: Final = member
        self._score: float = score
        self._history: list[Message] = list()
        self._last_time: float = time.time()
        self.mute_role: Final = member.guild.get_role(mute_role_id)
        self.unmute_schedule: Optional[asyncio.Task] = None

    @property
    def score(self) -> float:
        offset = (time.time() - self._last_time) * X['Rep_Lin_Dec']
        if offset > abs(self._score):
            self._score = 0.0
        elif self._score > 0:
            self._score -= offset
        else:
            self._score += offset

        self._last_time = time.time()
        return self._score

    @score.setter
    def score(self, value: float):
        self._score = value

    @property
    def history(self) -> list[Message]:
        return self._history

    def add_history(self, msg: Message):
        self._history.insert(0, msg)
        if len(self._history) > 10:
            self._history = self._history[:10]

    def _clear_unmute(self, _):
        if _ != self.unmute_schedule:
            raise ValueError('something about the muting system completely bonked itself')
        if not self.unmute_schedule.done():
            raise ValueError('Unmute task has not completed yet but tried to remove reference')
        self.unmute_schedule = None

    def time_until_score(self, score: float) -> float:
        """Estimates time in seconds for current score to naturally decay to a target value"""
        if (self.score - score) * self.score < 0:  # Makes sure the target score is between the current score and 0
            raise ValueError(f'A current score of {self.score} will never naturally decay to {score}')

        return abs(self.score - score) / X['Rep_Lin_Dec']

    @property
    def muted(self) -> bool:
        if self.unmute_schedule is None:
            return False
        else:
            if self.unmute_schedule.done():
                raise ValueError('Unmute scheduled task is done but reference was not removed.')
            return True

    async def mute(self, duration: float = 60.):
        if self.muted:
            raise ValueError('Tried to mute member that was already muted...???')

        async def unmute_scheduled_task():
            await asyncio.sleep(duration)
            await self.member.remove_roles(self.mute_role, atomic=True)

        self.unmute_schedule = asyncio.create_task(unmute_scheduled_task())
        self.unmute_schedule.add_done_callback(self._clear_unmute)
        await self.member.add_roles(self.mute_role, atomic=True)

    async def unmute(self):
        if not self.muted:
            raise ValueError('Tried to unmute member that was never muted...???')

        if not self.unmute_schedule.done():
            self.unmute_schedule.cancel()
        self.unmute_schedule = None
        await self.member.remove_roles(self.mute_role, atomic=True)


class AntiSpam(Cog):
    @staticmethod
    def sigmoidy(x, in_max=1., out_max=1.) -> float:
        return (1 / (1 + 15.7 ** (-3 * (x / in_max) + 1.5))) * out_max if x != 0 else 0

    @staticmethod
    def paraboly(x, in_max=1., out_max=1.) -> float:
        return min((1.1 * (x / in_max) + 0.3) ** 2.1 - 0.04, (x / in_max) + 1) * out_max if x != 0 else 0

    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self._trackers: dict[Member, Tracker] = dict()
        self.config_init(__file__)

        default_config = {'flag_threshold': -5, 'mute_threshold': -6.5, 'unmute_reserve': -0.3,
                          'enabled_guilds': {}}
        default_config.update(self.config)
        self.config.update(default_config)

    @property
    def enabled_guids(self) -> Iterable[int]:
        return self.config['enabled_guilds'].keys()

    @Cog.listener(name='on_message_all')
    async def _process_message(self, msg: Message):
        if msg.author.bot or not msg.guild:
            return
        if msg.guild.id not in self.enabled_guids:
            raise ExtensionDisabledGuild(f'AntiSpam is disabled for guild {msg.guild.name} ({msg.guild.id}).',
                                         name=type(self).__name__)

        if msg.author not in self._trackers:
            self._trackers[msg.author] = Tracker(msg.author)

        data = await self._update_score(msg)
        await self._process_score(msg.author, data_log=data, msg=msg)

    async def _update_score(self, msg: Message) -> \
            tuple[float, tuple[int, int, int, int, int, int, float, float, float, float, float, float, float]]:
        tracker = self._trackers[msg.author]

        msg_ascii = msg.content.encode('ascii', 'ignore').decode()
        non_asciis = len(msg.content) - len(msg_ascii)
        disc_objs = len(re.findall(r'<(:\w+:|@|#|@&)\d{18}>', msg.content))
        unique_mentions = set(msg.mentions)
        unique_mentions = list(filter(lambda x: x.id != msg.author.id and not x.bot, unique_mentions))
        unique_mentions += list(set(msg.role_mentions))

        msg_len = len(msg.content)
        msg_men = len(unique_mentions)
        msg_att = len(msg.attachments)
        msg_chr = non_asciis + disc_objs

        if msg.reference and msg.reference.cached_message and msg.reference.cached_message.author in msg.mentions:
            msg_men -= 1  # negate two ping-counts when someone is reply-mentioned and explicitly mentioned

        scr_len = AntiSpam.sigmoidy(msg_len, X['Msg_Len_Scl'], X['Msg_Len_Mlt'])  # Message Text Length
        scr_men = AntiSpam.paraboly(msg_men, X['Msg_Men_Scl'], X['Msg_Men_Mlt'])  # Message User/Role Mentions
        scr_att = AntiSpam.sigmoidy(msg_att, X['Msg_Att_Scl'], X['Msg_Att_Mlt'])  # Message Attachments
        scr_chr = AntiSpam.sigmoidy(msg_chr, X['Msg_Chr_Scl'], X['Msg_Chr_Mlt'])  # Special Characters

        raw_score = - sum((scr_len, scr_men, scr_att, scr_chr))

        rep_mlt = AntiSpam.sigmoidy(abs(tracker.score), X['Rep_Grw_Scl'], X['Rep_Grw_Mlt']) + 1
        score = rep_mlt * raw_score

        tracker.score += score

        return tracker.score, (
            non_asciis, disc_objs, msg_len, msg_men, msg_att, msg_chr, scr_len, scr_men, scr_att, scr_chr, raw_score,
            rep_mlt, score)

    async def _detail_log(self, msg: Message, data: tuple) -> str:
        chl_id = self.config['enabled_guilds'][msg.guild.id]['detail_log_channel']
        if not chl_id:
            return 'detailed logging not enabled'
        chl = self.bot.get_channel(chl_id)
        if not chl:
            raise ValueError(f'didnt find detail-log channel for antispam for guild {msg.guild.name} ({msg.guild.id})')

        score, data = data

        log = \
            f'{msg.author.mention} sent [this]({msg.jump_url}) in {msg.channel.mention} \n' \
            f'Contents: \n{msg.content} \n\n Attachments: \n{msg.attachments} \n\n' \
            f'`Non-ASCII:` `{data[0]:<4}` \n' \
            f'`Mentions :` `{data[1]:<4}` \n' \
            f'`Msg_Len  :` `{data[2]:<4}` `=>` `{data[6]:.4f}` \n' \
            f'`Msg_Men  :` `{data[3]:<4}` `=>` `{data[7]:.4f}` \n' \
            f'`Msg_Att  :` `{data[4]:<4}` `=>` `{data[8]:.4f}` \n' \
            f'`Msg_Chr  :` `{data[5]:<4}` `=>` `{data[9]:.4f}` \n\n' \
            f'`Tot_Raw  :` `{data[10]}` \n' \
            f'`Final    :` `{round(data[10], 3)}` * `{round(data[11], 3)}` = **`{round(data[12], 3)}`** \n\n' \
            f'`Rep_Scr  :` `{score}` \n'

        embed_data = {
            "type"       : "rich",
            "title"      : f"AntiSpam Logged `{msg.author.name}` | Score: `{round(score, 5)}`",
            "description": log,
            "color"      : 16711680
        }

        return (await chl.send(embed=Embed.from_dict(embed_data))).jump_url

    async def _flagged_log(self, msg: Message, log_url: str):
        chl_id = self.config['enabled_guilds'][msg.guild.id]['flagged_log_channel']
        if not chl_id:
            return
        chl = self.bot.get_channel(chl_id)
        if not chl:
            raise ValueError(f'didnt find flag-log channel for antispam for guild {msg.guild.name} ({msg.guild.id})')

        embed_data = {
            "type"       : "rich",
            "title"      : f"AntiSpam Flagged {msg.author.name}",
            "description": f"Detailed log at: {log_url}",
            "color"      : 16711680
        }

        await chl.send(embed=Embed.from_dict(embed_data))

    async def _process_score(self, member: Member, *, data_log=None, msg: Message = None):
        tracker = self._trackers[member]
        score = tracker.score
        if msg:
            with protect(compact=True):
                log_url = await self._detail_log(msg, data_log)

            if score < self.config['flag_threshold']:
                with protect(compact=True):
                    await self._flagged_log(msg, log_url)

                with suppress(Forbidden):
                    await msg.channel.send(f'{member.mention} stop spam or mute.')

        if score < self.config['mute_threshold']:
            if not tracker.muted:
                unmute_delay = tracker.time_until_score(self.config['unmute_reserve'])
                await tracker.mute(unmute_delay)
                with suppress(Forbidden):
                    msg and await msg.channel.send(f'{member.mention} get muted heheheha')

        elif score > self.config['unmute_reserve']:
            if tracker.muted:
                print(f'prematurely cancelling scheduled unmute task for {member} because apparently score went past unmute reserve')
                await tracker.unmute()

    def score_of(self, member: Member) -> float:
        if member not in self._trackers:
            self._trackers[member] = Tracker(member)
        return self._trackers.get(member).score

    def set_score(self, member: Member, value: float):
        if member in self._trackers:
            self._trackers[member].score = value
        else:
            self._trackers[member] = Tracker(member, value)

    # ============= USER DISCORD COMMANDS ============= #

    @group(name='anti_spam', aliases=['antispam', 'as'])
    @guild_admin_or_perms(manage_roles=True)
    async def _anti_spam(self, ctx: Context):
        if ctx.guild.id not in self.enabled_guids:
            raise ExtensionDisabledGuild(f'AntiSpam is disabled for guild {ctx.guild.name} ({ctx.guild.id}).',
                                         name=type(self).__name__)

    @_anti_spam.command(name='set_score', aliases=['setscore', 'set'])
    @guild_admin_or_perms(manage_roles=True)
    async def _set_score(self, ctx: Context, member: Member, value: float):
        prev_score = self.score_of(member)
        self.set_score(member, value)
        await self._process_score(member)
        await ctx.send(f'Score of `{member.display_name}` has been changed from `{prev_score:.4}` to `{value}`')

    @_anti_spam.command(name='get_score', aliases=['getscore', 'get'])
    @guild_admin_or_perms(manage_roles=True)
    async def _get_score(self, ctx: Context, member: Member):
        score = self.score_of(member)
        await ctx.send(f'Score of `{member.display_name}` is `{score:.4f}`')

    @_anti_spam.command(name='unmute')
    @guild_admin_or_perms(manage_roles=True)
    async def _unmute(self, ctx: Context, member: Member):
        if member not in self._trackers:
            self._trackers[member] = Tracker(member)

        tracker = self._trackers.get(member)
        if tracker.muted:
            await tracker.unmute()
            await ctx.reply(f'Unmuted `{member.display_name}`')
        else:
            await ctx.reply(f'`{member.display_name}` is already unmuted. '
                            f'(If they have the mute role, it was not automatically given by AntiSpam)')

    @_anti_spam.command(name='mute')
    @guild_admin_or_perms(manage_roles=True)
    async def _mute(self, ctx: Context, member: Member, duration: int):
        if member not in self._trackers:
            self._trackers[member] = Tracker(member)

        tracker = self._trackers.get(member)
        await tracker.mute(duration)
        await ctx.reply('ok boomer muted.')


def setup(bot: 'BotClient'):
    bot.add_cog(AntiSpam(bot))
