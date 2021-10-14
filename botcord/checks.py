from discord.ext import commands
from discord.ext.commands import Context, MissingPermissions


def guild_owner_or_perms(**perms):
    has_perms = commands.has_permissions(**perms).predicate

    async def check_func(ctx: Context):
        if ctx.guild is None:
            return False
        return ctx.guild.owner_id == ctx.author.id or await has_perms(ctx)

    return commands.check(check_func)


def guild_admin_or_perms(**perms):
    has_perms = commands.has_permissions(**perms).predicate

    async def check_func(ctx: Context):
        if ctx.guild is None:
            return False
        return ctx.message.author.guild_permissions.administrator or await has_perms(ctx)

    return commands.check(check_func)


def has_global_perms(**perms):
    def predicate(ctx: Context):
        invalid = set(perms) - set(ctx.bot.configs['permissions'])
        if invalid:
            raise TypeError(f'Permission(s) {invalid} not found in Global Permissions.')

        missing = [perm for perm in perms if ctx.author.id not in ctx.bot.configs['permissions'][perm]]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return commands.check(predicate)


def has_custom_perms(**perms):
    def predicate(ctx: Context):
        guild = ctx.guild
        invalid = set(perms) - set(ctx.bot.guild_config(guild))
        if invalid:
            raise TypeError(f'Permission(s) {invalid} not found in Global Permissions.')

        missing = [perm for perm in perms if ctx.author.id not in ctx.bot.configs['permissions'][perm]]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return commands.check(predicate)
