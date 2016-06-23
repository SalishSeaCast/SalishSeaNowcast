# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

from nowcast import lib


class WorkerError(Exception):
    """Raised when a worker encounters an error or exception that it can't
    recover from.
    """


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
        self.socket = self._init_zmq_interface()
        self._do_work()

    def _do_work(self):
        """Execute the worker function,
        communicate its success or failure to the nowcast manager via
        the messaging framework,
        and handle any exceptions it raises.
        """
        try:
            checklist = self.worker_func(
                self.parsed_args, self.config, self.tell_manager)
            msg_type = self.success(self.parsed_args)
            self.tell_manager(msg_type, checklist)
        except WorkerError:
            msg_type = self.failure(self.parsed_args)
            self.tell_manager(msg_type)
        except SystemExit:
            # Normal termination
            pass
        except:
            self.logger.critical(
                'unhandled exception:\n{traceback}'
                .format(traceback=traceback.format_exc()))
            self.tell_manager('crash')
        self.context.destroy()
        self.logger.debug('task completed; shutting down')

    def _init_zmq_interface(self):
        """Initialize a ZeroMQ request/reply (REQ/REP) interface.

        :returns: ZeroMQ socket for communication with nowcast manager process.
        """
        if self.parsed_args.debug:
            self.logger.debug('**debug mode** no connection to manager')
            return
        socket = self.context.socket(zmq.REQ)
        mgr_host = self.config['zmq']['server']
        port = self.config['zmq']['ports']['frontend']
        socket.connect(
            'tcp://{mgr_host}:{port}'.format(mgr_host=mgr_host, port=port))
        self.logger.debug(
            'connected to {mgr_host} port {port}'
            .format(mgr_host=mgr_host, port=port))
        return socket

    def tell_manager(self, msg_type, payload=None):
        """Exchange messages with the nowcast manager process.

        Message is composed of workers name, msg_type, and payload.
        Acknowledgement message from manager process is logged,
        and payload of that message is returned.

        :arg str msg_type: Key of the message type to send; must be defined for
                       worker name in the configuration data structure.

        :arg payload: Data object to send in the message;
                      e.g. dict containing worker's checklist of
                      accomplishments.

        :returns: Payload included in acknowledgement message from manager
                  process.
        """
        if self.parsed_args.debug:
            self.logger.debug(
                '**debug mode** '
                'message that would have been sent to manager: '
                '({msg_type} {msg_words})'
                .format(
                    msg_type=msg_type,
                    msg_words=self.config['msg_types'][self.name][msg_type]))
            return
        # Send message to nowcast manager
        message = lib.serialize_message(self.name, msg_type, payload)
        self.socket.send_string(message)
        self.logger.debug(
            'sent message: ({msg_type}) {msg_words}'
            .format(
                msg_type=msg_type,
                msg_words=self.config['msg_types'][self.name][msg_type]))
        # Wait for and process response
        msg = self.socket.recv_string()
        message = lib.deserialize_message(msg)
        source = message['source']
        msg_type = message['msg_type']
        self.logger.debug(
            'received message from {source}: ({msg_type}) {msg_words}'
            .format(source=source,
                    msg_type=message['msg_type'],
                    msg_words=self.config['msg_types'][source][msg_type]))
        return message['payload']
