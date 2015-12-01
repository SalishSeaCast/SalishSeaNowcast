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

"""Salish Sea NEMO nowcast library functions for use by manager and workers.
"""
import argparse
import grp
import logging
import logging.handlers
import os
import signal
import socket
import stat
import subprocess
import sys
import time

import arrow
import paramiko
import requests
import yaml
import zmq

from driftwood.formatters import JSONFormatter


# File permissions:
# rw-rw-r--
PERMS_RW_RW_R = (
    stat.S_IRUSR | stat.S_IWUSR |
    stat.S_IRGRP | stat.S_IWGRP |
    stat.S_IROTH
)
# rwxrwxr--
PERMS_RWX_RWX_R = (
    stat.S_IRWXU |
    stat.S_IRWXG |
    stat.S_IROTH
)
# rwxrwxr-x
PERMS_RWX_RWX_R_X = (
    stat.S_IRWXU |
    stat.S_IRWXG |
    stat.S_IROTH | stat.S_IXOTH
)


class WorkerError(Exception):
    """Raised when a worker encounters an error or exception that it can'try:
    recover from.
    """


def get_module_name():
    """Return the name of the module with the path and the extension stripped.

    Example::

      get_module_name('foo/bar/baz.py')

    returns 'baz'.

    Typically used to create a module-level :data:`worker_name` variable::

      worker_name = lib.get_module_name()

    :returns: The name portion of the module filename.
    """
    return os.path.splitext(os.path.basename(sys.argv[0]))[0]


def basic_arg_parser(worker_name, description=None, add_help=True):
    """Return a command-line argument parser w/ handling for always-used args.

    The returned parser provides help messages, and handles the
    :option:`config_file` argument, and the :option:`--debug` option.
    It can be used as the parser for a worker,
    or as a parent parser if the worker has additional arguments
    and/or options.

    :arg worker_name: Name of the worker that the parser is for;
                      used to buid the usage message.
    :type worker_name: str

    :arg description: Brief description of what the worker does that
                      will be displayed in help messages.
    :type description: str

    :arg add_help: Add a `-h/--help` option to the parser.
                   Disable this if you are going to use the returned
                   parser as a parent parser to facilitate adding more
                   args/options.
    :type add_help: boolean

    :returns: :class:`argparse.ArgumentParser` object
    """
    parser = argparse.ArgumentParser(
        description=description, add_help=add_help)
    parser.prog = (
        'python -m salishsea_tools.nowcast.workers.{}'.format(worker_name))
    parser.add_argument(
        'config_file',
        help='''
        Path/name of YAML configuration file for Salish Sea NEMO nowcast.
        '''
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='''
        Send logging output to the console instead of the log file;
        intended only for use when the worker is run in foreground
        from the command-line.
        ''',
    )
    return parser


def arrow_date(string, tz='Canada/Pacific'):
    """Convert a YYYY-MM-DD string to a timezone-aware arrow object
    or raise :py:exc:`argparse.ArgumentTypeError`.

    The time part of the resulting arrow object is set to 00:00:00.

    :arg string: YYYY-MM-DD string to convert.
    :type string: str

    :arg tz: Timezone of the date.
    :type tz: str

    :returns: Date string converted to an :py:class:`arrow.Arrow` object
              with tz as its timezone.

    :raises: :py:exc:`argparse.ArgumentTypeError`
    """
    try:
        arw = arrow.get(string, 'YYYY-MM-DD')
        return arrow.get(arw.date(), tz)
    except arrow.parser.ParserError:
        msg = (
            'unrecognized date format: {} - '
            'please use YYYY-MM-DD'.format(string))
        raise argparse.ArgumentTypeError(msg)


def load_config(config_file):
    """Load the YAML config_file and return its contents as a dict.

    The value of config_file is added to the config dict with the key
    :kbd:`config_file`.

    :arg config_file: Path/name of YAML configuration file for
                      Salish Sea NEMO nowcast.
    :type config_file: str

    :returns: config dict
    """
    with open(config_file, 'rt') as f:
        config = yaml.load(f)
    config['config_file'] = config_file
    return config


