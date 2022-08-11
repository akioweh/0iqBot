import os
from typing import Optional

import ruamel.yaml

from .functions import log
from .types import ConfigDict

DEFAULT_GLOBAL_CONFIG_PATH: str = os.path.dirname(os.path.realpath(__file__)) + '/default_global_configs.yml'
DEFAULT_GUILD_CONFIG_PATH: str = os.path.dirname(os.path.realpath(__file__)) + '/default_guild_configs.yml'

YAML = ruamel.yaml.YAML()
YAML.indent(mapping=4, sequence=4, offset=2)


def recursive_update(base: dict, extra: dict) -> None:
    """Recursively updates dictionary with extra data.

    **updates base IN PLACE**"""
    for k, v in extra.items():
        if k in base and isinstance(base[k], dict) and isinstance(extra[k], dict):
            recursive_update(base[k], extra[k])
        else:
            base[k] = extra[k]


def load_configs(*, global_path: str = 'global_configs.yml',
                 guild_dir: str = 'configs/') -> [ConfigDict, dict[int, ConfigDict]]:
    """Loads global config AND guild configs from file.

    :return: configs in the format of: tuple(global_config, {guild_id: guild_config})"""
    # Global Configuration File
    global_config_path = os.getcwd() + '/' + global_path
    try:
        global_configs = default_global()
        with open(global_config_path, encoding='UTF-8') as wfile:
            wloaded = YAML.load(wfile)
            if wloaded:
                recursive_update(global_configs, wloaded)
    except FileNotFoundError:
        log(f'Did not find Global Configuration File at {global_config_path}; using Defaults.', tag='Info')
        global_configs = default_global()

    # Guild Configuration Files
    guild_configs = {}
    guild_configs_dir = os.getcwd() + '/' + guild_dir
    for file in os.listdir(guild_configs_dir):
        file_name = os.path.basename(file).rpartition('.')
        if file_name[-1] != 'yml':
            continue

        config_file = default_guild()
        with open(guild_configs_dir + file, encoding='UTF-8') as wfile:
            wloaded = YAML.load(wfile)
            if not wloaded:
                continue
            recursive_update(config_file, wloaded)

        guild_id = int(config_file['guild']['id'])
        if int(file_name[0]) != guild_id:
            raise AttributeError(f'Mismatched file name ID and Guild ID in file: {file}')

        guild_configs[guild_id] = config_file

    return global_configs, guild_configs


def new_guild_config(guild_id: int,
                     initial_config: Optional[ConfigDict] = None, *,
                     guild_dir: str = 'configs/') -> ConfigDict:
    """Creates a new guild config file with optional initial data
    and saves to file.

    :return: the new config dictionary"""
    guild_configs_dir = os.getcwd() + '/' + guild_dir
    config = default_guild()
    recursive_update(config, {'guild': {'id': guild_id}})
    if initial_config is not None:
        recursive_update(config, initial_config)
    try:
        with open(f'{guild_configs_dir}{guild_id}.yml', mode='x', encoding='UTF-8') as file:
            YAML.dump(config, file)
    except FileExistsError:
        raise FileExistsError(f'There already exists a config for guild {guild_id}')
    return config


def save_config(config: ConfigDict, *, global_path: str = 'global_configs.yml'):
    """Saves config to file."""
    global_config_path = os.getcwd() + '/' + global_path
    with open(global_config_path, mode='w', encoding='UTF-8') as file:
        YAML.dump(config, file)


def save_guild_config(config: ConfigDict, guild_id: int, *, guild_dir: str = 'configs/'):
    """Saves guild config to file."""
    guild_configs_dir = os.getcwd() + '/' + guild_dir
    with open(f'{guild_configs_dir}{guild_id}.yml', mode='w', encoding='UTF-8') as file:
        YAML.dump(config, file)


def default_global() -> ConfigDict:
    """Returns defailt Global Config"""
    try:
        with open(DEFAULT_GLOBAL_CONFIG_PATH, encoding='UTF-8') as file:
            return YAML.load(file)
    except FileNotFoundError as e:
        raise FileNotFoundError('Could not find default Global Configuration File.') from e


def default_guild() -> ConfigDict:
    """Returns default Guild Config"""
    try:
        with open(DEFAULT_GUILD_CONFIG_PATH, encoding='UTF-8') as file:
            return YAML.load(file)
    except FileNotFoundError as e:
        raise FileNotFoundError('Could not find default Guild Configuration File.') from e
# End
