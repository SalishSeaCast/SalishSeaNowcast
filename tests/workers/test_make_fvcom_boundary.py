# Copyright 2013-2018 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for Vancouver Harbour & Fraser River FVCOM make_fvcom_boundary
worker.
"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_fvcom_boundary


@patch(
    "nowcast.workers.make_fvcom_boundary.NowcastWorker", spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_fvcom_boundary",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        make_fvcom_boundary.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_boundary.make_fvcom_boundary,
            make_fvcom_boundary.success,
            make_fvcom_boundary.failure,
        )


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.make_fvcom_boundary.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        make_fvcom_boundary.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        msg_type = make_fvcom_boundary.success(parsed_args)
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.make_fvcom_boundary.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        make_fvcom_boundary.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-11-29")
        )
        msg_type = make_fvcom_boundary.failure(parsed_args)
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_fvcom_boundary.logger", autospec=True)
@patch(
    "nowcast.workers.make_fvcom_boundary.OPPTools.nesting.read_metrics",
    return_value=tuple(
        "x y z tri nsiglev siglev nsiglay siglay nemo_lon nemo_lat "
        "e1t e2t e3u_0 e3v_0 gdept_0 gdepw_0 gdepu gdepv "
        "tmask umask vmask gdept_1d nemo_h".split()
    ),
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_boundary.OPPTools.nesting.read_nesting",
    return_value=tuple("inest xb yb".split()),
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_boundary.OPPTools.nesting.make_type3_nesting_file2",
    autospec=True,
)
class TestMakeFVCOMBoundary:
    """Unit tests for make_fvcom_boundary() function.
    """

    config = {
        "vhfr fvcom runs": {
            "run prep dir": "fvcom-runs/",
            "fvcom grid": {
                "grid dir": "VHFR-FVCOM-config/grid/",
                "grid file": "vhfr_low_v2_utm10_grd.dat",
                "utm zone": 10,
                "depths file": "vhfr_low_v2_utm10_dep.dat",
                "sigma file": "vhfr_low_v2_sigma.dat",
            },
            "nemo coupling": {
                "coupling dir": "VHFR-FVCOM-config/coupling_nemo_cut/",
                "fvcom nest indices file": "vhfr_low_v2_nesting_indices.txt",
                "fvcom nest ref line file": "vhfr_low_v2_nesting_innerboundary.txt",
                "nemo cut i range": [225, 369],
                "nemo cut j range": [340, 561],
                "transition zone width": 8500,
                "tanh dl": 2,
                "tanh du": 2,
                "nemo coordinates": "grid/coordinates_seagrid_SalishSea201702.nc",
                "nemo mesh mask": "grid/mesh_mask201702.nc",
                "nemo bathymetry": "grid/bathymetry_201702.nc",
                "boundary file template": "bdy_{run_type}_btrp_{yyyymmdd}.nc",
            },
            "input dir": "fvcom-runs/input",
            "run types": {
                "nowcast": {"nemo boundary results": "SalishSea/nowcast/"},
                "forecast": {"nemo boundary results": "SalishSea/forecast/"},
            },
        }
    }

    @pytest.mark.parametrize(
        "run_type, file_date", [("nowcast", "20180108"), ("forecast", "20180109")]
    )
    def test_checklist(
        self,
        m_mk_nest_file2,
        m_read_nesting,
        m_read_metrics,
        m_logger,
        run_type,
        file_date,
    ):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-01-08")
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            checklist = make_fvcom_boundary.make_fvcom_boundary(
                parsed_args, self.config
            )
        input_dir = Path(self.config["vhfr fvcom runs"]["input dir"])
        expected = {
            run_type: {
                "run date": "2018-01-08",
                "open boundary file": os.fspath(
                    input_dir / f"bdy_{run_type}_btrp_{file_date}.nc"
                ),
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
    def test_nesting_read_metrics(
        self, m_mk_nest_file2, m_read_nesting, m_read_metrics, m_logger, run_type
    ):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-01-08")
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            make_fvcom_boundary.make_fvcom_boundary(parsed_args, self.config)
        coupling_dir = Path(
            self.config["vhfr fvcom runs"]["nemo coupling"]["coupling dir"]
        )
        grid_dir = Path(self.config["vhfr fvcom runs"]["fvcom grid"]["grid dir"])
        m_read_metrics.assert_called_once_with(
            fgrd=os.fspath(grid_dir / "vhfr_low_v2_utm10_grd.dat"),
            fbathy=os.fspath(grid_dir / "vhfr_low_v2_utm10_dep.dat"),
            fsigma=os.fspath(grid_dir / "vhfr_low_v2_sigma.dat"),
            fnemocoord="grid/coordinates_seagrid_SalishSea201702.nc",
            fnemomask="grid/mesh_mask201702.nc",
            fnemobathy="grid/bathymetry_201702.nc",
            nemo_cut_i=[225, 369],
            nemo_cut_j=[340, 561],
        )

    @pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
    def test_nesting_read_nesting(
        self, m_mk_nest_file2, m_read_nesting, m_read_metrics, m_logger, run_type
    ):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-25")
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            make_fvcom_boundary.make_fvcom_boundary(parsed_args, self.config)
        coupling_dir = Path(
            self.config["vhfr fvcom runs"]["nemo coupling"]["coupling dir"]
        )
        m_read_nesting.assert_called_once_with(
            fnest=os.fspath(coupling_dir / "vhfr_low_v2_nesting_indices.txt"),
            frefline=os.fspath(coupling_dir / "vhfr_low_v2_nesting_innerboundary.txt"),
        )

    @pytest.mark.parametrize(
        "run_type, time_start, time_end, nemo_file_list",
        [
            (
                "nowcast",
                "2018-01-08 00:00:00",
                "2018-01-09 00:00:00",
                [
                    "SalishSea/nowcast/07jan18/FVCOM_T.nc",
                    "SalishSea/nowcast/08jan18/FVCOM_T.nc",
                ],
            ),
            (
                "forecast",
                "2018-01-09 00:00:00",
                "2018-01-10 12:00:00",
                [
                    "SalishSea/nowcast/07jan18/FVCOM_T.nc",
                    "SalishSea/nowcast/08jan18/FVCOM_T.nc",
                    "SalishSea/forecast/08jan18/FVCOM_T.nc",
                ],
            ),
        ],
    )
    def test_nesting_make_type3_nesting_file2(
        self,
        m_mk_nest_file2,
        m_read_nesting,
        m_read_metrics,
        m_logger,
        run_type,
        time_start,
        time_end,
        nemo_file_list,
    ):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-01-08")
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            make_fvcom_boundary.make_fvcom_boundary(parsed_args, self.config)
        input_dir = Path(self.config["vhfr fvcom runs"]["input dir"])
        m_mk_nest_file2.assert_called_once_with(
            fout=os.fspath(
                input_dir
                / f'bdy_{run_type}_btrp_{arrow.get(time_start).format("YYYYMMDD")}.nc'
            ),
            x="x",
            y="y",
            z="z",
            tri="tri",
            nsiglev="nsiglev",
            siglev="siglev",
            nsiglay="nsiglay",
            siglay="siglay",
            utmzone=10,
            inest="inest",
            xb="xb",
            yb="yb",
            rwidth=8500,
            dl=2,
            du=2,
            nemo_lon="nemo_lon",
            nemo_lat="nemo_lat",
            e1t="e1t",
            e2t="e2t",
            e3u_0="e3u_0",
            e3v_0="e3v_0",
            nemo_file_list=nemo_file_list,
            time_start=time_start,
            time_end=time_end,
            ua_name="ubarotropic",
            va_name="vbarotropic",
        )
