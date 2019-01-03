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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM run_fvcom worker.
"""
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import run_fvcom


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
vhfr fvcom runs:
  case name: vhfr_low_v2
  run prep dir: fvcom-runs/

  fvcom grid:
    grid dir: /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/grid/
    grid file: vhfr_low_v2_utm10_grd.dat
    depths file: vhfr_low_v2_utm10_dep.dat
    sigma file: vhfr_low_v2_sigma.dat
    coriolis file: vhfr_low_v2_utm10_cor.dat
    sponge file: vhfr_low_v2_nospg_spg.dat
    obc nodes file: vhfr_low_v2_obc.dat

  nemo coupling:
    # Directory on compute host where FVCOM-NEMO coupling files are stored
    coupling dir: /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/coupling_nemo_cut/
    # File containing FVCOM indices for the NEMO nesting zone
    fvcom nest indices file: vhfr_low_v2_nesting_indices.txt
    # File containing nesting zone reference line for weights calculation
    fvcom nest ref line file: vhfr_low_v2_nesting_innerboundary.txt
    # NEMO index ranges contained in the boundary files
    nemo cut i range: [225, 369]
    nemo cut j range: [340, 561]
    # Transition zone width [m] over which weights rise from 0 to 1
    transition zone width: 8500
    # Transition profile tanh function parameters
    tanh dl: 2
    tanh du: 2
    # NEMO coordinates file
    nemo coordinates: /nemoShare/MEOPAR/nowcast-sys/grid/coordinates_seagrid_SalishSea201702.nc
    # NEMO mesh mask file
    nemo mesh mask: /nemoShare/MEOPAR/nowcast-sys/grid/mesh_mask201702.nc
    # NEMO bathymetry file
    nemo bathymetry: /nemoShare/MEOPAR/nowcast-sys/grid/bathymetry_201702.nc
    # Template for boundary forcing file names
    # **Must be quoted to project {} characters**
    boundary file template: 'bdy_{run_type}_btrp_{yyyymmdd}.nc'

  atmospheric forcing:
    # Directory on host where make_fccom_atmos_forcing worker runs where HRDPS GRIB files are stored
    hrdps grib dir: /results/forcing/atmospheric/GEM2.5/GRIB/
    # Directory on host where make_fccom_atmos_forcing worker runs where FVCOM atmospheric forcing files are stored
    fvcom atmos dir: /results/forcing/atmospheric/GEM2.5/vhfr-fvcom
    # Template for atmospheric forcing file names
    # **Must be quoted to project {} characters**
    atmos file template: 'atmos_{run_type}_{field_type}_{yyyymmdd}.nc'
    # Directory on host where make_fvcom_atmos_forcing worker runs where FVCOM grid files are stored
    fvcom grid dir: /results/nowcast-sys/FVCOM-VHFR-config/grid/

  # Directory on compute host where FVCOM input files are stored
  input dir: /nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input/
  # Path and name of file on compute host that defines the tide gauge stations
  # to produce point outputs at
  output station timeseries: /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/output/vhfr_low_v2_utm10_station.dat
  namelists:
    # Name of the namelist file to create by concatenating the list of namelist
    # section files below
    # **Must be quoted to project {} characters**
    '{casename}_run.nml':
      - namelist.case
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.startup.hotstart
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.io
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.numerics
      - namelist.restart
      - namelist.netcdf
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.physics
      - namelist.surface
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.rivers
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.obc
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.grid
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.groundwater
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.lagrangian
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.probes
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.bounds_check
      - namelist.nesting
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.station_timeseries
      - /nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.additional_models
  # Path to the tree that contains the FVCOM executable at FVCOM_source/fvcom
  FVCOM exe path: /nemoShare/MEOPAR/nowcast-sys/FVCOM41/
  # Number of processors
  number of processors: 64
  # Location on the compute host of the file that contains IP addresses
  # and MPI slots specifications.
  mpi hosts file: ${HOME}/mpi_hosts.fvcom
  # Path to the FVCOM command processor executable to use in the run script
  fvc_cmd: /nemoShare/MEOPAR/nowcast-sys/nowcast-env/bin/fvc
  # Run type specific configurations for the runs that are executed on the
  # compute host; keyed by run type
  run types:
    nowcast:
      # Directory on compute host where NEMO run results for boundary forcing
      # are stored
      nemo boundary results: /nemoShare/MEOPAR/SalishSea/nowcast/
      # Directory on compute host where results are stored
      results: /nemoShare/MEOPAR/SalishSea/fvcom-nowcast/
    forecast:
      results: /nemoShare/MEOPAR/SalishSea/fvcom-forecast/
      nemo boundary results: /nemoShare/MEOPAR/SalishSea/forecast/
  # Directories on results server where run results are stored
  # in ddmmmyy/ directories; keyed by run type
  results archive:
    nowcast: /opp/fvcom/nowcast/
    forecast: /opp/fvcom/forecast/
  # Name of the results file containing the tide gauge stations sea surface height time series
  stations dataset filename: vhfr_low_v2_station_timeseries.nc
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture(scope="function")
def config():
    """
    nowcast.yaml config object section for FVCOM VHFR runs.

    :return: :py:class:`nemo_nowcast.Config`-like dict
    :rtype: dict
    """
    return {
        "vhfr fvcom runs": {
            "case name": "vhfr_low_v2",
            "run prep dir": "fvcom-runs/",
            "fvcom grid": {
                "grid dir": "VHFR-FVCOM-config/grid/",
                "grid file": "vhfr_low_v2_utm10_grd.dat",
                "depths file": "vhfr_low_v2_utm10_dep.dat",
                "sigma file": "vhfr_low_v2_sigma.dat",
                "coriolis file": "vhfr_low_v2_utm10_cor.dat",
                "sponge file": "vhfr_low_v2_nospg_spg.dat",
                "obc nodes file": "vhfr_low_v2_obc.dat",
            },
            "nemo coupling": {
                "boundary file template": "bdy_{run_type}_btrp_{yyyymmdd}.nc"
            },
            "atmospheric forcing": {
                "atmos file template": "atmos_{run_type}_{field_type}_{yyyymmdd}.nc"
            },
            "input dir": "fvcom-runs/input/",
            "output station timeseries": "VHFR-FVCOM-config/output/vhfr_low_v2_utm10_station.dat",
            "namelists": {"{casename}_run.nml": ["namelist.case"]},
            "number of processors": 32,
            "mpi hosts file": "${HOME}/mpi_hosts.fvcom",
            "fvc_cmd": "bin/fvc",
            "run types": {
                "nowcast": {"results": "SalishSea/fvcom-nowcast/"},
                "forecast": {"results": "SalishSea/fvcom-forecast/"},
            },
        }
    }


@patch("nowcast.workers.run_fvcom.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker.call_args
        assert args == ("run_fvcom",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().run.call_args
        assert args == (run_fvcom.run_fvcom, run_fvcom.success, run_fvcom.failure)


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        run_fvcom.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        msg_type = run_fvcom.success(parsed_args)
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        run_fvcom.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        msg_type = run_fvcom.failure(parsed_args)
        assert msg_type == f"failure {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._create_run_desc_file")
@patch("nowcast.workers.run_fvcom.fvcom_cmd.api.prepare")
@patch("nowcast.workers.run_fvcom._prep_fvcom_input_dir")
@patch("nowcast.workers.run_fvcom.shutil.copy2", autospec=True)
@patch("nowcast.workers.run_fvcom._create_run_script")
@patch("nowcast.workers.run_fvcom._launch_run_script")
class TestRunFVCOM:
    """Unit tests for run_fvcom() function.
    """

    def test_checklist(
        self,
        m_launch,
        m_crs,
        m_copy2,
        m_pfid,
        m_prep,
        m_crdf,
        m_logger,
        run_type,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        tmp_run_dir = (
            f"/fvcom-runs/29nov17vhfr-{run_type}_2017-11-29T183043.555919-0700"
        )
        m_prep.return_value = tmp_run_dir
        checklist = run_fvcom.run_fvcom(parsed_args, config)
        expected = {
            run_type: {
                "host": "west.cloud",
                "run dir": tmp_run_dir,
                "run exec cmd": m_launch(),
                "run date": "2017-11-29",
            }
        }
        assert checklist == expected


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom.yaml.dump", autospec=True)
@patch("nowcast.workers.run_fvcom._run_description")
class TestCreateRunDescFile:
    """Unit tests for _create_fun_desc_file() function.
    """

    def test_run_desc_file_path(
        self, m_run_desc, m_yaml_dump, m_logger, run_type, config
    ):
        run_date = arrow.get("2017-12-11")
        with patch("nowcast.workers.run_fvcom.Path.open") as m_open:
            run_desc_file_path = run_fvcom._create_run_desc_file(
                run_date, run_type, config
            )
        expected = Path(f"fvcom-runs/11dec17fvcom-{run_type}.yaml")
        assert run_desc_file_path == expected

    def test_run_desc_yaml_dump(
        self, m_run_desc, m_yaml_dump, m_logger, run_type, config, tmpdir
    ):
        run_date = arrow.get("2017-12-12")
        run_prep_dir = Path(str(tmpdir.ensure_dir("nowcast-sys/fvcom-runs")))
        with patch("nowcast.workers.run_fvcom.Path.open") as m_open:
            run_desc_file_path = run_fvcom._create_run_desc_file(
                run_date, run_type, config
            )
            m_yaml_dump.assert_called_once_with(
                m_run_desc(), m_open().__enter__(), default_flow_style=False
            )


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._edit_namelists")
@patch("nowcast.workers.run_fvcom._assemble_namelist")
class TestRunDescription:
    """Unit test for _run_description() function.
    """

    def test_run_desc(self, m_mk_nml, m_edit_nml, m_logger, run_type, config, tmpdir):
        run_id = f"11dec17fvcom-{run_type}"
        fvcom_repo_dir = Path(str(tmpdir.ensure_dir("FVCOM41")))
        run_prep_dir = Path(str(tmpdir.ensure_dir("fvcom-runs")))
        m_mk_nml.return_value = Path(str(run_prep_dir), "vhfr_low_v2_run.nml")
        p_config = patch.dict(
            config["vhfr fvcom runs"],
            {"run prep dir": run_prep_dir, "FVCOM exe path": fvcom_repo_dir},
        )
        with p_config:
            run_desc = run_fvcom._run_description(
                run_id, arrow.get("2017-12-11"), run_type, run_prep_dir, config
            )
        expected = {
            "run_id": run_id,
            "casename": "vhfr_low_v2",
            "nproc": 32,
            "paths": {
                "FVCOM": os.fspath(fvcom_repo_dir),
                "runs directory": os.fspath(run_prep_dir),
                "input": os.fspath(run_prep_dir / "input"),
            },
            "namelist": os.fspath(run_prep_dir / "vhfr_low_v2_run.nml"),
        }
        assert run_desc == expected


@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._patch_namelist")
class TestEditNamelists:
    """Unit test for _edit_namelists() function.
    """

    def test_edit_namelists_nowcast(self, m_patch_nml, m_logger, config):
        run_fvcom._edit_namelists(
            "vhfr_low_v2",
            arrow.get("2018-01-15"),
            "nowcast",
            Path("run_prep_dir"),
            config,
        )
        assert m_patch_nml.call_args_list == [
            call(
                Path("run_prep_dir/namelist.case"),
                {
                    "nml_case": {
                        "start_date": "2018-01-15 00:00:00.00",
                        "end_date": "2018-01-16 00:00:00.00",
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.restart"),
                {"nml_restart": {"rst_first_out": "2018-01-16 00:00:00.00"}},
            ),
            call(
                Path("run_prep_dir/namelist.netcdf"),
                {
                    "nml_netcdf": {
                        "nc_first_out": "2018-01-15 01:00:00.00",
                        "nc_output_stack": 24,
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.surface"),
                {"nml_surface_forcing": {"wind_file": "atmos_nowcast_wnd_20180115.nc"}},
            ),
            call(
                Path("run_prep_dir/namelist.nesting"),
                {"nml_nesting": {"nesting_file_name": "bdy_nowcast_btrp_20180115.nc"}},
            ),
        ]

    def test_edit_namelists_forecast(self, m_patch_nml, m_logger, config):
        run_fvcom._edit_namelists(
            "vhfr_low_v2",
            arrow.get("2018-01-15"),
            "forecast",
            Path("run_prep_dir"),
            config,
        )
        assert m_patch_nml.call_args_list == [
            call(
                Path("run_prep_dir/namelist.case"),
                {
                    "nml_case": {
                        "start_date": "2018-01-16 00:00:00.00",
                        "end_date": "2018-01-17 12:00:00.00",
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.restart"),
                {"nml_restart": {"rst_first_out": "2018-01-17 00:00:00.00"}},
            ),
            call(
                Path("run_prep_dir/namelist.netcdf"),
                {
                    "nml_netcdf": {
                        "nc_first_out": "2018-01-16 01:00:00.00",
                        "nc_output_stack": 36,
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.surface"),
                {
                    "nml_surface_forcing": {
                        "wind_file": "atmos_forecast_wnd_20180116.nc"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.nesting"),
                {"nml_nesting": {"nesting_file_name": "bdy_forecast_btrp_20180116.nc"}},
            ),
        ]


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestAssembleNamelist:
    """Unit test for _assemble_namelist() function.
    """

    def test_assemble_namelist(self, m_logger, run_type, config, tmpdir):
        run_prep_dir = Path(str(tmpdir.ensure_dir("fvcom-runs")))
        tmpdir.ensure("fvcom-runs", "namelist.case")
        namelist_path = run_fvcom._assemble_namelist(
            "vhfr_low_v2", run_type, run_prep_dir, config
        )
        assert namelist_path.exists()


@pytest.mark.parametrize(
    "run_type, restart_date", [("nowcast", "17jan18"), ("forecast", "18jan18")]
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestPrepFVCOM_InputDir:
    """Unit test for _prep_fvcom_input_dir() function.
    """

    def test_prep_fvcom_input_dir(self, m_logger, run_type, restart_date, config):
        with patch("nowcast.workers.run_fvcom.Path.symlink_to") as m_link:
            run_fvcom._prep_fvcom_input_dir(arrow.get("2018-01-18"), run_type, config)
        assert m_link.call_args_list == [
            call(Path("VHFR-FVCOM-config/grid/vhfr_low_v2_utm10_grd.dat")),
            call(Path("VHFR-FVCOM-config/grid/vhfr_low_v2_utm10_dep.dat")),
            call(Path("VHFR-FVCOM-config/grid/vhfr_low_v2_sigma.dat")),
            call(Path("VHFR-FVCOM-config/grid/vhfr_low_v2_utm10_cor.dat")),
            call(Path("VHFR-FVCOM-config/grid/vhfr_low_v2_nospg_spg.dat")),
            call(Path("VHFR-FVCOM-config/grid/vhfr_low_v2_obc.dat")),
            call(Path("VHFR-FVCOM-config/output/vhfr_low_v2_utm10_station.dat")),
            call(
                Path(
                    f"SalishSea/fvcom-nowcast/{restart_date}/vhfr_low_v2_restart_0001.nc"
                )
            ),
        ]


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._build_script", return_value="script", autospec=True)
class TestCreateRunScript:
    """Unit tests for _create_run_script() function.
    """

    def test_run_script_path(self, m_bld_script, m_logger, run_type, config, tmpdir):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        run_script_path = run_fvcom._create_run_script(
            arrow.get("2017-12-20"),
            run_type,
            Path(str(tmp_run_dir)),
            Path(f"20dec17fvcom-{run_type}.yaml"),
            config,
        )
        expected = Path(str(tmp_run_dir.join("VHFR_FVCOM.sh")))
        assert run_script_path == expected


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.yaml.load", autospec=True)
class TestBuildScript:
    """Unit tests for _build_script() function.
    """

    def test_script(self, m_yaml_load, run_type, config, tmpdir):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        run_desc_file_path = tmp_run_dir.ensure(f"20dec17fvcom-{run_type}.yaml")
        m_yaml_load.return_value = {"run_id": f"20dec17fvcom-{run_type}"}
        results_dir = tmpdir.ensure_dir(
            config["vhfr fvcom runs"]["run types"][run_type]["results"]
        )
        script = run_fvcom._build_script(
            Path(str(tmp_run_dir)),
            Path(str(run_desc_file_path)),
            Path(str(results_dir)) / "20dec17",
            config,
        )
        expected = """#!/bin/bash

        RUN_ID="20dec17fvcom-{run_type}"
        RUN_DESC="20dec17fvcom-{run_type}.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}"
        MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts.fvcom"
        GATHER="bin/fvc gather"
        
        mkdir -p ${{RESULTS_DIR}}

        cd ${{WORK_DIR}}
        echo "working dir: $(pwd)" >>${{RESULTS_DIR}}/stdout

        echo "Starting run at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{MPIRUN}} -np 32 --bind-to-core ./fvcom \
--casename=vhfr_low_v2 --logfile=./fvcom.log \
>>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr
        echo "Ended run at $(date)" >>${{RESULTS_DIR}}/stdout

        echo "Results gathering started at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{GATHER}} ${{RESULTS_DIR}} --debug >>${{RESULTS_DIR}}/stdout
        echo "Results gathering ended at $(date)" >>${{RESULTS_DIR}}/stdout
        
        chmod g+rwx ${{RESULTS_DIR}}
        chmod g+rw ${{RESULTS_DIR}}/*
        chmod o+rx ${{RESULTS_DIR}}
        chmod o+r ${{RESULTS_DIR}}/*

        echo "Deleting run directory" >>${{RESULTS_DIR}}/stdout
        rmdir $(pwd)
        echo "Finished at $(date)" >>${{RESULTS_DIR}}/stdout
        """.format(
            run_type=run_type,
            tmp_run_dir=tmp_run_dir,
            results_dir=results_dir / "20dec17",
        )
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
class TestDefinitions:
    """Unit tests for _definitions() function.
    """

    def test_definitions(self, run_type, config, tmpdir):
        run_desc_file_path = tmpdir.ensure(f"21dec17fvcom-{run_type}.yaml")
        run_desc = {"run_id": f"21dec17fvcom-{run_type}"}
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        results_dir = tmpdir.ensure_dir(f"SalishSea/fvcom-{run_type}/21dec17/")
        defns = run_fvcom._definitions(
            run_desc,
            Path(str(tmp_run_dir)),
            Path(str(run_desc_file_path)),
            Path(str(results_dir)),
            config,
        )
        expected = """RUN_ID="21dec17fvcom-{run_type}"
        RUN_DESC="21dec17fvcom-{run_type}.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}"
        MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts.fvcom"
        GATHER="bin/fvc gather"
        """.format(
            run_type=run_type, tmp_run_dir=tmp_run_dir, results_dir=results_dir
        )
        defns = defns.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert defns[i].strip() == line.strip()


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
class TestExecute:
    """Unit tests for _execute() function.
    """

    def test_execute(self, run_type, config):
        script = run_fvcom._execute(config)
        expected = """mkdir -p ${RESULTS_DIR}

        cd ${WORK_DIR}
        echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout

        echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout
        ${MPIRUN} -np 32 --bind-to-core ./fvcom \
--casename=vhfr_low_v2 --logfile=./fvcom.log \
>>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr
        echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout

        echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout
        ${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout
        echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout
        """
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom.subprocess.Popen", autospec=True)
@patch("nowcast.workers.run_fvcom.subprocess.run", autospec=True)
class TestLaunchRunScript:
    """Unit tests for _launch_run_script() function.
    """

    def test_launch_run_script(self, m_run, m_popen, m_logger, run_type):
        run_fvcom._launch_run_script(run_type, "VHFR_FVCOM.sh", "west.cloud")
        m_popen.assert_called_once_with(["bash", "VHFR_FVCOM.sh"])

    def test_find_run_process_id(self, m_run, m_popen, m_logger, run_type):
        run_fvcom._launch_run_script(run_type, "VHFR_FVCOM.sh", "west.cloud")
        m_run.assert_called_once_with(
            ["pgrep", "--newest", "--exact", "--full", "bash VHFR_FVCOM.sh"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        )

    def test_run_exec_cmd(self, m_run, m_popen, m_logger, run_type):
        run_exec_cmd = run_fvcom._launch_run_script(
            run_type, "VHFR_FVCOM.sh", "west.cloud"
        )
        assert run_exec_cmd == "bash VHFR_FVCOM.sh"
