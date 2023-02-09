"""Functional interface to manage bot configs"""

import os
from copy import deepcopy
from typing import Optional

from ruamel.yaml import YAML

from .functions import log, recursive_update, to_int
from .types import ConfigDict

DEFAULT_GLOBAL_CONFIG_PATH: str = os.path.dirname(os.path.realpath(__file__)) + '/default_global_configs.yml'
DEFAULT_GUILD_CONFIG_PATH: str = os.path.dirname(os.path.realpath(__file__)) + '/default_guild_configs.yml'

YAML_rw: YAML = YAML()  # yaml reader-writer
YAML_rw.indent(mapping=4, sequence=4, offset=2)

# for caching purposes
_default_global: ConfigDict | None = None
_default_guild: ConfigDict | None = None


def load_configs(*, global_path: str = 'global_configs.yml',
                 guild_dir: str = 'configs/') -> [ConfigDict, dict[int, ConfigDict]]:
    """Loads global config AND guild configs from file.

    :return: configs in the format of: tuple(global_config, {guild_id: guild_config})"""
    # Global Configuration File
    global_config_path = os.getcwd() + '/' + global_path
    try:
        global_configs = default_global()
        with open(global_config_path, encoding='UTF-8') as wfile:
            wloaded = YAML_rw.load(wfile)
            if wloaded:
                try:
                    recursive_update(global_configs, wloaded)
                except TypeError:
                    log(f'Incorrect data format in global config file. Using default.', tag='Warning')
                    global_configs = default_global()  # reset to default (in case of partial overwrite)

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
            wloaded = YAML_rw.load(wfile)
            if not wloaded:
                continue
            try:
                recursive_update(config_file, wloaded)
            except TypeError:
                log(f'Incorrect data format in config file: {file}. Using default.', tag='Warning')
                config_file = default_guild()  # reset to default (in case of partial overwrite)

        guild_id = to_int(config_file['guild']['id'])
        if guild_id is None:
            log(f'Guild id not set in config file: {file}. Automatically setting from file name.', tag='Warning')
            log(file_name[0])
            config_file['guild']['id'] = int(file_name[0])
        elif int(file_name[0]) != guild_id:
            raise AttributeError(f'Mismatched file name ID and Guild ID in file: {file}')

        guild_configs[int(file_name[0])] = config_file

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
        try:
            recursive_update(config, initial_config)
        except TypeError:
            log(f'Incorrect data format in initial config while creating new config for guild {guild_id}. '
                f'Using default.', tag='Warning')
            config = default_guild()
            recursive_update(config, {'guild': {'id': guild_id}})
    try:
        with open(f'{guild_configs_dir}{guild_id}.yml', mode='x', encoding='UTF-8') as file:
            YAML_rw.dump(config, file)
    except FileExistsError:
        raise FileExistsError(f'There already exists a config for guild {guild_id}')
    return config


def save_config(config: ConfigDict, *, global_path: str = 'global_configs.yml'):
    """Saves config to file."""
    global_config_path = os.getcwd() + '/' + global_path
    with open(global_config_path, mode='w', encoding='UTF-8') as file:
        YAML_rw.dump(config, file)


def save_guild_config(config: ConfigDict, guild_id: int, *, guild_dir: str = 'configs/'):
    """Saves guild config to file."""
    guild_configs_dir = os.getcwd() + '/' + guild_dir
    with open(f'{guild_configs_dir}{guild_id}.yml', mode='w', encoding='UTF-8') as file:
        YAML_rw.dump(config, file)


def default_global() -> ConfigDict:
    """Returns default Global Config. Caches data from first call."""
    global _default_global
    if _default_global is None:
        try:
            with open(DEFAULT_GLOBAL_CONFIG_PATH, encoding='UTF-8') as file:
                _default_global = YAML_rw.load(file)
        except FileNotFoundError as e:
            raise FileNotFoundError('Could not find default Global Configuration File.') from e

    return deepcopy(_default_global)


def default_guild() -> ConfigDict:
    """Returns default Guild Config. Caches data from first call."""
    global _default_guild
    if _default_guild is None:
        try:
            with open(DEFAULT_GUILD_CONFIG_PATH, encoding='UTF-8') as file:
                _default_guild = YAML_rw.load(file)
        except FileNotFoundError as e:
            raise FileNotFoundError('Could not find default Guild Configuration File.') from e

    return deepcopy(_default_guild)
# End
