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
"""Salish Sea FVCOM Vancouver Harbour and Fraser River model worker that
prepares the temporary run directory and bash run script for a nowcast or
forecast run on the ONC cloud, and launches the run.
"""
from datetime import timedelta
import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

import arrow
import f90nml
import fvcom_cmd.api
from nemo_nowcast import NowcastWorker
import yaml

from nowcast import lib

NAME = "run_fvcom"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.run_fvcom --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument("host_name", help="Name of the host to execute the run on")
    worker.cli.add_argument(
        "model_config",
        choices={"r12", "x2"},
        help="""
        Model configuration of run to execute:
        'r12' means the r12 resolution
        'x2' means the x2 resolution
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="""
        Type of run to execute:
        'nowcast' means run for present UTC day (after NEMO nowcast run)
        'forecast' means updated forecast run 
        (next 36h UTC, after NEMO forecast run)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date to execute the run for.",
    )
    worker.run(run_fvcom, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"{parsed_args.model_config} {parsed_args.run_type} FVCOM VH-FR run for "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f"on {parsed_args.host_name} started"
    )
    msg_type = f"success {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"{parsed_args.model_config} {parsed_args.run_type} FVCOM VH-FR run for "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f"on {parsed_args.host_name} failed"
    )
    msg_type = f"failure {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def run_fvcom(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    model_config = parsed_args.model_config
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    run_desc_file_path = _create_run_desc_file(run_date, model_config, run_type, config)
    tmp_run_dir = fvcom_cmd.api.prepare(run_desc_file_path)
    logger.debug(f"{run_type}: temporary run directory: {tmp_run_dir}")
    ## TODO: It would be nice if prepare() copied YAML file to tmp run dir
    shutil.copy2(run_desc_file_path, tmp_run_dir / run_desc_file_path.name)
    _prep_fvcom_input_dir(run_date, model_config, run_type, config)
    run_script_path = _create_run_script(
        run_date, model_config, run_type, tmp_run_dir, run_desc_file_path, config
    )
    run_desc_file_path.unlink()
    run_exec_cmd = _launch_run_script(run_type, run_script_path, host_name)
    return {
        run_type: {
            "host": host_name,
            "run dir": os.fspath(tmp_run_dir),
            "run exec cmd": run_exec_cmd,
            "model config": model_config,
            "run date": run_date.format("YYYY-MM-DD"),
        }
    }


