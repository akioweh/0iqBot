from os import getenv

import discord

from botcord import BotClient


def init():
    client = BotClient(status=discord.Status("online"),
                       activity=discord.Activity(name="YOU | -IQ help", type=3),
                       multiprocessing=3)
    client.run(getenv("TOKEN"))


init()
