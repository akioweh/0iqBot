from typing import TYPE_CHECKING

from discord import Forbidden, Member

from botcord.ext.commands import Cog

if TYPE_CHECKING:
    from botcord import BotClient


class KeepRoles(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot
        self.config_init(__file__)
        if 'keep_roles' not in self.config:
            self.config['keep_roles'] = {'logs': dict()}

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        roles = [role.id for role in member.roles[1:]]
        if not roles:
            return
        if member.id not in self.config['keep_roles']['logs']:
            self.config['keep_roles']['logs'] = {member.id: {member.guild.id: list()}}
        self.config['keep_roles']['logs'][member.id][member.guild.id] = roles
        self.save_config()

    @Cog.listener()
    async def on_member_join(self, member: Member):
        try:
            role_ids = self.config['keep_roles']['logs'][member.id][member.guild.id]
        except KeyError:
            return
        roles = [member.guild.get_role(i) for i in role_ids if member.guild.get_role(i)]

        try:
            await member.add_roles(*roles, reason='KeepRoles re-granting roles upon join', atomic=True)
        except Forbidden:
            pass


def setup(bot: 'BotClient'):
    bot.add_cog(KeepRoles(bot))
