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

"""Salish Sea NEMO nowcast worker that creates an instance (node) in an
OpenStack cloud to run NEMO.
"""
import argparse
import logging
import os
import time
import traceback

import novaclient.client
import zmq

from salishsea_tools.nowcast import lib


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


def main():
    # Prepare the worker
    base_parser = lib.basic_arg_parser(
        worker_name, description=__doc__, add_help=False)
    parser = configure_argparser(
        prog=base_parser.prog,
        description=base_parser.description,
        parents=[base_parser],
    )
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
        checklist = create_compute_node(
            host_name, config, parsed_args.node_name)
        # Exchange success messages with the nowcast manager process
        logger.info(
            '{0.node_name} node creation on {host} completed'
            .format(parsed_args, host=host_name))
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            '{0.node_name} node creation on {host} failed'
            .format(parsed_args, host=host_name))
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


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument('node_name', help='Name to use for the node')
    return parser


def create_compute_node(host_name, config, node_name):
    host = config['run'][host_name]
    # Authenticate
    credentials = lib.get_nova_credentials_v2()
    nova = novaclient.client.Client(**credentials)
    logger.debug('authenticated nova client on {}'.format(host_name))
    # Prepare node configuration
    if node_name == 'nowcast0':
        image = nova.images.find(name=host['images']['head node'])
    else:
        image = nova.images.find(name=host['images']['compute node'])
    flavor = nova.flavors.find(name=host['flavor name'])
    network_label = host['network label']
    network = nova.networks.find(label=network_label)
    nics = [{'net-id': network.id}]
    key_name = host['ssh key name']['image']
    # Create node
    nova.servers.create(
        name=node_name, image=image, flavor=flavor, nics=nics,
        key_name=key_name)
    logger.debug(
        'creating {flavor} node {name} based on {image} image '
        'with {key} key loaded'
        .format(flavor=flavor.name, name=node_name, image=image.name,
                key=key_name))
    time.sleep(5)
    while nova.servers.find(name=node_name).status != u'ACTIVE':
        time.sleep(5)
    logger.debug('{} node is active'.format(node_name))
    # Get node's private IP address
    node = nova.servers.find(name=node_name)
    node_addr = node.addresses[network_label][0]['addr']
    checklist = {node_name: node_addr.encode('ascii')}
    return checklist


if __name__ == '__main__':
    main()
