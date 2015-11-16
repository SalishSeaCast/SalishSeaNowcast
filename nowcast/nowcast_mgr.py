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

"""Salish Sea NEMO nowcast manager.
"""
import argparse
from copy import copy
import logging
import os
import pprint
import subprocess
import traceback

import yaml
import zmq

from nowcast import lib


mgr_name = lib.get_module_name()

logger = logging.getLogger(mgr_name)
checklist_logger = logging.getLogger('checklist')
worker_loggers = {}

context = zmq.Context()

checklist = {}


def main():
    # Parse command-line arguments
    base_parser = lib.basic_arg_parser(
        mgr_name, description=__doc__, add_help=False)
    parser = configure_argparser(
        prog='python -m salishsea_tools.nowcast.{}'.format(mgr_name),
        description=base_parser.description,
        parents=[base_parser],
    )
    parsed_args = parser.parse_args()

    # Load configuration and set up logging
    config = lib.load_config(parsed_args.config_file)
    config['logging']['console'] = parsed_args.debug
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.info('running in process {}'.format(os.getpid()))
    logger.debug('read config from {.config_file}'.format(parsed_args))
    configure_checklist_logging(config)

    # Set up interrupt and kill signal handlers
    lib.install_signal_handlers(logger, context)

    # Create messaging socket and connect to broker
    socket = context.socket(zmq.REP)
    backend_port = config['zmq']['ports']['backend']
    socket.connect('tcp://localhost:{}'.format(backend_port))
    logger.debug('connected to port {}'.format(backend_port))

    if not parsed_args.ignore_checklist:
        # Load the serialized checklist left by a previous instance of
        # the manager
        try:
            with open('nowcast_checklist.yaml', 'rt') as f:
                global checklist
                checklist = yaml.load(f)
                logger.info('checklist read from disk')
                logger.info(
                    'checklist:\n{}'.format(pprint.pformat(checklist)))
        except IOError as e:
            logger.warning('checklist load failed: {.message}'.format(e))
            logger.warning('running with empty checklist')

    while True:
        # Process messages from workers
        logger.debug('listening...')
        try:
            message = socket.recv_string()
            reply, next_steps = message_processor(config, message)
            socket.send_string(reply)
            if next_steps is not None:
                for next_step, next_step_args in next_steps:
                    next_step(*next_step_args)
        except zmq.ZMQError as e:
            # Fatal ZeroMQ problem
            logger.critical('ZMQError: {}'.format(e))
            logger.critical('shutting down')
            break
        except SystemExit:
            # Termination by signal
            break
        except:
            logger.critical('unhandled exception:')
            for line in traceback.format_exc().splitlines():
                logger.error(line)


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        '--ignore-checklist', action='store_true',
        help='''
        Don't load the serialized checklist left by a previously
        running instance of the nowcast manager.
        ''',
    )
    return parser


def configure_checklist_logging(config):
    checklist_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        config['logging']['message_format'],
        datefmt=config['logging']['datetime_format'])
    log_file = os.path.join(
        os.path.dirname(config['config_file']),
        config['logging']['checklist_log_file'])
    handler = logging.handlers.RotatingFileHandler(
        log_file, backupCount=config['logging']['backup_count'])
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    checklist_logger.addHandler(handler)


