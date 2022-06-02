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


"""SalishSeaCast worker that rotates hindcast processing logs.

Call the :py:meth:`~logging.handlers.RotatingFileHandler.doRollover` method on the
:py:class:`logging.handlers.RotatingFileHandler` handlers of the ``run_NEMO_hindcast``
logger.

This worker is intended to be launched from the command-line
by the nowcast administrator as necessary for maintenance of the hindcast log files
e.g. when a new hindcast is started,
or when the logs from a running hindcast become annoying long.
"""
import logging
import logging.config
from pathlib import Path

from nemo_nowcast import NowcastWorker
from nemo_nowcast.fileutils import FilePerms

NAME = "rotate_hindcast_logs"
logger = logging.getLogger(NAME)


def main():
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.run(rotate_hindcast_logs, success, failure)
    return worker


def success(parsed_args):
    logger.info("hindcast log files rotated")
    msg_type = "success"
    return msg_type


def failure(parsed_args):
    logger.critical("failed to rotate hindcast log files")
    msg_type = "failure"
    return msg_type


def rotate_hindcast_logs(parsed_args, config, *args):
    logger.info("rotating hindcast log files")
    checklist = {"hindcast log files": []}
    for handler in logging.getLogger("run_NEMO_hindcast").handlers:
        if handler.name in {"hindcast_info", "hindcast_debug"}:
            handler.flush()
            handler.doRollover()
            logger.info(f"hindcast log file rotated: {handler.baseFilename}")
            p = Path(handler.baseFilename)
            p.chmod(int(FilePerms(user="rw", group="rw", other="r")))
            logger.debug(
                f"new {handler.baseFilename} log file permissions set to rw-rw-r--"
            )
            checklist["hindcast log files"].append(handler.baseFilename)
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
