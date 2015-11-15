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

"""Salish Sea NEMO nowcast ZeroMQ message broker.
This broker provides the static point in the nowcast messaging framework,
allowing the nowcast_mgr to be restarted more or less at will to update
its configuration.
"""
import logging
import os
import signal
import sys
import traceback

import zmq

from salishsea_tools.nowcast import lib


broker_name = lib.get_module_name()

logger = logging.getLogger(broker_name)

context = zmq.Context()


def main():
    # Parse command-line arguments
    parser = lib.basic_arg_parser(broker_name, description=__doc__)
    parser.prog = 'python -m salishsea_tools.nowcast.{}'.format(broker_name)
    parsed_args = parser.parse_args()

    # Load configuration and set up logging
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.info('running in process {}'.format(os.getpid()))
    logger.info('read config from {.config_file}'.format(parsed_args))

    # Create sockets and bind them to ports
    frontend = context.socket(zmq.ROUTER)
    backend = context.socket(zmq.DEALER)
    frontend_port = config['zmq']['ports']['frontend']
    frontend.bind('tcp://*:{}'.format(frontend_port))
    logger.info('frontend bound to port {}'.format(frontend_port))
    backend_port = config['zmq']['ports']['backend']
    backend.bind('tcp://*:{}'.format(backend_port))
    logger.info('backend bound to port {}'.format(backend_port))

    # Set up interrupt and kill signal handlers
    def sigint_handler(signal, frame):
        logger.info(
            'interrupt signal (SIGINT or Ctrl-C) received; shutting down')
        frontend.close()
        backend.close()
        context.destroy()
        sys.exit(0)
    signal.signal(signal.SIGINT, sigint_handler)

    def sigterm_handler(signal, frame):
        logger.info(
            'termination signal (SIGTERM) received; shutting down')
        frontend.close()
        backend.close()
        context.destroy()
        sys.exit(0)
    signal.signal(signal.SIGTERM, sigterm_handler)

    # Broker messages between workers on frontend and manager on backend
    try:
        zmq.device(zmq.QUEUE, frontend, backend)
    except zmq.ZMQError as e:
        # Fatal ZeroMQ problem
        logger.critical('ZMQError: {}'.format(e))
        logger.critical('shutting down')
    except SystemExit:
        # Termination by signal
        pass
    except:
        logger.critical('unhandled exception:')
        for line in traceback.format_exc().splitlines():
            logger.error(line)

if __name__ == '__main__':
    main()
