import warnings
from collections.abc import Sequence
from os import getcwd, path
from typing import TYPE_CHECKING

from discord.abc import Snowflake
from discord.ext.commands import Cog as _bruh_do_not_import_this_Cog

from botcord.configs import YAML_rw, recursive_update
from botcord.utils.extensions import parent_package_path, resolve_extension_path

if TYPE_CHECKING:
    from botcord import BotClient

__all__ = ['Cog']


# noinspection PyAttributeOutsideInit
class Cog(_bruh_do_not_import_this_Cog):
    """
    Same as :class:`discord.ext.commands.Cog` but with extra file-based configuration features.
    Allows the cog to conveniently save and access data from a config file.

    Your custom extension class should inherit this class the same way you use the ordinary Cog.

    This class offers two structurally different ways of accessing and storing configurations:

    One is guild-based, where each guild has its own independent configuration dictionary.
    The other is global, where one configuration file serves the entire extension/cog as a whole, and do not natively
    relate to any guilds.

    The guild-based configuration options are stored inside BotCord generic guild configuration files under a
    sub-dictionary named after the extension's name.
    The global configuration options are stored inside the extension's own configuration file which lives in the same
    directory as the code file of the extension.


    Global config methods and attributes:
        ``init_local_config()`` must be called (only once) during cog setup before using local config features;
        it reads any data from the local config file on disk to be accessed via ``self.local_config`` as a dictionary

        ``save_local_config()``, ``load_local_config()``, and ``refresh_local_config()`` methods are self-explanatory


    Per-guild config methods and attributes:
        ``config(guild)`` returns ``guild``'s config as a dictionary.

        ``save_config(guild)``, ``load_config(guild)``, and ``refresh_config(guild)`` methods are self-explanatory
    """
    bot: 'BotClient'

    def _inject(
            self,
            bot: 'BotClient',  # type: ignore
            override: bool,
            guild: Snowflake | None,
            guilds: Sequence[Snowflake]
    ):
        # Makes sure self.bot is always set
        if getattr(self, 'bot', None) is None:
            self.bot = bot
        return super()._inject(bot, override, guild, guilds)

    def init_local_config(self, module_path: str, file_name: str = 'configs.yml'):
        """PASS THE __file__ VARIABLE IN AS AN ARGUMENT FROM THE EXTENSION FILE,
        SO THE CONFIG PATH IS IN THE EXTENSION'S FOLDER AND NOT IN THE BOTCORD FILES HERE

        It should always look like: ``self.init_local_config(__file__)``
        """
        if getattr(self, '_configed', False):
            raise RuntimeError('init_local_config() has already been called, but was called again')

        cwd = path.abspath(getcwd())
        dir_path = path.dirname(path.abspath(module_path))
        if not path.commonpath([cwd, dir_path]) == path.commonpath([cwd, cwd]):
            warnings.warn(f'Confile file directory {dir_path} is not relative to the current working directory {cwd}.')
        self._config_dir = path.join(dir_path, file_name)
        self.load_local_config()
        self._configed = True

    def save_local_config(self):
        """overwrites config on disk with config in memory"""
        with open(self._config_dir, mode='w', encoding='UTF-8') as file:
            YAML_rw.dump(self.local_config, file)

    def load_local_config(self):
        """overwrites config in memory with config on disk"""
        self._config = self._read_local_config()

    def refresh_local_config(self):
        """recursively merges configs from disk and memory
        (disk as base, memory as overwrite)
        THEN saves merged to disk"""
        file_conf = self._read_local_config()
        recursive_update(file_conf, self.local_config)
        self.save_local_config()

    def _read_local_config(self) -> dict:
        """reads and returns config from disk"""
        with open(self._config_dir, mode='a+', encoding='UTF-8') as file:
            file.seek(0)
            config = YAML_rw.load(file)
            return config or {}

    @property
    def local_config(self) -> dict:
        if not getattr(self, '_configed', False):
            raise AttributeError(f'type {type(self)} {self.qualified_name} has no attribute \'local_config\' \n'
                                 f'NOTE: Please call \'self.init_local_config()\' if you wish to utilize '
                                 f'local config files for this Cog.')
        return self._config

    # ========== Global Config stuff ========== #

    @property
    def full_ext_path(self) -> str:
        """returns the full extension path of this cog
        as a module path relative to the bot's configured extension package"""
        if not getattr(self, '_full_ext_path', False):
            self._full_ext_path = resolve_extension_path(self.__module__, self.bot.ext_module)
        return self._full_ext_path

    @property
    def global_config_key(self) -> str:
        """They key that all the extension's per-guild configs are stored under (in each guild config file)"""
        return parent_package_path(type(self)).partition(self.bot.ext_module_name)[2].lstrip('.')

    def guild_config(self, guild) -> dict:
        """Returns the guild's config for this extension as a dictionary"""
        return self.bot.guild_config(guild.id)[self.global_config_key]

    async def cog_unload(self):
        self.save_local_config()
        await super().cog_unload()

    # ========== Custom method pre-Definitions ========== #

    async def __init_async__(self):
        pass