def configure_logging(config, logger, debug, email=True):
    """Set up logging configuration.

    This function assumes that the logger object has been created
    in the module from which the function is called.
    That is typically done with a module-level commands like::

      worker_name = lib.get_module_name()

      logger = logging.getLogger(worker_name)

    :arg config: Configuration data structure.
    :type config: dict

    :arg logger: Logger to be configured.
    :type logger: :obj:`logging.Logger`

    :arg debug: Debug mode; log to console instead of to file.
    :type debug: boolean

    :arg email: Configure SMTP logging handler;
                only effective when debug == False.
    :type email: boolean
    """
    logger.setLevel(logging.DEBUG)
    text_formatter = logging.Formatter(
        config['logging']['message_format'],
        datefmt=config['logging']['datetime_format'])
    json_formatter = JSONFormatter(extra_attrs=[
        'forecast',
        'date',
        'run_type',
        'host_name',
        'plot_type',
        'page_type',
    ])
    for level, filename in config['logging']['log_files'].items():
        # Text log files
        log_file = os.path.join(
            os.path.dirname(config['config_file']), filename)
        handler = (
            logging.StreamHandler() if debug
            else logging.handlers.RotatingFileHandler(
                log_file, backupCount=config['logging']['backup_count']))
        handler.setLevel(getattr(logging, level.upper()))
        handler.setFormatter(text_formatter)
        logger.addHandler(handler)
        if not debug:
            # JSON log files
            log_file = '{}.json'.format(log_file)
            handler = logging.handlers.TimedRotatingFileHandler(
                log_file, when='d', interval=30, backupCount=120)
            handler.setLevel(getattr(logging, level.upper()))
            handler.setFormatter(json_formatter)
            logger.addHandler(handler)
    if not debug and email:
        # Email notifications
        level = config['logging']['email']['level']
        subject = config['logging']['email']['subject'].format(level=level)
        email = logging.handlers.SMTPHandler(
            mailhost=config['logging']['email']['mailhost'],
            fromaddr=config['logging']['email']['fromaddr'],
            toaddrs=config['logging']['email']['toaddrs'],
            subject=subject,
        )
        email.setLevel(getattr(logging, level.upper()))
        email.setFormatter(text_formatter)
        logger.addHandler(email)


def install_signal_handlers(logger, context):
    """Install handlers to cleanly deal with interrupt and terminate signals.

    This function assumes that the logger and context objects
    have been created in the module from which the function is called.
    That is typically done with a module-level commands like::

      worker_name = lib.get_module_name()

      logger = logging.getLogger(worker_name)

      context = zmq.Context()

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg context: ZeroMQ context object.
    :type context: :class:`zmq.Context`
    """
    def sigint_handler(signal, frame):
        logger.info(
            'interrupt signal (SIGINT or Ctrl-C) received; shutting down')
        context.destroy()
        sys.exit(0)

    def sigterm_handler(signal, frame):
        logger.info(
            'termination signal (SIGTERM) received; shutting down')
        context.destroy()
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)


def init_zmq_req_rep_worker(context, config, logger, mgr_host='localhost'):
    """Initialize a ZeroMQ request/reply (REQ/REP) worker.

    :arg context: ZeroMQ context object.
    :type context: :class:`zmq.Context`

    :arg config: Configuration data structure.
    :type config: dict

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg mgr_host: Host name or IP address of the nost that the nowcast
                   manager process runs on.
                   Defaults to 'localhost'.
    :type mgr_host: str

    :returns: ZeroMQ socket for communication with nowcast manager process.
    """
    socket = context.socket(zmq.REQ)
    port = config['zmq']['ports']['frontend']
    socket.connect(
        'tcp://{mgr_host}:{port}'.format(mgr_host=mgr_host, port=port))
    logger.debug(
        'connected to {mgr_host} port {port}'
        .format(mgr_host=mgr_host, port=port))
    return socket


def tell_manager(
    worker_name, msg_type, config, logger, socket, payload=None,
):
    """Exchange messages with the nowcast manager process.

    Message is composed of workers name, msg_type, and payload.
    Acknowledgement message from manager process is logged,
    and payload of that message is returned.

    :arg worker_name: Name of the worker sending the message.
    :arg worker_name: str

    :arg msg_type: Key of the message type to send; must be defined for
                   worker_name in the configuration data structure.
    :type msg_type: str

    :arg config: Configuration data structure.
    :type config: dict

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg socket: ZeroMQ socket for communication with nowcast manager
                 process.
    :type socket: :py:class:`zmq.Socket`

    :arg payload: Data object to send in the message;
                  e.g. dict containing worker's checklist of accomplishments.

    :returns: Payload included in acknowledgement message from manager
              process.
    """
    # Send message to nowcast manager
    message = serialize_message(worker_name, msg_type, payload)
    socket.send_string(message)
    logger.debug(
        'sent message: ({msg_type}) {msg_words}'
        .format(
            msg_type=msg_type,
            msg_words=config['msg_types'][worker_name][msg_type]))
    # Wait for and process response
    msg = socket.recv_string()
    message = deserialize_message(msg)
    source = message['source']
    msg_type = message['msg_type']
    logger.debug(
        'received message from {source}: ({msg_type}) {msg_words}'
        .format(source=source,
                msg_type=message['msg_type'],
                msg_words=config['msg_types'][source][msg_type]))
    return message['payload']


