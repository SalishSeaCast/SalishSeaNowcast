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


"""Functions to calculate lists of workers to launch after previous workers
end their work.

Function names **must** be of the form :py:func:`after_worker_name`.
"""
from pathlib import Path

import arrow
from nemo_nowcast import NextWorker


def after_download_weather(msg, config, checklist):
    """Calculate the list of workers to launch after the download_weather worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure 2.5km 00": [],
        "failure 2.5km 06": [],
        "failure 2.5km 12": [],
        "failure 2.5km 18": [],
        "failure 1km 00": [],
        "failure 1km 12": [],
        "success 2.5km 00": [],
        "success 2.5km 06": [],
        "success 2.5km 12": [],
        "success 2.5km 18": [],
        "success 1km 00": [],
        "success 1km 12": [],
    }
    if msg.type.startswith("success"):
        data_date = arrow.now().shift(days=-1).format("YYYY-MM-DD")
        if msg.type.endswith("2.5km 06"):
            for river_name in config["rivers"]["stations"]["ECCC"]:
                next_workers["success 2.5km 06"].append(
                    NextWorker(
                        "nowcast.workers.collect_river_data",
                        args=["ECCC", river_name, "--data-date", data_date],
                    )
                )
            for stn in config["observations"]["ctd data"]["stations"]:
                next_workers["success 2.5km 06"].append(
                    NextWorker("nowcast.workers.get_onc_ctd", args=[stn])
                )
            for ferry in config["observations"]["ferry data"]["ferries"]:
                next_workers["success 2.5km 06"].append(
                    NextWorker("nowcast.workers.get_onc_ferry", args=[ferry])
                )
            next_workers["success 2.5km 06"].append(
                NextWorker(
                    "nowcast.workers.get_vfpa_hadcp", args=["--data-date", data_date]
                )
            )
            if "forecast2" in config["run types"]:
                next_workers["success 2.5km 06"].append(
                    NextWorker("nowcast.workers.collect_NeahBay_ssh", args=["00"]),
                )
                race_condition_workers = {
                    "grib_to_netcdf",
                    "make_201702_runoff_file",
                    "make_runoff_file",
                }
                return next_workers[msg.type], race_condition_workers
        if msg.type.endswith("2.5km 12"):
            for river_name in config["rivers"]["stations"]["USGS"]:
                next_workers["success 2.5km 12"].append(
                    NextWorker(
                        "nowcast.workers.collect_river_data",
                        args=["USGS", river_name, "--data-date", data_date],
                    )
                )
            next_workers["success 2.5km 12"].extend(
                [
                    NextWorker("nowcast.workers.make_turbidity_file"),
                    NextWorker("nowcast.workers.collect_NeahBay_ssh", args=["06"]),
                    NextWorker("nowcast.workers.download_live_ocean"),
                ]
            )
            race_condition_workers = {
                "grib_to_netcdf",
                "make_live_ocean_files",
                "make_201702_runoff_file",
                "make_runoff_file",
            }
            return next_workers[msg.type], race_condition_workers
    return next_workers[msg.type]


def after_collect_weather(msg, config, checklist):
    """Calculate the list of workers to launch after the collect_weather worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure 2.5km 00": [],
        "failure 2.5km 06": [],
        "failure 2.5km 12": [],
        "failure 2.5km 18": [],
        "failure 1km 00": [],
        "failure 1km 12": [],
        "success 2.5km 00": [],
        "success 2.5km 06": [],
        "success 2.5km 12": [],
        "success 2.5km 18": [],
        "success 1km 00": [],
        "success 1km 12": [],
        msg.type: after_download_weather(msg, config, checklist),
    }
    if msg.type.endswith("2.5km 00"):
        if msg.type.startswith("success"):
            grib_dir = Path(checklist["weather forecast"]["00 2.5km"])
            fcst_date_yyyymmdd = grib_dir.parent.stem
            fcst_date = arrow.get(fcst_date_yyyymmdd, "YYYYMMDD").format("YYYY-MM-DD")
            next_workers["success 2.5km 00"].extend(
                [
                    NextWorker("nowcast.workers.collect_weather", args=["06", "2.5km"]),
                    NextWorker(
                        "nowcast.workers.crop_gribs",
                        args=["06", "--fcst-date", fcst_date],
                    ),
                ]
            )
    if msg.type.endswith("2.5km 06"):
        if msg.type.startswith("success"):
            next_workers, race_condition_workers = after_download_weather(
                msg, config, checklist
            )
            next_workers.extend(
                [
                    NextWorker("nowcast.workers.collect_weather", args=["12", "2.5km"]),
                    NextWorker("nowcast.workers.crop_gribs", args=["12"]),
                ]
            )
            return next_workers, race_condition_workers
    if msg.type.endswith("2.5km 12"):
        if msg.type.startswith("success"):
            next_workers, race_condition_workers = after_download_weather(
                msg, config, checklist
            )
            next_workers.extend(
                [
                    NextWorker("nowcast.workers.collect_weather", args=["18", "2.5km"]),
                    NextWorker("nowcast.workers.crop_gribs", args=["18"]),
                ]
            )
            return next_workers, race_condition_workers
    if msg.type.endswith("2.5km 18"):
        if msg.type.startswith("success"):
            grib_dir = Path(checklist["weather forecast"]["18 2.5km"])
            fcst_date_yyyymmdd = grib_dir.parent.stem
            fcst_date = (
                arrow.get(fcst_date_yyyymmdd, "YYYYMMDD")
                .shift(days=+1)
                .format("YYYY-MM-DD")
            )
            next_workers["success 2.5km 18"].extend(
                [
                    NextWorker("nowcast.workers.download_weather", args=["00", "1km"]),
                    NextWorker("nowcast.workers.download_weather", args=["12", "1km"]),
                    NextWorker("nowcast.workers.collect_weather", args=["00", "2.5km"]),
                    NextWorker(
                        "nowcast.workers.crop_gribs",
                        args=["00", "--fcst-date", fcst_date],
                    ),
                ]
            )
    return next_workers[msg.type]


