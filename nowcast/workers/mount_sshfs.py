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

"""Salish Sea NEMO nowcast worker that mounts an SSHFS filesystem on each
node of an OpenStack cloud to run NEMO.
"""
import logging
import os
import traceback

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
    host = config['run'][host_name]
    try:
        checklist = mount_sshfs(host_name, config, socket)
        # Exchange success messages with the nowcast manager process
        logger.info(
            'SSHFS mounted at {} on all nodes in {}'
            .format(host['sshfs storage']['mount point'], host_name))
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            'SSHFS mount on nodes in {} failed'.format(host_name))
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


def mount_sshfs(host_name, config, socket):
    host = config['run'][host_name]
    nodes = lib.tell_manager(
        worker_name, 'need', config, logger, socket, 'nodes')
    mount_cmd = (
        'sshfs -o idmap=user {user name}@{host name}:{host path} {mount point}'
        .format(**host['sshfs storage']))
    ssh_client = lib.ssh(host_name, host['ssh key name']['nowcast'])
    ssh_client.exec_command(mount_cmd)
    logger.debug('"{}" executed on nowcast0'.format(mount_cmd))
    nodes.pop('nowcast0')
    for node_name in sorted(nodes):
        cmd = (
            'ssh {node_name} {mount_cmd}'
            .format(node_name=node_name, mount_cmd=mount_cmd))
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        for line in stdout:
            line = line.strip('\n')
            if line:
                logger.debug('stdout: {}'.format(line))
        for line in stderr:
            if line.startswith('fuse: mountpoint is not empty'):
                break
            line.strip('\n')
            if line:
                logger.debug('stderr: {}'.format(line))
        logger.debug('"{}" executed on {}'.format(cmd, node_name))
    ssh_client.close()
    return True


if __name__ == '__main__':
    main()