def serialize_message(source, msg_type, payload=None):
    """Transform message dict into byte-stream suitable for sending.

    :arg source: Name of the worker or manager sending the message;
                 typically :data:`worker_name`.
    :arg source: str

    :arg msg_type: Key of a message type that is defined for source
                   in the configuration data structure.
    :type msg_type: str

    :arg payload: Content of message;
                  must be serializable by YAML such that it can be
                  deserialized by :func:`yaml.safe_load`.
    :type payload: Python object

    :returns: Message dict serialized using YAML.
    """
    message = {
        'source': source,
        'msg_type': msg_type,
        'payload': payload,
    }
    return yaml.dump(message)


def deserialize_message(message):
    """Transform received message from byte-stream to dict.

    :arg message: Message dict serialized using YAML.
    :type message: bytes
    """
    return yaml.safe_load(message)


def get_web_data(
    url,
    logger,
    filepath=None,
    first_retry_delay=2,        # seconds
    retry_backoff_factor=2,
    retry_time_limit=60 * 60,   # seconds
):
    """Download content from url, optionally storing it in filepath.

    If the first download attempt fails, retry at intervals until the
    retry_time_limit is exceeded. The first retry occurs after
    first_retry_delay seconds. The delay until the next retry is
    calculated by multiplying the previous delay by retry_backoff_factor.

    So, with the default arugment values, the first retry will occur
    2 seconds after the download fails, and subsequent retries will
    occur at 4, 8, 16, 32, 64, ..., 2048 seconds after each failure.

    :arg url: URL to download content from.
    :type url: str

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg filepath: File path/name in which to store the downloaded content;
                   defaults to :py:obj:`None`, in which case the content
                   is returned.
    :type filepath: str

    :arg first_retry_delay: Number of seconds to wait before doing the
                            first retry after the initial download
                            attempt fails.
    :type first_retry_delay: int or float

    :arg retry_backoff_factor: Multiplicative factor that increases the
                               time interval between retries.
    :type retry_backoff_factor: int or float

    :arg retry_time_limit: Maximum number of seconds for the final retry
                           wait interval.
                           The actual wait time is less than or equal to
                           the limit so it may be significantly less than
                           the limit;
                           e.g. with the default argument values the final
                           retry wait interval will be 2048 seconds.
    :type retry_time_limit: int or float

    :returns: Downloaded content if filepath is :py:obj:`None`,
              otherwise :py:obj:`requests.Response.headers` dict.

    :raises: :py:exc:`nowcast.lib.WorkerError`
    """
    try:
        response = requests.get(url, stream=filepath is not None)
        response.raise_for_status()
        return _handle_url_content(response, filepath)
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.HTTPError,
        socket.error,
    ) as e:
        logger.debug('received {0} from {url}'.format(e, url=url))
        delay = first_retry_delay
        retries = 0
        while delay <= retry_time_limit:
            logger.debug('waiting {} seconds until retry'.format(delay))
            time.sleep(delay)
            try:
                response = requests.get(url, stream=filepath is not None)
                response.raise_for_status()
                return _handle_url_content(response, filepath)
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.HTTPError,
                socket.error,
            ) as e:
                logger.debug(
                    'received {0} from {url}'.format(e, url=url))
                delay *= retry_backoff_factor
                retries += 1
        logger.error(
            'giving up; download from {} failed {} times'
            .format(url, retries + 1))
        raise WorkerError


def _handle_url_content(response, filepath=None):
    """Return HTTP response content or store it in filepath.

    :arg response: HTTP response object.
    :type response: :py:class:`requests.Response`

    :arg filepath: File path/name in which to store the downloaded content;
                   defaults to :py:obj:`None`, in which case the content
                   is returned.
    :type filepath: str

    :returns: Downloaded content if filepath is :py:obj:`None`,
              otherwise :py:obj:`requests.Response.headers` dict.
    """
    if filepath is None:
        # Return the content as text
        return response.content
    # Store the streamed content in filepath and return the headers
    with open(filepath, 'wb') as f:
        for block in response.iter_content(1024):
            if not block:
                break
            f.write(block)
    return response.headers


def fix_perms(path, mode=PERMS_RW_RW_R, grp_name=None):
    """Try to set the permissions and group ownership of the file
    or directory at path.

    The desired permissions are given by mode.
    If grp_name is given,
    set the directory's gid to that associated with the grp_name.

    In the event that the file or directory at path is owned by another
    user the gid or permissions changes fail silently because they are
    probably correct already.

    :arg path: Path to fix the permissions of.
    :type path: str

    :arg mode: Numeric mode to set the directory's permissions to.
    :type mode: int

    :arg grp_name: Group name to change the path's ownership to.
                   Defaults to None meaning do nothing.
    :type grp_name: str
    """
    try:
        if grp_name is not None:
            gid = grp.getgrnam(grp_name).gr_gid
            os.chown(path, -1, gid)
        os.chmod(path, mode)
    except OSError:
        # Can't change gid or mode of a directory we don't own
        # but we just accept that
        pass


