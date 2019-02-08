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
"""Unit tests for Salish Sea NEMO nowcast make_live_ocean_files worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_live_ocean_files


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
temperature salinity:
  download:
    dest dir: forcing/LiveOcean/downloaded
  bc dir: forcing/LiveOcean/boundary_conditions
  file template: 'LiveOcean_v201712_{:y%Ym%md%d}.nc'
  mesh mask: grid/mesh_mask201702.nc
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_live_ocean_files.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_live_ocean_files",)
        assert "description" in kwargs

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            make_live_ocean_files.make_live_ocean_files,
            make_live_ocean_files.success,
            make_live_ocean_files.failure,
        )
        assert args == expected


@patch("nowcast.workers.make_live_ocean_files.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-01-12"))
        make_live_ocean_files.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]["extra"]["run_date"] == "2017-01-12"

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-01-12"))
        msg_type = make_live_ocean_files.success(parsed_args)
        assert msg_type == "success"


@patch("nowcast.workers.make_live_ocean_files.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-01-12"))
        make_live_ocean_files.failure(parsed_args)
        assert m_logger.critical.called
        expected = "2017-01-12"
        assert m_logger.critical.call_args[1]["extra"]["run_date"] == expected

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-01-12"))
        msg_type = make_live_ocean_files.failure(parsed_args)
        assert msg_type == "failure"


@patch("nowcast.workers.make_live_ocean_files.logger", autospec=True)
@patch("nowcast.workers.make_live_ocean_files.create_LiveOcean_TS_BCs", spec=True)
class TestMakeLiveOceanFiles:
    """Unit test for make_live_ocean_files() function.
    """

    def test_checklist(self, m_create_ts, m_logger, config):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-01-30"))
        m_create_ts.return_value = ["LiveOcean_v201712_y2017m01d30.nc"]
        checklist = make_live_ocean_files.make_live_ocean_files(parsed_args, config)
        expected = {"temperature & salinity": "LiveOcean_v201712_y2017m01d30.nc"}
        assert checklist == expected
