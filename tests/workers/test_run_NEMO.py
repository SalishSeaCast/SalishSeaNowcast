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
"""Unit tests for Salish Sea NEMO nowcast run_NEMO worker.
"""
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch, Mock

import arrow
import pytest

from nowcast.workers import run_NEMO


@pytest.fixture
def config(scope="function"):
    return {
        "coordinates": "coordinates_seagrid_SalishSea.nc",
        "run types": {
            "nowcast": {
                "config name": "SalishSea",
                "coordinates": "coordinates_seagrid_SalishSea2.nc",
                "bathymetry": "bathy_downonegrid2.nc",
                "mesh_mask": "mesh_mask_downbyone2.nc",
                "land processor elimination": "bathy_downonegrid2.csv",
                "duration": 1,
                "restart from": "nowcast",
            },
            "nowcast-dev": {
                "config name": "SalishSea",
                "coordinates": "coordinates_seagrid_SalishSea201702.nc",
                "bathymetry": "bathymetry_201702.nc",
                "mesh_mask": "mesh_mask201702.nc",
                "land processor elimination": "bathymetry_201702.csv",
                "duration": 1,
                "restart from": "nowcast-green",
            },
            "nowcast-green": {
                "config name": "SOG",
                "coordinates": "coordinates_seagrid_SalishSea2.nc",
                "bathymetry": "bathy_downonegrid2.nc",
                "mesh_mask": "mesh_mask_downbyone2.nc",
                "land processor elimination": "bathy_downonegrid2.csv",
                "duration": 1,
                "restart from": "nowcast-green",
            },
            "forecast": {
                "config name": "SalishSea",
                "coordinates": "coordinates_seagrid_SalishSea2.nc",
                "bathymetry": "bathy_downonegrid2.nc",
                "mesh_mask": "mesh_mask_downbyone2.nc",
                "land processor elimination": "bathy_downonegrid2.csv",
                "duration": 1.5,
                "restart from": "nowcast",
            },
            "forecast2": {
                "config name": "SalishSea",
                "coordinates": "coordinates_seagrid_SalishSea2.nc",
                "bathymetry": "bathy_downonegrid2.nc",
                "mesh_mask": "mesh_mask_downbyone2.nc",
                "land processor elimination": "bathy_downonegrid2.csv",
                "duration": 1.25,
                "restart from": "forecast",
            },
        },
        "run": {
            "enabled hosts": {
                "arbutus.cloud": {
                    "mpi hosts file": "${HOME}/mpi_hosts",
                    "xios host": "192.168.238.14",
                    "run prep dir": "nowcast-sys/runs/",
                    "grid dir": "nowcast-sys/grid/",
                    "salishsea_cmd": "bin/salishsea",
                    "job exec cmd": "bash",
                    "run types": {
                        "nowcast": {
                            "run sets dir": "SS-run-sets/SalishSea/nemo3.6/nowcast-blue/",
                            "mpi decomposition": "9x19",
                            "results": "results/SalishSea/nowcast",
                        },
                        "forecast": {
                            "run sets dir": "SS-run-sets/SalishSea/nemo3.6/forecast/",
                            "mpi decomposition": "9x19",
                            "results": "results/SalishSea/forecast/",
                        },
                        "forecast2": {
                            "run sets dir": "SS-run-sets/SalishSea/nemo3.6/forecast2/",
                            "mpi decomposition": "9x19",
                            "results": "results/SalishSea/forecast2/",
                        },
                        "nowcast-green": {
                            "run sets dir": "SS-run-sets/SalishSea/nemo3.6/nowcast-green/",
                            "mpi decomposition": "9x19",
                            "results": "results/SalishSea/nowcast-green/",
                        },
                    },
                    "forcing": {
                        "bottom friction mask": "/grid/jetty_mask_bathy201702.nc"
                    },
                },
                "salish-nowcast": {
                    "run prep dir": "nowcast-sys/runs/",
                    "grid dir": "nowcast-sys/grid/",
                    "salishsea_cmd": "bin/salishsea",
                    "job exec cmd": "qsub",
                    "email": "somebody@example.com",
                    "run types": {
                        "nowcast-dev": {
                            "run sets dir": "SS-run-sets/SalishSea/nemo3.6/nowcast-dev/",
                            "mpi decomposition": "1x7",
                            "walltime": "23:30:00",
                            "results": "results/SalishSea/nowcast-dev",
                        },
                        "nowcast-green": {"results": "results/SalishSea/nowcast-dev"},
                    },
                    "forcing": {
                        "bottom friction mask": "/grid/jetty_mask_bathy201702.nc"
                    },
                },
            }
        },
    }


@pytest.fixture
def run_date(scope="module"):
    return arrow.get("2016-01-04")


