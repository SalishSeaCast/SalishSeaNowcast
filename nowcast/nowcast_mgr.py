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
import logging
import os
import pprint
import subprocess
import traceback

import yaml
import zmq

from nowcast import lib


def main():
    mgr = NowcastManager()
    mgr.run()


class NowcastManager:
    """Construct a :py:class:`nowcast.nowcast_mgr.NowcastManager` instance.

    A manager instance has the following atrributes:

    * :py:attr:`name` - The name of the manager instance:
      the manager's module name without the :kbd:`.py` extension;
      obtained by calling the :py:func:`nowcast.lib.get_module_name`
      function in the constructor.

    * :py:attr:`logger` - A :py:class:`logging.Logger` instance
      named :py:attr:`name`

    * :py:attr:`checklist_logger` - A :py:class:`logging.Logger` instance
      named :kbd:`checklist`;
      used to log the :py:attr:`checklist` at the end of each day's
      processing.

    * :py:attr:`worker_loggers` - A :py:class:`dict` of
      :py:class:`logging.Logger` instances;
      used to log messages from the :py:mod:`nowcast.workers.run_NEMO`
      and :py:mod:`nowcast.workers.watch_NEMO` workers that typically run
      on a different machine than the manager.

    * :py:attr:`context` - A :py:class:`zmq.Context` instance that
      provides the basis for the worker's interface to the nowcast
      messaging framework

    * :py:attr:`checklist` - A :py:class:`dict` containing the nowcast
      system state as updated by the workers.

    * :py:attr:`parsed_args` - An :py:class:`argparse.Namespace` instance
      containing the arguments and option flags and values parsed from the
      command-line when the manager was started.

    * :py:attr:`config` - A :py:class:`dict` containing the nowcast system
      configuration that was read from the configuration file given on the
      command-line when the manager was started.

    :returns: :py:class:`nowcast_mgr.NowcastManager` instance
    """
    def __init__(self):
        self.name = lib.get_module_name()
        self.logger = logging.getLogger(self.name)
        self.checklist_logger = logging.getLogger('checklist')
        self.worker_loggers = {}
        self.context = zmq.Context()
        self.checklist = {}

    @property
    def _after_actions(self):
        """Registry of methods used to calculate next step action(s)
        upon completion of a worker's task.
        """
        return {
            # worker name: method to calculate next step action(s)
            'download_weather': self._after_download_weather,
            'get_NeahBay_ssh': self._after_get_NeahBay_ssh,
            'make_runoff_file': self._after_make_runoff_file,
            'grib_to_netcdf': self._after_grib_to_netcdf,
            'upload_forcing': self._after_upload_forcing,
            # 'upload_all_files': self._after_upload_all_files,
            'make_forcing_links': self._after_make_forcing_links,
            'run_NEMO': self._after_run_NEMO,
            'watch_NEMO': self._after_watch_NEMO,
            'download_results': self._after_download_results,
            'make_plots': self._after_make_plots,
            'make_site_page': self._after_make_site_page,
            'push_to_web': self._after_push_to_web,
        }

    def run(self):
        """Set up and run the nowcast manager.
        """
        self.parsed_args = self._cli()
        self.config = self._load_config()
        self._prep_logging()
        self._install_signal_handlers()
        self._socket = self._prep_messaging()
        if not self.parsed_args.ignore_checklist:
            self._load_checklist()
        self._process_messages()

    def _cli(self):
        """Configure command-line argument parser and return parsed arguments
        object.
        """
        base_parser = lib.basic_arg_parser(
            self.name, description=__doc__, add_help=False)
        parser = argparse.ArgumentParser(
            prog='python -m salishsea_tools.nowcast.{.name}'.format(self),
            description=base_parser.description,
            parents=[base_parser])
        parser.add_argument(
            '--ignore-checklist', action='store_true',
            help='''
            Don't load the serialized checklist left by a previously
            running instance of the nowcast manager.
            ''',
        )
        return parser.parse_args()

    def _load_config(self):
        """Load config from file specified on command-line and set key to
        send logging output to console if we're running in debug mode.
        """
        config = lib.load_config(self.parsed_args.config_file)
        config['logging']['console'] = self.parsed_args.debug
        return config

    def _prep_logging(self):
        """Set up logging and emit PID and config file used.
        """
        lib.configure_logging(self.config, self.logger, self.parsed_args.debug)
        self.logger.info('running in process {}'.format(os.getpid()))
        self.logger.debug(
            'read config from {.config_file}'.format(self.parsed_args))
        self.checklist_logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            self.config['logging']['message_format'],
            datefmt=self.config['logging']['datetime_format'])
        log_file = os.path.join(
            os.path.dirname(self.config['config_file']),
            self.config['logging']['checklist_log_file'])
        handler = logging.handlers.RotatingFileHandler(
            log_file, backupCount=self.config['logging']['backup_count'])
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        self.checklist_logger.addHandler(handler)

    def _install_signal_handlers(self):
        """Install signal handlers for hangup, interrupt, and terminate signals.
        """
        ## TODO: Add handler for hangup signal to reload config file
        lib.install_signal_handlers(self.logger, self.context)

    def _prep_messaging(self):
        """Set up messaging system interface and connect to broker.
        """
        socket = self.context.socket(zmq.REP)
        backend_port = self.config['zmq']['ports']['backend']
        socket.connect('tcp://localhost:{}'.format(backend_port))
        self.logger.debug('connected to port {}'.format(backend_port))
        return socket

    def _load_checklist(self):
        """Load the serialized checklist left on disk by a previous
        instance of the manager.
        """
        checklist_file = self.config['checklist file']
        try:
            with open(checklist_file, 'rt') as f:
                self.checklist = yaml.load(f)
                self.logger.info(
                    'checklist read from {}'.format(checklist_file))
                self.logger.info(
                    'checklist:\n{}'.format(pprint.pformat(self.checklist)))
        except FileNotFoundError as e:
            self.logger.warning('checklist load failed: {}'.format(e))
            self.logger.warning('running with empty checklist')

    def _process_messages(self):
        """Process messages from workers.
        """
        while True:
            self.logger.debug('listening...')
            try:
                message = self._socket.recv()
                reply, next_steps = self._message_handler(message)
                self._socket.send_string(reply)
                if next_steps is not None:
                    for next_step, next_step_args in next_steps:
                        next_step(*next_step_args)
            except zmq.ZMQError as e:
                # Fatal ZeroMQ problem
                self.logger.critical('ZMQError: {}\nshutting down'.format(e))
                break
            except SystemExit:
                # Termination by signal
                break
            except:
                msg = 'unhandled exception:'
                for line in traceback.format_exc().splitlines():
                    msg = '\n'.join((msg, line))
                self.logger.critical(msg)

    def _message_handler(self, message):
        """Handle message from worker.
        """
        msg = lib.deserialize_message(message)
        worker = msg['source']
        msg_type = msg['msg_type']
        payload = msg['payload']
        if msg_type not in self.config['msg_types'][worker]:
            reply = self._handle_undefined_msg(worker, msg_type)
            return reply, None
        self._log_received_msg(worker, msg_type)
        if msg_type.startswith('need'):
            reply = self._handle_need_msg(payload)
            return reply, None
        if msg_type.startswith('log'):
            reply = self._handle_log_msg(worker, msg_type, payload)
            return reply, None
        reply, next_steps = self._handle_action_msg(worker, msg_type, payload)
        return reply, next_steps

    def _handle_undefined_msg(self, worker, msg_type):
        """Emit warning message about undefined message type and create
        reply to worker.
        """
        self.logger.warning(
            'undefined message type received from {worker}: {msg_type}'
            .format(worker=worker, msg_type=msg_type))
        reply = lib.serialize_message(self.name, 'undefined msg')
        return reply

    def _log_received_msg(self, worker, msg_type):
        """Emit debug message about message received from worker.
        """
        self.logger.debug(
            'received message from {worker}: ({msg_type}) {msg_words}'
            .format(worker=worker,
                    msg_type=msg_type,
                    msg_words=self.config['msg_types'][worker][msg_type]))

    def _handle_need_msg(self, payload):
        """Handle request for checklist section message from worker.
        """
        reply = lib.serialize_message(
            self.name, 'ack', self.checklist[payload])
        return reply

    def _handle_log_msg(self, worker, msg_type, payload):
        """Handle logging message from worker.
        """
        level = getattr(logging, msg_type.split('.')[1].upper())
        self.worker_loggers[worker].log(level, payload)
        reply = lib.serialize_message(self.name, 'ack')
        return reply

    def _handle_action_msg(self, worker, msg_type, payload):
        """Handle success, failure, or crash message from worker with
        appropriate next step action(s).
        """
        next_steps = self._after_actions[worker](msg_type, payload)
        reply = lib.serialize_message(self.name, 'ack')
        return reply, next_steps

    def _after_download_weather(self, msg_type, payload):
        """Return list of next step action method(s) and args to take
        upon receipt of success, failure, or crash message from
        download_weather worker.
        """
        actions = {
            'crash': None,
            'failure 00': None,
            'failure 06': None,
            'failure 12': None,
            'failure 18': None,
        }
        if msg_type.startswith('success'):
            actions[msg_type] = [
                (self._update_checklist,
                    ['download_weather', 'weather', payload]),
            ]
            if msg_type.endswith('06'):
                actions['success 06'].extend([
                    (self._launch_worker, ['make_runoff_file']),
                ])
                if 'forecast2' in self.config['run_types']:
                    actions['success 06'].extend([
                        (self._launch_worker,
                            ['get_NeahBay_ssh', ['forecast2']]),
                        (self._launch_worker,
                            ['grib_to_netcdf', ['forecast2']]),
                    ])
            if all((
                msg_type.endswith('12'),
                'nowcast' in self.config['run_types']
            )):
                actions['success 12'].extend([
                    (self._launch_worker, ['get_NeahBay_ssh', ['nowcast']]),
                    (self._launch_worker, ['grib_to_netcdf', ['nowcast+']]),
                ])
        return actions[msg_type]

    def _after_get_NeahBay_ssh(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        get_NeahBay_ssh worker.
        """
        actions = {
            'crash': None,
            'failure nowcast': None,
            'failure forecast': None,
            'failure forecast2': None,
        }
        if msg_type.startswith('success'):
            actions[msg_type] = [
                (self._update_checklist,
                    ['get_NeahBay_ssh', 'Neah Bay ssh', payload]),
            ]
            for host in ('hpc host', 'cloud host'):
                if 'forecast' in self.config['run_types']:
                    if all((
                        host in self.config['run'],
                        msg_type.endswith('forecast')
                    )):
                        actions['success forecast'].append(
                            (self._launch_worker,
                                ['upload_forcing',
                                    [self.config['run'][host], 'ssh']])
                        )
        return actions[msg_type]

    def _after_make_runoff_file(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        make_runoff_file worker.
        """
        actions = {
            'crash': None,
            'failure': None,
            'success':
                [(self._update_checklist,
                    ['make_runoff_file', 'rivers', payload])],
        }
        return actions[msg_type]

    def _after_grib_to_netcdf(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        grib_to_netcdf worker.
        """
        actions = {
            'crash': None,
            'failure nowcast+': None,
            'failure forecast2': None,
            'success nowcast+': [
                (self._update_checklist,
                    ['grib_to_netcdf', 'weather forcing', payload]),
            ],
            'success forecast2': [
                (self._update_checklist,
                    ['grib_to_netcdf', 'weather forcing', payload]),
            ],
        }
        for host in ('cloud host', 'hpc host'):
            if host in self.config['run']:
                if 'nowcast' in self.config['run_types']:
                    actions['success nowcast+'].append(
                        (self._launch_worker,
                            ['upload_forcing',
                                [self.config['run'][host], 'nowcast+']])
                    )
                if 'forecast2' in self.config['run_types']:
                    actions['success forecast2'].append(
                        (self._launch_worker,
                            ['upload_forcing',
                                [self.config['run'][host], 'forecast2']])
                    )
        if all(
            ('nowcast-green host' in self.config['run'],
             'nowcast-green' in self.config['run_types'])):
                actions['success nowcast+'].append(
                    (self._launch_worker,
                        ['make_forcing_links',
                            [self.config['run']['nowcast-green host'],
                             'nowcast-green', '--shared-storage']])
                )
        return actions[msg_type]

    def _after_upload_forcing(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        upload_forcing worker.
        """
        try:
            host_name = list(payload.keys())[0]
        except (AttributeError, IndexError):
            # Malformed payload of no host name in payload;
            # upload_forcing worker probably crashed
            return None
        actions = {
            'crash': None,
            'failure nowcast+': None,
            'failure forecast2': None,
            'failure ssh': None,
            'success nowcast+': [
                (self._update_checklist,
                    ['upload_forcing', 'forcing upload', payload]),
            ],
            'success forecast2': [
                (self._update_checklist,
                    ['upload_forcing', 'forcing upload', payload]),
            ],
            'success ssh': [
                (self._update_checklist,
                    ['upload_forcing', 'forcing upload', payload]),
            ],
        }
        run_types = [
            # (upload_forcing, make_forcing_links)
            ('nowcast', 'nowcast+'),
            ('forecast', 'ssh'),
            ('forecast2', 'forecast2'),
        ]
        for run_type, upload_run_type in run_types:
            if run_type in self.config['run_types']:
                actions['success {}'.format(upload_run_type)].append(
                    (self._launch_worker,
                        ['make_forcing_links', [host_name, upload_run_type]])
                )
        return actions[msg_type]

    def _after_make_forcing_links(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        make_forcing_links worker.
        """
        actions = {
            'crash': None,
            'failure nowcast+': None,
            'failure forecast2': None,
            'failure ssh': None,
            'failure nowcast-green': None,
        }
        if msg_type.startswith('success'):
            actions[msg_type] = [
                (self._update_checklist,
                    ['make_forcing_links', 'forcing links', payload]),
            ]
            if ('cloud host' in self.config['run']
                    and self.config['run']['cloud host'] in payload):
                for worker in ('run_NEMO', 'watch_NEMO'):
                    self.worker_loggers[worker] = logging.getLogger(worker)
                    lib.configure_logging(
                        self.config, self.worker_loggers[worker],
                        self.parsed_args.debug)
                run_type = {
                    'nowcast+': 'nowcast',
                    'forecast2': 'forecast2',
                    'ssh': 'forecast',
                }[msg_type.split()[1]]
                actions[msg_type].append(
                    (self._launch_worker, ['run_NEMO', [run_type],
                     self.config['run']['cloud host']])
                )
        return actions[msg_type]

    def _after_run_NEMO(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        run_NEMO worker.
        """
        for handler in self.worker_loggers['run_NEMO'].handlers:
            self.worker_loggers['run_NEMO'].removeHandler(handler)
        actions = {
            'crash': None,
            'failure': None,
            'success':
                [(self._update_checklist,
                    ['run_NEMO', 'NEMO run', payload])],
        }
        return actions[msg_type]

    def _after_watch_NEMO(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        watch_NEMO worker.
        """
        for handler in self.worker_loggers['watch_NEMO'].handlers:
            self.worker_loggers['watch_NEMO'].removeHandler(handler)
        actions = {
            'crash': None,
            'failure nowcast': None,
            'failure forecast': None,
            'failure forecast2': None,
        }
        if msg_type.startswith('success'):
            run_type = msg_type.split()[1]
            actions[msg_type] = [
                (self._update_checklist, ['watch_NEMO', 'NEMO run', payload]),
                (self._launch_worker,
                    ['download_results',
                        [self.config['run']['cloud host'], run_type,
                         '--run-date', payload[run_type]['run date']]]),
            ]
            if msg_type == 'success nowcast':
                actions[msg_type].insert(
                    1, (self._launch_worker, ['get_NeahBay_ssh', ['forecast']])
                )
        return actions[msg_type]

    def _after_download_results(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        download_results worker.
        """
        actions = {
            'crash': None,
            'failure nowcast': None,
            'failure forecast': None,
            'failure forecast2': None,
        }
        if msg_type.startswith('success'):
            run_type = msg_type.split()[1]
            plot_type = 'research' if run_type == 'nowcast' else 'publish'
            actions[msg_type] = [
                (self._update_checklist,
                    ['download_results', 'results files', payload]),
                (self._launch_worker,
                    ['make_plots', [run_type, plot_type, '--run-date',
                     self.checklist['NEMO run'][run_type]['run date']]]),
            ]
        return actions[msg_type]

    def _after_make_plots(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        make_plots worker.
        """
        actions = {
            'crash': None,
            'failure nowcast research': None,
            'failure nowcast publish': None,
            'failure nowcast comparison': None,
            'failure forecast publish': None,
            'failure forecast2 publish': None,
        }
        if msg_type.startswith('success'):
            _, run_type, page_type = msg_type.split()
            actions[msg_type] = [
                (self._update_checklist, ['make_plots', 'plots', payload]),
                (self._launch_worker,
                    ['make_site_page', [run_type, page_type, '--run-date',
                     self.checklist['NEMO run'][run_type]['run date']]])
            ]
        return actions[msg_type]

    def _after_make_site_page(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        make_site_page worker.
        """
        actions = {
            'crash': None,
            'failure index': None,
            'failure research': None,
            'failure publish': None,
        }
        if msg_type.startswith('success'):
            _, page_type = msg_type.split()
            actions[msg_type] = [
                (self._update_checklist,
                    ['make_site_page', 'salishsea site pages', payload]),
            ]
            if page_type in ('index', 'publish'):
                actions[msg_type].append(
                    (self._launch_worker, ['push_to_web']))
            if page_type == 'research':
                actions[msg_type].append(
                    (self._launch_worker,
                        ['make_plots', ['nowcast', 'publish', '--run-date',
                         self.checklist['NEMO run']['nowcast']['run date']]])
                )
        return actions[msg_type]

    def _after_push_to_web(self, msg_type, payload):
        """Return list of next step action method(s) and args to execute
        upon receipt of success, failure, or crash message from
        push_to_web worker.
        """
        actions = {
            'crash': None,
            'failure': None,
            'success':
                [(self._update_checklist,
                    ['push_to_web', 'push to salishsea site', payload])],
        }
        if 'finish the day' in self.checklist['salishsea site pages']:
            actions['success'].append((self._finish_the_day, []))
        return actions[msg_type]

    def _update_checklist(self, worker, key, worker_checklist):
        """Update the checklist value at key with the items passed from
        the worker.

        If key is not present in the checklist, add it with the worker
        items as its value.

        Write the checklist to disk as a YAML file so that it can be
        inspected and/or recovered if the manager instance is restarted.
        """
        try:
            self.checklist[key].update(worker_checklist)
        except (KeyError, ValueError, AttributeError):
            self.checklist[key] = worker_checklist
        self.logger.info(
            'checklist updated with {} items from {} worker'
            .format(key, worker))
        self._write_checklist_to_disk()

    def _write_checklist_to_disk(self):
        """Write the checklist to disk as a YAML file so that it can be
        inspected and/or recovered if the manager instance is restarted.
        """
        with open(self.config['checklist file'], 'wt') as f:
            yaml.dump(self.checklist, f)

    def _launch_worker(self, worker, cmd_line_args=[], host='localhost'):
        """Use a subprocess to launch worker on host with the given
        command-line arguments.

        This method *does not* wait for the subprocess to complete.
        """
        if host == 'localhost':
            cmd = [self.config['python'], '-m']
            config_file = self.config['config_file']
        else:
            cmd = ['ssh', host, self.config['run'][host]['python'], '-m']
            config_file = self.config['run'][host]['config_file']
        cmd.extend(['nowcast.workers.{}'.format(worker), config_file])
        if cmd_line_args:
            cmd.extend(cmd_line_args)
        self.logger.info('launching {} worker on {}'.format(worker, host))
        self.logger.debug(cmd)
        subprocess.Popen(cmd)

    def _finish_the_day(self):
        """Finish automation process for the day.

        Clear the checklist and rotate the log files.
        """
        self.logger.info('nowcast and forecast processing completed for today')
        self.checklist_logger.info(
            'checklist:\n{}'.format(pprint.pformat(self.checklist)))
        self.checklist = {}
        self.logger.info('checklist cleared')
        self._write_checklist_to_disk()
        self._rotate_log_files()

    def _rotate_log_files(self):
        self.logger.info('rotating log files')
        for handler in self.logger.handlers:
            if not hasattr(handler, 'when'):
                try:
                    handler.doRollover()
                except AttributeError:
                    # Logging handler has no rolloever;
                    # probably a StreamHandler
                    continue
                level = logging.getLevelName(handler.level).lower()
                log_file = self.config['logging']['log_files'][level]
                lib.fix_perms(log_file)
                self.logger.info(
                    'log file rotated: {}'.format(log_file))
        for handler in self.checklist_logger.handlers:
            try:
                handler.doRollover()
            except AttributeError:
                # Logging handler has no rolloever; probably a StreamHandler
                continue
            log_file = self.config['logging']['checklist_log_file']
            lib.fix_perms(log_file)
            self.logger.info('log file rotated: {}'.format(log_file))
        self.logger.debug('running in process {}'.format(os.getpid()))


if __name__ == '__main__':
    main()  # pragma: no cover