def after_crop_gribs(msg, config, checklist):
    """Calculate the list of workers to launch after the crop_gribs worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure 00": [],
        "failure 06": [],
        "failure 12": [],
        "failure 18": [],
        "success 00": [],
        "success 06": [],
        "success 12": [],
        "success 18": [],
    }
    if msg.type == "success 06":
        next_workers["success 06"].append(
            NextWorker("nowcast.workers.grib_to_netcdf", args=["forecast2"])
        )
    if msg.type == "success 12":
        next_workers["success 12"].append(
            NextWorker("nowcast.workers.grib_to_netcdf", args=["nowcast+"])
        )
    return next_workers[msg.type]


def after_collect_river_data(msg, config, checklist):
    """Calculate the list of workers to launch after the collect_river_data
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    return next_workers[msg.type]


def after_make_runoff_file(msg, config, checklist):
    """Calculate the list of workers to launch after the make_runoff_file
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    return next_workers[msg.type]


def after_make_201702_runoff_file(msg, config, checklist):
    """Calculate the list of workers to launch after the make_201702_runoff_file
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    return next_workers[msg.type]


def after_collect_NeahBay_ssh(msg, config, checklist):
    """Calculate the list of workers to launch after the collect_NeahBay_ssh worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure 00": [],
        "failure 06": [],
        "failure 12": [],
        "failure 18": [],
        "success 00": [],
        "success 06": [],
        "success 12": [],
        "success 18": [],
    }
    if msg.type.startswith("success"):
        ssh_fcst_run_type_map = {
            "00": "forecast2",
            "06": "nowcast",
        }
        data_date = checklist["Neah Bay ssh data"]["data date"]
        ssh_forecast = msg.type.split()[1]
        next_workers[f"success {ssh_forecast}"] = [
            NextWorker(
                "nowcast.workers.make_ssh_files",
                args=[
                    ssh_fcst_run_type_map[ssh_forecast],
                    "--run-date",
                    data_date,
                ],
            )
        ]
    return next_workers[msg.type]


def after_make_ssh_files(msg, config, checklist):
    """Calculate the list of workers to launch after the make_ssh_files worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success forecast2": [],
    }
    if msg.type.startswith("success"):
        next_workers[msg.type].extend(
            [
                NextWorker("nowcast.workers.make_runoff_file", args=["v202108"]),
                NextWorker("nowcast.workers.make_201702_runoff_file"),
            ]
        )
    return next_workers[msg.type]