def mkdir(path, logger, mode=PERMS_RWX_RWX_R_X, grp_name=None, exist_ok=True):
    """Create a directory at path with its permissions set to mode.
    If grp_name is given,
    set the directory's gid to that associated with the grp_name.
    If path already exists and exist_ok is False,
    log an error messages and raise an exception.

    In the event that the directory already exists at path but is owned by
    another user the gid or permissions changes fail silently because they
    are probably correct already.

    :arg path: Path to create the directory at.
    :type path: str

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg mode: Numeric mode to set the directory's permissions to.
    :type mode: int

    :arg grp_name: Group name to change the directory's ownership to.
                   Defaults to None meaning that the directory's group
                   will be the same as its parent's.
    :type grp_name: str

    :arg exist_ok: Indicate whether or not to log and error message and
                   raise an exception if path already exists.
                   Defaults to True meaning that an existing path is
                   accepted silently.
    :type exist_ok: boolean

    :raises: :py:exc:`lib.WorkerError`
             if path already exists and exist_ok is False
    """
    try:
        os.mkdir(path)
    except OSError:
        if not exist_ok:
            msg = '{} directory already exists; not overwriting'.format(path)
            logger.error(msg)
            raise WorkerError
    fix_perms(path, mode, grp_name)


def run_in_subprocess(cmd, output_logger, error_logger):
    """Run cmd in a subprocess and log its stdout to output_logger.
    Catch errors from the subprocess, log them to error_logger,
    and raise the exception for handling somewhere higher in the call stack.

    :arg cmd: Command and its arguments/options to run in subprocess.
    :type cmd: list

    :arg output_logger: Logger object to send command output to when
                        command is successful.
    :type output_logger: :class:`logging.Logger`

    :arg error_logger: Logger object to send error message(s) to when
                        command returns non-zero status cdoe.
    :type error_logger: :class:`logging.Logger`

    :raises: :py:exc:`nowcast.lib.WorkerError`
    """
    output_logger(
        'running command in subprocess: {}'.format(cmd))
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        for line in output.splitlines():
            if line:
                output_logger(line)
    except subprocess.CalledProcessError as e:
        error_logger(
            'subprocess {cmd} failed with return code {status}'
            .format(cmd=cmd, status=e.returncode))
        for line in e.output.splitlines():
            if line:
                error_logger(line)
        raise WorkerError


def get_nova_credentials_v2():
    """Return an OpenStack compute API credentials dict containing credential
    values from the environment.

    :returns: OpenStack nova API credentials dict
    """
    credentials = {
        'version': '2',
        'username': os.environ['OS_USERNAME'],
        'api_key': os.environ['OS_PASSWORD'],
        'auth_url': os.environ['OS_AUTH_URL'],
        'project_id': os.environ['OS_TENANT_NAME'],
    }
    return credentials


def ssh(host, key_filename, ssh_config_file='~/.ssh/config'):
    """Return an SSH client connected to host.

    It is assumed that ssh_config_file contains an entry for host,
    and that the corresponding identity is loaded and active in the
    user's ssh agent.

    The client's close() method should be called when its usefulness
    had ended.

    :arg host: Name of the host to connect the client to.
    :type config: str

    :arg ssh_config_file: File path/name of the SSH2 config file to obtain
                     the hostname and username values.
    :type ssh_config_file: str

    :returns: :class:`paramiko.client.SSHClient` object
    """
    ssh_client = paramiko.client.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_config = paramiko.config.SSHConfig()
    with open(os.path.expanduser(ssh_config_file)) as f:
        ssh_config.parse(f)
    host = ssh_config.lookup(host)
    ssh_client.connect(
        host['hostname'], username=host['user'],
        key_filename=key_filename,
        compress=True,
    )
    return ssh_client


def sftp(host, key_filename, ssh_config_file='~/.ssh/config'):
    """Return an SFTP client connected to host, and the SSH client on
    which it is based.

    It is assumed that ssh_config_file contains an entry for host,
    and that the corresponding identity is loaded and active in the
    user's ssh agent.

    The clients' close() methods should be called when their usefulness
    had ended.

    :arg host: Name of the host to connect the client to.
    :type config: str

    :arg ssh_config_file: File path/name of the SSH2 config file to obtain
                     the hostname and username values.
    :type ssh_config_file: str

    :returns: 2-tuple containing a :class:`paramiko.client.SSHClient`
              object and a :class:`paramiko.sftp_client.SFTPClient` object.
    """
    ssh_client = ssh(host, key_filename, ssh_config_file)
    sftp_client = ssh_client.open_sftp()
    return ssh_client, sftp_client
