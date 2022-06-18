from os.path import abspath as _abspath, dirname as _dirname

from discord.ext.commands import Cog as _bruh_do_not_import_this_Cog

from botcord.configs import YAML as _YAML, recursive_update as _recursive_update


# noinspection PyAttributeOutsideInit
class Cog(_bruh_do_not_import_this_Cog):
    """
    Same as :class:`discord.ext.commands.Cog` but extra configuration file features.
    Allows the cog to conviniently save and access data from a config file.

    Your custom extension class should inherit this class the same way you use the ordinary Cog.

    ``config_init()`` must be called (only once) at the beginning before using config features
    it loads any data from the config file on disk to be accessed via ``self.config`` as a dictionary

    ``save_config()``, ``load_config()``, and ``refresh_config()`` are self-explanatory
    """
    def config_init(self, file, path='configs.yml'):
        """PASS THE __file__ VARIABLE IN AS AN ARGUMENT FROM THE EXTENSION FILE,
        SO THE CONFIG PATH IS IN THE EXTENSION'S FOLDER AND NOT IN THE BOTCORD FILES HERE"""
        if getattr(self, '_configed', False):
            raise RuntimeError('config_init() has already been called, but was called again')

        self._config_dir = f'{_dirname(_abspath(file))}/{path}'
        self.load_config()
        self._configed = True

    def save_config(self):
        """overwrites config on disk with config in memory"""
        with open(self._config_dir, mode='w', encoding='UTF-8') as file:
            _YAML.dump(self.config, file)

    def load_config(self):
        """overwrites config in memory with config on disk"""
        self._config = self._load_config()

    def refresh_config(self):
        """recursively merges configs from disk and memory
        (disk as base, memory as overwrite)
        THEN saves merged to disk"""
        file_conf = self._load_config()
        _recursive_update(file_conf, self.config)
        self.save_config()

    def _load_config(self):
        """reads and returns config from disk"""
        with open(self._config_dir, mode='a+', encoding='UTF-8') as wfile:
            wfile.seek(0)
            wloaded = _YAML.load(wfile)
            if not wloaded:
                wloaded = {}
            return wloaded

    @property
    def config(self) -> dict:
        if not getattr(self, '_configed', False):
            raise AttributeError(f'type {type(self)} {self.__name__} has no attribute \'config\' \n'
                                 f'NOTE: Please call \'config_init()\' if you wish to utilize config files for this Cog.')
        return self._config

    def cog_unload(self):
        self.save_config()
        super().cog_unload()


__all__ = ['Cog']
