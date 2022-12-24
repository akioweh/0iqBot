import itertools
from typing import Mapping, TYPE_CHECKING

from discord import Embed, Forbidden
from discord.ext.commands import (Bot, Cog, Command, DefaultHelpCommand as _DefaultHelpCommand,
                                  Group)

from botcord.utils import protect

if TYPE_CHECKING:
    from botcord import BotClient


class HelpCommand(_DefaultHelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.color = options.pop('color', 0xFF5500)

    async def send_embed(self, embed: Embed) -> None:
        try:
            await self.get_destination().send(embed=embed)
        except Forbidden:
            with protect(Forbidden):
                await self.get_destination().send('Failed to send help. The `Embed Links` permission is required.')

    async def send_bot_help(self, mapping: Mapping[Cog | None, list[Command]], /) -> None:
        ctx = self.context
        bot: BotClient | Bot = ctx.bot
        tab = '\u3164'
        embed = Embed(
                title='Help',
                description=f'Valid prefixes: `{"` | `".join(await bot.command_prefix(bot, ctx.message))}`',
                color=self.color
        )

        if bot.description:
            # <description> portion
            embed.description = f'{bot.description}\n{embed.description}'

        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else 'No Category'

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name)
            embed.add_field(
                    name=category,
                    value='\n'.join(f'{tab}`{c.name}`' +
                                    (f'\n{tab} ↳ {c.short_doc}' if c.short_doc else '')
                                    for c in commands),
                    inline=False
            )

        embed.set_footer(
                text=f'Type `{self.context.clean_prefix}{self.invoked_with} <command>` for more info on a command.\n'
                     f'You can also type `{self.context.clean_prefix}{self.invoked_with} <category>` for more info on a category.'
        )

        await self.send_embed(embed)

    async def send_cog_help(self, cog: Cog, /) -> None:
        tab = '\u3164'
        embed = Embed(
                title=f'{cog.qualified_name} Commands',
                description=f'`{cog.description}`' if cog.description else 'No Group Description',
                color=self.color
        )

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for command in filtered:
            embed.add_field(
                    name=f'`{command.name}`',
                    value=tab + (command.short_doc or 'N/A'),
                    inline=False
            )
        await self.send_embed(embed)

    async def send_group_help(self, group: Group, /) -> None:
        embed = Embed(title=f'`{group.name}`', color=self.color)
        embed.add_field(name='Description', value=group.help or 'N/A', inline=False)
        embed.add_field(
                name='Arguments',
                value=f'`{group.usage or group.signature or "None"}`',
                inline=False
        )
        await self.send_embed(embed)

    async def send_command_help(self, command: Command, /) -> None:
        embed = Embed(title=f'`{command.name}`', color=self.color)
        embed.add_field(name='Description', value=command.help or 'N/A', inline=False)
        embed.add_field(
                name='Arguments',
                value=f'`{command.usage or command.signature or "None"}`',
                inline=False
        )
        await self.send_embed(embed)