def after_grib_to_netcdf(msg, config, checklist):
    """Calculate the list of workers to launch after the grib_to_netcdf worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast+": [],
        "failure forecast2": [],
        "success nowcast+": [],
        "success forecast2": [],
    }
    if msg.type.startswith("success"):
        _, run_type = msg.type.split()
        if run_type == "nowcast+":
            next_workers["success nowcast+"].append(
                NextWorker("nowcast.workers.ping_erddap", args=["weather"])
            )
        if run_type == "forecast2":
            for host in config["run"]["enabled hosts"]:
                if not config["run"]["enabled hosts"][host]["shared storage"]:
                    next_workers[f"success {run_type}"].append(
                        NextWorker(
                            "nowcast.workers.upload_forcing", args=[host, run_type]
                        )
                    )
    return next_workers[msg.type]


def after_get_onc_ctd(msg, config, checklist):
    """Calculate the list of workers to launch after the get_onc_ctd
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure": [],
        "success SCVIP": [],
        "success SEVIP": [],
        "success USDDL": [],
    }
    if msg.type.startswith("success"):
        ctd_stn = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.ping_erddap", args=[f"{ctd_stn}-CTD"])
        )
    return next_workers[msg.type]


def after_get_onc_ferry(msg, config, checklist):
    """Calculate the list of workers to launch after the get_onc_ferry
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure TWDP": [], "success TWDP": []}
    if msg.type.startswith("success"):
        ferry_platform = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.ping_erddap", args=[f"{ferry_platform}-ferry"])
        )
    return next_workers[msg.type]


def after_download_live_ocean(msg, config, checklist):
    """Calculate the list of workers to launch after the download_live_ocean
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    if msg.type == "success":
        next_workers["success"].append(
            NextWorker(
                "nowcast.workers.make_live_ocean_files",
                args=["--run-date", list(checklist["Live Ocean products"].keys())[-1]],
            )
        )
    return next_workers[msg.type]


def after_make_live_ocean_files(msg, config, checklist):
    """Calculate the list of workers to launch after the make_live_ocean_files
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    if msg.type == "success":
        for host in config["run"]["enabled hosts"]:
            if not config["run"]["enabled hosts"][host]["shared storage"]:
                next_workers[msg.type].append(
                    NextWorker(
                        "nowcast.workers.upload_forcing", args=[host, "nowcast+"]
                    )
                )
    return next_workers[msg.type]


def after_make_turbidity_file(msg, config, checklist):
    """Calculate the list of workers to launch after the make_turbidity_file
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    return next_workers[msg.type]


