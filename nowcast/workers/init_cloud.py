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

"""Salish Sea NEMO nowcast worker that initiates the setup of an
OpenStack cloud to run NEMO by collecting the names and cloud subnet
IP addresses of any existing nodes.
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
        checklist = init_cloud(host_name, config)
        # Exchange success messages with the nowcast manager process
        logger.info(
            'names and addresses collected from existing nodes in {}'
            .format(host_name))
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            'collection of names and addresses from existing nodes '
            'in {} failed'
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


def init_cloud(host_name, config):
    # Authenticate
    credentials = lib.get_nova_credentials_v2()
    nova = novaclient.client.Client(**credentials)
    logger.debug('authenticated nova client on {}'.format(host_name))
    checklist = {}
    network_label = config['run'][host_name]['network label']
    for node in nova.servers.list():
        try:
            node_addr = [a['addr'] for a in node.addresses[network_label]
                         if a['OS-EXT-IPS:type'] == u'fixed'][0]
        except IndexError:
            logger.warning('node {.name} exists but lacks an ip address')
        logger.debug('node {.name} found with ip {}'.format(node, node_addr))
        checklist[node.name.encode('ascii')] = node_addr.encode('ascii')
    return checklist


if __name__ == '__main__':
    main()