def _create_run_desc_file(run_date, model_config, run_type, config):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str model_config:
    :param str run_type:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run description file path
    :rtype: :py:class:`pathlib.Path`
    """
    ddmmmyy = run_date.format("DDMMMYY").lower()
    run_id = f"{ddmmmyy}fvcom-{model_config}-{run_type}"
    run_prep_dir = Path(config["vhfr fvcom runs"]["run prep dir"])
    run_desc = _run_description(
        run_id, run_date, model_config, run_type, run_prep_dir, config
    )
    run_desc_file_path = run_prep_dir / f"{run_id}.yaml"
    with run_desc_file_path.open("wt") as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    logger.debug(f"{run_type}: run description file: {run_desc_file_path}")
    return run_desc_file_path


def _run_description(run_id, run_date, model_config, run_type, run_prep_dir, config):
    """
    :param str run_id:
    :param :py:class:`arrow.Arrow` run_date:
    :param str model_config:
    :param str run_type:
    :param :py:class:`pathlib.Path` run_prep_dir:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run description
    :rtype dict:
    """
    casename = config["vhfr fvcom runs"]["case name"][model_config]
    _edit_namelists(casename, run_date, model_config, run_type, run_prep_dir, config)
    namelist_path = _assemble_namelist(casename, run_type, run_prep_dir, config)
    run_desc = {
        "run_id": run_id,
        "casename": casename,
        "nproc": config["vhfr fvcom runs"]["number of processors"],
        "paths": {
            "FVCOM": os.fspath(
                Path(config["vhfr fvcom runs"]["FVCOM exe path"]).resolve()
            ),
            "runs directory": os.fspath(run_prep_dir.resolve()),
            "input": os.fspath((run_prep_dir / "input").resolve()),
        },
        "namelist": os.fspath(namelist_path.resolve()),
        ## TODO: Add VCS revision tracking, but need to be able to handle Git
        ##       repos to do so.
    }
    return run_desc


def _edit_namelists(casename, run_date, model_config, run_type, run_prep_dir, config):
    """
    :param str casename:
    :param :py:class:`arrow.Arrow` run_date:
    :param str model_config:
    :param str run_type:
    :param :py:class:`pathlib.Path` run_prep_dir:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    start_offsets = {"nowcast": timedelta(hours=0), "forecast": timedelta(hours=24)}
    start_date = run_date + start_offsets[run_type]
    run_durations = {"nowcast": timedelta(hours=24), "forecast": timedelta(hours=36)}
    atmos_file_tmpl = config["vhfr fvcom runs"]["atmospheric forcing"][
        "atmos file template"
    ]
    atmos_files = {
        field_type: atmos_file_tmpl.format(
            model_config=model_config,
            run_type=run_type,
            field_type=field_type,
            yyyymmdd=start_date.format("YYYYMMDD"),
        )
        for field_type in config["vhfr fvcom runs"]["atmospheric forcing"][
            "field types"
        ]
    }
    rivers_file_tmpl = config["vhfr fvcom runs"]["rivers forcing"][
        "rivers file template"
    ]
    rivers_file = Path(
        rivers_file_tmpl.format(
            model_config=model_config,
            run_type=run_type,
            yyyymmdd=start_date.format("YYYYMMDD"),
        )
    ).with_suffix(".nc_riv.nml")
    bdy_file_tmpl = config["vhfr fvcom runs"]["nemo coupling"]["boundary file template"]
    bdy_file = bdy_file_tmpl.format(
        model_config=model_config,
        run_type=run_type,
        yyyymmdd=start_date.format("YYYYMMDD"),
    )
    time_step = config["vhfr fvcom runs"]["run types"][f"{run_type} {model_config}"][
        "time step"
    ]
    patches = {
        run_prep_dir
        / "namelist.case": {
            "nml_case": {
                "case_title": casename,
                "start_date": start_date.format("YYYY-MM-DD HH:mm:ss.00"),
                "end_date": (
                    (start_date + run_durations[run_type]).format(
                        "YYYY-MM-DD HH:mm:ss.00"
                    )
                ),
            }
        },
        run_prep_dir
        / "namelist.startup.hotstart": {
            "nml_startup": {"startup_file": f"vh_{model_config}_restart_0001.nc"}
        },
        run_prep_dir
        / "namelist.numerics": {"nml_integration": {"extstep_seconds": time_step}},
        run_prep_dir
        / "namelist.restart": {
            "nml_restart": {
                "rst_first_out": start_date.shift(days=+1).format(
                    "YYYY-MM-DD HH:mm:ss.00"
                )
            }
        },
        run_prep_dir
        / "namelist.netcdf": {
            "nml_netcdf": {
                "nc_first_out": start_date.format("YYYY-MM-DD 01:00:00.00"),
                "nc_output_stack": 24 if run_type == "nowcast" else 36,
            }
        },
        run_prep_dir
        / "namelist.physics": {
            "nml_heating_calculated": {"heating_calculate_file": atmos_files["hfx"]}
        },
        run_prep_dir
        / "namelist.surface": {
            "nml_surface_forcing": {
                "wind_file": atmos_files["wnd"],
                "precipitation_file": atmos_files["precip"],
                "airpressure_file": atmos_files["hfx"],
            }
        },
        run_prep_dir
        / "namelist.rivers": {
            "nml_river_type": {"river_info_file": os.fspath(rivers_file)}
        },
        run_prep_dir
        / "namelist.obc": {
            "nml_open_boundary_control": {
                "obc_node_list_file": config["vhfr fvcom runs"]["fvcom grid"][
                    model_config
                ]["obc nodes file"]
            }
        },
        run_prep_dir
        / "namelist.grid": {
            "nml_grid_coordinates": {
                "grid_file": config["vhfr fvcom runs"]["fvcom grid"][model_config][
                    "grid file"
                ],
                "sigma_levels_file": config["vhfr fvcom runs"]["fvcom grid"][
                    model_config
                ]["sigma file"],
                "depth_file": config["vhfr fvcom runs"]["fvcom grid"][model_config][
                    "depths file"
                ],
                "coriolis_file": config["vhfr fvcom runs"]["fvcom grid"][model_config][
                    "coriolis file"
                ],
                "sponge_file": config["vhfr fvcom runs"]["fvcom grid"][model_config][
                    "sponge file"
                ],
            }
        },
        run_prep_dir
        / "namelist.nesting": {"nml_nesting": {"nesting_file_name": bdy_file}},
        run_prep_dir
        / "namelist.station_timeseries": {
            "nml_station_timeseries": {
                "station_file": Path(
                    config["vhfr fvcom runs"]["output station timeseries"][model_config]
                ).name
            }
        },
    }
    for namelist_path, patch in patches.items():
        _patch_namelist(namelist_path, patch)