def message_processor(config, message):
    msg = lib.deserialize_message(message)
    # Unpack message items
    worker = msg['source']
    msg_type = msg['msg_type']
    payload = msg['payload']
    # Message to acknowledge receipt of message from worker
    reply_ack = lib.serialize_message(mgr_name, 'ack')
    # Lookup table of functions to return next step function and its
    # arguments for the message types that we know how to handle
    after_actions = {
        'download_weather': after_download_weather,
        'get_NeahBay_ssh': after_get_NeahBay_ssh,
        'make_runoff_file': after_make_runoff_file,
        'grib_to_netcdf': after_grib_to_netcdf,
        'init_cloud': after_init_cloud,
        'create_compute_node': after_create_compute_node,
        'set_head_node_ip': after_set_head_node_ip,
        'set_ssh_config': after_set_ssh_config,
        'set_mpi_hosts': after_set_mpi_hosts,
        'mount_sshfs': after_mount_sshfs,
        'upload_forcing': after_upload_forcing,
        'upload_all_files': after_upload_all_files,
        'make_forcing_links': after_make_forcing_links,
        'run_NEMO': after_run_NEMO,
        'watch_NEMO': after_watch_NEMO,
        'download_results': after_download_results,
        'make_plots': after_make_plots,
        'make_site_page': after_make_site_page,
        'push_to_web': after_push_to_web,
    }
    # Handle undefined message type
    if msg_type not in config['msg_types'][worker]:
        logger.warning(
            'undefined message type received from {worker}: {msg_type}'
            .format(worker=worker, msg_type=msg_type))
        reply = lib.serialize_message(mgr_name, 'undefined msg')
        return reply, None
    # Recognized message type
    logger.debug(
        'received message from {worker}: ({msg_type}) {msg_words}'
        .format(worker=worker,
                msg_type=msg_type,
                msg_words=config['msg_types'][worker][msg_type]))
    # Handle need messages from workers
    if msg_type.startswith('need'):
        reply = lib.serialize_message(mgr_name, 'ack', checklist[payload])
        return reply, None
    # Handle log messages from workers
    if msg_type.startswith('log'):
        level = getattr(logging, msg_type.split('.')[1].upper())
        worker_loggers[worker].log(level, payload)
        return reply_ack, None
    # Handle success, failure, and crash messages from workers
    next_steps = after_actions[worker](worker, msg_type, payload, config)
    return reply_ack, next_steps


def after_download_weather(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success 00': [
            (update_checklist, [worker, 'weather', payload]),
        ],
        'failure 00': None,
        'success 06': [
            (update_checklist, [worker, 'weather', payload]),
            (launch_worker, ['make_runoff_file', config]),
        ],
        'failure 06': None,
        'success 12': [
            (update_checklist, [worker, 'weather', payload]),
        ],
        'failure 12': None,
        'success 18': [
            (update_checklist, [worker, 'weather', payload]),
        ],
        'failure 18': None,
        'crash': None,
    }
    if 'forecast2' in config['run_types']:
        actions['success 06'].extend([
            (launch_worker, ['get_NeahBay_ssh', config, ['forecast2']]),
            (launch_worker, ['grib_to_netcdf', config, ['forecast2']]),
        ])
    if 'nowcast' in config['run_types']:
        actions['success 12'].extend([
            (launch_worker, ['get_NeahBay_ssh', config, ['nowcast']]),
            (launch_worker, ['grib_to_netcdf', config, ['nowcast+']]),
        ])
    return actions[msg_type]


def after_get_NeahBay_ssh(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success nowcast': [
            (update_checklist, [worker, 'sshNeahBay', payload]),
        ],
        'failure nowcast': None,
        'success forecast': [
            (update_checklist, [worker, 'sshNeahBay', payload]),
        ],
        'failure forecast': None,
        'success forecast2': [
            (update_checklist, [worker, 'sshNeahBay', payload]),
        ],
        'failure forecast2': None,
        'crash': None,
    }
    if 'hpc host' in config['run'] and 'forecast' in config['run_types']:
        actions['success forecast'].append(
            (launch_worker, [
             'upload_forcing', config, [config['run']['hpc host'], 'ssh']]))
    if 'cloud host' in config['run'] and 'forecast' in config['run_types']:
        actions['success forecast'].append(
            (launch_worker, [
             'upload_forcing', config, [config['run']['cloud host'], 'ssh']]))
    return actions[msg_type]


def after_make_runoff_file(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'rivers', payload]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_grib_to_netcdf(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success nowcast+': [
            (update_checklist, [worker, 'weather forcing', payload]),
        ],
        'failure nowcast+': None,
        'success forecast2': [
            (update_checklist, [worker, 'weather forcing', payload]),
        ],
        'failure forecast2': None,
        'crash': None,
    }
    if 'hpc host' in config['run']:
        if 'nowcast' in config['run_types']:
            actions['success nowcast+'].append(
                (launch_worker, [
                    'upload_forcing', config,
                    [config['run']['hpc host'], 'nowcast+']]))
        if 'forecast2' in config['run_types']:
            actions['success forecast2'].append(
                (launch_worker, [
                    'upload_forcing', config,
                    [config['run']['hpc host'], 'forecast2']]))
    if 'cloud host' in config['run']:
        if 'nowcast' in config['run_types']:
            actions['success nowcast+'].append(
                (launch_worker, [
                 'upload_forcing', config,
                 [config['run']['cloud host'], 'nowcast+']]))
        if 'forecast2' in config['run_types']:
            actions['success forecast2'].append(
                (launch_worker, [
                 'upload_forcing', config,
                 [config['run']['cloud host'], 'forecast2']]))
    return actions[msg_type]