@pytest.fixture
def tmp_results(tmpdir, run_date, scope="function"):
    """Temporary directory structure that mimics the parts of /results on
    skookum that we need for testing.
    Created anew for each test function/method.
    """
    tmp_results = tmpdir.ensure_dir("results")
    for run_type in ("nowcast", "nowcast-green", "nowcast-dev", "forecast"):
        tmp_results.ensure(
            "SalishSea",
            run_type,
            run_date.shift(days=-1).format("DDMMMYY").lower(),
            "SalishSea_00002160_restart.nc",
        )
    tmp_results.ensure(
        "SalishSea",
        "forecast",
        run_date.shift(days=-2).format("DDMMMYY").lower(),
        "SalishSea_00002160_restart.nc",
    )
    tmp_results.ensure(
        "SalishSea",
        "forecast2",
        run_date.shift(days=-2).format("DDMMMYY").lower(),
        "SalishSea_00002160_restart.nc",
    )
    tmp_results.ensure(
        "SalishSea",
        "nowcast-green",
        run_date.shift(days=-1).format("DDMMMYY").lower(),
        "SalishSea_00002160_restart_trc.nc",
    )
    tmp_run_prep = tmp_results.ensure_dir("nowcast-sys", "runs")
    tmp_run_prep.ensure("namelist.time")
    tmp_namelists = tmp_run_prep.ensure_dir(
        "..", "SS-run-sets", "SalishSea", "nemo3.6", "nowcast"
    )
    namelist_sections = (
        "domain",
        "surface.blue",
        "surface.green",
        "lateral",
        "bottom",
        "tracer",
        "dynamics",
        "vertical",
        "compute",
    )
    for s in namelist_sections:
        tmp_namelists.ensure("namelist.{}".format(s))
    tmp_namelists.ensure("namelist_top_cfg")
    tmp_namelists.ensure("namelist_pisces_cfg")
    tmp_run_prep.ensure_dir("..", "XIOS-2")
    tmp_run_prep.ensure_dir("..", "NEMO-3.6-code", "NEMOGCM", "CONFIG")
    tmp_run_prep.ensure("iodef.xml")
    tmp_run_prep.ensure("..", "SS-run-sets", "SalishSea", "nemo3.6", "domain_def.xml")
    tmp_run_prep.ensure(
        "..", "SS-run-sets", "SalishSea", "nemo3.6", "nowcast", "field_def.xml"
    )
    for dir in ("NEMO-atmos", "rivers"):
        tmp_run_prep.ensure_dir(dir)
    return {
        "run prep dir": tmp_run_prep,
        "results": {
            "nowcast": tmp_results.ensure_dir("SalishSea", "nowcast"),
            "nowcast-dev": tmp_results.ensure_dir("SalishSea", "nowcast-dev"),
            "nowcast-green": tmp_results.ensure_dir("SalishSea", "nowcast-green"),
            "forecast": tmp_results.ensure_dir("SalishSea", "forecast"),
            "forecast2": tmp_results.ensure_dir("SalishSea", "forecast2"),
        },
    }


@patch("nowcast.workers.run_NEMO.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO.main()
        args, kwargs = m_worker.call_args
        assert args == ("run_NEMO",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {
            "nowcast",
            "nowcast-green",
            "nowcast-dev",
            "forecast",
            "forecast2",
        }
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO.main()
        args, kwargs = m_worker().run.call_args
        assert args == (run_NEMO.run_NEMO, run_NEMO.success, run_NEMO.failure)


@pytest.mark.parametrize(
    "run_type", ["nowcast", "nowcast-green", "nowcast-dev", "forecast", "forecast2"]
)
@patch("nowcast.workers.run_NEMO.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2015-12-28"),
        )
        msg_type = run_NEMO.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type", ["nowcast", "nowcast-green", "nowcast-dev", "forecast", "forecast2"]
)
@patch("nowcast.workers.run_NEMO.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2015-12-28"),
        )
        msg_type = run_NEMO.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


class TestCalcNewNamelistLines:
    """Unit tests for _calc_new_namelist_lines() function."""

    @pytest.mark.parametrize(
        "run_type, run_date, run_duration, prev_it000, dt_per_day, "
        "it000, itend, date0, restart, next_restart",
        [
            (
                "nowcast",
                arrow.get("2015-12-30"),
                1,
                1,
                2160,
                2161,
                4320,
                "20151230",
                2160,
                4320,
            ),
            (
                "nowcast-green",
                arrow.get("2015-12-30"),
                1,
                1,
                2160,
                2161,
                4320,
                "20151230",
                2160,
                4320,
            ),
            (
                "forecast",
                arrow.get("2015-12-30"),
                1.25,
                558_001,
                2160,
                560_161,
                562_860,
                "20151231",
                560_160,
                562_320,
            ),
            (
                "forecast2",
                arrow.get("2015-12-30"),
                1.25,
                558_001,
                2160,
                560_161,
                562_860,
                "20160101",
                560_160,
                562_320,
            ),
        ],
    )
    def test_calc_new_namelist_lines(
        self,
        run_date,
        run_type,
        run_duration,
        prev_it000,
        dt_per_day,
        it000,
        itend,
        date0,
        restart,
        next_restart,
    ):
        lines = [
            "  nn_it000 = 1\n",
            "  nn_itend = 2160\n",
            "  nn_date0 = 20160102\n",
            "  nn_stocklist = 2160, 0, 0, 0, 0, 0, 0, 0, 0, 0\n",
        ]
        new_lines, restart_timestep = run_NEMO._calc_new_namelist_lines(
            run_date, run_type, run_duration, prev_it000, dt_per_day, lines
        )
        assert new_lines == [
            "  nn_it000 = {}\n".format(it000),
            "  nn_itend = {}\n".format(itend),
            "  nn_date0 = {}\n".format(date0),
            "  nn_stocklist = {}, 0, 0, 0, 0, 0, 0, 0, 0, 0\n".format(next_restart),
        ]
        assert restart_timestep == restart


