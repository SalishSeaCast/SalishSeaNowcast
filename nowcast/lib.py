#  Copyright 2013 – present by the SalishSeaCast Project contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# SPDX-License-Identifier: Apache-2.0


"""SalishSeaCast utility functions for use by workers."""
import grp
import logging
import logging.handlers
import os
import subprocess

from nemo_nowcast import WorkerError
from nemo_nowcast.fileutils import FilePerms


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
        config["logging"]["message_format"],
        datefmt=config["logging"]["datetime_format"],
    )
    for level, filename in config["logging"]["log_files"].items():
        # Text log files
        log_file = os.path.join(os.path.dirname(config["config_file"]), filename)
        handler = (
            logging.StreamHandler()
            if debug
            else logging.handlers.RotatingFileHandler(
                log_file, backupCount=config["logging"]["backup_count"]
            )
        )
        handler.setLevel(getattr(logging, level.upper()))
        handler.setFormatter(text_formatter)
        logger.addHandler(handler)
    if not debug and email:
        # Email notifications
        level = config["logging"]["email"]["level"]
        subject = config["logging"]["email"]["subject"].format(level=level)
        email = logging.handlers.SMTPHandler(
            mailhost=config["logging"]["email"]["mailhost"],
            fromaddr=config["logging"]["email"]["fromaddr"],
            toaddrs=config["logging"]["email"]["toaddrs"],
            subject=subject,
        )
        email.setLevel(getattr(logging, level.upper()))
        email.setFormatter(text_formatter)
        logger.addHandler(email)


def fix_perms(
    path, mode=FilePerms(user="rw", group="rw", other="r").__int__(), grp_name=None
):
    """Try to set the permissions and group ownership of the file
    or directory at path.

    The desired permissions are given by mode.
    If grp_name is given,
    set the directory's gid to that associated with the grp_name.

    In the event that the file or directory at path is owned by another
    user the gid or permissions changes fail silently because they are
    probably correct already.

    :arg path: Path to fix the permissions of.
    :type path: :py:class:`pathlib.Path` or str

    :arg mode: Permissions to set for the path.
    :type mode: int

    :arg grp_name: Group name to change the path ownership to.
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


def mkdir(
    path,
    logger,
    mode=FilePerms(user="rwx", group="rwx", other="rx").__int__(),
    grp_name=None,
    exist_ok=True,
):
    """Create a directory at path with its permissions set to mode.
    If grp_name is given,
    set the directory's gid to that associated with the grp_name.
    If path already exists and exist_ok is False,
    log an error messages and raise an exception.

    In the event that the directory already exists at path but is owned by
    another user the gid or permissions changes fail silently because they
    are probably correct already.

    :arg path: Path to create the directory at.
    :type path: :py:class:`pathlib.Path` or str

    :arg logger: Logger object.
    :type logger: :class:`logging.Logger`

    :arg mode: Permissions to set for the directory.
    :type mode: int

    :arg grp_name: Group name to change the directory's ownership to.
                   Defaults to None meaning that the directory's group
                   will be the same as its parent's.
    :type grp_name: str

    :arg exist_ok: Indicate whether to log and error message and
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
            msg = f"{path} directory already exists; not overwriting"
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
    :type output_logger: :meth:`logging.Logger` method

    :arg error_logger: Logger object to send error message(s) to when
                       command returns non-zero status code.
    :type error_logger: :meth:`logging.Logger` method

    :raises: :py:exc:`nowcast.lib.WorkerError`
    """
    output_logger(f"running command in subprocess: {cmd}")
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        for line in output.splitlines():
            if line:
                output_logger(line)
    except subprocess.CalledProcessError as e:
        error_logger(f"subprocess {cmd} failed with return code {e.returncode}")
        for line in e.output.splitlines():
            if line:
                error_logger(line)
        raise WorkerError
