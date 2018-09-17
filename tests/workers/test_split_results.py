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
"""Unit tests for Salish Sea NEMO nowcast split_results worker.
"""
from unittest.mock import Mock, patch

from nowcast.workers import split_results


@patch("nowcast.workers.split_results.NowcastWorker")
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        split_results.main()
        args, kwargs = m_worker.call_args
        assert args == ("split_results",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        split_results.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        split_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        expected = {"hindcast"}
        assert kwargs["choices"] == expected
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        split_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_date",)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        split_results.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            split_results.split_results,
            split_results.success,
            split_results.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self):
        parsed_args = Mock(run_type="hindcast")
        with patch("nowcast.workers.split_results.logger") as m_logger:
            split_results.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]["extra"]["run_type"] == "hindcast"

    def test_success_msg_type(self):
        parsed_args = Mock(run_type="hindcast")
        with patch("nowcast.workers.split_results.logger"):
            msg_typ = split_results.success(parsed_args)
        assert msg_typ == "success hindcast"


class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_info(self):
        parsed_args = Mock(run_type="hindcast")
        with patch("nowcast.workers.split_results.logger") as m_logger:
            split_results.failure(parsed_args)
        assert m_logger.critical.called
        assert m_logger.critical.call_args[1]["extra"]["run_type"] == "hindcast"

    def test_failure_msg_type(self):
        parsed_args = Mock(run_type="hindcast")
        with patch("nowcast.workers.split_results.logger"):
            msg_typ = split_results.failure(parsed_args)
        assert msg_typ == "failure hindcast"
