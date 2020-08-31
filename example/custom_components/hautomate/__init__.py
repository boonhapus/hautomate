"""
Hautomate. A task automation library focused on home automation.

Component to integrate with gPodder.
For more details about this component, please refer to
https://github.com/boonhapus/hautomate/example/custom_components/README.md
"""
import logging

# import hautomate


_LOGGER = logging.getLogger(__name__)
DOMAIN = 'hautomate'


async def async_setup(hass, config):
    hass.states.async_set('hautomate.hello', 'world')

    # Return boolean to indicate that initialization was successful.
    return True
