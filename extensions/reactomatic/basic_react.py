from discord import Forbidden


async def react(message, reaction):
    try:
        await message.add_reaction(reaction)
    except Forbidden:
        pass
