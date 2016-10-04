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

"""Salish Sea NEMO nowcast library functions for use by manager and workers.
"""
import grp
import logging
import logging.handlers
import os
import stat
import subprocess

import paramiko
from driftwood.formatters import JSONFormatter
from nemo_nowcast import WorkerError


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
