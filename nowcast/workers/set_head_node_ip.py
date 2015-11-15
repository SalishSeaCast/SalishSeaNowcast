# Copyright 2013-2015 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Salish Sea NEMO nowcast worker that associates a public IP address
from a floating IP address pool with the instance (node) designated as
the head node for running NEMO in an OpenStack cloud.
"""
import logging
import os
import traceback

import novaclient.client
import zmq

from salishsea_tools.nowcast import lib


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


def main():
    # Prepare the worker
    parser = lib.basic_arg_parser(worker_name, description=__doc__)
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.info('running in process {}'.format(os.getpid()))
    logger.info('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    host_name = config['run']['cloud host']
    try:
        checklist = set_head_node_ip(host_name, config)
        # Exchange success messages with the nowcast manager process
        logger.info(
            'public IP address associated with nowcast0 node in {}'
            .format(host_name))
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            'public IP address association with nowcast0 in {} failed'
            .format(host_name))
        # Exchange failure messages with the nowcast manager process
        lib.tell_manager(worker_name, 'failure', config, logger, socket)
    except SystemExit:
        # Normal termination
        pass
    except:
        logger.critical('unhandled exception:')
        for line in traceback.format_exc().splitlines():
            logger.error(line)
        # Exchange crash messages with the nowcast manager process
        lib.tell_manager(worker_name, 'crash', config, logger, socket)
    # Finish up
    context.destroy()
    logger.info('task completed; shutting down')


def set_head_node_ip(host_name, config):
    host = config['run'][host_name]
    # Authenticate
    credentials = lib.get_nova_credentials_v2()
    nova = novaclient.client.Client(**credentials)
    logger.debug('authenticated nova client on {}'.format(host_name))
    # Check for public IP already associated
    network_label = host['network label']
    nowcast0 = nova.servers.find(name='nowcast0')
    ip = get_ip(nowcast0, network_label)
    if ip is not None:
        logger.info('{} already associated with nowcast0 node'.format(ip))
        return ip.encode('ascii')
    # Associate a floating IP
    fip = nova.floating_ips.find(pool=host['floating ip pool'])
    nowcast0 = nova.servers.find(name='nowcast0')
    nowcast0.add_floating_ip(fip)
    nowcast0 = nova.servers.find(name='nowcast0')
    ip = get_ip(nowcast0, network_label)
    if ip is None:
        logger.error('public IP address association with nowcast0 failed')
        raise lib.WorkerError
        return
    logger.info('{} associated with nowcast0 node'.format(ip))
    return ip.encode('ascii')


def get_ip(node, network_label):
    try:
        ip = [a['addr'] for a in node.addresses[network_label]
              if a['OS-EXT-IPS:type'] == u'floating'][0]
    except IndexError:
        ip = None
    return ip


if __name__ == '__main__':
    main()