def after_init_cloud(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'nodes', payload]),
        ],
        'failure': None,
        'crash': None,
    }
    if msg_type == 'success':
        existing_nodes = []
        for node in copy(payload.keys()):
            try:
                existing_nodes.append(int(node.lstrip('nowcast')))
            except ValueError:
                # ignore nodes whose names aren't of the form nowcasti
                payload.pop(node)
        host_name = config['run']['cloud host']
        host = config['run'][host_name]
        for i in range(host['nodes']):
            if i not in existing_nodes:
                node_name = 'nowcast{}'.format(i)
                actions['success'].append(
                    (launch_worker,
                     ['create_compute_node', config, [node_name]]))
        actions['success'].append([is_cloud_ready, [config]])
    return actions[msg_type]


def after_create_compute_node(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'nodes', payload]),
            (is_cloud_ready, [config]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_set_head_node_ip(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'cloud addr', payload]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_set_ssh_config(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'ssh config', payload]),
            (launch_worker, ['set_mpi_hosts', config]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_set_mpi_hosts(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'mpi_hosts', payload]),
            (launch_worker, ['mount_sshfs', config]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_mount_sshfs(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'sshfs mount', payload]),
# This is a problem.
# The upload_forcing worker needs to know which run type to use.
            (launch_worker,
             ['upload_forcing', config, [config['run']['cloud host']]]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_upload_forcing(worker, msg_type, payload, config):
    try:
        host_name = payload.keys()[0]
    except (AttributeError, IndexError):
        # Malformed payload of no host name in payload;
        # upload_forcing worker probably crashed
        return None
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success nowcast+': [
            (update_checklist, [worker, 'forcing upload', payload]),
        ],
        'failure nowcast+': None,
        'success forecast2': [
            (update_checklist, [worker, 'forcing upload', payload]),
        ],
        'failure forecast2': None,
        'success ssh': [
            (update_checklist, [worker, 'forcing upload', payload]),
        ],
        'failure ssh': None,
        'crash': None,
    }
    if 'nowcast' in config['run_types']:
        actions['success nowcast+'].append(
            (launch_worker,
             ['make_forcing_links', config, [host_name, 'nowcast+']]),
        )
    if 'forecast' in config['run_types']:
        actions['success ssh'].append(
            (launch_worker,
             ['make_forcing_links', config, [host_name, 'ssh']]),
        )
    if 'forecast2' in config['run_types']:
        actions['success forecast2'].append(
            (launch_worker,
             ['make_forcing_links', config, [host_name, 'forecast2']]),
        )
    return actions[msg_type]


def after_upload_all_files(worker, msg_type, payload, config):
    actions = {
        'success': None,
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_make_forcing_links(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success nowcast+': [
            (update_checklist, [worker, 'forcing links', payload]),
        ],
        'failure nowcast+': None,
        'success forecast2': [
            (update_checklist, [worker, 'forcing links', payload]),
        ],
        'failure forecast2': None,
        'success ssh': [
            (update_checklist, [worker, 'forcing links', payload]),
        ],
        'failure ssh': None,
        'crash': None,
    }
    if ('cloud host' in config['run']
            and config['run']['cloud host'] in payload):
        global worker_loggers
        worker_loggers = {}
        for worker in 'run_NEMO watch_NEMO'.split():
            worker_loggers[worker] = logging.getLogger(worker)
            lib.configure_logging(
                config, worker_loggers[worker], config['logging']['console'])
        actions['success nowcast+'].append(
            (launch_worker,
             ['run_NEMO', config, ['nowcast'], config['run']['cloud host']]))
        actions['success forecast2'].append(
            (launch_worker,
             ['run_NEMO', config, ['forecast2'], config['run']['cloud host']]))
        actions['success ssh'].append(
            (launch_worker,
             ['run_NEMO', config, ['forecast'], config['run']['cloud host']]))
    return actions[msg_type]


