from typing import Dict
import importlib

from pendulum.tz.zoneinfo.exceptions import InvalidTimezone
from pydantic import BaseModel, validator
import pendulum
import pydantic


class Settings(BaseModel):
    """
    Base class for all settings.
    """


class HautoConfig(Settings):
    """
    Validator to ensure proper Hautomate configuration.

    Tools:
      https://www.freemaptools.com/elevation-finder.htm
    """
    apps_dir: pydantic.DirectoryPath
    latitude: float
    longitude: float
    elevation: float
    timezone: pendulum._Timezone
    api_configs: Dict[str, Settings] = {}

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

    @validator('api_configs', pre=True)
    def is_api_config(cls, data: dict):
        for api_name, settings in data.copy().items():
            try:
                cfg = importlib.import_module(f'hautomate.apis.{api_name}.settings')
            except ModuleNotFoundError:
                raise ValueError(f"unrecognized api '{api_name}'")

            data[api_name] = cfg.Config.parse_obj(settings)

        return data

    #

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            pendulum._Timezone: lambda v: v.name
        }
