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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM
make_fvcom_atmos_forcing worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import numpy
import pytest

from nowcast.workers import make_fvcom_atmos_forcing


@patch(
    "nowcast.workers.make_fvcom_atmos_forcing.NowcastWorker",
    spec=nemo_nowcast.NowcastWorker,
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_fvcom_atmos_forcing",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        make_fvcom_atmos_forcing.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_atmos_forcing.make_fvcom_atmos_forcing,
            make_fvcom_atmos_forcing.success,
            make_fvcom_atmos_forcing.failure,
        )


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.make_fvcom_atmos_forcing.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-15")
        )
        make_fvcom_atmos_forcing.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-15")
        )
        msg_type = make_fvcom_atmos_forcing.success(parsed_args)
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.make_fvcom_atmos_forcing.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-15")
        )
        make_fvcom_atmos_forcing.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-15")
        )
        msg_type = make_fvcom_atmos_forcing.failure(parsed_args)
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_fvcom_atmos_forcing.logger", autospec=True)
@patch(
    "nowcast.workers.make_fvcom_atmos_forcing.OPPTools.fvcomToolbox.readMesh_V3",
    return_value=(numpy.ones((44157, 2)), numpy.ones((24476, 2))),
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_atmos_forcing.OPPTools.atm.create_atm_hrdps",
    autospec=True,
)
class TestMakeFVCOMAtmosForcing:
    """Unit tests for make_fvcom_atmos_forcing() function.
    """

    config = {
        "vhfr fvcom runs": {
            "fvcom grid": {"grid file": "vhfr_low_v2_utm10_grd.dat", "utm zone": 10},
            "atmospheric forcing": {
                "hrdps grib dir": "forcing/atmospheric/GEM2.5/GRIB/",
                "fvcom atmos dir": "forcing/atmospheric/GEM2.5/vhfr-fvcom",
                "atmos file template": "atmos_{run_type}_{field_type}_{yyyymmdd}.nc",
                "fvcom grid dir": "nowcast-sys/FVCOM-VHFR-config/grid/",
            },
        }
    }

    @pytest.mark.parametrize("run_type", ["nowcast"])
    def test_checklist(self, m_create_atm_hrdps, m_readMesh, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-16")
        )
        checklist = make_fvcom_atmos_forcing.make_fvcom_atmos_forcing(
            parsed_args, self.config
        )
        expected = {
            run_type: {
                "run date": "2018-03-16",
                "wnd": "forcing/atmospheric/GEM2.5/vhfr-fvcom/atmos_nowcast_wnd_20180316.nc",
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
    def test_readMesh_V3(self, m_create_atm_hrdps, m_readMesh, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-16")
        )
        make_fvcom_atmos_forcing.make_fvcom_atmos_forcing(parsed_args, self.config)
        m_readMesh.assert_called_once_with(
            "nowcast-sys/FVCOM-VHFR-config/grid/vhfr_low_v2_utm10_grd.dat"
        )

    @pytest.mark.parametrize(
        "run_type, file_date", [("nowcast", "20180316"), ("forecast", "20180317")]
    )
    def test_create_atm_hrdps(
        self, m_create_atm_hrdps, m_readMesh, m_logger, run_type, file_date
    ):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-03-16")
        )
        make_fvcom_atmos_forcing.make_fvcom_atmos_forcing(parsed_args, self.config)
        assert m_create_atm_hrdps.call_args[0][0] == "wnd"
        numpy.testing.assert_array_equal(
            m_create_atm_hrdps.call_args[0][1], numpy.ones((24476,))
        )
        numpy.testing.assert_array_equal(
            m_create_atm_hrdps.call_args[0][2], numpy.ones((24476,))
        )
        numpy.testing.assert_array_equal(
            m_create_atm_hrdps.call_args[0][3], numpy.ones((44157, 2))
        )
        assert m_create_atm_hrdps.call_args[1]["utmzone"] == 10
        expected = (
            f"forcing/atmospheric/GEM2.5/vhfr-fvcom/"
            f"atmos_{run_type}_wnd_{file_date}.nc"
        )
        assert m_create_atm_hrdps.call_args[1]["fname"] == expected
        expected = "forcing/atmospheric/GEM2.5/GRIB/20180316/"
        assert m_create_atm_hrdps.call_args[1]["hrdps_folder"] == expected
