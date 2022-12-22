import asyncio
import re
from typing import Final, TYPE_CHECKING

from bs4 import BeautifulSoup
from discord import Embed, HTTPException, Message, NotFound
from discord.ext.commands import Context, command
from fake_useragent import UserAgent

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


# TEMPLATE = {
#     "title"      : title,
#     "description": desc,
#     "url"        : url,
#     "color"      : color,
#     "author"     : {
#         "name"    : "Mojira Bug Report",
#         "url"     : r"https://bugs.mojang.com/",
#         "icon_url": r"https://avatars.githubusercontent.com/u/8507096"
#     },
#     "fields"     : [
#         {
#             "name"  : "Status",
#             "value" : status,
#             "inline": True
#         },
#         {
#             "name"  : "Votes",
#             "value" : votes,
#             "inline": True
#         },
#         {
#             "name"  : "Watching",
#             "value" : watching,
#             "inline": True
#         },
#         {
#             "name"  : "Type",
#             "value" : issue_type,
#             "inline": True
#         },
#         {
#             "name"  : "Resolution",
#             "value" : resolution,
#             "inline": True
#         },
#         {
#             "name"  : "Fixed Version",
#             "value" : fixed_ver,
#             "inline": True
#         },
#         {
#             "name"  : "Created",
#             "value" : created,
#             "inline": True
#         },
#         {
#             "name"  : "Updated",
#             "value" : updated,
#             "inline": True
#         },
#         {
#             "name"  : "Resolved",
#             "value" : resolved,
#             "inline": True
#         },
#         {
#             "name"  : "Reporter",
#             "value" : reporter,
#             "inline": True
#         },
#         {
#             "name"  : "Assignee",
#             "value" : assignee,
#             "inline": True
#         },
#         {
#             "name"  : "Priority",
#             "value" : priority,
#             "inline": True
#         }
#     ],
#     "footer"     : {
#         "text": f"Auto embed for message by {user_name}"
#     },
#     "timestamp"  : "2022-08-17T20:00:00.000Z"
# }


