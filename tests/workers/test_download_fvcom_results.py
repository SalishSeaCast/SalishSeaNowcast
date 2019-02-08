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
"""Unit tests for SalishSeaCast download_fvcom_results worker.
"""
from pathlib import Path
import shlex
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import download_fvcom_results


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
file group: allen

vhfr fvcom runs:
  host: west.cloud-nowcast
  run types:
    nowcast: 
      results: /nemoShare/MEOPAR/SalishSea/fvcom-nowcast/
    forecast: 
      results: /nemoShare/MEOPAR/SalishSea/fvcom-forecast/
  results archive:
    nowcast: /opp/fvcom/nowcast/
    forecast: /opp/fvcom/forecast/ 
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.download_fvcom_results.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker.call_args
        assert args == ("download_fvcom_results",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        expected = {"nowcast", "forecast"}
        assert kwargs["choices"] == expected
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            download_fvcom_results.download_fvcom_results,
            download_fvcom_results.success,
            download_fvcom_results.failure,
        )


@pytest.mark.parametrize(
    "run_type, host_name",
    [("nowcast", "west.cloud-nowcast"), ("forecast", "west.cloud-nowcast")],
)
@patch("nowcast.workers.download_fvcom_results.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-02-16")
        )
        download_fvcom_results.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]["extra"]["run_type"] == run_type
        assert m_logger.info.call_args[1]["extra"]["host_name"] == host_name

    def test_success_msg_type(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-02-16")
        )
        msg_typ = download_fvcom_results.success(parsed_args)
        assert msg_typ == "success {}".format(run_type)


@pytest.mark.parametrize(
    "run_type, host_name",
    [("nowcast", "west.cloud-nowcast"), ("forecast", "west.cloud-nowcast")],
)
@patch("nowcast.workers.download_fvcom_results.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_info(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-02-16")
        )
        download_fvcom_results.failure(parsed_args)
        assert m_logger.critical.called
        assert m_logger.critical.call_args[1]["extra"]["run_type"] == run_type
        assert m_logger.critical.call_args[1]["extra"]["host_name"] == host_name

    def test_failure_msg_type(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-02-16")
        )
        msg_typ = download_fvcom_results.failure(parsed_args)
        assert msg_typ == "failure {}".format(run_type)


@pytest.mark.parametrize(
    "run_type, host_name",
    [("nowcast", "west.cloud-nowcast"), ("forecast", "west.cloud-nowcast")],
)
@patch("nowcast.workers.download_fvcom_results.logger", autospec=True)
@patch("nowcast.workers.download_fvcom_results.lib.run_in_subprocess", autospec=True)
@patch("nowcast.workers.download_fvcom_results.lib.fix_perms", autospec=True)
class TestDownloadFVCOMResults:
    """Unit tests for download_fvcom_results() function.
    """

    def test_checklist(
        self, m_fix_perms, m_run_sub, m_logger, run_type, host_name, config
    ):
        pass

    def test_scp_subprocess(
        self, m_fix_perms, m_run_sub, m_logger, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-02-16")
        )
        download_fvcom_results.download_fvcom_results(parsed_args, config)
        m_run_sub.assert_called_once_with(
            shlex.split(
                f"scp -Cpr "
                f"{host_name}:/nemoShare/MEOPAR/SalishSea/fvcom-{run_type}/16feb18 "
                f"/opp/fvcom/{run_type}"
            ),
            m_logger.debug,
            m_logger.error,
        )
