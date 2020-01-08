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
"""Unit tests for SalishSeaCast download_fvcom_results worker.
"""
from pathlib import Path
import shlex
import textwrap
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
            textwrap.dedent(
                """\
                file group: allen
                
                vhfr fvcom runs:
                  host: arbutus.cloud
                  run types:
                    nowcast x2: 
                      results: /nemoShare/MEOPAR/SalishSea/fvcom-nowcast-x2/
                    forecast x2: 
                      results: /nemoShare/MEOPAR/SalishSea/fvcom-forecast-x2/
                    nowcast r12: 
                      results: /nemoShare/MEOPAR/SalishSea/fvcom-nowcast-r12/
                  results archive:
                    nowcast x2: /opp/fvcom/nowcast-x2/
                    forecast x2: /opp/fvcom/forecast-x2/ 
                    nowcast r12: /opp/fvcom/nowcast-r12/
                """
            )
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

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_fvcom_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
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


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "download_fvcom_results" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "download_fvcom_results"
        ]
        assert msg_registry["checklist key"] == "VHFR FVCOM results files"

    @pytest.mark.parametrize(
        "msg",
        (
            "success x2 nowcast",
            "failure x2 nowcast",
            "success x2 forecast",
            "failure x2 forecast",
            "success r12 nowcast",
            "failure r12 nowcast",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "download_fvcom_results"
        ]
        assert msg in msg_registry

    def test_run_types_section(self, prod_config):
        run_types = prod_config["vhfr fvcom runs"]["run types"]
        assert run_types["nowcast x2"] == {
            "nemo boundary results": "/nemoShare/MEOPAR/SalishSea/nowcast/",
            "time step": 0.5,
            "results": "/nemoShare/MEOPAR/SalishSea/fvcom-nowcast-x2/",
        }
        assert run_types["forecast x2"] == {
            "nemo boundary results": "/nemoShare/MEOPAR/SalishSea/forecast/",
            "time step": 0.5,
            "results": "/nemoShare/MEOPAR/SalishSea/fvcom-forecast-x2/",
        }
        assert run_types["nowcast r12"] == {
            "nemo boundary results": "/nemoShare/MEOPAR/SalishSea/nowcast/",
            "time step": 0.2,
            "results": "/nemoShare/MEOPAR/SalishSea/fvcom-nowcast-r12/",
        }

    def test_results_archive_section(self, prod_config):
        results_archive = prod_config["vhfr fvcom runs"]["results archive"]
        assert results_archive["nowcast x2"] == "/opp/fvcom/nowcast-x2/"
        assert results_archive["forecast x2"] == "/opp/fvcom/forecast-x2/"
        assert results_archive["nowcast r12"] == "/opp/fvcom/nowcast-r12/"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.download_fvcom_results.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-02-16"),
        )
        msg_type = download_fvcom_results.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {model_config} {run_type}"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.download_fvcom_results.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-02-16"),
        )
        msg_type = download_fvcom_results.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {model_config} {run_type}"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.download_fvcom_results.logger", autospec=True)
@patch("nowcast.workers.download_fvcom_results.lib.run_in_subprocess", autospec=True)
@patch("nowcast.workers.download_fvcom_results.lib.fix_perms", autospec=True)
class TestDownloadFVCOMResults:
    """Unit tests for download_fvcom_results() function.
    """

    def test_checklist(
        self, m_fix_perms, m_run_sub, m_logger, model_config, run_type, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-02-16"),
        )
        checklist = download_fvcom_results.download_fvcom_results(parsed_args, config)
        expected = {
            run_type: {
                "host": "arbutus.cloud",
                "model config": model_config,
                "run date": "2018-02-16",
                "files": [],
            }
        }
        assert checklist == expected

    def test_scp_subprocess(
        self, m_fix_perms, m_run_sub, m_logger, model_config, run_type, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-02-16"),
        )
        download_fvcom_results.download_fvcom_results(parsed_args, config)
        m_run_sub.assert_called_once_with(
            shlex.split(
                f"scp -Cpr "
                f"arbutus.cloud:/nemoShare/MEOPAR/SalishSea/fvcom-{run_type}-{model_config}/16feb18 "
                f"/opp/fvcom/{run_type}-{model_config}"
            ),
            m_logger.debug,
            m_logger.error,
        )
