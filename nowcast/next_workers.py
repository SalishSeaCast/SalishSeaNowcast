#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""Functions to calculate lists of workers to launch after previous workers
end their work.

Function names **must** be of the form :py:func:`after_worker_name`.
"""
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
        if msg.type.endswith("2.5km 06"):
            data_date = arrow.now().shift(days=-1).format("YYYY-MM-DD")
            for river_name in config["rivers"]["stations"]:
                next_workers["success 2.5km 06"].append(
                    NextWorker(
                        "nowcast.workers.collect_river_data",
                        args=[river_name, "--data-date", data_date],
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
            if "forecast2" in config["run types"]:
                next_workers["success 2.5km 06"].extend(
                    [
                        NextWorker(
                            "nowcast.workers.get_NeahBay_ssh", args=["forecast2"]
                        ),
                        NextWorker(
                            "nowcast.workers.grib_to_netcdf", args=["forecast2"]
                        ),
                    ]
                )
        if msg.type.endswith("2.5km 12"):
            next_workers["success 2.5km 12"].extend(
                [
                    NextWorker("nowcast.workers.get_NeahBay_ssh", args=["nowcast"]),
                    NextWorker("nowcast.workers.grib_to_netcdf", args=["nowcast+"]),
                    NextWorker("nowcast.workers.download_live_ocean"),
                ]
            )
            race_condition_workers = {"grib_to_netcdf", "make_live_ocean_files"}
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
        next_workers["success 2.5km 00"].append(
            NextWorker("nowcast.workers.collect_weather", args=["06", "2.5km"])
        )
    if msg.type.endswith("2.5km 06"):
        next_workers["success 2.5km 06"].append(
            NextWorker("nowcast.workers.collect_weather", args=["12", "2.5km"])
        )
    if msg.type.endswith("2.5km 12"):
        if msg.type.startswith("success"):
            next_workers, race_condition_workers = after_download_weather(
                msg, config, checklist
            )
            next_workers.append(
                NextWorker("nowcast.workers.collect_weather", args=["18", "2.5km"])
            )
            return next_workers, race_condition_workers
    if msg.type.endswith("2.5km 18"):
        next_workers["success 2.5km 18"].extend(
            [
                NextWorker("nowcast.workers.download_weather", args=["00", "1km"]),
                NextWorker("nowcast.workers.download_weather", args=["12", "1km"]),
                NextWorker("nowcast.workers.collect_weather", args=["00", "2.5km"]),
            ]
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
    if msg.type == "success" and checklist["river data"]["river name"] == "Fraser":
        next_workers["success"].append(NextWorker("nowcast.workers.make_runoff_file"))
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


def after_get_NeahBay_ssh(msg, config, checklist):
    """Calculate the list of workers to launch after the get_NeahBay_ssh worker
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
        "failure forecast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success forecast2": [],
        "success forecast": [],
    }
    if msg.type == "success forecast":
        for host in config["run"]["enabled hosts"]:
            enabled_host_config = config["run"]["enabled hosts"][host]
            upload_forcing_ssh = (
                "forecast" in enabled_host_config["run types"]
                and not enabled_host_config["shared storage"]
            )
            if upload_forcing_ssh:
                next_workers["success forecast"].append(
                    NextWorker("nowcast.workers.upload_forcing", args=[host, "ssh"])
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
    next_workers = {"crash": [], "failure": [], "success TWDP": []}
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
    if msg.type == "success":
        for host in config["run"]["enabled hosts"]:
            if not config["run"]["enabled hosts"][host]["shared storage"]:
                next_workers["success"].append(
                    NextWorker(
                        "nowcast.workers.upload_forcing", args=[host, "turbidity"]
                    )
                )
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
    try:
        host_name = list(msg.payload.keys())[0]
        host_config = config["run"]["enabled hosts"][host_name]
    except (AttributeError, IndexError):
        # Malformed payload - no host name in payload;
        # upload_forcing worker probably crashed
        return []
    run_types = [
        # (run_type, make_forcing_links)
        ("nowcast", "nowcast+"),
        ("forecast", "ssh"),
        ("forecast2", "forecast2"),
        ("turbidity", "nowcast-green"),
        ("turbidity", "nowcast-agrif"),
    ]
    for run_type, links_run_type in run_types:
        if host_config["make forcing links"]:
            if run_type == "turbidity" and links_run_type in host_config["run types"]:
                next_workers[f"success turbidity"] = [
                    NextWorker(
                        "nowcast.workers.make_forcing_links",
                        args=[host_name, links_run_type],
                    )
                ]
            if run_type in config["run types"]:
                next_workers[f"success {links_run_type}"] = [
                    NextWorker(
                        "nowcast.workers.make_forcing_links",
                        args=[host_name, links_run_type],
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
        "failure nowcast-dev": [],
        "failure forecast2": [],
        "failure ssh": [],
        "success nowcast+": [],
        "success nowcast-green": [],
        "success nowcast-agrif": [],
        "success nowcast-dev": [],
        "success forecast2": [],
        "success ssh": [],
    }
    if msg.type.startswith("success"):
        run_types = {
            "nowcast+": ("nowcast", "nowcast-dev"),
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
        "failure nowcast-dev": [],
        "failure forecast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success nowcast-green": [],
        "success nowcast-dev": [],
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
        "failure nowcast-dev": [],
        "failure forecast": [],
        "failure forecast2": [],
        "success nowcast": [],
        "success nowcast-green": [],
        "success nowcast-dev": [],
        "success forecast": [],
        "success forecast2": [],
    }
    race_condition_workers = {}
    if msg.type.startswith("success"):
        run_type = msg.type.split()[1]
        wave_forecast_after = config["wave forecasts"]["run when"].split("after ")[1]
        if run_type == "nowcast":
            next_workers[msg.type].extend(
                [
                    NextWorker("nowcast.workers.get_NeahBay_ssh", args=["forecast"]),
                    NextWorker(
                        "nowcast.workers.make_fvcom_boundary",
                        args=[(config["vhfr fvcom runs"]["host"]), "x2", "nowcast"],
                        host=(config["vhfr fvcom runs"]["host"]),
                    ),
                    NextWorker(
                        "nowcast.workers.make_fvcom_boundary",
                        args=[(config["vhfr fvcom runs"]["host"]), "r12", "nowcast"],
                        host=(config["vhfr fvcom runs"]["host"]),
                    ),
                ]
            )
        if run_type == "forecast":
            if wave_forecast_after == "forecast":
                host_name = config["wave forecasts"]["host"]
                next_workers[msg.type].extend(
                    [
                        NextWorker(
                            "nowcast.workers.make_ww3_wind_file",
                            args=[host_name, "forecast"],
                            host=host_name,
                        ),
                        NextWorker(
                            "nowcast.workers.make_ww3_current_file",
                            args=[host_name, "forecast"],
                            host=host_name,
                        ),
                    ]
                )
                race_condition_workers = {"make_ww3_wind_file", "make_ww3_current_file"}
            else:
                next_workers[msg.type].append(
                    NextWorker(
                        "nowcast.workers.make_turbidity_file",
                        args=["--run-date", msg.payload[run_type]["run date"]],
                    )
                )
        if run_type == "nowcast-green":
            if wave_forecast_after == "nowcast-green":
                host_name = config["wave forecasts"]["host"]
                next_workers[msg.type].extend(
                    [
                        NextWorker(
                            "nowcast.workers.make_ww3_wind_file",
                            args=[host_name, "forecast"],
                            host=host_name,
                        ),
                        NextWorker(
                            "nowcast.workers.make_ww3_current_file",
                            args=[host_name, "forecast"],
                            host=host_name,
                        ),
                    ]
                )
                race_condition_workers = {"make_ww3_wind_file", "make_ww3_current_file"}
            for host in config["run"]["enabled hosts"]:
                run_types = config["run"]["enabled hosts"][host]["run types"]
                if "nowcast-dev" in run_types:
                    next_workers[msg.type].append(
                        NextWorker(
                            "nowcast.workers.make_forcing_links",
                            args=[host, "nowcast+", "--shared-storage"],
                        )
                    )
        if run_type == "forecast2":
            host_name = config["wave forecasts"]["host"]
            next_workers[msg.type].extend(
                [
                    NextWorker(
                        "nowcast.workers.make_ww3_wind_file",
                        args=[host_name, "forecast2"],
                        host=host_name,
                    ),
                    NextWorker(
                        "nowcast.workers.make_ww3_current_file",
                        args=[host_name, "forecast2"],
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


def after_make_fvcom_boundary(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_make_fvcom_boundary worker ends.

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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[2]
        model_config = msg.payload[run_type]["model config"]
        run_date = msg.payload[run_type]["run date"]
        next_workers[msg.type].extend(
            [
                NextWorker(
                    "nowcast.workers.make_fvcom_atmos_forcing",
                    args=[model_config, run_type, "--run-date", run_date],
                    host="localhost",
                ),
                NextWorker(
                    "nowcast.workers.make_fvcom_rivers_forcing",
                    args=[
                        (config["vhfr fvcom runs"]["host"]),
                        model_config,
                        run_type,
                        "--run-date",
                        run_date,
                    ],
                    host=(config["vhfr fvcom runs"]["host"]),
                ),
            ]
        )
    return next_workers[msg.type]


def after_make_fvcom_rivers_forcing(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_make_fvcom_rivers_forcing worker ends.

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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    return []


def after_make_fvcom_atmos_forcing(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_make_fvcom_atmos_forcing worker ends.

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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    if msg.type.startswith("success"):
        host_name = config["vhfr fvcom runs"]["host"]
        run_type = msg.type.split()[2]
        model_config = msg.payload[run_type]["model config"]
        run_date = msg.payload[run_type]["run date"]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.upload_fvcom_atmos_forcing",
                args=[host_name, model_config, run_type, "--run-date", run_date],
            )
        )
    return next_workers[msg.type]


def after_upload_fvcom_atmos_forcing(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_upload_fvcom_atmos_forcing worker ends.

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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    if msg.type.startswith("success"):
        host_name = config["vhfr fvcom runs"]["host"]
        run_type = msg.type.split()[2]
        model_config = msg.payload[host_name][run_type]["model config"]
        run_date = msg.payload[host_name][run_type]["run date"]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.run_fvcom",
                args=[host_name, model_config, run_type, "--run-date", run_date],
                host=host_name,
            )
        )
    return next_workers[msg.type]


def after_run_fvcom(msg, config, checklist):
    """Calculate the list of workers to launch after the after_run_fvcom worker
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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    if msg.type.startswith("success"):
        _, model_config, run_type = msg.type.split()
        host_name = msg.payload[f"{model_config} {run_type}"]["host"]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.watch_fvcom",
                args=[host_name, model_config, run_type],
                host=host_name,
            )
        )
    return next_workers[msg.type]


def after_watch_fvcom(msg, config, checklist):
    """Calculate the list of workers to launch after the after_watch_fvcom worker
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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    if msg.type.startswith("success"):
        _, model_config, run_type = msg.type.split()
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.download_fvcom_results",
                args=[
                    msg.payload[f"{model_config} {run_type}"]["host"],
                    model_config,
                    run_type,
                    "--run-date",
                    msg.payload[f"{model_config} {run_type}"]["run date"],
                ],
            )
        )
        if run_type == "nowcast" and model_config == "x2":
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.make_fvcom_boundary",
                    args=[(config["vhfr fvcom runs"]["host"]), "x2", "forecast"],
                    host=(config["vhfr fvcom runs"]["host"]),
                )
            )
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
        "failure forecast": [],
        "success forecast2": [],
        "success forecast": [],
    }
    if msg.type.startswith("success"):
        host_name = config["wave forecasts"]["host"]
        run_type = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.run_ww3",
                # We make the current files for the period of nowcast+forecast,
                # but run nowcast then forecast separately
                args=[
                    host_name,
                    "nowcast" if run_type == "forecast" else run_type,
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
                    NextWorker("nowcast.workers.ping_erddap", args=["nowcast-green"])
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
    return []


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
        run_date = checklist["WWATCH3 run"][run_type]["run date"]
        if run_type.startswith("forecast"):
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.update_forecast_datasets",
                    args=["wwatch3", run_type, "--run-date", run_date],
                )
            )
    return next_workers[msg.type]


