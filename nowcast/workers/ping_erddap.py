#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
"""Salish Sea nowcast worker that creates flag files to tell the ERDDAP
server to reload datasets for which new results have been downloaded.
"""
import logging
from pathlib import Path

from nemo_nowcast import NowcastWorker

NAME = "ping_erddap"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.ping_erddap --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "dataset",
        choices={
            "download_weather",
            "SCVIP-CTD",
            "SEVIP-CTD",
            "USDDL-CTD",
            "TWDP-ferry",
            "VFPA-HADCP",
            "nowcast-green",
            "nemo-forecast",
            "wwatch3-forecast",
        },
        help="""
        Type of dataset to notify ERDDAP of:
        'download_weather' means atmospheric forcing downloaded & processed,
        'SCVIP-CTD' means ONC SCVIP node CTD T&S observations downloaded &
        processed,
        'SEVIP-CTD' means ONC SEVIP node CTD T&S observations downloaded &
        processed,
        'USDDL-CTD' means ONC USDDL node CTD T&S observations downloaded &
        processed,
        'TWDP-ferry' means ONC Tsawwassen/Duke Pt. ferry observations 
        downloaded & processed,
        'VFPA-HADCP' means VFPA 2nd Narrows Rail Bridge HADCP observations processed,
        'nowcast-green' means nowcast green ocean run,
        'nemo-forecast' means updated NEMO rolling forecast,
        'wwatch3-forecast' means updated WaveWatch3 rolling forecast
        """,
    )
    worker.run(ping_erddap, success, failure)


def success(parsed_args):
    logger.info(
        f"{parsed_args.dataset} ERDDAP dataset flag file(s) created",
        extra={"dataset": parsed_args.dataset},
    )
    msg_type = f"success {parsed_args.dataset}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f"{parsed_args.dataset} ERDDAP dataset flag file(s) creation failed",
        extra={"dataset": parsed_args.dataset},
    )
    msg_type = f"failure {parsed_args.dataset}"
    return msg_type


def ping_erddap(parsed_args, config, *args):
    dataset = parsed_args.dataset
    flag_path = Path(config["erddap"]["flag dir"])
    checklist = {dataset: []}
    try:
        for dataset_id in config["erddap"]["datasetIDs"][dataset]:
            (flag_path / dataset_id).touch()
            logger.debug(f"{flag_path / dataset_id} touched")
            checklist[dataset].append(dataset_id)
    except KeyError:
        # run type is not in datasetIDs dict
        pass
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