def after_run_NEMO(worker, msg_type, payload, config):
    global worker_loggers
    for handler in worker_loggers['run_NEMO'].handlers:
        worker_loggers['run_NEMO'].removeHandler(handler)
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'NEMO run', payload]),
        ],
        'failure': None,
        'crash': None,
    }
    return actions[msg_type]


def after_watch_NEMO(worker, msg_type, payload, config):
    global worker_loggers
    for handler in worker_loggers['watch_NEMO'].handlers:
        worker_loggers['watch_NEMO'].removeHandler(handler)
    actions = {
        'crash': None,
        'failure nowcast': None,
        'failure forecast': None,
        'failure forecast2': None,
    }
    try:
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        actions['success nowcast'] = [
            (update_checklist, [worker, 'NEMO run', payload]),
            (launch_worker, ['get_NeahBay_ssh', config, ['forecast']]),
            (launch_worker, ['download_results', config,
                             [config['run']['cloud host'], 'nowcast',
                              '--run-date', payload['nowcast']['run_date']]]),
        ]
    except KeyError:
        # No nowcast run date in payload so not handling a nowcat run
        pass
    try:
        actions['success forecast'] = [
            (update_checklist, [worker, 'NEMO run', payload]),
            (launch_worker, ['download_results', config,
                             [config['run']['cloud host'], 'forecast',
                              '--run-date', payload['forecast']['run_date']]]),
        ]
    except KeyError:
        pass
    try:
        actions['success forecast2'] = [
            (update_checklist, [worker, 'NEMO run', payload]),
            (launch_worker, [
                'download_results', config,
                [config['run']['cloud host'], 'forecast2',
                 '--run-date', payload['forecast2']['run_date']]]),
        ]
    except KeyError:
        pass
    return actions[msg_type]


def after_download_results(worker, msg_type, payload, config):
    global checklist
    actions = {
        'crash': None,
        'failure nowcast': None,
        'failure forecast': None,
        'failure forecast2': None,
    }
    try:
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        actions['success nowcast'] = [
            (update_checklist, [worker, 'results files', payload]),
            (launch_worker, ['make_plots', config, ['nowcast', 'research',
             '--run-date', checklist['NEMO run']['nowcast']['run_date']]]),
        ]
    except KeyError:
        # No nowcast run date in checklist, so not handling a nowcast run
        pass
    try:
        actions['success forecast'] = [
            (update_checklist, [worker, 'results files', payload]),
            (launch_worker, ['make_plots', config, ['forecast', 'publish',
             '--run-date', checklist['NEMO run']['forecast']['run_date']]]),
        ]
    except KeyError:
        pass
    try:
        actions['success forecast2'] = [
            (update_checklist, [worker, 'results files', payload]),
            (launch_worker, ['make_plots', config, ['forecast2', 'publish',
             '--run-date', checklist['NEMO run']['forecast2']['run_date']]]),
        ]
    except KeyError:
        pass
    return actions[msg_type]


def after_make_plots(worker, msg_type, payload, config):
    actions = {
        'crash': None,
        'failure nowcast research': None,
        'failure nowcast publish': None,
        'failure forecast publish': None,
        'failure forecast2 publish': None,
    }
    try:
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        actions['success nowcast research'] = [
            (update_checklist, [worker, 'plots', payload]),
            (launch_worker, ['make_site_page', config, ['nowcast', 'research',
             '--run-date', checklist['NEMO run']['nowcast']['run_date']]]),
        ]
    except KeyError:
        # No nowcast run_date value in checklist
        pass
    try:
        actions['success nowcast publish'] = [
            (update_checklist, [worker, 'plots', payload]),
            (launch_worker, ['make_site_page', config, ['nowcast', 'publish',
             '--run-date', checklist['NEMO run']['nowcast']['run_date']]]),
        ]
    except KeyError:
        pass
    try:
        actions['success forecast publish'] = [
            (update_checklist, [worker, 'plots', payload]),
            (launch_worker, ['make_site_page', config, ['forecast', 'publish',
             '--run-date', checklist['NEMO run']['forecast']['run_date']]]),
        ]
    except KeyError:
        pass
    try:
        actions['success forecast2 publish'] = [
            (update_checklist, [worker, 'plots', payload]),
            (launch_worker, ['make_site_page', config, ['forecast2', 'publish',
             '--run-date', checklist['NEMO run']['forecast2']['run_date']]]),
        ]
    except KeyError:
        pass
    return actions[msg_type]


