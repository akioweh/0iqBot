"""
Additional check functions to restrict command execution

same format/usage as builtin :package:`discord.ext.commands` checks
"""

from discord import Member
from discord.ext.commands import Context, MissingPermissions, check as _to_check_func, has_permissions as _has_perms

__all__ = ['guild_owner_or_perms', 'guild_admin_or_perms', 'has_global_perms', 'has_custom_perms']


def guild_owner_or_perms(**perms: bool):
    has_perms = _has_perms(**perms).predicate

    async def check_func(ctx: Context):
        if ctx.guild is None:
            return False
        return ctx.guild.owner_id == ctx.author.id or await has_perms(ctx)

    return _to_check_func(check_func)


def guild_admin_or_perms(**perms: bool):
    has_perms = _has_perms(**perms).predicate

    async def check_func(ctx: Context):
        if not isinstance(ctx.message.author, Member):  # === if ctx.guild is None:
            return False
        return ctx.message.author.guild_permissions.administrator or await has_perms(ctx)

    return _to_check_func(check_func)


def has_global_perms(**perms: bool):
    def predicate(ctx: Context):
        invalid = set(perms) - set(ctx.bot.configs['permissions'])
        if invalid:
            raise TypeError(f'Permission(s) {invalid} not found in Global Permissions.')

        missing = [perm for perm in perms if ctx.author.id not in ctx.bot.configs['permissions'][perm]]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return _to_check_func(predicate)


def has_custom_perms(**perms: bool):
    def predicate(ctx: Context):
        guild = ctx.guild
        invalid = set(perms) - set(ctx.bot.guild_config(guild))
        if invalid:
            raise TypeError(f'Permission(s) {invalid} not found in Global Permissions.')

        missing = [perm for perm in perms if ctx.author.id not in ctx.bot.configs['permissions'][perm]]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return _to_check_func(predicate)
