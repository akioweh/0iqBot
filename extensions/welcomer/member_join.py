import datetime
from typing import TYPE_CHECKING

from discord import Embed, Member
from discord.ext.commands import Cog

from botcord.functions import log

if TYPE_CHECKING:
    from botcord import BotClient


class Welcomer(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot

    async def get_welcome_channel(self, guild):
        if not (welcome_channel_id := self.bot.ext_guild_config('welcomer', guild)['welcome_channel']):
            log(f'Could not find welcome channel ID in configuration file for guild {guild.id}')
            return None
        if not (welcome_channel := guild.get_channel(welcome_channel_id)):
            log(f'Could not find welcome channel {welcome_channel_id} in guild {guild.id}', tag='Error')
            return None
        return welcome_channel

    @Cog.listener()
    async def on_member_join(self, member: Member):
        if not (welcome_channel := await self.get_welcome_channel(member.guild)):
            return

        embed_data = {
            "type"       : "rich",
            "title"      : f"Welcome `{member.name}` to {member.guild.name}!",
            "description": f"**You are Member #`{member.guild.member_count}`\nGlad to see you here, "
                           f"{member.mention}! 👋**\n\nNow that you see this message, please, please, please, "
                           f"do not just leave straight away <:pepesmile:867100567151181824>, please. *Well, "
                           f"I can't really stop you... can I?*",
            "color"      : 16711680,
            "author"     : {
                "name"    : f"{member.name}#{member.discriminator}",
                "icon_url": str(member.avatar.url)
            },
            "footer"     : {
                "text": "Stay, at least on account of not being greeted by 50 pings and 5 blocked MEE6 messages."
            }
        }

        embed_obj = Embed.from_dict(embed_data)
        await welcome_channel.send(content="<@&770590410485530644> A New Member Has Joined!!!", embed=embed_obj)

    @Cog.listener()
    async def on_verification_complete(self, member: Member):
        if not (welcome_channel := await self.get_welcome_channel(member.guild)):
            return
        time_difference = datetime.datetime.utcnow() - member.joined_at
        await welcome_channel.send(f'It took `{member.name}` **`{time_difference}`** '
                                   f'to complete the Member Verification. <:pepesmile:867100567151181824>')

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        if not (welcome_channel := await self.get_welcome_channel(member.guild)):
            return
        await welcome_channel.send(
            f'**`{member.name}#{member.discriminator}`** just left the server <:sad:736527953235804161>')


async def setup(bot: 'BotClient'):
    await bot.add_cog(Welcomer(bot))