def after_make_site_page(worker, msg_type, payload, config):
    actions = {
        'crash': None,
        'failure index': None,
        'failure publish': None,
        'failure research': None,
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success index': [
            (update_checklist, [worker, 'salishsea site pages', payload]),
            (launch_worker, ['push_to_web', config]),
        ],
        'success publish': [
            (update_checklist, [worker, 'salishsea site pages', payload]),
            (launch_worker, ['push_to_web', config]),
        ],
    }
    try:
        actions['success research'] = [
            (update_checklist, [worker, 'salishsea site pages', payload]),
            (launch_worker, ['make_plots', config, ['nowcast', 'publish',
             '--run-date', checklist['NEMO run']['nowcast']['run_date']]]),
        ]
    except KeyError:
        # No nowcat run date in checklist
        pass
    return actions[msg_type]


def after_push_to_web(worker, msg_type, payload, config):
    actions = {
        # msg type: [(step, [step_args, [step_extra_arg1, ...]])]
        'success': [
            (update_checklist, [worker, 'push to salishsea site', payload]),
        ],
        'failure': None,
        'crash': None,
    }
    if 'finish the day' in checklist['salishsea site pages']:
        actions['success'].append((finish_the_day, [config]))
    return actions[msg_type]


def update_checklist(worker, key, worker_checklist):
    global checklist
    try:
        checklist[key].update(worker_checklist)
    except (KeyError, ValueError, AttributeError):
        checklist[key] = worker_checklist
    logger.info(
        'checklist updated with {} items from {} worker'.format(key, worker))
    with open('nowcast_checklist.yaml', 'wt') as f:
        yaml.dump(checklist, f)


def launch_worker(worker, config, cmd_line_args=[], host='localhost'):
    if host == 'localhost':
        cmd = [config['python'], '-m']
        config_file = config['config_file']
    else:
        cmd = ['ssh', host, 'python', '-m']
        config_file = '/home/ubuntu/MEOPAR/nowcast/nowcast.yaml'
    cmd.extend([
        'salishsea_tools.nowcast.workers.{}'.format(worker),
        config_file,
    ])
    if cmd_line_args:
        cmd.extend(cmd_line_args)
    logger.info('launching {} worker on {}'.format(worker, host))
    logger.debug(cmd)
    subprocess.Popen(cmd)


def is_cloud_ready(config):
    global checklist
    host_name = config['run']['cloud host']
    host = config['run'][host_name]
    if 'nowcast0' in checklist['nodes']:
        if 'cloud addr' not in checklist:
            # Add an empty address so that worker only gets launched once
            checklist['cloud addr'] = ''
            launch_worker('set_head_node_ip', config)
        if len(checklist['nodes']) >= host['nodes']:
            checklist['cloud ready'] = True
            logger.info(
                '{node_count} nodes in {host} ready for '
                'run provisioning'
                .format(node_count=host['nodes'], host=host_name))
            launch_worker('set_ssh_config', config)


def finish_the_day(config):
    """Finish nowcast and forecast automation process for the day.

    Clear the checklist and rotate the log file.
    """
    global checklist
    logger.info('nowcast and forecast processing completed for today')
    checklist_logger.info('checklist:\n{}'.format(pprint.pformat(checklist)))
    checklist = {}
    logger.info('checklist cleared')
    with open('nowcast_checklist.yaml', 'wt') as f:
        yaml.dump(checklist, f)
    rotate_log_files(config)


def rotate_log_files(config):
    try:
        for handler in logger.handlers:
            logger.info('rotating log file')
            if not hasattr(handler, 'when'):
                handler.doRollover()
            level = logging.getLevelName(handler.level).lower()
            lib.fix_perms(config['logging']['log_files'][level])
            logger.info('log file rotated')
            logger.debug('running in process {}'.format(os.getpid()))
    except AttributeError:
        # Logging handler has no rollover; probably a StreamHandler
        pass
    try:
        for handler in checklist_logger.handlers:
            handler.doRollover()
            lib.fix_perms(config['logging']['checklist_log_file'])
    except AttributeError:
        # Logging handler has no rollover; probably a StreamHandler
        pass


if __name__ == '__main__':
    main()
