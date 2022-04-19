#  Copyright 2013 – present The Salish Sea MEOPAR contributors
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
"""SalishSeaCast worker that collects river discharge observations data from an ECCC
datamart CSV file mirror and appends a day average discharge to a SOG forcing file.
"""
import logging
from pathlib import Path

import arrow
import pandas
import sentry_sdk
from nemo_nowcast import NowcastWorker

NAME = "collect_river_data"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.collect_river_data --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument("river_name", help="Name of the river to collect data for.")
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.now().floor("day"),
        help="Date to collect river data for.",
    )
    worker.run(collect_river_data, success, failure)
    return worker


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"{parsed_args.river_name} river average discharge for "
        f"{parsed_args.data_date.format('YYYY-MM-DD')} calculated and appended to "
        f"{parsed_args.river_name}_flow file"
    )
    return "success"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"Calculation of {parsed_args.river_name} river average discharge for "
        f"{parsed_args.data_date.format('YYYY-MM-DD')} or "
        f"appending it to {parsed_args.river_name}_flow file failed"
    )
    return "failure"


def collect_river_data(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    river_name = parsed_args.river_name
    sentry_sdk.set_tag("river-name", river_name)
    data_date = parsed_args.data_date
    logger.info(
        f"Collecting {river_name} river data for {data_date.format('YYYY-MM-DD')}"
    )
    stn_id = config["rivers"]["stations"][river_name]
    sentry_sdk.set_tag("stn-id", stn_id)
    csv_file_template = config["rivers"]["csv file template"]
    csv_file = Path(config["rivers"]["datamart dir"]) / csv_file_template.format(
        stn_id=stn_id
    )
    day_avg_discharge = _calc_day_avg_discharge(csv_file, data_date)
    daily_avg_file = Path(config["rivers"]["SOG river files"][river_name])
    _store_day_avg_discharge(data_date, day_avg_discharge, daily_avg_file)
    checklist = {"river name": river_name, "data date": data_date.format("YYYY-MM-DD")}
    logger.info(
        f"Appended {river_name} river average discharge for {data_date.format('YYYY-MM-DD')} to: {daily_avg_file}"
    )
    return checklist


def _calc_day_avg_discharge(csv_file, data_date):
    """
    :param :py:class:`pathlib.Path` csv_file:
    :param :py:class:`Arrow.arrow` data_date:

    :rtype: float
    """
    df = pandas.read_csv(
        csv_file,
        usecols=["Date", "Discharge / Débit (cms)"],
        index_col="Date",
        date_parser=lambda x: pandas.to_datetime(x.rpartition("-")[0]),
    )
    day_avg_discharge = df.loc[f"{data_date.format('YYYY-MM-DD')}"].mean()[
        "Discharge / Débit (cms)"
    ]
    logger.debug(
        f"average discharge for {data_date.format('YYYY-MM-DD')} from {csv_file}: {day_avg_discharge:.6e} m^3/s"
    )
    return day_avg_discharge


def _store_day_avg_discharge(data_date, day_avg_discharge, sog_flow_file):
    """
    :param :py:class:`Arrow.arrow` data_date:
    :param float day_avg_discharge:
    :param :py:class:`pathlib.Path` sog_flow_file:
    """
    with sog_flow_file.open("at") as f:
        f.write(f"{data_date.format('YYYY MM DD')} {day_avg_discharge:.6e}\n")
    logger.debug(
        f"appended {data_date.format('YYYY MM DD')} {day_avg_discharge:.6e} to: {sog_flow_file}"
    )


if __name__ == "__main__":
    main()  # pragma: no cover
