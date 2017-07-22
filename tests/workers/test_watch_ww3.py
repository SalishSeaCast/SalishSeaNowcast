# Copyright 2013-2017 The Salish Sea MEOPAR Contributors
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

"""Unit tests for Salish Sea nowcast watch_ww3 worker.
"""
from types import SimpleNamespace
from unittest.mock import (
    call,
    patch,
    Mock,
)

import pytest
import subprocess

from nowcast.workers import watch_ww3


@patch('nowcast.workers.watch_ww3.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        watch_ww3.main()
        args, kwargs = m_worker.call_args
        assert args == ('watch_ww3',)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker):
        watch_ww3.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        watch_ww3.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'forecast2', 'forecast'}
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        watch_ww3.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            watch_ww3.watch_ww3,
            watch_ww3.success,
            watch_ww3.failure,
        )


@patch('nowcast.workers.watch_ww3.logger')
class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('run_type, host_name', [
        ('forecast2', 'west.cloud-nowcast'),
        ('forecast', 'west.cloud-nowcast'),
    ])
    def test_success_log_info(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
        )
        watch_ww3.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize('run_type, host_name, expected', [
        ('forecast2', 'west.cloud-nowcast', 'success forecast2'),
        ('forecast', 'west.cloud-nowcast', 'success forecast'),
    ])
    def test_success_msg_type(self, m_logger, run_type, host_name, expected):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
        )
        msg_type = watch_ww3.success(parsed_args)
        assert msg_type == expected


@patch('nowcast.workers.watch_ww3.logger')
class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('run_type, host_name', [
        ('forecast2', 'west.cloud-nowcast'),
        ('forecast', 'west.cloud-nowcast'),
    ])
    def test_failure_log_critical(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
        )
        watch_ww3.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize('run_type, host_name, expected', [
        ('forecast2', 'west.cloud-nowcast', 'failure forecast2'),
        ('forecast', 'west.cloud-nowcast', 'failure forecast'),
    ])
    def test_failure_msg_type(self, m_logger, run_type, host_name, expected):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
        )
        msg_type = watch_ww3.failure(parsed_args)
        assert msg_type == expected


@patch('nowcast.workers.watch_ww3.logger')
@patch('nowcast.workers.watch_ww3.subprocess.run')
class TestFindRunPid:
    """Unit test for _find_run_pid() function.
    """
    def test_find_run_pid(self, m_run, m_logger):
        run_info = {'run exec cmd': 'bash SoGWW3.sh'}
        m_run.return_value = Mock(stdout='4343')
        watch_ww3._find_run_pid(run_info)
        assert m_run.call_args_list == [call(
            ['pgrep', '--newest', '--exact', '--full', 'bash SoGWW3.sh'],
            stdout=subprocess.PIPE, check=True, universal_newlines=True)]


class TestPidExists:
    """Unit tests for _pid_exists() function.
    """
    def test_negative_pid(self):
        pid_exists = watch_ww3._pid_exists(-1)
        assert not pid_exists

    def test_zero_pid(self):
        with pytest.raises(ValueError):
            watch_ww3._pid_exists(0)

    @patch('nowcast.workers.watch_ww3.os.kill', return_value=None)
    def test_pid_exists(self, m_kill):
        pid_exists = watch_ww3._pid_exists(42)
        assert pid_exists

    @patch('nowcast.workers.watch_ww3.os.kill', side_effect=ProcessLookupError)
    def test_no_such_pid(self, m_kill):
        pid_exists = watch_ww3._pid_exists(42)
        assert not pid_exists

    @patch('nowcast.workers.watch_ww3.os.kill', side_effect=PermissionError)
    def test_pid_permission_error(self, m_kill):
        pid_exists = watch_ww3._pid_exists(42)
        assert pid_exists

    @patch('nowcast.workers.watch_ww3.os.kill', side_effect=OSError)
    def test_oserror(self, m_kill):
        with pytest.raises(OSError):
            watch_ww3._pid_exists(42)