class Mojira(Cog):
    COLORS: Final[dict[str, int]] = {  # matches a "resolution" to a color code (base 10)
        "N/A"              : int('000000', 16),

        "Unresolved"       : int('ff0000', 16),  # Open

        "Invalid"          : int('808080', 16),  # Resolved (dismissed)
        "Duplicate"        : int('909962', 16),  # Resolved (dismissed)
        "Cannot Reproduce" : int('999999', 16),  # Resolved (dismissed)

        "Fixed"            : int('00ff00', 16),  # Resolved
        "Awaiting Response": int('64b327', 16),  # Resolved

        "Won't Fix"        : int('0000ff', 16),  # Resolved (nothing changed)
        "Works As Intended": int('105e13', 16)  # Resolved (nothing changed)
    }

    def __init__(self, bot):
        self.bot: 'BotClient' = bot
        self.fake_ua: UserAgent | None = None

        self.init_local_config(__file__)
        if 'use_fakeua' not in self.local_config:
            self.local_config['use_fakeua'] = False

    async def __init_async__(self):
        if self.local_config['use_fakeua']:
            # sometimes it takes a while to get the useragent data (such as no cache)
            self.fake_ua = await asyncio.to_thread(UserAgent)

    def _get_ua(self):
        if self.fake_ua is None:
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36"
        return self.fake_ua.edge

    @Cog.listener('on_message')
    async def _on_message(self, message: Message):
        """check if message contains mojira link or mojira bug id,
        and send embed if yes"""
        # don't trigger on commands (avoid duplicate embeds when using explicit embed command below)
        if await self.bot.does_trigger_command(message):
            return
        # checks for MC-#### bug id's in message
        if not (issue_ids := re.findall(r'\bMC-\d+\b', message.content)):
            return

        # remove duplicates and limit size to 3
        if not (issue_ids := list(set(issue_ids))[:3]):
            return
        # get and generate embed data, concurrently
        embed_dicts: tuple[dict | NotFound | HTTPException | ValueError, ...] = await asyncio.gather(
                *(self.get_embed(issue_id) for issue_id in issue_ids),
                return_exceptions=True
        )

        for embed_dict in embed_dicts:  # sends the embeds
            if not isinstance(embed_dict, dict):  # if embed_dict is not a dict, it's an exception
                continue
            await message.channel.send(embed=Embed.from_dict(embed_dict))

    @command(name='mojira', aliases=['moj'], ignore_extra=False)
    async def _mojira(self, ctx: Context, *, issue_id: str):
        """command to explicitly send embed for a mojira issue

        issue should be a full Minecraft: Java Edition bug id; MC-x"""
        try:
            embed_data = await self.get_embed(issue_id)

        except NotFound:
            await ctx.reply(f'Issue `{issue_id}` not found', delete_after=5)
        except HTTPException as e:
            await ctx.reply(f'Failed to get issue `{issue_id}` (`{e.status}`)', delete_after=5)
        except ValueError:
            await ctx.reply(f'Invalid issue id `{issue_id}`', delete_after=5)

        else:
            embed: Embed = Embed.from_dict(embed_data)
            await ctx.send(embed=embed)

    # ========== GENERATOR FUNCTION ========== #

    async def get_embed(self, issue_id: str) -> dict:
        """fetches issue from the mojira site,
        and return discord embed dict with a summary of the info
        (only supports ``Minecraft: Java Edition`` issues for now)

        :raises ValueError: if issue_id is obviously invalid
        :raises discord.NotFound: if issue page does not exist (404)
        :raises discord.HTTPException: if requesting for the page fails (not-200)"""

        if not re.fullmatch(r'MC-\d+', issue_id):  # only MC-x issues (no MCL, MCD, MCPE, etc.)
            raise ValueError(f"Obiously invalid mojira issue id: {issue_id}")

        url = f'https://bugs.mojang.com/browse/{issue_id}'
        headers = {'User-Agent': self._get_ua()}
        async with self.bot.aiohttp_session.get(url, headers=headers) as resp:
            if resp.status == 404:
                raise NotFound(resp, f"Mojira issue {issue_id} does not exist")
            if resp.status != 200:
                raise HTTPException(resp, f"Mojira issue {issue_id} returned status code {resp.status}")

            html: str = await resp.text()
        soup = BeautifulSoup(html, 'html.parser')
        # IDK but non-existent issues may not have a 404 response code for whatever reason
        # so, we check by html... requiring login basically means issue is not public or doesn't exist
        if soup.select('.error-image-canNotBeViewed') or soup.select('form#login-form'):
            raise NotFound(resp, f"Mojira issue {issue_id} does not exist")

        def find(selector: str) -> str:
            ele = soup.select_one(selector)
            return ele.text.strip() if ele is not None else 'N/A'

        title = find('h1#summary-val')
        desc = find('div#description-val')[:100]
        status = find('span#status-val')
        issue_type = find('span#type-val')
        resolution = find('span#resolution-val')
        fixed_ver = find('span#fixfor-val')
        created = find('span#created-val')
        updated = find('span#updated-val')
        resolved = find('span#resolutiondate-val')
        reporter = find('span#reporter-val')
        assignee = find('span#assignee-val')
        priority = find('div#customfield_12200-val')
        votes = find('aui-badge#vote-data')
        watching = find('aui-badge#watcher-data')
        color: int = self.COLORS.get(resolution, int('000000', 16))

        embed_data = {
            "title"      : title,
            "description": desc,
            "url"        : url,
            "color"      : color,
            "author"     : {
                "name"    : "Mojira Bug Report",
                "url"     : r"https://bugs.mojang.com/",
                "icon_url": r"https://avatars.githubusercontent.com/u/8507096"
            },
            "fields"     : [
                {
                    "name"  : "Status",
                    "value" : status,
                    "inline": True
                },
                {
                    "name"  : "Votes",
                    "value" : votes,
                    "inline": True
                },
                {
                    "name"  : "Watching",
                    "value" : watching,
                    "inline": True
                },
                {
                    "name"  : "Type",
                    "value" : issue_type,
                    "inline": True
                },
                {
                    "name"  : "Resolution",
                    "value" : resolution,
                    "inline": True
                },
                {
                    "name"  : "Fixed Version",
                    "value" : fixed_ver,
                    "inline": True
                },
                {
                    "name"  : "Created",
                    "value" : created,
                    "inline": True
                },
                {
                    "name"  : "Updated",
                    "value" : updated,
                    "inline": True
                },
                {
                    "name"  : "Resolved",
                    "value" : resolved,
                    "inline": True
                },
                {
                    "name"  : "Reporter",
                    "value" : reporter,
                    "inline": True
                },
                {
                    "name"  : "Assignee",
                    "value" : assignee,
                    "inline": True
                },
                {
                    "name"  : "Priority",
                    "value" : priority,
                    "inline": True
                }
            ]
        }

        return embed_data


async def setup(bot: 'BotClient'):
    await bot.add_cog(Mojira(bot))