class TestGetNamelistValue:
    """Unit tests for _get_namelist_value() function."""

    def test_get_value(self):
        lines = ["  nn_it000 = 8641  ! first time step\n"]
        line_index, value = run_NEMO._get_namelist_value("nn_it000", lines)
        assert line_index == 0
        assert value == str(8641)

    def test_get_last_occurrence(self):
        lines = [
            "  nn_it000 = 8641  ! first time step\n",
            "  nn_it000 = 8642  ! last time step\n",
        ]
        line_index, value = run_NEMO._get_namelist_value("nn_it000", lines)
        assert line_index == 1
        assert value == str(8642)

    def test_handle_empty_line(self):
        lines = ["\n", "  nn_it000 = 8641  ! first time step\n"]
        line_index, value = run_NEMO._get_namelist_value("nn_it000", lines)
        assert line_index == 1
        assert value == str(8641)


class TestRunDescription:
    """Unit tests for _run_description() function."""

    def test_config_missing_results_dir(self, config):
        run_date = arrow.get("2015-12-30")
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type="nowcast")
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        p_config = patch.dict(host_config["run types"], nowcast={})
        with p_config:
            with patch("nowcast.workers.run_NEMO.logger", autospec=True):
                with pytest.raises(run_NEMO.WorkerError):
                    run_NEMO._run_description(
                        run_date, "nowcast", run_id, 2160, "arbutus.cloud", config
                    )

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            ("arbutus.cloud", "nowcast", "SalishSea"),
            ("arbutus.cloud", "nowcast-green", "SOG"),
            ("salish-nowcast", "nowcast-dev", "SalishSea"),
            ("arbutus.cloud", "forecast", "SalishSea"),
            ("arbutus.cloud", "forecast2", "SalishSea"),
        ],
    )
    def test_config_name(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["config_name"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            ("arbutus.cloud", "nowcast", "04jan16nowcast"),
            ("arbutus.cloud", "nowcast-green", "04jan16nowcast-green"),
            ("salish-nowcast", "nowcast-dev", "04jan16nowcast-dev"),
            ("arbutus.cloud", "forecast", "04jan16forecast"),
            ("arbutus.cloud", "forecast2", "04jan16forecast2"),
        ],
    )
    def test_run_id(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["run_id"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            ("arbutus.cloud", "nowcast", "9x19"),
            ("arbutus.cloud", "nowcast-green", "9x19"),
            ("salish-nowcast", "nowcast-dev", "1x7"),
            ("arbutus.cloud", "forecast", "9x19"),
            ("arbutus.cloud", "forecast2", "9x19"),
        ],
    )
    def test_mpi_decomposition(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["MPI decomposition"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            ("arbutus.cloud", "nowcast", None),
            ("arbutus.cloud", "nowcast-green", None),
            ("salish-nowcast", "nowcast-dev", "23:30:00"),
            ("arbutus.cloud", "forecast", None),
            ("arbutus.cloud", "forecast2", None),
        ],
    )
    def test_walltime(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["walltime"] == expected

    @pytest.mark.parametrize(
        "run_type, path, expected",
        [
            ("nowcast", "NEMO code config", "NEMO-3.6-code/NEMOGCM/CONFIG"),
            ("nowcast-green", "XIOS", "XIOS-2"),
        ],
    )
    def test_paths(
        self, run_type, path, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, "arbutus.cloud", config
            )
        assert run_desc["paths"][path] == tmp_run_prep.join("..", expected)
        assert run_desc["paths"]["forcing"] == tmp_run_prep

    @pytest.mark.parametrize(
        "host_name, run_type, path",
        [
            ("arbutus.cloud", "nowcast", "runs directory"),
            ("arbutus.cloud", "nowcast-green", "runs directory"),
            ("salish-nowcast", "nowcast-dev", "runs directory"),
            ("arbutus.cloud", "forecast", "runs directory"),
            ("arbutus.cloud", "forecast2", "runs directory"),
        ],
    )
    def test_runs_dir_path(
        self, host_name, run_type, path, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["paths"][path] == tmp_run_prep

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            (
                "arbutus.cloud",
                "nowcast",
                "nowcast-sys/grid/coordinates_seagrid_SalishSea2.nc",
            ),
            (
                "arbutus.cloud",
                "nowcast-green",
                "nowcast-sys/grid/coordinates_seagrid_SalishSea2.nc",
            ),
            (
                "salish-nowcast",
                "nowcast-dev",
                "nowcast-sys/grid/coordinates_seagrid_SalishSea201702.nc",
            ),
            (
                "arbutus.cloud",
                "forecast",
                "nowcast-sys/grid/coordinates_seagrid_SalishSea2.nc",
            ),
            (
                "arbutus.cloud",
                "forecast2",
                "nowcast-sys/grid/coordinates_seagrid_SalishSea2.nc",
            ),
        ],
    )
    def test_grid_coordinates(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["grid"]["coordinates"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            ("arbutus.cloud", "nowcast", "nowcast-sys/grid/bathy_downonegrid2.nc"),
            (
                "arbutus.cloud",
                "nowcast-green",
                "nowcast-sys/grid/bathy_downonegrid2.nc",
            ),
            ("salish-nowcast", "nowcast-dev", "nowcast-sys/grid/bathymetry_201702.nc"),
            ("arbutus.cloud", "forecast", "nowcast-sys/grid/bathy_downonegrid2.nc"),
            ("arbutus.cloud", "forecast2", "nowcast-sys/grid/bathy_downonegrid2.nc"),
        ],
    )
    def test_grid_bathymetry(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["grid"]["bathymetry"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, expected",
        [
            ("arbutus.cloud", "nowcast", "nowcast-sys/grid/bathy_downonegrid2.csv"),
            (
                "arbutus.cloud",
                "nowcast-green",
                "nowcast-sys/grid/bathy_downonegrid2.csv",
            ),
            ("salish-nowcast", "nowcast-dev", False),
        ],
    )
    def test_grid_land_processor_elimination(
        self, host_name, run_type, expected, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        assert run_desc["grid"]["land processor elimination"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, link_name, expected",
        [
            ("arbutus.cloud", "nowcast", "NEMO-atmos", "NEMO-atmos"),
            ("arbutus.cloud", "nowcast", "ssh", "ssh"),
            ("arbutus.cloud", "nowcast", "tides", "tides"),
            ("arbutus.cloud", "nowcast", "tracers", "tracers"),
            ("arbutus.cloud", "nowcast", "LiveOcean", "LiveOcean"),
            ("arbutus.cloud", "nowcast", "rivers", "rivers"),
            ("arbutus.cloud", "nowcast", "grid", "grid"),
            ("arbutus.cloud", "nowcast", "rivers-climatology", "rivers-climatology"),
            ("arbutus.cloud", "nowcast-green", "NEMO-atmos", "NEMO-atmos"),
            ("arbutus.cloud", "nowcast-green", "ssh", "ssh"),
            ("arbutus.cloud", "nowcast-green", "tides", "tides"),
            ("arbutus.cloud", "nowcast-green", "tracers", "tracers"),
            ("arbutus.cloud", "nowcast-green", "LiveOcean", "LiveOcean"),
            ("arbutus.cloud", "nowcast-green", "rivers", "rivers"),
            ("arbutus.cloud", "nowcast-green", "grid", "grid"),
            (
                "arbutus.cloud",
                "nowcast-green",
                "rivers-climatology",
                "rivers-climatology",
            ),
            ("salish-nowcast", "nowcast-dev", "NEMO-atmos", "NEMO-atmos"),
            ("salish-nowcast", "nowcast-dev", "ssh", "ssh"),
            ("salish-nowcast", "nowcast-dev", "tides", "tides"),
            ("salish-nowcast", "nowcast-dev", "tracers", "tracers"),
            ("salish-nowcast", "nowcast-dev", "LiveOcean", "LiveOcean"),
            ("salish-nowcast", "nowcast-dev", "rivers", "rivers"),
            ("salish-nowcast", "nowcast-dev", "grid", "grid"),
            (
                "salish-nowcast",
                "nowcast-dev",
                "rivers-climatology",
                "rivers-climatology",
            ),
            ("arbutus.cloud", "forecast", "NEMO-atmos", "NEMO-atmos"),
            ("arbutus.cloud", "forecast", "ssh", "ssh"),
            ("arbutus.cloud", "forecast", "tides", "tides"),
            ("arbutus.cloud", "forecast", "tracers", "tracers"),
            ("arbutus.cloud", "forecast", "LiveOcean", "LiveOcean"),
            ("arbutus.cloud", "forecast", "rivers", "rivers"),
            ("arbutus.cloud", "forecast", "grid", "grid"),
            ("arbutus.cloud", "forecast", "rivers-climatology", "rivers-climatology"),
            ("arbutus.cloud", "forecast2", "NEMO-atmos", "NEMO-atmos"),
            ("arbutus.cloud", "forecast2", "ssh", "ssh"),
            ("arbutus.cloud", "forecast2", "tides", "tides"),
            ("arbutus.cloud", "forecast2", "tracers", "tracers"),
            ("arbutus.cloud", "forecast2", "LiveOcean", "LiveOcean"),
            ("arbutus.cloud", "forecast2", "rivers", "rivers"),
            ("arbutus.cloud", "forecast2", "grid", "grid"),
            ("arbutus.cloud", "forecast2", "rivers-climatology", "rivers-climatology"),
        ],
    )
    def test_forcing_links(
        self,
        host_name,
        run_type,
        link_name,
        expected,
        config,
        run_date,
        tmp_results,
        tmpdir,
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        expected = tmp_run_prep.join(expected)
        assert run_desc["forcing"][link_name]["link to"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type",
        [
            ("arbutus.cloud", "nowcast"),
            ("arbutus.cloud", "forecast"),
            ("arbutus.cloud", "nowcast-green"),
            ("salish-nowcast", "nowcast-dev"),
            ("arbutus.cloud", "forecast2"),
        ],
    )
    def test_bottom_friction_mask_link(
        self, host_name, run_type, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        expected = "/grid/jetty_mask_bathy201702.nc"
        assert run_desc["forcing"]["bfr_coef.nc"]["link to"] == expected

    @pytest.mark.parametrize(
        "host_name, run_type, link_name, expected",
        [
            (
                "arbutus.cloud",
                "nowcast",
                "restart.nc",
                "03jan16/SalishSea_00002160_restart.nc",
            ),
            (
                "arbutus.cloud",
                "nowcast-green",
                "restart_trc.nc",
                "03jan16/SalishSea_00002160_restart_trc.nc",
            ),
        ],
    )
    def test_restart_links(
        self,
        host_name,
        run_type,
        link_name,
        expected,
        config,
        run_date,
        tmp_results,
        tmpdir,
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}{run_type}".format(dmy=dmy, run_type=run_type)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        p_config_run_prep = patch.dict(
            host_config, {"run prep dir": str(tmp_results["run prep dir"])}
        )
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        tmp_results_dir = tmp_results["results"][run_type]
        expected = tmp_results_dir.join(expected)
        assert run_desc["restart"][link_name] == expected

    @pytest.mark.parametrize(
        "host_name, run_type",
        [
            ("arbutus.cloud", "nowcast"),
            ("arbutus.cloud", "nowcast-green"),
            ("salish-nowcast", "nowcast-dev"),
            ("arbutus.cloud", "forecast"),
            ("arbutus.cloud", "forecast2"),
        ],
    )
    def test_namelists(
        self, host_name, run_type, config, run_date, tmp_results, tmpdir
    ):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}nowcast".format(dmy=dmy)
        host_config = config["run"]["enabled hosts"][host_name]
        p_config_results = patch.dict(
            host_config["run types"][run_type],
            results=str(tmp_results["results"][run_type]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        run_type_config = config["run"]["enabled hosts"][host_name]["run types"][
            run_type
        ]
        tmp_run_sets = tmpdir.ensure_dir(run_type_config["run sets dir"])
        p_config_run_sets_dir = patch.dict(
            run_type_config, {"run sets dir": str(tmp_run_sets)}
        )
        with p_config_results, p_config_run_prep, p_config_run_sets_dir:
            run_desc = run_NEMO._run_description(
                run_date, run_type, run_id, 2160, host_name, config
            )
        expected = [
            str(tmp_run_prep.join("namelist.time")),
            str(tmp_run_sets.join("namelist.domain")),
            str(tmp_run_sets.join("namelist.atmos_rivers")),
            str(tmp_run_sets.join("namelist.light")),
            str(tmp_run_sets.join("namelist.lateral")),
            str(tmp_run_sets.join("namelist.bottom")),
            str(tmp_run_sets.join("namelist.tracer")),
            str(tmp_run_sets.join("namelist.dynamics")),
            str(tmp_run_sets.join("namelist.vertical")),
            str(tmp_run_sets.join("namelist.compute")),
        ]
        assert run_desc["namelists"]["namelist_cfg"] == expected

    def test_namelists_nowcast_green(self, config, run_date, tmp_results, tmpdir):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}nowcast".format(dmy=dmy)
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        p_config_results = patch.dict(
            host_config["run types"]["nowcast-green"],
            results=str(tmp_results["results"]["nowcast-green"]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        run_type_config = config["run"]["enabled hosts"]["arbutus.cloud"]["run types"][
            "nowcast-green"
        ]
        tmp_run_sets = tmpdir.ensure_dir(run_type_config["run sets dir"])
        p_config_run_sets_dir = patch.dict(
            run_type_config, {"run sets dir": str(tmp_run_sets)}
        )
        with p_config_results, p_config_run_prep, p_config_run_sets_dir:
            run_desc = run_NEMO._run_description(
                run_date, "nowcast-green", run_id, 2160, "arbutus.cloud", config
            )
        expected = [
            str(tmp_run_sets.join("namelist_top_restart")),
            str(tmp_run_sets.join("namelist_top_TracerDefAndBdy")),
            str(tmp_run_sets.join("namelist_top_physics")),
        ]
        assert run_desc["namelists"]["namelist_top_cfg"] == expected
        expected = [
            str(tmp_run_sets.join("namelist_smelt_biology")),
            str(tmp_run_sets.join("namelist_smelt_rivers")),
            str(tmp_run_sets.join("namelist_smelt_skog")),
        ]
        assert run_desc["namelists"]["namelist_smelt_cfg"] == expected

    def test_output_nowcast(self, config, run_date, tmpdir, tmp_results):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}nowcast".format(dmy=dmy)
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        p_config_results = patch.dict(
            host_config["run types"]["nowcast"],
            results=str(tmp_results["results"]["nowcast"]),
        )
        run_type_config = host_config["run types"]["nowcast"]
        tmp_run_sets = tmpdir.ensure_dir(run_type_config["run sets dir"])
        p_config_run_sets_dir = patch.dict(
            run_type_config, {"run sets dir": str(tmp_run_sets)}
        )
        with p_config_results, p_config_run_sets_dir:
            run_desc = run_NEMO._run_description(
                run_date, "nowcast", run_id, 2160, "arbutus.cloud", config
            )
        assert run_desc["output"]["iodefs"] == tmp_run_sets.join("iodef.xml")
        assert run_desc["output"]["domaindefs"] == tmp_run_sets.join("domain_def.xml")
        assert run_desc["output"]["fielddefs"] == tmp_run_sets.join("field_def.xml")
        assert run_desc["output"]["separate XIOS server"]
        assert run_desc["output"]["XIOS servers"] == 1
        assert "domain" not in run_desc["output"]
        assert "fields" not in run_desc["output"]

    def test_output_nowcast_xios2(self, config, run_date, tmpdir, tmp_results):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}nowcast".format(dmy=dmy)
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        p_config_results = patch.dict(
            host_config["run types"]["nowcast"],
            results=str(tmp_results["results"]["nowcast"]),
        )
        run_type_config = host_config["run types"]["nowcast"]
        tmp_run_sets = tmpdir.ensure_dir(run_type_config["run sets dir"])
        tmp_run_sets.ensure("file_def.xml")
        p_config_run_sets_dir = patch.dict(
            run_type_config, {"run sets dir": str(tmp_run_sets)}
        )
        with p_config_results, p_config_run_sets_dir:
            run_desc = run_NEMO._run_description(
                run_date, "nowcast", run_id, 2160, "arbutus.cloud", config
            )
        assert run_desc["output"]["filedefs"] == str(tmp_run_sets.join("file_def.xml"))

    def test_vc_revisions(self, config, run_date, tmpdir, tmp_results):
        dmy = run_date.format("DDMMMYY").lower()
        run_id = "{dmy}nowcast".format(dmy=dmy)
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        p_config_results = patch.dict(
            host_config["run types"]["nowcast"],
            results=str(tmp_results["results"]["nowcast"]),
        )
        tmp_run_prep = tmp_results["run prep dir"]
        p_config_run_prep = patch.dict(host_config, {"run prep dir": str(tmp_run_prep)})
        with p_config_results, p_config_run_prep:
            run_desc = run_NEMO._run_description(
                run_date, "nowcast", run_id, 2160, "arbutus.cloud", config
            )
        assert run_desc["vcs revisions"]["git"] == [
            str(tmp_run_prep.join("..", "grid")),
            str(tmp_run_prep.join("..", "moad_tools")),
            str(tmp_run_prep.join("..", "NEMO-Cmd")),
            str(tmp_run_prep.join("..", "NEMO_Nowcast")),
            str(tmp_run_prep.join("..", "rivers-climatology")),
            str(tmp_run_prep.join("..", "SalishSeaCmd")),
            str(tmp_run_prep.join("..", "SalishSeaNowcast")),
            str(tmp_run_prep.join("..", "SS-run-sets")),
            str(tmp_run_prep.join("..", "tides")),
            str(tmp_run_prep.join("..", "tools")),
            str(tmp_run_prep.join("..", "tracers")),
            str(tmp_run_prep.join("..", "XIOS-ARCH")),
        ]


class TestCreateRunScript:
    """Unit test for _create_run_script() function."""

    @pytest.mark.parametrize(
        "run_type", ["nowcast", "nowcast-green", "forecast", "forecast2"]
    )
    @patch("nowcast.workers.run_NEMO._build_script", return_value="")
    def test_run_script_filepath(self, m_built_script, run_type, config, tmpdir):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        run_script_filepath = run_NEMO._create_run_script(
            arrow.get("2016-12-03"),
            run_type,
            Path(str(tmp_run_dir)),
            "30nov16.yaml",
            "arbutus.cloud",
            config,
        )
        expected = Path(str(tmp_run_dir.join("SalishSeaNEMO.sh")))
        assert run_script_filepath == expected


class TestBuildScript:
    """Unit test for _build_script function."""

    @pytest.mark.parametrize(
        "run_type", ["nowcast", "nowcast-green", "forecast", "forecast2"]
    )
    @patch("nowcast.workers.run_NEMO.nemo_cmd.prepare.load_run_desc")
    @patch(
        "nowcast.workers.run_NEMO.nemo_cmd.prepare.get_n_processors", return_value=119
    )
    def test_script_west_cloud(self, m_gnp, m_lrd, run_type, config, tmpdir):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        run_desc_file = tmpdir.ensure("13may17.yaml")
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        results_dir = tmpdir.ensure_dir(host_config["run types"][run_type]["results"])
        p_config = patch.dict(config, [("results archive", str(results_dir))])
        m_lrd.return_value = {
            "run_id": "13may17nowcast",
            "MPI decomposition": "11x18",
            "output": {"XIOS servers": 1},
        }
        with p_config:
            script = run_NEMO._build_script(
                Path(str(tmp_run_dir)),
                run_type,
                Path(str(run_desc_file)),
                Path(str(results_dir)) / "13may17",
                "arbutus.cloud",
                config,
            )
        expected = """#!/bin/bash

        RUN_ID="13may17nowcast"
        RUN_DESC="13may17.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}"
        MPIRUN="mpirun --mca btl ^openib --mca orte_tmpdir_base /dev/shm --hostfile ${{HOME}}/mpi_hosts"
        COMBINE="bin/salishsea combine"
        GATHER="bin/salishsea gather"

        mkdir -p ${{RESULTS_DIR}}

        cd ${{WORK_DIR}}
        echo "working dir: $(pwd)" >>${{RESULTS_DIR}}/stdout

        echo "Starting run at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{MPIRUN}} -np 119 --bind-to none ./nemo.exe : \
-host 192.168.238.14 -np 1 --bind-to none ./xios_server.exe \
>>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr
        echo "Ended run at $(date)" >>${{RESULTS_DIR}}/stdout

        echo "Results combining started at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{COMBINE}} ${{RUN_DESC}} --debug \
>>${{RESULTS_DIR}}/stdout
        echo "Results combining ended at $(date)" >>${{RESULTS_DIR}}/stdout

        echo "Results gathering started at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{GATHER}} ${{RESULTS_DIR}} --debug \
>>${{RESULTS_DIR}}/stdout
        echo "Results gathering ended at $(date)" >>${{RESULTS_DIR}}/stdout
        
        chmod g+rwx ${{RESULTS_DIR}}
        chmod g+rw ${{RESULTS_DIR}}/*
        chmod o+rx ${{RESULTS_DIR}}
        chmod o+r ${{RESULTS_DIR}}/*

        echo "Deleting run directory" >>${{RESULTS_DIR}}/stdout
        rmdir $(pwd)
        echo "Finished at $(date)" >>${{RESULTS_DIR}}/stdout
        """.format(
            tmp_run_dir=tmp_run_dir, results_dir=Path(str(results_dir)) / "13may17"
        )
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()

    @patch("nowcast.workers.run_NEMO.nemo_cmd.prepare.load_run_desc")
    @patch("nowcast.workers.run_NEMO.nemo_cmd.prepare.get_n_processors", return_value=7)
    def test_script_salish(self, m_gnp, m_lrd, config, tmpdir):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        run_desc_file = tmpdir.ensure("13may17.yaml")
        host_config = config["run"]["enabled hosts"]["salish-nowcast"]
        results_dir = tmpdir.ensure_dir(
            host_config["run types"]["nowcast-dev"]["results"]
        )
        p_config = patch.dict(config, [("results archive", str(results_dir))])
        m_lrd.return_value = {
            "run_id": "13may17nowcast",
            "MPI decomposition": "1x7",
            "walltime": "23:30:00",
            "output": {"XIOS servers": 1},
        }
        with p_config:
            script = run_NEMO._build_script(
                Path(str(tmp_run_dir)),
                "nowcast-dev",
                Path(str(run_desc_file)),
                Path(str(results_dir)) / "13may17",
                "salish-nowcast",
                config,
            )
        expected = f"""#!/bin/bash
        
        #PBS -N 13may17nowcast
        #PBS -S /bin/bash
        #PBS -l walltime=23:30:00
        # email when the job [b]egins and [e]nds, or is [a]borted
        #PBS -m bea
        #PBS -M somebody@example.com
        #PBS -l procs=8
        # memory per processor
        #PBS -l pmem=2000mb

        RUN_ID="13may17nowcast"
        RUN_DESC="13may17.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}/13may17"
        MPIRUN="mpirun"
        COMBINE="bin/salishsea combine"
        GATHER="bin/salishsea gather"

        mkdir -p ${{RESULTS_DIR}}

        cd ${{WORK_DIR}}
        echo "working dir: $(pwd)" >>${{RESULTS_DIR}}/stdout

        echo "Starting run at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{MPIRUN}} -np 7 --bind-to core ./nemo.exe : \
-np 1 --bind-to core ./xios_server.exe \
>>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr
        echo "Ended run at $(date)" >>${{RESULTS_DIR}}/stdout

        echo "Results combining started at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{COMBINE}} ${{RUN_DESC}} --debug \
>>${{RESULTS_DIR}}/stdout
        echo "Results combining ended at $(date)" >>${{RESULTS_DIR}}/stdout

        echo "Results gathering started at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{GATHER}} ${{RESULTS_DIR}} --debug \
>>${{RESULTS_DIR}}/stdout
        echo "Results gathering ended at $(date)" >>${{RESULTS_DIR}}/stdout
        
        chmod g+rwx ${{RESULTS_DIR}}
        chmod g+rw ${{RESULTS_DIR}}/*
        chmod o+rx ${{RESULTS_DIR}}
        chmod o+r ${{RESULTS_DIR}}/*

        echo "Deleting run directory" >>${{RESULTS_DIR}}/stdout
        rmdir $(pwd)
        echo "Finished at $(date)" >>${{RESULTS_DIR}}/stdout
        """

        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()


class TestDefinitions:
    """Unit test for _definitions() function."""

    @pytest.mark.parametrize(
        "run_type", ["nowcast", "nowcast-green", "forecast", "forecast2"]
    )
    def test_definitions(self, run_type, config):
        run_desc = {"run_id": "03dec16nowcast"}
        run_desc_filepath = Mock()
        run_desc_filepath.name = "03dec16.yaml"
        run_dir = "tmp_run_dir"
        results_dir = "results_dir"
        defns = run_NEMO._definitions(
            run_type,
            run_desc,
            run_desc_filepath,
            run_dir,
            results_dir,
            "salish-nowcast",
            config,
        )
        expected = """RUN_ID="03dec16nowcast"
        RUN_DESC="03dec16.yaml"
        WORK_DIR="tmp_run_dir"
        RESULTS_DIR="results_dir"
        MPIRUN="mpirun"
        COMBINE="bin/salishsea combine"
        GATHER="bin/salishsea gather"
        """
        defns = defns.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert defns[i].strip() == line.strip()

    @pytest.mark.parametrize(
        "run_type", ["nowcast", "nowcast-green", "forecast", "forecast2"]
    )
    def test_definitions_with_mpi_hosts_file(self, run_type, config):
        run_desc = {"run_id": "03dec16nowcast"}
        run_desc_filepath = Mock()
        run_desc_filepath.name = "03dec16.yaml"
        run_dir = "tmp_run_dir"
        results_dir = "results_dir"
        defns = run_NEMO._definitions(
            run_type,
            run_desc,
            run_desc_filepath,
            run_dir,
            results_dir,
            "arbutus.cloud",
            config,
        )
        expected = """RUN_ID="03dec16nowcast"
        RUN_DESC="03dec16.yaml"
        WORK_DIR="tmp_run_dir"
        RESULTS_DIR="results_dir"
        MPIRUN="mpirun --mca btl ^openib --mca orte_tmpdir_base /dev/shm --hostfile ${HOME}/mpi_hosts"
        COMBINE="bin/salishsea combine"
        GATHER="bin/salishsea gather"
        """
        defns = defns.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert defns[i].strip() == line.strip()


class TestExecute:
    """Unit test for _execute() function."""

    def test_execute(self, config):
        script = run_NEMO._execute(
            nemo_processors=15, xios_processors=1, xios_host=None
        )
        expected = """mkdir -p ${RESULTS_DIR}

        cd ${WORK_DIR}
        echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout

        echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout
        ${MPIRUN} -np 15 --bind-to core ./nemo.exe : \
-np 1 --bind-to core ./xios_server.exe \
>>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr
        echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout

        echo "Results combining started at $(date)" >>${RESULTS_DIR}/stdout
        ${COMBINE} ${RUN_DESC} --debug >>${RESULTS_DIR}/stdout
        echo "Results combining ended at $(date)" >>${RESULTS_DIR}/stdout

        echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout
        ${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout
        echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout
        """
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()

    def test_execute_with_xios_host(self, config):
        script = run_NEMO._execute(
            nemo_processors=15, xios_processors=1, xios_host="192.168.1.79"
        )
        expected = """mkdir -p ${RESULTS_DIR}

        cd ${WORK_DIR}
        echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout

        echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout
        ${MPIRUN} -np 15 --bind-to none ./nemo.exe : \
-host 192.168.1.79 -np 1 --bind-to none ./xios_server.exe \
>>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr
        echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout

        echo "Results combining started at $(date)" >>${RESULTS_DIR}/stdout
        ${COMBINE} ${RUN_DESC} --debug >>${RESULTS_DIR}/stdout
        echo "Results combining ended at $(date)" >>${RESULTS_DIR}/stdout

        echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout
        ${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout
        echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout
        """
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()


@patch("nowcast.workers.run_NEMO.logger", autospec=True)
@patch("nowcast.workers.run_NEMO.subprocess.Popen", autospec=True)
@patch("nowcast.workers.run_NEMO.subprocess.run", autospec=True)
class TestLaunchRun:
    """Unit tests for _launch_run() function."""

    @pytest.mark.parametrize(
        "run_type, host",
        [
            ("nowcast", "arbutus.cloud"),
            ("nowcast-green", "arbutus.cloud"),
            ("forecast", "arbutus.cloud"),
            ("forecast2", "arbutus.cloud"),
        ],
    )
    def test_bash_launch_run_script(
        self, m_run, m_popen, m_logger, run_type, host, config
    ):
        run_NEMO._launch_run_script(run_type, "SalishSeaNEMO.sh", host, config)
        m_popen.assert_called_once_with(["bash", "SalishSeaNEMO.sh"])

    @pytest.mark.parametrize("run_type, host", [("nowcast-dev", "salish-nowcast")])
    def test_qsub_launch_run_script(
        self, m_run, m_popen, m_logger, run_type, host, config
    ):
        run_NEMO._launch_run_script(run_type, "SalishSeaNEMO.sh", host, config)
        assert m_run.call_args_list[0] == call(
            ["qsub", "SalishSeaNEMO.sh"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        )

    @pytest.mark.parametrize(
        "run_type, host",
        [
            ("nowcast", "arbutus.cloud"),
            ("nowcast-green", "arbutus.cloud"),
            ("forecast", "arbutus.cloud"),
            ("forecast2", "arbutus.cloud"),
        ],
    )
    def test_find_bash_run_process_pid(
        self, m_run, m_popen, m_logger, run_type, host, config
    ):
        run_NEMO._launch_run_script(run_type, "SalishSeaNEMO.sh", host, config)
        m_run.assert_called_once_with(
            ["pgrep", "--newest", "--exact", "--full", "bash SalishSeaNEMO.sh"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        )

    @pytest.mark.parametrize("run_type, host", [("nowcast-dev", "salish-nowcast")])
    def test_find_qsub_run_process_pid(
        self, m_run, m_popen, m_logger, run_type, host, config
    ):
        m_run.side_effect = [
            SimpleNamespace(stdout="4343.master"),
            SimpleNamespace(stdout="4444"),
        ]
        run_NEMO._launch_run_script(run_type, "SalishSeaNEMO.sh", host, config)
        assert m_run.call_args_list[1] == call(
            ["pgrep", "4343.master"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        )

    @pytest.mark.parametrize(
        "run_type, host",
        [
            ("nowcast", "arbutus.cloud"),
            ("nowcast-green", "arbutus.cloud"),
            ("forecast", "arbutus.cloud"),
            ("forecast2", "arbutus.cloud"),
        ],
    )
    def test_bash_run(self, m_run, m_popen, m_logger, run_type, host, config):
        m_run.return_value = SimpleNamespace(stdout="4444")
        run_exec_cmd, run_id = run_NEMO._launch_run_script(
            run_type, "SalishSeaNEMO.sh", host, config
        )
        assert run_exec_cmd == "bash SalishSeaNEMO.sh"
        assert run_id is None

    @pytest.mark.parametrize("run_type, host", [("nowcast-dev", "salish-nowcast")])
    def test_qsub_run(self, m_run, m_popen, m_logger, run_type, host, config):
        m_run.side_effect = [
            SimpleNamespace(stdout="4343.master"),
            SimpleNamespace(stdout="4444"),
        ]
        run_exec_cmd, run_id = run_NEMO._launch_run_script(
            run_type, "SalishSeaNEMO.sh", host, config
        )
        assert run_exec_cmd == "qsub SalishSeaNEMO.sh"
        assert run_id == "4343.master"
