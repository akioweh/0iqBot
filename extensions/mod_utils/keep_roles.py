from typing import TYPE_CHECKING

from discord import Forbidden, Member

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


class KeepRoles(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.init_local_config(__file__)
        if 'keep_roles' not in self.local_config:
            self.local_config['keep_roles'] = {'logs': dict()}

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        roles = [role.id for role in member.roles[1:]]
        if not roles:
            return
        if member.id not in self.local_config['keep_roles']['logs']:
            self.local_config['keep_roles']['logs'] = {member.id: {member.guild.id: list()}}
        self.local_config['keep_roles']['logs'][member.id][member.guild.id] = roles
        self.save_local_config()

    @Cog.listener()
    async def on_verification_complete(self, member: Member):
        # On verification complete instead of on member join because
        # giving roles automatically skips member verification
        # which causes FAST automatic verification
        # and defeats the purpose of using skill to get a short time
        try:
            role_ids = self.local_config['keep_roles']['logs'][member.id][member.guild.id]
        except KeyError:
            return
        roles = [member.guild.get_role(i) for i in role_ids if member.guild.get_role(i)]

        try:
            await member.add_roles(*roles, reason='KeepRoles re-granting roles upon join', atomic=True)
        except Forbidden:
            pass


async def setup(bot: 'BotClient'):
    await bot.add_cog(KeepRoles(bot))
