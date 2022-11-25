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


"""SalishSeaCast worker that creates a down-sampled time-series dataset netCDF4 file from
another model product file using the Reshapr API.
"""
# Intended uses:
#
# * create day-averaged datasets from hour-averaged NEMO output files as a model run
#   post-processing step
# * create month-averaged datasets from day-averaged at the end of each month of running
import logging
import os
from pathlib import Path

import arrow
import structlog
from nemo_nowcast import NowcastWorker, WorkerError
import reshapr.api.v1.extract


NAME = "make_averaged_dataset"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_averaged_dataset --help`
    """
    _configure_structlog()
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to run the downsampling extraction on"
    )
    worker.cli.add_argument(
        "avg_time_interval",
        choices={"day", "month"},
        help="Time interval over which to average the dataset",
    )
    worker.cli.add_argument(
        "reshapr_var_group",
        choices={"biology", "chemistry", "physics"},
        help="Dataset variable group to run extraction for",
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="""
            Date of the run to calculate the day-averaged dataset for,
            or start date of the collection of daily runs to calculate
            the month-averaged dataset for.
        """,
    )
    worker.run(make_averaged_dataset, success, failure)
    return worker


def _configure_structlog():
    """Configure structlog (used by Reshapr) to pass a formatted log message string
    to the :py:mod:`logging`.

    ref: https://www.structlog.org/en/latest/standard-library.html#rendering-within-structlog
    """
    structlog.configure(
        processors=[
            # If log level is too low, abort pipeline and throw away log entry.
            structlog.stdlib.filter_by_level,
            # If the "stack_info" key in the event dict is true, remove it and
            # render the current stack trace in the "stack" key.
            structlog.processors.StackInfoRenderer(),
            # If the "exc_info" key in the event dict is either true or a
            # sys.exc_info() tuple, remove "exc_info" and render the exception
            # with traceback into the "exception" key.
            structlog.processors.format_exc_info,
            # If some value is in bytes, decode it to a unicode str.
            structlog.processors.UnicodeDecoder(),
            # Render the final event dict nicely aligned and ordered, but without colours
            # because we're generally logging to files.
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        # ``wrapper_class`` is the bound logger that you get back from
        # get_logger(). This one imitates the API of ``logging.Logger``.
        wrapper_class=structlog.stdlib.BoundLogger,
        # ``logger_factory`` is used to create wrapped loggers that are used for
        # OUTPUT. This one returns a ``logging.Logger``. The final value (a string)
        # from the final processor (``ConsoleRenderer``) will be passed to
        # the method of the same name as that called on the bound logger.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Effectively freeze configuration after creating the first bound logger.
        cache_logger_on_first_use=True,
    )


def success(parsed_args):
    avg_time_interval = parsed_args.avg_time_interval
    run_date = parsed_args.run_date
    reshapr_var_group = parsed_args.reshapr_var_group
    host_name = parsed_args.host_name
    match avg_time_interval:
        case "day":
            logger.info(
                f"{avg_time_interval}-averaged dataset for {run_date.format('DD-MMM-YYYY')} "
                f"{reshapr_var_group} created on {host_name}"
            )
        case "month":
            logger.info(
                f"{avg_time_interval}-averaged dataset for {run_date.format('MMM-YYYY')} "
                f"{reshapr_var_group} created on {host_name}"
            )
    msg_type = "success"
    return msg_type


def failure(parsed_args):
    avg_time_interval = parsed_args.avg_time_interval
    run_date = parsed_args.run_date
    reshapr_var_group = parsed_args.reshapr_var_group
    host_name = parsed_args.host_name
    match avg_time_interval:
        case "day":
            logger.critical(
                f"{avg_time_interval}-averaged dataset for {run_date.format('DD-MMM-YYYY')} "
                f"{reshapr_var_group} creation on {host_name} failed"
            )
        case "month":
            logger.critical(
                f"{avg_time_interval}-averaged dataset for {run_date.format('MMM-YYYY')} "
                f"{reshapr_var_group} creation on {host_name} failed"
            )
    msg_type = "failure"
    return msg_type


def make_averaged_dataset(parsed_args, config, *args):
    avg_time_interval = parsed_args.avg_time_interval
    reshapr_var_group = parsed_args.reshapr_var_group
    host_name = parsed_args.host_name
    run_date = parsed_args.run_date
    if avg_time_interval == "month" and run_date.day != 1:
        logger.error(
            f"Month-averaging must start on the first day of a month but "
            f"run_date = {run_date.format('YYYY-MM-DD')}"
        )
        raise WorkerError
    reshapr_config_dir = Path(config["averaged datasets"]["reshapr config dir"])
    reshapr_config_yaml = config["averaged datasets"][avg_time_interval][
        reshapr_var_group
    ]["reshapr config"]
    match avg_time_interval:
        case "day":
            logger.info(
                f"creating {avg_time_interval}-averaged dataset for "
                f"{run_date.format('DD-MMM-YYYY')} {reshapr_var_group} on {host_name}"
            )
            reshapr_config = reshapr.api.v1.extract.load_extraction_config(
                reshapr_config_dir / reshapr_config_yaml, run_date, run_date
            )
            dest_dir = Path(reshapr_config["extracted dataset"]["dest dir"])
            ddmmmyy = run_date.format("DDMMMYY").lower()
            reshapr_config["extracted dataset"]["dest dir"] = dest_dir / ddmmmyy
        case "month":
            logger.info(
                f"creating {avg_time_interval}-averaged dataset for "
                f"{run_date.format('MMM-YYYY')} {reshapr_var_group} on {host_name}"
            )
            start_date = run_date
            end_date = run_date.shift(months=+1, days=-1)
            reshapr_config = reshapr.api.v1.extract.load_extraction_config(
                reshapr_config_dir / reshapr_config_yaml, start_date, end_date
            )
    nc_path = reshapr.api.v1.extract.extract_netcdf(reshapr_config, reshapr_config_yaml)
    if avg_time_interval == "day":
        file_pattern = config["averaged datasets"][avg_time_interval][
            reshapr_var_group
        ]["file pattern"]
        dest_nc_filename = file_pattern.format(yyyymmdd=run_date.format("YYYYMMDD"))
        nc_path = nc_path.rename(nc_path.with_name(dest_nc_filename))
    return {
        f"{run_date.format('YYYY-MM-DD')} {avg_time_interval} {reshapr_var_group}": os.fspath(
            nc_path
        )
    }


if __name__ == "__main__":
    main()  # pragma: no cover