def after_upload_forcing(msg, config, checklist):
    """Calculate the list of workers to launch after the upload_forcing worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast+": [],
        "failure forecast2": [],
        "failure ssh": [],
        "failure turbidity": [],
        "success nowcast+": [],
        "success forecast2": [],
        "success ssh": [],
        "success turbidity": [],
    }
    if not msg.type.startswith("success"):
        return next_workers[msg.type]
    forcing_run_type = msg.type.split()[1]
    run_types = {
        "forecast2": ("forecast2",),
        "nowcast+": ("nowcast",),
        "ssh": ("forecast",),
        "turbidity": ("nowcast-green", "nowcast-agrif"),
    }[forcing_run_type]
    try:
        host_name = list(msg.payload.keys())[0]
        host_config = config["run"]["enabled hosts"][host_name]
    except (AttributeError, IndexError):
        # Malformed payload - no host name in payload;
        # upload_forcing worker probably crashed
        return []
    if not host_config["make forcing links"]:
        return []
    for nemo_run_type in run_types:
        if nemo_run_type in host_config["run types"]:
            links_run_type = (
                nemo_run_type if forcing_run_type == "turbidity" else forcing_run_type
            )
            next_workers[f"success {forcing_run_type}"] = [
                NextWorker(
                    "nowcast.workers.make_forcing_links",
                    args=[
                        host_name,
                        links_run_type,
                        "--run-date",
                        msg.payload[host_name][forcing_run_type]["run date"],
                    ],
                )
            ]
    return next_workers[msg.type]


def after_make_forcing_links(msg, config, checklist):
    """Calculate the list of workers to launch after the make_forcing_links
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast+": [],
        "failure nowcast-green": [],
        "failure nowcast-agrif": [],
        "failure forecast2": [],
        "failure ssh": [],
        "success nowcast+": [],
        "success nowcast-green": [],
        "success nowcast-agrif": [],
        "success forecast2": [],
        "success ssh": [],
    }
    if msg.type.startswith("success"):
        run_types = {
            "nowcast+": ("nowcast",),
            "nowcast-green": ("nowcast-green",),
            "nowcast-agrif": ("nowcast-agrif",),
            "ssh": ("forecast",),
            "forecast2": ("forecast2",),
        }[msg.type.split()[1]]
        for host in msg.payload:
            host_run_types = config["run"]["enabled hosts"][host]["run types"]
            for run_type in run_types:
                if run_type in host_run_types:
                    if run_type == "nowcast-agrif":
                        next_workers[msg.type] = [
                            NextWorker(
                                "nowcast.workers.run_NEMO_agrif",
                                args=[
                                    host,
                                    run_type,
                                    "--run-date",
                                    checklist["forcing links"][host]["run date"],
                                ],
                            )
                        ]
                    else:
                        next_workers[msg.type] = [
                            NextWorker(
                                "nowcast.workers.run_NEMO",
                                args=[
                                    host,
                                    run_type,
                                    "--run-date",
                                    checklist["forcing links"][host]["run date"],
                                ],
                                host=host,
                            )
                        ]
    return next_workers[msg.type]


def after_run_NEMO(msg, config, checklist):
    """Calculate the list of workers to launch after the run_NEMO worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast": [],
        "failure nowcast-green": [],
        "failure forecast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success nowcast-green": [],
        "success forecast": [],
        "success forecast2": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        host = msg.payload[run_type]["host"]
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.watch_NEMO", args=[host, run_type], host=host)
        )
    return next_workers[msg.type]


def after_watch_NEMO(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_NEMO worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast": [],
        "failure nowcast-green": [],
        "failure forecast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success nowcast-green": [],
        "success forecast": [],
        "success forecast2": [],
    }
    race_condition_workers = {}
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        if run_type == "nowcast":
            next_workers[msg.type].extend(
                [
                    NextWorker(
                        "nowcast.workers.make_forcing_links",
                        args=[
                            msg.payload["nowcast"]["host"],
                            "ssh",
                            "--run-date",
                            msg.payload[run_type]["run date"],
                        ],
                    ),
                ]
            )
        if run_type == "forecast":
            host_name = config["wave forecasts"]["host"]
            next_workers[msg.type].extend(
                [
                    NextWorker(
                        "nowcast.workers.make_ww3_wind_file",
                        args=[
                            host_name,
                            "forecast",
                            "--run-date",
                            msg.payload[run_type]["run date"],
                        ],
                        host=host_name,
                    ),
                    NextWorker(
                        "nowcast.workers.make_ww3_current_file",
                        args=[
                            host_name,
                            "forecast",
                            "--run-date",
                            msg.payload[run_type]["run date"],
                        ],
                        host=host_name,
                    ),
                ]
            )
            race_condition_workers = {"make_ww3_wind_file", "make_ww3_current_file"}
            for host in config["run"]["enabled hosts"]:
                if not config["run"]["enabled hosts"][host]["shared storage"]:
                    next_workers[msg.type].append(
                        NextWorker(
                            "nowcast.workers.upload_forcing",
                            args=[
                                host,
                                "turbidity",
                                "--run-date",
                                msg.payload[run_type]["run date"],
                            ],
                        )
                    )
        if run_type == "forecast2":
            host_name = config["wave forecasts"]["host"]
            run_date = arrow.get(msg.payload[run_type]["run date"]).shift(days=+1)
            next_workers[msg.type].extend(
                [
                    NextWorker(
                        "nowcast.workers.make_ww3_wind_file",
                        args=[
                            host_name,
                            "forecast2",
                            "--run-date",
                            run_date.format("YYYY-MM-DD"),
                        ],
                        host=host_name,
                    ),
                    NextWorker(
                        "nowcast.workers.make_ww3_current_file",
                        args=[
                            host_name,
                            "forecast2",
                            "--run-date",
                            run_date.format("YYYY-MM-DD"),
                        ],
                        host=host_name,
                    ),
                ]
            )
            race_condition_workers = {"make_ww3_wind_file", "make_ww3_current_file"}
        enabled_host_config = config["run"]["enabled hosts"][
            msg.payload[run_type]["host"]
        ]
        if not enabled_host_config["shared storage"]:
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.download_results",
                    args=[
                        msg.payload[run_type]["host"],
                        run_type,
                        "--run-date",
                        msg.payload[run_type]["run date"],
                    ],
                )
            )
    if race_condition_workers:
        return next_workers[msg.type], race_condition_workers
    return next_workers[msg.type]


def after_run_NEMO_agrif(msg, config, checklist):
    """Calculate the list of workers to launch after the run_NEMO_agrif worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    if msg.type.startswith("success"):
        host = msg.payload["nowcast-agrif"]["host"]
        job_id = msg.payload["nowcast-agrif"]["job id"]
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.watch_NEMO_agrif", args=[host, job_id])
        )
    return next_workers[msg.type]


