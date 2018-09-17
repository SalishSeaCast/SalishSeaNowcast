# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""Unit tests for SalishSeaCast watch_NEMO_hindcast worker.
"""
from types import SimpleNamespace
from unittest.mock import patch, Mock

import nemo_nowcast

from nowcast.workers import watch_NEMO_hindcast


@patch(
    "nowcast.workers.watch_NEMO_hindcast.NowcastWorker", spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker.call_args
        assert args == ("watch_NEMO_hindcast",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        watch_NEMO_hindcast.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_id_option(self, m_worker):
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("--run-id",)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            watch_NEMO_hindcast.watch_NEMO_hindcast,
            watch_NEMO_hindcast.success,
            watch_NEMO_hindcast.failure,
        )


@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(host_name="cedar")
        watch_NEMO_hindcast.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(host_name="cedar")
        msg_type = watch_NEMO_hindcast.success(parsed_args)
        assert msg_type == f"success"


@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger):
        parsed_args = SimpleNamespace(host_name="cedar")
        watch_NEMO_hindcast.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(host_name="cedar")
        msg_type = watch_NEMO_hindcast.failure(parsed_args)
        assert msg_type == f"failure"


class TestWatchNEMO_Hindcast:
    """Unit test for watch_NEMO_hindcast() function.
    """

    @patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.sftp",
        return_value=(Mock(name="ssh_client"), Mock(name="sftp_client")),
        autospec=True,
    )
    @patch(
        "nowcast.workers.watch_NEMO_hindcast._get_run_id",
        return_value=("9813234", "01jul18hindcast"),
        autospec=True,
    )
    @patch(
        "nowcast.workers.watch_NEMO_hindcast._is_queued",
        return_value=False,
        autospec=True,
    )
    @patch(
        "nowcast.workers.watch_NEMO_hindcast._get_tmp_run_dir",
        return_value="tmp_run_dir",
        autospec=True,
    )
    @patch(
        "nowcast.workers.watch_NEMO_hindcast._get_run_info",
        return_value=SimpleNamespace(),
        autospec=True,
    )
    @patch(
        "nowcast.workers.watch_NEMO_hindcast._is_running",
        return_value=False,
        autospec=True,
    )
    @patch(
        "nowcast.workers.watch_NEMO_hindcast._is_completed",
        return_value=True,
        autospec=True,
    )
    def test_checklist(
        self,
        m_is_completed,
        m_is_running,
        m_get_run_info,
        m_get_tmp_run_dir,
        m_is_queued,
        m_get_run_id,
        m_sftp,
        m_logger,
    ):
        parsed_args = SimpleNamespace(host_name="cedar", run_id=None)
        config = {
            "run": {
                "hindcast hosts": {
                    "cedar": {
                        "ssh key": "SalishSeaNEMO-nowcast_id_rsa",
                        "users": "allen,dlatorne",
                        "scratch dir": "scratch/hindcast",
                    }
                }
            }
        }
        checklist = watch_NEMO_hindcast.watch_NEMO_hindcast(parsed_args, config)
        expected = {
            "hindcast": {
                "host": "cedar",
                "run id": "01jul18hindcast",
                "run date": "2018-07-01",
                "completed": True,
            }
        }
        assert checklist == expected
