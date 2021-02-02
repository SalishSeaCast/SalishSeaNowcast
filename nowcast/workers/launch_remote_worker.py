#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""SalishSeaCast worker that launches a specified worker on a remote host.

*This worker is for use when it is necessary to intervene after an automation failure.
It does the job of `nemo_nowcast.worker.NextWorker.launch()` with a non-default
`host` argument, avoiding the need to manually construct a complicated `ssh` command.*
"""
import logging

from nemo_nowcast import NowcastWorker, NextWorker

NAME = "launch_remote_worker"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.launch_remote_worker --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to launch the remote worker on"
    )
    worker.cli.add_argument("remote_worker", help="Name of the remote worker to launch")
    worker.cli.add_argument(
        "worker_args",
        help="Quoted string of arguments to launch the remote worker with",
    )
    worker.run(launch_remote_worker, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"remote worker launched on {parsed_args.host_name}: {parsed_args.remote_worker}"
    )
    return "success"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"remote worker launch on {parsed_args.host_name} failed: {parsed_args.remote_worker}"
    )
    return "failure"


def launch_remote_worker(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    remote_worker = parsed_args.remote_worker
    worker_args = parsed_args.worker_args.split()
    remote_worker = (
        remote_worker if "." in remote_worker else f"nowcast.workers.{remote_worker}"
    )
    worker = NextWorker(remote_worker, worker_args, host_name)
    worker.launch(config, logger.name)
    checklist = {
        "host name": host_name,
        "remote worker": remote_worker,
        "worker args": worker_args,
    }
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
