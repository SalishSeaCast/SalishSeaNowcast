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
"""SalishSeaCast worker that collects river discharge observation data from
an ECCC datamart CSV file mirror, or the USGS Water Service REST service,
and appends a day-average discharge to a SOG-format forcing file.
"""
import logging
from pathlib import Path

import arrow
import httpx
import pandas
import sentry_sdk
from nemo_nowcast import NowcastWorker, WorkerError

NAME = "collect_river_data"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.collect_river_data --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "data_src", choices={"ECCC", "USGS"}, help="Name of the river data service."
    )
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
        f"{parsed_args.data_src} {parsed_args.river_name} river data collection for "
        f"{parsed_args.data_date.format('YYYY-MM-DD')} completed"
    )
    return "success"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"Calculation of {parsed_args.data_src} {parsed_args.river_name} "
        f"river average discharge for {parsed_args.data_date.format('YYYY-MM-DD')} or "
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
    data_src = parsed_args.data_src
    river_name = parsed_args.river_name
    stn_id = config["rivers"]["stations"][data_src][river_name]
    sentry_sdk.set_tag("stn-id", stn_id)
    sentry_sdk.set_tag("river-name", river_name)
    data_date = parsed_args.data_date
    logger.info(
        f"Collecting {data_src} {river_name} river data for {data_date.format('YYYY-MM-DD')}"
    )
    day_avg_discharge_funcs = {
        # data_src: function
        "ECCC": _calc_eccc_day_avg_discharge,
        "USGS": _get_usgs_day_avg_discharge,
    }
    day_avg_discharge = day_avg_discharge_funcs[data_src](river_name, data_date, config)
    daily_avg_file = Path(config["rivers"]["SOG river files"][river_name])
    _store_day_avg_discharge(data_date, day_avg_discharge, daily_avg_file)
    checklist = {"river name": river_name, "data date": data_date.format("YYYY-MM-DD")}
    logger.info(
        f"Appended {data_src} {river_name} river average discharge for "
        f"{data_date.format('YYYY-MM-DD')} to: {daily_avg_file}"
    )
    return checklist


def _calc_eccc_day_avg_discharge(river_name, data_date, config):
    """
    :param str river_name:
    :param :py:class:`Arrow.arrow` data_date:
    :param :py:class:`nemo_nowcast.Config` config:

    :rtype: float
    """
    csv_file_template = config["rivers"]["csv file template"]
    stn_id = config["rivers"]["stations"]["ECCC"][river_name]
    csv_file = Path(config["rivers"]["datamart dir"]) / csv_file_template.format(
        stn_id=stn_id
    )
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


def _get_usgs_day_avg_discharge(river_name, data_date, config):
    """
    :param str river_name:
    :param :py:class:`Arrow.arrow` data_date:
    :param :py:class:`nemo_nowcast.Config` config:

    :rtype: float
    """
    usgs_url = config["rivers"]["usgs url"]
    usgs_parmas = config["rivers"]["usgs params"]
    stn_id = config["rivers"]["stations"]["USGS"][river_name]
    yyyymmdd = data_date.format("YYYY-MM-DD")
    usgs_parmas.update(
        {
            "sites": stn_id,
            "startDT": yyyymmdd,
            "endDT": yyyymmdd,
        }
    )
    with httpx.Client() as client:
        try:
            response = client.get(usgs_url, params=usgs_parmas, follow_redirects=True)
            response.raise_for_status()
        except httpx.RequestError as exc:
            msg = f"Error while requesting {exc.request.url}"
            logger.critical(msg)
            raise WorkerError(msg)
        except httpx.HTTPStatusError as exc:
            msg = f"Error response {exc.response.status_code} while requesting {exc.request.url}"
            logger.critical(msg)
            raise WorkerError(msg)
        try:
            timeseries = response.json()["value"]["timeSeries"][0]
        except IndexError:
            msg = f"{river_name} {yyyymmdd} timeSeries is empty"
            logger.critical(msg)
            raise WorkerError(msg)
    no_data_value = timeseries["variable"]["noDataValue"]
    try:
        cfs = timeseries["values"][0]["value"][0]["value"]
    except IndexError:
        msg = f"IndexError in {river_name} {yyyymmdd} timeSeries JSON"
        logger.critical(msg)
        raise WorkerError(msg)
    except KeyError:
        msg = f"KeyError in {river_name} {yyyymmdd} timeSeries JSON"
        logger.critical(msg)
        raise WorkerError(msg)
    if cfs == no_data_value:
        msg = (
            f"Got no-data value ({no_data_value}) in {river_name} {yyyymmdd} timeSeries"
        )
        logger.critical(msg)
        raise WorkerError(msg)
    day_avg_discharge = float(cfs) * 0.0283168
    logger.debug(
        f"average discharge for {river_name} on {yyyymmdd} from {usgs_url}: {day_avg_discharge:.6e} m^3/s"
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
