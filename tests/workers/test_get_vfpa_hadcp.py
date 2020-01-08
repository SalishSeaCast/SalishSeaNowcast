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
"""Unit tests for SalishSeaCast get_vfpa_hadcp worker.
"""
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import get_vfpa_hadcp


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                observations:
                  hadcp data:
                    csv dir: opp/obs/AISDATA/
                    dest dir: opp/obs/AISDATA/netcdf/
                    filepath template: 'VFPA_2ND_NARROWS_HADCP_2s_{yyyymm}.nc'
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.get_vfpa_hadcp.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_vfpa_hadcp.main()
        args, kwargs = m_worker.call_args
        assert args == ("get_vfpa_hadcp",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_vfpa_hadcp.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_data_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_vfpa_hadcp.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--data-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_vfpa_hadcp.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            get_vfpa_hadcp.get_vfpa_hadcp,
            get_vfpa_hadcp.success,
            get_vfpa_hadcp.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "get_vfpa_hadcp" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["get_vfpa_hadcp"]
        assert msg_registry["checklist key"] == "VFPA HADCP data"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["get_vfpa_hadcp"]
        assert msg in msg_registry

    def test_observations(self, prod_config):
        assert "hadcp data" in prod_config["observations"]
        hadcp_obs = prod_config["observations"]["hadcp data"]
        assert hadcp_obs["csv dir"] == "/opp/observations/AISDATA/"
        assert hadcp_obs["dest dir"] == "/opp/observations/AISDATA/netcdf/"
        assert hadcp_obs["filepath template"] == "VFPA_2ND_NARROWS_HADCP_2s_{yyyymm}.nc"


@patch("nowcast.workers.get_vfpa_hadcp.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-01"))
        msg_type = get_vfpa_hadcp.success(parsed_args)
        m_logger.info.assert_called_once_with(
            "VFPA HADCP observations added to 2018-10 netcdf file"
        )
        assert msg_type == "success"


@patch("nowcast.workers.get_vfpa_hadcp.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-01"))
        msg_type = get_vfpa_hadcp.failure(parsed_args)
        m_logger.critical.assert_called_once_with(
            "Addition of VFPA HADCP observations to 2018-10 netcdf file failed"
        )
        assert msg_type == "failure"


@patch("nowcast.workers.get_vfpa_hadcp.logger", autospec=True)
@patch("nowcast.workers.get_vfpa_hadcp._make_hour_dataset", autospec=True)
class TestGetVFPA_HADCP:
    """Unit test for get_vfpa_hadcp() function.
    """

    def test_checklist_create(self, m_mk_hr_ds, m_logger, config):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-01"))
        checklist = get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        expected = {
            "created": "opp/obs/AISDATA/netcdf/VFPA_2ND_NARROWS_HADCP_2s_201810.nc",
            "UTC date": "2018-10-01",
        }
        assert checklist == expected

    @patch(
        "nowcast.workers.get_vfpa_hadcp.Path.exists", return_value=True, autospec=True
    )
    @patch("nowcast.workers.get_vfpa_hadcp.xarray", autospec=True)
    def test_checklist_extend(self, m_xarray, m_exists, m_mk_hr_ds, m_logger, config):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-21"))
        checklist = get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        expected = {
            "extended": "opp/obs/AISDATA/netcdf/VFPA_2ND_NARROWS_HADCP_2s_201810.nc",
            "UTC date": "2018-10-21",
        }
        assert checklist == expected

    @pytest.mark.parametrize("ds_exists", (True, False))
    @patch("nowcast.workers.get_vfpa_hadcp.xarray", autospec=True)
    def test_checklist_missing_data(
        self, m_xarray, m_mk_hr_ds, m_logger, ds_exists, config
    ):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-12-23"))
        m_mk_hr_ds.side_effect = ValueError
        p_exists = patch(
            "nowcast.workers.get_vfpa_hadcp.Path.exists",
            return_value=ds_exists,
            autospec=True,
        )
        with p_exists:
            checklist = get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        expected = {
            "missing data": "opp/obs/AISDATA/netcdf/VFPA_2ND_NARROWS_HADCP_2s_201812.nc",
            "UTC date": "2018-12-23",
        }
        assert checklist == expected
