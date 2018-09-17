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
"""SalishSeaCast worker that produces tiles of surface current visualization
images for the web site from run results.

The tile specifications and initial code implementation were provided by IOS.
"""
import logging

from nemo_nowcast import NowcastWorker

NAME = "make_surface_current_tiles"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_surface_current_tiles --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.run(make_surface_current_tiles, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info("surface current tile figures completed")
    msg_type = f"success"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical("surface current tile figures production failed")
    msg_type = f"failure"
    return msg_type


def make_surface_current_tiles(parsed_args, checklist, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    checklist = {}
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
