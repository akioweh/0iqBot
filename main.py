from os import getenv

import discord

from botcord import BotClient


def init():
    CLIENT = BotClient(status=discord.Status("online"),
                       activity=discord.Activity(name="YOU | -IQ help", type=3))
    CLIENT.run(getenv("TOKEN"))


init()
