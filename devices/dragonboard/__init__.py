# Copyright (C) 2016-2019 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Dragonboard support code."""

import logging
import yaml

import snappy_device_agents
from devices.dragonboard.dragonboard import Dragonboard
from snappy_device_agents import logmsg
from devices import catch, DefaultDevice, RecoveryError, SerialLogger

device_name = "dragonboard"


class DeviceAgent(DefaultDevice):

    """Tool for provisioning baremetal with a given image."""

    @catch(RecoveryError, 46)
    def provision(self, args):
        """Method called when the command is invoked."""
        with open(args.config) as configfile:
            config = yaml.safe_load(configfile)
        snappy_device_agents.configure_logging(config)
        device = Dragonboard(args.config, args.job_data)
        logmsg(logging.INFO, "BEGIN provision")
        logmsg(logging.INFO, "Booting Master Image")
        serial_host = config.get("serial_host")
        serial_port = config.get("serial_port")
        serial_proc = SerialLogger(
            serial_host, serial_port, "provision-serial.log"
        )
        serial_proc.start()
        try:
            device.provision()
        except Exception as e:
            raise e
        finally:
            serial_proc.stop()
