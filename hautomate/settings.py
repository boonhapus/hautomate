from typing import Union, Dict
import importlib
import logging

from pendulum.tz.zoneinfo.exceptions import InvalidTimezone
from pydantic import BaseModel, validator
import pendulum
import pydantic


_log = logging.getLogger(__name__)


class Settings(BaseModel):
    """
    Base class for all settings.
    """


class HautoConfig(Settings):
    """
    Validator to ensure proper Hautomate configuration.

    apps_dir
        may take the form of single-file apps, or a directory for the app, where the app
        lives as a same-named file (aka /apps_dir/app_name/app_name.py). App files which
        start with either a single- or double-underscore will be ignored.

    Tools:
      https://www.freemaptools.com/elevation-finder.htm
    """
    apps_dir: pydantic.DirectoryPath
    latitude: float
    longitude: float
    elevation: float
    timezone: pendulum._Timezone
    api_configs: Dict[str, Union[Settings, None]] = {
        'trigger': {},
        'moment': {}
    }

    # @classmethod
    # def from_yaml(cls, fp: str):
    #     raise NotImplementedError()

    # @classmethod
    # def from_json(cls, fp: str):
    #     raise NotImplementedError()

    #

    @validator('timezone', pre=True)
    def is_timezone(cls, tzname: str):
        try:
            tz = pendulum.now(tz=tzname).timezone
        except InvalidTimezone:
            msg = (
                f'Invalid timezone "{tzname}", use a TZ database name from '
                f'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones'
            )
            raise ValueError(msg) from None

        return tz

    @validator('api_configs', pre=True, always=True)
    def is_api_config(cls, data: dict):

        # ensure we have our defaults
        for api in ('trigger', 'moment'):
            if api not in data:
                data[api] = {}

        for api_name, cfg_data in data.copy().items():
            try:
                importlib.import_module(f'hautomate.apis.{api_name}.{api_name}')
            except ModuleNotFoundError:
                raise ValueError(f"api '{api_name}' does not appear to exist")

            try:
                settings = importlib.import_module('.settings', package=f'hautomate.apis.{api_name}')
            except ModuleNotFoundError:
                if api_name != 'trigger':
                    _log.warning(f"api '{api_name}' does not appear to have a configuration validator")
                cfg = None
            else:
                cfg = settings.Config.parse_obj(cfg_data)

            data[api_name] = cfg

        return data

    #

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            pendulum._Timezone: lambda v: v.name
        }
