#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""SalishSeaCast ssh and sftp client functions.
"""
import os

import paramiko

from nowcast import lib


class SSHCommandError(Exception):
    """Raised when :py:func:`nowcast.ssh_sftp.ssh_exec_command` result in
    stderr output.

    :param str cmd: Command that was executed via ssh on remote host.

    :param str stdout: stdout from command execution.

    :param str stderr: stderr from command execution.
    """

    def __init__(self, cmd, stdout, stderr):
        self.cmd = cmd
        self.stdout = stdout
        self.stderr = stderr


def ssh(host, key_filename, ssh_config_file="~/.ssh/config"):
    """Return an SSH client connected to host.

    It is assumed that ssh_config_file contains an entry for host,
    and that the corresponding identity is loaded and active in the
    user's ssh agent.

    The client's close() method should be called when its usefulness
    had ended.

    :param host: Name of the host to connect the client to.
    :type config: str

    :param str ssh_config_file: File path/name of the SSH2 config file from
                                which to obtain the hostname and username
                                values.

    :returns: ssh client object
    :rtype: :py:class:`paramiko.client.SSHClient`
    """
    ssh_client = paramiko.client.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_config = paramiko.config.SSHConfig()
    with open(os.path.expanduser(ssh_config_file)) as f:
        ssh_config.parse(f)
    host = ssh_config.lookup(host)
    ssh_client.connect(
        host["hostname"], username=host["user"], key_filename=os.fspath(key_filename)
    )
    return ssh_client


def ssh_exec_command(ssh_client, cmd, host, logger):
    """Execute cmd on host via ssh_client connection.

    :param :py:class:`paramiko.client.SSHClient`

    :param str cmd: Command to execute on host

    :param str host: Name of the host to execute cmd on.

    :param logger: Logger object to send debug messages to.
    :type logger: :py:class:`logging.Logger`

    :return: stdout that results from execution of cmd on host.
    :rtype: str with newline separators

    :raises: :py:class:`nowcast.ssh_sftp.SSHError`
    """
    _, _stdout, _stderr = ssh_client.exec_command(cmd)
    logger.debug(f"executing {cmd} on {host}")
    stderr = _stderr.read().decode()
    if stderr:
        raise SSHCommandError(cmd, _stdout.read().decode(), stderr)
    return _stdout.read().decode()


def sftp(host, key_filename, ssh_config_file="~/.ssh/config"):
    """Return an SFTP client connected to host, and the SSH client on
    which it is based.

    It is assumed that ssh_config_file contains an entry for host,
    and that the corresponding identity is loaded and active in the
    user's ssh agent.

    The clients' close() methods should be called when their usefulness
    had ended.

    :param host: Name of the host to connect the client to.
    :type config: str

    :param str ssh_config_file: File path/name of the SSH2 config file from
                                which to obtain the hostname and username
                                values.

    :returns: 2-tuple containing a ssh and sftp client objects
    :rtype: (:py:class:`paramiko.client.SSHClient`,
             :py:class:`paramiko.sftp_client.SFTPClient`)
    """
    ssh_client = ssh(host, key_filename, ssh_config_file)
    sftp_client = ssh_client.open_sftp()
    return ssh_client, sftp_client


def upload_file(sftp_client, host, localpath, remotepath, logger):
    """Upload the file at localpath to remotepath on host_name via SFTP.

    :param sftp_client: SFTP client instance to use for upload.
    :type sftp_client: :py:class:`paramiko.sftp_client.SFTPClient`

    :param str host: Name of the host to upload the file to.

    :param localpath: Local path and file name of file to upload.
    :type localpath: :py:class:`pathlib.Path`

    :param remotepath: Path and file name to upload file to on remote host.
    :type localpath: :py:class:`pathlib.Path`

    :param logger: Logger object to send debug message to.
    :type logger: :py:class:`logging.Logger`
    """
    sftp_client.put(os.fspath(localpath), os.fspath(remotepath))
    try:
        sftp_client.chmod(
            os.fspath(remotepath), int(lib.FilePerms(user="rw", group="rw", other="r"))
        )
    except PermissionError:
        # We're probably trying to change permissions on a file owned by
        # another user. We can live with not being able to do that.
        pass
    logger.debug(f"{localpath} uploaded to {host} at {remotepath}")