def _patch_namelist(namelist_path, patch):
    """
    :param :py:class:`pathlib.Path` namelist_path:
    :param dict patch:
    """
    # f90nml insists on writing the patched namelist to a file,
    # so we use an ephemeral temporary file
    with tempfile.TemporaryFile("wt") as tmp_patched_namelist:
        nml = f90nml.patch(namelist_path, patch, tmp_patched_namelist)
    with namelist_path.open("wt") as patched_nameslist:
        nml.write(patched_nameslist)
    logger.debug(f"patched namelist: {namelist_path}")


def _assemble_namelist(casename, run_type, run_prep_dir, config):
    """
    :param str casename:
    :param str run_type:
    :param :py:class:`pathlib.Path` run_prep_dir:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Namelist file path
    :rtype: :py:class:`pathlib.Path`
    """
    namelist_file_tmpl = list(config["vhfr fvcom runs"]["namelists"].keys())[0]
    namelist_files = config["vhfr fvcom runs"]["namelists"][namelist_file_tmpl]
    namelist_file = namelist_file_tmpl.format(casename=casename)
    with (run_prep_dir / namelist_file).open("wt") as namelist:
        for nml in namelist_files:
            nml_path = Path(nml)
            if not nml_path.is_absolute():
                nml_path = run_prep_dir / nml
            with nml_path.open("rt") as f:
                namelist.writelines(f.readlines())
                namelist.write("\n")
    logger.debug(f"{run_type}: namelist file: {run_prep_dir/namelist_file}")
    return run_prep_dir / namelist_file


def _prep_fvcom_input_dir(run_date, model_config, run_type, config):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str model_config:
    :param str run_type:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    fvcom_input_dir = Path(config["vhfr fvcom runs"]["input dir"])
    grid_dir = Path(config["vhfr fvcom runs"]["fvcom grid"]["grid dir"])
    for grid_file in (
        "grid file",
        "depths file",
        "sigma file",
        "coriolis file",
        "sponge file",
        "obc nodes file",
    ):
        f = Path(config["vhfr fvcom runs"]["fvcom grid"][model_config][grid_file])
        (fvcom_input_dir / f).symlink_to(grid_dir / f)
    logger.debug(f"symlinked {grid_dir} files into {fvcom_input_dir}")
    output_timeseries_file = Path(
        config["vhfr fvcom runs"]["output station timeseries"][model_config]
    )
    (fvcom_input_dir / output_timeseries_file.name).symlink_to(output_timeseries_file)
    logger.debug(f"symlinked {output_timeseries_file} file into {fvcom_input_dir}")
    casename = config["vhfr fvcom runs"]["case name"][model_config]
    restart_dir = Path(
        config["vhfr fvcom runs"]["run types"][f"nowcast {model_config}"]["results"]
    )
    restart_file_date = run_date.shift(days=-1) if run_type == "nowcast" else run_date
    restart_file = (
        restart_dir
        / restart_file_date.format("DDMMMYY").lower()
        / f"{casename}_restart_0001.nc"
    )
    (fvcom_input_dir / restart_file.name).symlink_to(restart_file)
    logger.debug(f"symlinked {restart_file} file into {fvcom_input_dir}")


