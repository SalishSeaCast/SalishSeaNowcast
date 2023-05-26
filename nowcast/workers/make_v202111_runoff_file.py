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


"""SalishSeaCast worker that calculates NEMO runoff forcing file from day-averaged river
discharge observations (lagged by 1 day) from representative gauged rivers in all watersheds
and fits developed by Susan Allen.
Missing river discharge observations are handled by a scheme of persistence or scaling of
a nearby gauged river, depending on time span of missing observations.
"""
import logging

import arrow
from nemo_nowcast import NowcastWorker

NAME = "make_v202111_runoff_file"
logger = logging.getLogger(NAME)


# TODO: Ideally these module-level variables should be in the main or a supplemental config file.
#       They should also be in a better data structure.
#       We're leaving them here for now because it's "good enough",
#       and the priority is getting v202111 into production.
watershed_names = [
    "bute",
    "evi_n",
    "jervis",
    "evi_s",
    "howe",
    "jdf",
    "skagit",
    "puget",
    "toba",
    "fraser",
]
rivers_for_watershed = {
    "bute": {"primary": "Homathko_Mouth", "secondary": None},
    "evi_n": {"primary": "Salmon_Sayward", "secondary": None},
    "jervis": {"primary": "Clowhom_ClowhomLake", "secondary": "RobertsCreek"},
    "evi_s": {"primary": "Englishman", "secondary": None},
    "howe": {"primary": "Squamish_Brackendale", "secondary": None},
    "jdf": {"primary": "SanJuan_PortRenfrew", "secondary": None},
    "skagit": {"primary": "Skagit_MountVernon", "secondary": "Snohomish_Monroe"},
    "puget": {"primary": "Nisqually_McKenna", "secondary": "Greenwater_Greenwater"},
    "toba": {"primary": "Homathko_Mouth", "secondary": "Theodosia"},
    "fraser": {"primary": "Fraser", "secondary": "Nicomekl_Langley"},
}


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_v202111_runoff_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.now().floor("day"),
        help="Date to make runoff file for.",
    )
    worker.run(make_v202111_runoff_file, success, failure)
    return worker


def success(parsed_args):
    logger.info(
        f"{parsed_args.data_date.format('YYYY-MM-DD')} runoff file creation completed"
    )
    return "success"


def failure(parsed_args):
    logger.critical(
        f"{parsed_args.data_date.format('YYYY-MM-DD')} runoff file creation failed"
    )
    return "failure"


def make_v202111_runoff_file(parsed_args, config, *args):
    obs_date = parsed_args.data_date
    logger.info(
        f"calculating NEMO runoff forcing for 202108 bathymetry for {obs_date.format('YYYY-MM-DD')}"
    )
    flows = _calc_watershed_flows(obs_date, config)

    checklist = {}

    return checklist


def _calc_watershed_flows(obs_date, config):
    """
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: dict
    """

    flows = {}
    for watershed_name in watershed_names:
        if watershed_name == "fraser":
            flows["fraser"], flows["non_fraser"] = _do_fraser(obs_date, config)
        else:
            if rivers_for_watershed[watershed_name]["secondary"] is None:
                logger.debug(f"no secondary river for {watershed_name} watershed")
            flows[watershed_name] = _do_a_river_pair(
                watershed_name,
                obs_date,
                rivers_for_watershed[watershed_name]["primary"],
                config,
                rivers_for_watershed[watershed_name]["secondary"],
            )
        logger.debug(
            f"{watershed_name} watershed flow: {flows[watershed_name]:.3f} m3 s-1"
        )
    return flows


def _do_fraser(obs_date, config):
    """
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: tuple
    """
    pass


def _do_a_river_pair(
    watershed_name,
    obs_date,
    primary_river_name,
    config,
    secondary_river_name=None,
):
    """
    :param str watershed_name:
    :param :py:class:`arrow.Arrow` obs_date:
    :param str primary_river_name:
    :param dict config:
    :param str or :py:class:`NoneType` secondary_river_name:

    :rtype: float
    """
    pass


if __name__ == "__main__":
    main()  # pragma: no cover
