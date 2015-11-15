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

"""Salish Sea NEMO nowcast worker.
"""
import argparse
import logging
import os
import traceback

import zmq

from . import lib


class NowcastWorker(object):
    """Construct a :py:class:`nowcast_worker.NowcastWorker` instance.

    In addition to the constructor arguments below,
    the worker instance has the following attributes:

    * :py:attr:`logger` - A :py:class:`logging.Logger` instance named
      :py:attr:`name`

    * :py:attr:`context` - A :py:class:`zmq.Context` instance that
      provides the basis for the worker's interface to the nowcast
      messaging framework

    * :py:attr:`arg_parser` - A :py:class:`argparse.ArgumentParser`
      instance configured to provide the default worker command-line
      interface that requires a nowcast config file name,
      and provides :kbd:`--debug`,
      :kbd:`--help`,
      and :kbd:`-h` options

    :arg name: The name of the worker.
               This should be the worker's module name without the
               :kbd:`.py` extension.
               That is easily obtained by calling the
               :py:func:`nowcast.lib.get_module_name` function in the
               worker module.
    :type name: str

    :arg description: A description of what the worker does;
                      used in the worker's command-line interface.
                      The worker's module docstring,
                      :py:attr:`__doc__` is often used as its description.
    :type description: str

    :returns: :py:class:`nowcast_worker.NowcastWorker` instance
    """
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(self.name)
        self.context = zmq.Context()
        self.arg_parser = lib.basic_arg_parser(
            self.name, description=self.description)

    def add_argument(self, *args, **kwargs):
        """Add an argument to the worker's command-line interface.

        This is a thin wrapper around
        :py:meth:`argparse.ArgumentParser.add_argument` that accepts
        that method's arguments.
        """
        self.arg_parser = argparse.ArgumentParser(
            prog=self.arg_parser.prog,
            description=self.arg_parser.description,
            parents=[self.arg_parser],
            add_help=False,
        )
        self.arg_parser.add_argument(*args, **kwargs)

    def run(self, worker_func, success, failure):
        """Prepare the worker to do its work, then do it.

        Preparations include:

        * Parsing the worker's command-line argument into a
          :py:class:`argparse.ArgumentParser.Namepsace` instance

        * Reading the nowcast configuration file named on the command
          line to a dict

        * Configuring the worker's logging interface

        * Configuring the worker's interface to the nowcast messaging
          framework

        * Installing handlers for signals from the operating system

        :arg worker_func: Function to be called to do the worker's job.
                          Called with the worker's parsed command-line
                          arguments
                          :py:class:`argparse.ArgumentParser.Namepsace`
                          instance,
                          and the worker's configuration dict.
        :type worker_func: Python function

        :arg success: Function to be called when the worker finishes
                      successfully.
                      Called with the worker's parsed command-line
                      arguments
                      :py:class:`argparse.ArgumentParser.Namepsace`
                      instance.
                      Must return a string whose value is a success
                      message type defined for the worker in the nowcast
                      configuration file.

        :type worker_func: Python function

        :arg failure: Function to be called when the worker fails.
                      Called with the worker's parsed command-line
                      arguments
                      :py:class:`argparse.ArgumentParser.Namepsace`
                      instance.
                      Must return a string whose value is a failure
                      message type defined for the worker in the nowcast
                      configuration file.

        :type worker_func: Python function
        """
        self.worker_func = worker_func
        self.success = success
        self.failure = failure
        self.parsed_args = self.arg_parser.parse_args()
        self.config = lib.load_config(self.parsed_args.config_file)
        lib.configure_logging(self.config, self.logger, self.parsed_args.debug)
        self.logger.debug('running in process {}'.format(os.getpid()))
        self.logger.debug(
            'read config from {.config_file}'.format(self.parsed_args))
        lib.install_signal_handlers(self.logger, self.context)
        self.socket = lib.init_zmq_req_rep_worker(
            self.context, self.config, self.logger)
        self._do_work()

    def _do_work(self):
        """Execute the worker function,
        communicate its success or failure to the nowcast manager via
        the messaging framework,
        and handle any exceptions it raises.
        """
        try:
            checklist = self.worker_func(self.parsed_args, self.config)
            msg_type = self.success(self.parsed_args)
            lib.tell_manager(
                self.name, msg_type, self.config, self.logger, self.socket,
                checklist)
        except lib.WorkerError:
            msg_type = self.failure(self.parsed_args)
            lib.tell_manager(
                self.name, msg_type, self.config, self.logger, self.socket)
        except SystemExit:
            # Normal termination
            pass
        except:
            self.logger.critical('unhandled exception:')
            for line in traceback.format_exc().splitlines():
                self.logger.error(line)
            lib.tell_manager(
                self.name, 'crash', self.config, self.logger, self.socket)
        self.context.destroy()
        self.logger.debug('task completed; shutting down')
