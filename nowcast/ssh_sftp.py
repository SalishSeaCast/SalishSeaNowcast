# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""SalishSeaCast ssh and sftp client functions.
"""
import os

import paramiko

from nowcast import lib


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
        host['hostname'],
        username=host['user'],
        key_filename=key_filename,
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


def upload_file(sftp_client, host_name, localpath, remotepath, logger):
    """Upload the file at localpath to remotepath on host_name via SFTP.

    :arg sftp_client: SFTP client instance to use for upload.
    :type sftp_client: :py:class:`paramiko.sftp_client.SFTPClient`

    :arg str host_name: Name of the host to upload the file to.

    :arg localpath: Local path and file name of file to upload.
    :type localpath: :py:class:`pathlib.Path`

    :arg remotepath: Path and file name to upload file to on remote host.
    :type localpath: :py:class:`pathlib.Path`

    :arg logger: Logger object to send debug message to.
    :type logger: :py:class:`logging.Logger`
    """
    sftp_client.put(os.fspath(localpath), os.fspath(remotepath))
    try:
        sftp_client.chmod(
            os.fspath(remotepath),
            int(lib.FilePerms(user='rw', group='rw', other='r'))
        )
    except PermissionError:
        # We're probably trying to change permissions on a file owned by
        # another user. We can live with not being able to do that.
        pass
    logger.debug(f'{localpath} uploaded to {host_name} at {remotepath}')