def after_watch_NEMO_agrif(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_NEMO_agrif worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    if msg.type == "success":
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.download_results",
                args=[
                    msg.payload["nowcast-agrif"]["host"],
                    "nowcast-agrif",
                    "--run-date",
                    msg.payload["nowcast-agrif"]["run date"],
                ],
            )
        )
    return next_workers[msg.type]


def after_watch_NEMO_hindcast(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_NEMO_handcast
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    if msg.type == "success":
        next_workers[msg.type].extend(
            [
                NextWorker(
                    "nowcast.workers.download_results",
                    args=[
                        msg.payload["hindcast"]["host"],
                        "hindcast",
                        "--run-date",
                        msg.payload["hindcast"]["run date"],
                    ],
                ),
                NextWorker(
                    "nowcast.workers.watch_NEMO_hindcast",
                    args=[msg.payload["hindcast"]["host"]],
                ),
                NextWorker(
                    "nowcast.workers.run_NEMO_hindcast",
                    args=[msg.payload["hindcast"]["host"]],
                ),
            ]
        )
    return next_workers[msg.type]


def after_run_NEMO_hindcast(msg, config, checklist):
    """Calculate the list of workers to launch after the run_NEMO_hindcast
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    return next_workers[msg.type]


def after_make_ww3_wind_file(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_make_ww3_wind_file worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_make_ww3_current_file(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_make_ww3_current_file worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure forecast2": [],
        "failure nowcast": [],
        "failure forecast": [],
        "success forecast2": [],
        "success nowcast": [],
        "success forecast": [],
    }
    if msg.type.startswith("success"):
        host_name = config["wave forecasts"]["host"]
        run_type = msg.type.split()[1]
        run_type = "nowcast" if run_type == "forecast" else run_type
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.run_ww3",
                # We make the current files for the period of nowcast+forecast,
                # but run nowcast then forecast separately
                args=[
                    host_name,
                    run_type,
                    "--run-date",
                    msg.payload["run date"],
                ],
                host=host_name,
            )
        )
    return next_workers[msg.type]


def after_run_ww3(msg, config, checklist):
    """Calculate the list of workers to launch after the after_run_ww3 worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure forecast2": [],
        "failure nowcast": [],
        "failure forecast": [],
        "success forecast2": [],
        "success nowcast": [],
        "success forecast": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        host = msg.payload[run_type]["host"]
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.watch_ww3", args=[host, run_type], host=host)
        )
    return next_workers[msg.type]


def after_watch_ww3(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_ww3 worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure forecast2": [],
        "failure nowcast": [],
        "failure forecast": [],
        "success forecast2": [],
        "success nowcast": [],
        "success forecast": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.download_wwatch3_results",
                args=[
                    msg.payload[run_type]["host"],
                    run_type,
                    "--run-date",
                    msg.payload[run_type]["run date"],
                ],
            )
        )
        if run_type == "nowcast":
            pass
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.run_ww3",
                    args=[
                        msg.payload[run_type]["host"],
                        "forecast",
                        "--run-date",
                        msg.payload[run_type]["run date"],
                    ],
                    host=msg.payload[run_type]["host"],
                )
            )
    return next_workers[msg.type]