def after_download_fvcom_results(msg, config, checklist):
    """Calculate the list of workers to launch after the
    download_fvcom_results worker ends.

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
        "failure x2 nowcast": [],
        "failure x2 forecast": [],
        "failure r12 nowcast": [],
        "success x2 nowcast": [],
        "success x2 forecast": [],
        "success r12 nowcast": [],
    }
    if msg.type.startswith("success"):
        run_type = msg.type.split()[2]
        run_date = msg.payload[run_type]["run date"]
        model_config = msg.payload[run_type]["model config"]
        next_workers[msg.type].extend(
            [
                NextWorker(
                    "nowcast.workers.get_vfpa_hadcp", args=["--data-date", run_date]
                ),
                NextWorker(
                    "nowcast.workers.make_plots",
                    args=[
                        "fvcom",
                        f"{run_type}-{model_config}",
                        "research",
                        "--run-date",
                        run_date,
                    ],
                ),
            ]
        )
        if run_type == "forecast":
            next_workers[msg.type].append(
                NextWorker(
                    "nowcast.workers.update_forecast_datasets",
                    args=["fvcom", "forecast", "--run-date", run_date],
                )
            )
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
        "failure fvcom forecast": [],
        "failure nemo forecast": [],
        "failure nemo forecast2": [],
        "failure wwatch3 forecast": [],
        "failure wwatch3 forecast2": [],
        "success fvcom forecast": [],
        "success nemo forecast": [],
        "success nemo forecast2": [],
        "success wwatch3 forecast": [],
        "success wwatch3 forecast2": [],
    }
    if msg.type.startswith("success"):
        model = msg.type.split()[1]
        run_type = msg.type.split()[2]
        try:
            run_date = checklist[f"{model.upper()} run"][run_type]["run date"]
        except KeyError:
            # FVCOM run has model config prefixed to run type
            run_date = checklist[f"{model.upper()} run"][f"x2 {run_type}"]["run date"]
        next_workers[msg.type].append(
            NextWorker("nowcast.workers.ping_erddap", args=[f"{model}-forecast"])
        )
        if model == "nemo":
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
        "success download_weather": [],
        "failure download_weather": [],
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
        run_types = checklist["WWATCH3 run"].keys()
        run_type = "forecast2" if "forecast2" in run_types else "forecast"
        run_date = checklist["WWATCH3 run"][run_type]["run date"]
        next_workers[msg.type].append(
            NextWorker(
                "nowcast.workers.make_plots",
                args=["wwatch3", run_type, "publish", "--run-date", run_date],
            )
        )
    if msg.type == "success VFPA-HADCP":
        try:
            keys = checklist["FVCOM run"].keys()
        except KeyError:
            # "FVCOM run" is only in the checklist after runs.
            # If it's too early in the day, just return.
            return next_workers[msg.type]
        for key in keys:
            model_config, run_type = key.split()
            if "completed" not in checklist["FVCOM run"][f"{model_config} {run_type}"]:
                continue
            run_date = checklist["FVCOM run"][f"{model_config} {run_type}"]["run date"]
            next_workers[msg.type].extend(
                [
                    NextWorker(
                        "nowcast.workers.make_plots",
                        args=[
                            "fvcom",
                            f"{run_type}-{model_config}",
                            "publish",
                            "--run-date",
                            run_date,
                        ],
                    )
                ]
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
        "failure fvcom nowcast-x2 publish": [],
        "failure fvcom forecast-x2 publish": [],
        "failure fvcom nowcast-r12 publish": [],
        "failure fvcom nowcast-x2 research": [],
        "failure fvcom forecast-x2 research": [],
        "failure fvcom nowcast-r12 research": [],
        "failure wwatch3 forecast publish": [],
        "failure wwatch3 forecast2 publish": [],
        "success nemo nowcast research": [],
        "success nemo nowcast comparison": [],
        "success nemo nowcast publish": [],
        "success nemo nowcast-green research": [],
        "success nemo nowcast-agrif research": [],
        "success nemo forecast publish": [],
        "success nemo forecast2 publish": [],
        "success fvcom nowcast-x2 publish": [],
        "success fvcom forecast-x2 publish": [],
        "success fvcom nowcast-r12 publish": [],
        "success fvcom nowcast-x2 research": [],
        "success fvcom forecast-x2 research": [],
        "success fvcom nowcast-r12 research": [],
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
