"""Commands for managing extensions."""

from typing import TYPE_CHECKING

from discord.ext.commands import Context, group

from ..ext.commands.checks import has_global_perms
from ..ext.commands.cog import Cog
from ..utils.extensions import full_extension_path, parent_package_path

if TYPE_CHECKING:
    from ..botclient import BotClient


class PkgMgr(Cog):
    def __init__(self, bot: 'BotClient'):
        self.bot = bot

    @group(invoke_without_command=True, hidden=True)
    @has_global_perms(owner=True)
    async def pkgmgr(self, ctx: Context):
        """Discord-command interface to manage the bot's extensions."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.pkgmgr)

    # noinspection DuplicatedCode
    @pkgmgr.command()
    @has_global_perms(owner=True)
    async def load(self, ctx: Context, extension: str):
        """loads ONE extension in the form of a module (specified by its str name)"""
        try:
            qualified_name = full_extension_path(extension, self.bot.ext_module)
            if qualified_name in self.bot.extensions.keys():
                raise ImportError(f'Extension `{extension}` (`{qualified_name}`) is already loaded.')
            await self.bot.load_extension(qualified_name)
            await ctx.reply(f'Extension `{extension}` (`{qualified_name}`) loaded.')
        except (ImportError, NameError) as e:
            await ctx.reply(e)

    # noinspection DuplicatedCode
    @pkgmgr.command()
    @has_global_perms(owner=True)
    async def unload(self, ctx: Context, extension: str):
        """unloads ONE extension in the form of a module (specified by its str name)"""
        try:
            qualified_name = full_extension_path(extension, self.bot.ext_module)
            if qualified_name not in self.bot.extensions.keys():
                raise ImportError(f'Extension `{extension}` (`{qualified_name}`) is not loaded.')
            await self.bot.unload_extension(qualified_name)
            await ctx.reply(f'Extension `{extension}` (`{qualified_name}`) unloaded.')
        except(ImportError, NameError) as e:
            await ctx.reply(e)

    # noinspection DuplicatedCode
    @pkgmgr.command()
    @has_global_perms(owner=True)
    async def reload(self, ctx: Context, extension: str):
        """reloads ONE extension in the form of a module (specified by its str name)"""
        try:
            qualified_name = full_extension_path(extension, self.bot.ext_module)
            if qualified_name not in self.bot.extensions.keys():
                raise ImportError(f'Extension `{extension}` (`{qualified_name}`) is not loaded.')
            await self.bot.reload_extension(qualified_name)
            await ctx.reply(f'Extension `{extension}` (`{qualified_name}`) reloaded.')
        except(ImportError, NameError) as e:
            await ctx.reply(e)

    @pkgmgr.command()
    @has_global_perms(owner=True)
    async def list(self, ctx: Context):
        """lists all loaded extensions"""
        msg = '__**Loaded extensions**__:\n (``✅ -> enabled``; ``❌ -> disabled``; ``❔ -> unknown``)\n'

        for ext in self.bot.extensions.keys():
            try:  # try to get the extension's enabled status for the current guild
                enabled = self.bot.guild_config(ctx.guild)['ext'][parent_package_path(ext, self.bot.ext_module_name)]['enabled']
                status = '✅' if enabled else '❌'
            except (KeyError, FileNotFoundError):
                status = '❔'

            full_name = ext.rpartition('.')
            msg += f'``{status} {full_name[0]}{full_name[1]}``**``{full_name[2]}``**\n' if full_name[2] else f'**``{full_name[0]}``**\n'

        await ctx.reply(msg)


async def setup(bot: 'BotClient'):
    await bot.add_cog(PkgMgr(bot))