def after_download_results(msg, config, checklist):
    """Calculate the list of workers to launch after the download_results
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast": [],
        "failure nowcast-green": [],
        "failure forecast": [],
        "failure forecast2": [],
        "failure hindcast": [],
        "failure nowcast-agrif": [],
        "success nowcast": [],
        "success nowcast-green": [],
        "success forecast": [],
        "success forecast2": [],
        "success hindcast": [],
        "success nowcast-agrif": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        run_date = msg.payload[run_type]["run date"]
        if run_type == "hindcast":
            next_workers[msg.type].append(
                NextWorker("nowcast.workers.split_results", args=[run_type, run_date])
            )
            return next_workers[msg.type]
        if run_type.startswith("nowcast"):
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.make_plots",
                    args=["nemo", run_type, "research", "--run-date", run_date],
                )
            )
            if run_type == "nowcast":
                compare_date = arrow.get(run_date).shift(days=-1).format("YYYY-MM-DD")
                next_workers[msg.type].extend(
                    [
                        NextWorker(
                            "nowcast.workers.make_plots",
                            args=[
                                "nemo",
                                run_type,
                                "comparison",
                                "--run-date",
                                compare_date,
                            ],
                        ),
                        NextWorker(
                            "nowcast.workers.make_CHS_currents_file",
                            args=[run_type, "--run-date", run_date],
                        ),
                    ]
                )
            if run_type == "nowcast-green":
                next_workers[msg.type].append(
                    NextWorker("nowcast.workers.ping_erddap", args=["nowcast-green"]),
                )
                for var_group in {"biology", "chemistry", "physics"}:
                    next_workers[msg.type].append(
                        NextWorker(
                            "nowcast.workers.make_averaged_dataset",
                            args=["day", var_group, "--run-date", run_date],
                        )
                    )
                if arrow.get(run_date).shift(days=+1).day == 1:
                    yyyymmm = arrow.get(run_date).format("YYYY-MMM").lower()
                    next_workers[msg.type].append(
                        NextWorker(
                            "nowcast.workers.archive_tarball",
                            args=["nowcast-green", yyyymmm, "robot.graham"],
                        )
                    )
                return next_workers[msg.type]
        if run_type.startswith("forecast"):
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.make_CHS_currents_file",
                    args=[run_type, "--run-date", run_date],
                )
            )
    return next_workers[msg.type]


def after_make_averaged_dataset(msg, config, checklist):
    """Calculate the list of workers to launch after the make_averaged_dataset worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure day biology": [],
        "failure day chemistry": [],
        "failure day grazing": [],
        "failure day growth": [],
        "failure day physics": [],
        "failure month biology": [],
        "failure month chemistry": [],
        "failure month physics": [],
        "success day biology": [],
        "success day chemistry": [],
        "success day physics": [],
        "success month biology": [],
        "success month chemistry": [],
        "success month grazing": [],
        "success month growth": [],
        "success month physics": [],
    }
    if msg.type.startswith("success day"):
        *_, reshapr_var_group = msg.type.split()
        run_date = arrow.get(msg.payload[f"day {reshapr_var_group}"]["run date"])
        if run_date.shift(days=+1).day == 1:
            first_of_month = run_date.format("YYYY-MM-01")
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.make_averaged_dataset",
                    args=["month", reshapr_var_group, "--run-date", first_of_month],
                    host="localhost",
                )
            )
    if msg.type.startswith("success month"):
        *_, reshapr_var_group = msg.type.split()
        match reshapr_var_group:
            case "physics":
                run_date = arrow.get(msg.payload["month physics"]["run date"]).format(
                    "YYYY-MM-DD"
                )
                next_workers[msg.type].append(
                    NextWorker(
                        "nowcast.workers.make_averaged_dataset",
                        args=["month", "grazing", "--run-date", run_date],
                        host="localhost",
                    )
                )
            case "grazing":
                run_date = arrow.get(msg.payload["month grazing"]["run date"]).format(
                    "YYYY-MM-DD"
                )
                next_workers[msg.type].append(
                    NextWorker(
                        "nowcast.workers.make_averaged_dataset",
                        args=["month", "growth", "--run-date", run_date],
                        host="localhost",
                    )
                )
            case _:
                pass
    return next_workers[msg.type]


