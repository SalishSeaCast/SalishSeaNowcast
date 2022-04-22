#  Copyright 2013 – present by the SalishSeaCast Project contributors
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
"""Unit tests for Salish Sea NEMO nowcast make_plots worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import pytest

from nowcast.workers import make_plots


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@patch("nowcast.workers.make_plots.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_plots",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_model_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("model",)
        assert kwargs["choices"] == {"nemo", "fvcom", "wwatch3"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {
            "nowcast",
            "nowcast-green",
            "nowcast-agrif",
            "nowcast-x2",
            "nowcast-r12",
            "forecast",
            "forecast2",
            "forecast-x2",
        }
        assert "help" in kwargs

    def test_add_plot_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("plot_type",)
        assert kwargs["choices"] == {"publish", "research", "comparison"}
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_add_test_figure_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[3]
        assert args == ("--test-figure",)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_plots.main()
        args, kwargs = m_worker().run.call_args
        assert args == (make_plots.make_plots, make_plots.success, make_plots.failure)


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_plots" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_plots"]
        assert msg_registry["checklist key"] == "plots"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nemo nowcast publish",
            "success nemo nowcast research",
            "success nemo nowcast comparison",
            "failure nemo nowcast publish",
            "failure nemo nowcast research",
            "failure nemo nowcast comparison",
            "success nemo nowcast-green research",
            "failure nemo nowcast-green research",
            "success nemo nowcast-agrif research",
            "failure nemo nowcast-agrif research",
            "success nemo forecast publish",
            "failure nemo forecast publish",
            "success nemo forecast2 publish",
            "failure nemo forecast2 publish",
            "success fvcom nowcast-x2 publish",
            "failure fvcom nowcast-x2 publish",
            "success fvcom nowcast-r12 publish",
            "failure fvcom nowcast-r12 publish",
            "success fvcom nowcast-x2 research",
            "failure fvcom nowcast-x2 research",
            "success fvcom nowcast-r12 research",
            "failure fvcom nowcast-r12 research",
            "success wwatch3 forecast publish",
            "failure wwatch3 forecast publish",
            "success wwatch3 forecast2 publish",
            "failure wwatch3 forecast2 publish",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_plots"]
        assert msg in msg_registry


@pytest.mark.parametrize(
    "model, run_type, plot_type",
    [
        ("nemo", "nowcast", "publish"),
        ("nemo", "nowcast", "research"),
        ("nemo", "nowcast", "comparison"),
        ("nemo", "nowcast-green", "research"),
        ("nemo", "nowcast-agrif", "research"),
        ("nemo", "forecast", "publish"),
        ("nemo", "forecast2", "publish"),
        ("fvcom", "nowcast-x2", "publish"),
        ("fvcom", "forecast-x2", "publish"),
        ("fvcom", "nowcast-r12", "publish"),
        ("wwatch3", "forecast", "publish"),
        ("wwatch3", "forecast2", "publish"),
    ],
)
@patch("nowcast.workers.make_plots.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, model, run_type, plot_type):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get("2017-01-02"),
        )
        msg_type = make_plots.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {model} {run_type} {plot_type}"


@pytest.mark.parametrize(
    "model, run_type, plot_type",
    [
        ("nemo", "nowcast", "publish"),
        ("nemo", "nowcast", "research"),
        ("nemo", "nowcast", "comparison"),
        ("nemo", "nowcast-green", "research"),
        ("nemo", "nowcast-agrif", "research"),
        ("nemo", "forecast", "publish"),
        ("nemo", "forecast2", "publish"),
        ("fvcom", "nowcast-x2", "publish"),
        ("fvcom", "forecast-x2", "publish"),
        ("fvcom", "nowcast-r12", "publish"),
        ("wwatch3", "forecast", "publish"),
        ("wwatch3", "forecast2", "publish"),
    ],
)
@patch("nowcast.workers.make_plots.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, model, run_type, plot_type):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get("2017-01-02"),
        )
        msg_type = make_plots.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {model} {run_type} {plot_type}"
