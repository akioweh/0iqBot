from discord.ext.commands import Command, Context


class AdminNoCooldown(Command):
    async def prepare(self, ctx: Context):
        if ctx.guild and ctx.message.author.guild_permissions.administrator:
            print('yes')
            ctx.command.reset_cooldown(ctx)
        await super().prepare(ctx)