def after_archive_tarball(msg, config, checklist):
    """Calculate the list of workers to launch after the archive_tarball worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_make_CHS_currents_file(msg, config, checklist):
    """Calculate the list of workers to launch after the make_CHS_currents_file
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nowcast": [],
        "failure forecast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success forecast": [],
        "success forecast2": [],
    }
    if msg.type.startswith("success forecast"):
        run_type = msg.type.split()[1]
        run_date = msg.payload[run_type]["run date"]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.update_forecast_datasets",
                args=["nemo", run_type, "--run-date", run_date],
            )
        )
    return next_workers[msg.type]


def after_split_results(msg, config, checklist):
    """Calculate the list of workers to launch after the split_results
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure hindcast": [],
        "success hindcast": [],
    }
    if msg.type.startswith("success"):
        if config["results tarballs"]["archive hindcast"]:
            last_date = max(map(arrow.get, msg.payload))
            if arrow.get(last_date).shift(days=+1).day == 1:
                yyyymmm = arrow.get(last_date).format("YYYY-MMM").lower()
                next_workers[msg.type].append(
                    NextWorker(
                        "nowcast.workers.archive_tarball",
                        args=["hindcast", yyyymmm, "robot.graham"],
                    )
                )
    return next_workers[msg.type]


def after_download_wwatch3_results(msg, config, checklist):
    """Calculate the list of workers to launch after the
    download_wwatch3_results worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure forecast2": [],
        "failure nowcast": [],
        "failure forecast": [],
        "success forecast2": [],
        "success nowcast": [],
        "success forecast": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        try:
            run_date = checklist["WWATCH3 run"][run_type]["run date"]
        except KeyError:
            # Handling for the occasional occurrence of missing "WWATCH3 run" item in checklist
            # due to checklist being cleared while download_wwatch3_results is still running
            run_date = None
        if run_type.startswith("forecast"):
            next_worker = (
                NextWorker(
                    "nowcast.workers.update_forecast_datasets",
                    args=["wwatch3", run_type, "--run-date", run_date],
                )
                if run_date is not None
                else NextWorker(
                    "nowcast.workers.update_forecast_datasets",
                    args=["wwatch3", run_type],
                )
            )
            next_workers[msg.type].append(next_worker)
    return next_workers[msg.type]


def after_get_vfpa_hadcp(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_get_vfpa_hadcp worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {"crash": [], "failure": [], "success": []}
    if msg.type.startswith("success"):
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.ping_erddap", args=["VFPA-HADCP"])
        )
    return next_workers[msg.type]


