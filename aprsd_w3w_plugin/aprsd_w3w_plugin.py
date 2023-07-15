import logging
import random
import re

import what3words
from aprsd import packets, plugin, plugin_utils
from aprsd.utils import trace
from oslo_config import cfg

import aprsd_w3w_plugin
from aprsd_w3w_plugin import conf  # noqa


CONF = cfg.CONF
LOG = logging.getLogger("APRSD")


class W3WPlugin(plugin.APRSDRegexCommandPluginBase):

    version = aprsd_w3w_plugin.__version__
    # Change this regex to match for your plugin's command
    # Tutorial on regex here: https://regexone.com/
    # Look for any command that starts with w or W
    command_regex = "^[wW][3][wW]"
    # the command is for ?
    # Change this value to a 1 word description of the plugin
    # this string is used for help
    command_name = "weather"

    enabled = False

    def setup(self):
        """Allows the plugin to do some 'setup' type checks in here.

        If the setup checks fail, set the self.enabled = False.  This
        will prevent the plugin from being called when packets are
        received."""
        # Do some checks here?
        if not CONF.aprsd_w3w_plugin.enabled:
            self.enabled = False
            LOG.info("W3WPlugin Plugin is disabled in config")
            return

        if not CONF.aprsd_w3w_plugin.apikeys:
            self.enabled = False
            LOG.info("No API Keys configured in config.  Set aprsd_w3w_plugin.apikeys in config")
            return

        self.enabled = True

    @trace.trace
    def process(self, packet: packets.core.Packet):

        """This is called when a received packet matches self.command_regex.

        This is only called when self.enabled = True and the command_regex
        matches in the contents of the packet["message_text"]."""

        LOG.info("W3WPlugin Plugin")
        fromcall = packet.from_call
        message = packet.get("message_text", None)

        api_key = CONF.aprs_fi.apiKey

        # optional second argument is a callsign to search
        a = re.search(r"^.*\s+(.*)", message)
        if a is not None:
            searchcall = a.group(1)
            searchcall = searchcall.upper()
        else:
            # if no second argument, search for calling station
            searchcall = fromcall

        try:
            aprs_data = plugin_utils.get_aprs_fi(api_key, searchcall)
        except Exception as ex:
            LOG.error(f"Failed to fetch aprs.fi '{ex}'")
            return "Failed to fetch aprs.fi location"

        LOG.debug(f"LocationPlugin: aprs_data = {aprs_data}")
        if not len(aprs_data["entries"]):
            LOG.error("Didn't get any entries from aprs.fi")
            return "Failed to fetch aprs.fi location"

        lat = float(aprs_data["entries"][0]["lat"])
        lon = float(aprs_data["entries"][0]["lng"])

        # Now we can process
        apikey = random.choice(CONF.aprsd_w3w_plugin.apikeys)
        geocoder = what3words.Geocoder(apikey)
        res = None
        try:
            res = geocoder.convert_to_3wa(
                what3words.Coordinates(
                    lat, lon,
                ),
            )
        except what3words.GeocoderError as ex:
            LOG.exception(ex)
            return "Failed to fetch w3w location"

        if res:
            LOG.debug(res)
            words = res["words"]
            return words