def _create_run_script(
    run_date, model_config, run_type, tmp_run_dir, run_desc_file_path, config
):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str model_config:
    :param str run_type:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`pathlib.Path` run_desc_file_path:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script file path
    :rtype: :py:class:`pathlib.Path`
    """
    results_dir = Path(
        config["vhfr fvcom runs"]["run types"][f"{run_type} {model_config}"]["results"]
    )
    ddmmmyy = run_date.format("DDMMMYY").lower()
    script = _build_script(
        tmp_run_dir, run_desc_file_path, results_dir / ddmmmyy, model_config, config
    )
    run_script_path = tmp_run_dir / "VHFR_FVCOM.sh"
    with run_script_path.open("wt") as f:
        f.write(script)
    lib.fix_perms(run_script_path, lib.FilePerms(user="rwx", group="rwx", other="r"))
    logger.debug(f"{run_type}: run script: {run_script_path}")
    return run_script_path


def _build_script(tmp_run_dir, run_desc_file_path, results_dir, model_config, config):
    """
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`pathlib.Path` run_desc_file_path:
    :param :py:class:`pathlib.Path` results_dir:
    :param str model_config:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script
    :rtype: str
    """
    with run_desc_file_path.open("rt") as f:
        run_desc = yaml.load(f)
    script = "#!/bin/bash\n"
    script = "\n".join(
        (
            script,
            "{defns}\n"
            "{execute}\n"
            "{fix_permissions}\n"
            "{cleanup}".format(
                defns=_definitions(
                    run_desc, tmp_run_dir, run_desc_file_path, results_dir, config
                ),
                execute=_execute(model_config, config),
                fix_permissions=_fix_permissions(),
                cleanup=_cleanup(),
            ),
        )
    )
    return script


def _definitions(run_desc, tmp_run_dir, run_desc_file_path, results_dir, config):
    """
    :param dict run_desc:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`pathlib.Path` run_desc_file_path:
    :param :py:class:`pathlib.Path` results_dir:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script definitions
    :rtype: str
    """
    defns = (
        'RUN_ID="{run_id}"\n'
        'RUN_DESC="{run_desc_file}"\n'
        'WORK_DIR="{run_dir}"\n'
        'RESULTS_DIR="{results_dir}"\n'
        'MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts.fvcom"\n'
        'GATHER="{fvc_cmd} gather"\n'
    ).format(
        run_id=run_desc["run_id"],
        run_desc_file=run_desc_file_path.name,
        run_dir=tmp_run_dir,
        results_dir=results_dir,
        mpirun=f'mpirun --hostfile {config["vhfr fvcom runs"]["mpi hosts file"]}',
        fvc_cmd=config["vhfr fvcom runs"]["fvc_cmd"],
    )
    return defns


def _execute(model_config, config):
    """
    :param str model_config:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script model execution commands
    :rtype: str
    """
    mpirun = (
        f'${{MPIRUN}} -np {config["vhfr fvcom runs"]["number of processors"]} '
        f"--bind-to-core ./fvcom "
        f'--casename={config["vhfr fvcom runs"]["case name"][model_config]} '
        f"--logfile=./fvcom.log"
    )
    script = (
        "mkdir -p ${RESULTS_DIR}\n"
        "\n"
        "cd ${WORK_DIR}\n"
        'echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout\n'
        "\n"
        'echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    script += f"{mpirun} >>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr\n"
    script += (
        'echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout\n'
        "\n"
        'echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout\n'
        "${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout\n"
        'echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return script


def _fix_permissions():
    """
    :return: Run script results directory and files permissions adjustment commands
    :rtype: str
    """
    script = (
        "chmod g+rwx ${RESULTS_DIR}\n"
        "chmod g+rw ${RESULTS_DIR}/*\n"
        "chmod o+rx ${RESULTS_DIR}\n"
        "chmod o+r ${RESULTS_DIR}/*\n"
    )
    return script


def _cleanup():
    """
    :return: Run script commands to delete temporary run directory
    :rtype: str
    """
    script = (
        'echo "Deleting run directory" >>${RESULTS_DIR}/stdout\n'
        "rmdir $(pwd)\n"
        'echo "Finished at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return script


def _launch_run_script(run_type, run_script_path, host_name):
    """
    :param str run_type:
    :param :py:class:`pathlib.Path` run_script_path:
    :param str host_name:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run execution command
    :rtype: str
    """
    logger.info(f"{run_type}: launching {run_script_path} on {host_name}")
    run_exec_cmd = f"bash {run_script_path}"
    logger.debug(
        f"{run_type}: running command in subprocess: " f"{shlex.split(run_exec_cmd)}"
    )
    subprocess.Popen(shlex.split(run_exec_cmd))
    run_process_pid = None
    while not run_process_pid:
        try:
            proc = subprocess.run(
                shlex.split(f'pgrep --newest --exact --full "{run_exec_cmd}"'),
                stdout=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
            run_process_pid = int(proc.stdout)
        except subprocess.CalledProcessError:
            # Process has not yet been spawned
            pass
    logger.debug(f"{run_type} on {host_name}: run pid: {run_process_pid}")
    return run_exec_cmd


if __name__ == "__main__":
    main()  # pragma: no cover