def after_update_forecast_datasets(msg, config, checklist):
    """Calculate the list of workers to launch after the
    update_forecast_datasets worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nemo forecast": [],
        "failure nemo forecast2": [],
        "failure wwatch3 forecast": [],
        "failure wwatch3 forecast2": [],
        "success nemo forecast": [],
        "success nemo forecast2": [],
        "success wwatch3 forecast": [],
        "success wwatch3 forecast2": [],
    }
    if msg.type.startswith("success"):
        _, model, run_type = msg.type.split()
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.ping_erddap", args=[f"{model}-forecast"])
        )
        if model == "nemo":
            run_date = checklist[f"{model.upper()} run"][run_type]["run date"]
            next_workers[msg.type].extend(
                [
                    NextWorker(
                        "nowcast.workers.make_plots",
                        args=["nemo", run_type, "publish", "--run-date", run_date],
                    ),
                    NextWorker(
                        "nowcast.workers.make_surface_current_tiles",
                        args=[run_type, "--run-date", run_date],
                    ),
                ]
            )
    return next_workers[msg.type]


def after_ping_erddap(msg, config, checklist):
    """Calculate the list of workers to launch after the ping_erddap
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "success weather": [],
        "failure weather": [],
        "success SCVIP-CTD": [],
        "failure SCVIP-CTD": [],
        "success SEVIP-CTD": [],
        "failure SEVIP-CTD": [],
        "success USDDL-CTD": [],
        "failure USDDL-CTD": [],
        "success TWDP-ferry": [],
        "failure TWDP-ferry": [],
        "success VFPA-HADCP": [],
        "failure VFPA-HADCP": [],
        "success nowcast-green": [],
        "failure nowcast-green": [],
        "success nemo-forecast": [],
        "failure nemo-forecast": [],
        "success wwatch3-forecast": [],
        "failure wwatch3-forecast": [],
    }
    if msg.type == "success wwatch3-forecast":
        try:
            run_types = checklist["WWATCH3 run"].keys()
            run_type = "forecast" if "forecast" in run_types else "forecast2"
            run_date = checklist["WWATCH3 run"][run_type]["run date"]
        except KeyError:
            # Handling for the occasional occurrence of missing "WWATCH3 run" item in checklist
            # due to checklist being cleared before ping_erddap is launched
            run_type = "forecast2"
            run_date = None
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.make_plots",
                args=["wwatch3", run_type, "publish", "--run-date", run_date],
            )
            if run_date is not None
            else NextWorker(
                "nowcast.workers.make_plots", args=["wwatch3", "forecast2", "publish"]
            )
        )
    return next_workers[msg.type]


def after_make_plots(msg, config, checklist):
    """Calculate the list of workers to launch after the make_plots
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure nemo nowcast research": [],
        "failure nemo nowcast comparison": [],
        "failure nemo nowcast publish": [],
        "failure nemo nowcast-green research": [],
        "failure nemo nowcast-agrif research": [],
        "failure nemo forecast publish": [],
        "failure nemo forecast2 publish": [],
        "failure wwatch3 forecast publish": [],
        "failure wwatch3 forecast2 publish": [],
        "success nemo nowcast research": [],
        "success nemo nowcast comparison": [],
        "success nemo nowcast publish": [],
        "success nemo nowcast-green research": [],
        "success nemo nowcast-agrif research": [],
        "success nemo forecast publish": [],
        "success nemo forecast2 publish": [],
        "success wwatch3 forecast publish": [],
        "success wwatch3 forecast2 publish": [],
    }
    if msg.type.startswith("success"):
        _, model, run_type, _ = msg.type.split()
        if model == "nemo" and "forecast" in run_type:
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.make_feeds",
                    args=[
                        run_type,
                        "--run-date",
                        checklist["NEMO run"][run_type]["run date"],
                    ],
                )
            )
    return next_workers[msg.type]


def after_make_surface_current_tiles(msg, config, checklist):
    """Calculate the list of workers to launch after the
    make_surface_current_tiles worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_make_feeds(msg, config, checklist):
    """Calculate the list of workers to launch after the make_feeds
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure forecast": [],
        "failure forecast2": [],
        "success forecast": [],
        "success forecast2": [NextWorker("nemo_nowcast.workers.clear_checklist")],
    }
    return next_workers[msg.type]


def after_clear_checklist(msg, config, checklist):
    """Calculate the list of workers to launch after the clear_checklist
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        "crash": [],
        "failure": [],
        "success": [NextWorker("nemo_nowcast.workers.rotate_logs")],
    }
    return next_workers[msg.type]


def after_rotate_logs(msg, config, checklist):
    """Calculate the list of workers to launch after the rotate_logs worker
    ends, but it is an empty list because rotate_logs is the last worker in
    the daily automation cycle.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`collections.namedtuple`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_rotate_hindcast_logs(msg, config, checklist):
    """Calculate the list of workers to launch after the rotate_hindcast_logs worker
    ends, but it is an empty list because rotate_hindcast_logs is a maintenance tool
    that is outside the flow of automation.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`collections.namedtuple`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_launch_remote_worker(msg, config, checklist):
    """Calculate the list of workers to launch after the launch_remote_worker worker
    ends, but it is an empty list because launch_remote_worker is a maintenance tool
    that is outside the flow of automation.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`collections.namedtuple`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []
