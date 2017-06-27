# Copyright (C) 2017 Canonical
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

"""Ubuntu MaaS 2.x CLI support code."""

import json
import logging
import subprocess
import time
import yaml

from devices import (ProvisioningError,
                     RecoveryError)

logger = logging.getLogger()


class Maas2:

    """Device Agent for Maas2."""

    def __init__(self, config, job_data):
        with open(config) as configfile:
            self.config = yaml.load(configfile)
        with open(job_data) as j:
            self.job_data = json.load(j)

    def recover(self):
        agent_name = self.config.get('agent_name')
        logger.info("Releasing node %s", agent_name)
        self.node_release()

    def provision(self):
        maas_user = self.config.get('maas_user')
        node_id = self.config.get('node_id')
        agent_name = self.config.get('agent_name')
        provision_data = self.job_data.get('provision_data')
        # Default to a safe LTS if no distro is specified
        distro = provision_data.get('distro', 'xenial')
        logger.info('Acquiring node')
        cmd = ['maas', maas_user, 'machines', 'allocate',
               'system_id={}'.format(node_id)]
        # Do not use runcmd for this - we need the output, not the end user
        subprocess.check_call(cmd)
        logger.info(
            'Starting node %s with distro %s', agent_name, distro)
        cmd = ['maas', maas_user, 'machine', 'deploy', node_id,
               'distro_series={}'.format(distro)]
        output = subprocess.check_output(cmd)
        # Make sure the device is available before returning
        for timeout in range(0, 10):
            time.sleep(60)
            status = self.node_status()
            if status == 'Deployed':
                if self.check_test_image_booted():
                    return
        logger.error('Device %s still in "%s" state, deployment failed!',
                     agent_name, status)
        logger.error(output)
        raise ProvisioningError("Provisioning failed!")

    def check_test_image_booted(self):
        logger.info("Checking if test image booted.")
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no',
               '-o', 'UserKnownHostsFile=/dev/null',
               'ubuntu@{}'.format(self.config['device_ip']),
               'snap -h']
        try:
            subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=60)
        except:
            return False
        # If we get here, then the above command proved we are booted
        return True

    def node_status(self):
        """Return status of the node according to maas:

        Ready: Node is unused
        Allocated: Node is allocated
        Deploying: Deployment in progress
        Deployed: Node is provisioned and ready for use
        """
        maas_user = self.config.get('maas_user')
        node_id = self.config.get('node_id')
        cmd = ['maas', maas_user, 'machine', 'read', node_id]
        # Do not use runcmd for this - we need the output, not the end user
        output = subprocess.check_output(cmd)
        data = json.loads(output.decode())
        return data.get('status_name')

    def node_release(self):
        """Release the node to make it available again"""
        maas_user = self.config.get('maas_user')
        node_id = self.config.get('node_id')
        cmd = ['maas', maas_user, 'machine', 'release', node_id]
        subprocess.check_call(cmd)
        # Make sure the device is available before returning
        for timeout in range(0, 10):
            time.sleep(5)
            status = self.node_status()
            if status == 'Ready':
                return
        agent_name = self.config.get('agent_name')
        logger.error('Device %s still in "%s" state, could not recover!',
                     agent_name, status)
        raise RecoveryError("Device recovery failed!")