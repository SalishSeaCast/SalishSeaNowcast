# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

"""Unit tests for Salish Sea NEMO nowcast watch_NEMO worker.
"""
from unittest.mock import (
    patch,
    Mock,
)

import pytest


@pytest.fixture
def worker_module(scope='module'):
    from nowcast.workers import watch_NEMO
    return watch_NEMO


@patch.object(worker_module(), 'NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch.object(worker_module(), 'worker_name')
    def test_instantiate_worker(self, m_name, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {
            'nowcast', 'nowcast-green', 'forecast', 'forecast2'}
        assert 'help' in kwargs

    def test_add_pid_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[2]
        assert args == ('pid',)
        assert 'help' in kwargs

    def test_add_shared_storage_arg(self, m_worker, worker_module, lib_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[3]
        assert args == ('--shared-storage',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.watch_NEMO,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('run_type, host_name, shared_storage', [
        ('nowcast', 'west.cloud-nowcast', True),
        ('nowcast-green', 'salish-nowcast', False),
        ('forecast', 'west.cloud-nowcast', True),
        ('forecast2', 'west.cloud-nowcast', True),
    ])
    def test_success_log_info(
        self, run_type, host_name, worker_module, shared_storage,
    ):
        parsed_args = Mock(
            host_name=host_name,
            run_type=run_type,
            pid=42,
            shared_storage=shared_storage,
        )
        with patch.object(worker_module, 'logger') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize('run_type, host_name, shared_storage, expected', [
        ('nowcast', 'west.cloud-nowcast', True, 'success nowcast'),
        ('nowcast-green', 'salish-nowcast', False, 'success nowcast-green'),
        ('forecast', 'west.cloud-nowcast', True, 'success forecast'),
        ('forecast2', 'west.cloud-nowcast', True, 'success forecast2'),
    ])
    def test_success_msg_type(
        self, run_type, host_name, worker_module, shared_storage, expected,
    ):
        parsed_args = Mock(
            host_name=host_name,
            run_type=run_type,
            pid=42,
            shared_storage=shared_storage,
        )
        msg_type = worker_module.success(parsed_args)
        assert msg_type == expected


class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('run_type, host_name, shared_storage', [
        ('nowcast', 'west.cloud-nowcast', True),
        ('nowcast-green', 'salish-nowcast', False),
        ('forecast', 'west.cloud-nowcast', True),
        ('forecast2', 'west.cloud-nowcast', True),
    ])
    def test_failure_log_critical(
        self, run_type, host_name, worker_module, shared_storage,
    ):
        parsed_args = Mock(
            host_name=host_name,
            run_type=run_type,
            pid=42,
            shared_storage=shared_storage,
        )
        with patch.object(worker_module, 'logger') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize('run_type, host_name, shared_storage, expected', [
        ('nowcast', 'west.cloud-nowcast', True, 'failure nowcast'),
        ('nowcast-green', 'salish-nowcast', False, 'failure nowcast-green'),
        ('forecast', 'west.cloud-nowcast', True, 'failure forecast'),
        ('forecast2', 'west.cloud-nowcast', True, 'failure forecast2'),
    ])
    def test_failure_msg_type(
        self, run_type, host_name, worker_module, shared_storage, expected,
    ):
        parsed_args = Mock(
            host_name=host_name,
            run_type=run_type,
            pid=42,
            shared_storage=shared_storage,
        )
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == expected


class TestWatchNEMO:
    """Unit tests for watch_NEMO() function.
    """
    @pytest.mark.parametrize('run_type, host_name, shared_storage', [
        ('nowcast', 'west.cloud-nowcast', True),
        ('nowcast-green', 'salish-nowcast', False),
        ('forecast', 'west.cloud-nowcast', True),
        ('forecast2', 'west.cloud-nowcast', True),
    ])
    def test_no_run_pid(
        self, run_type, host_name, shared_storage, worker_module,
    ):
        parsed_args = Mock(
            host_name=host_name,
            run_type=run_type,
            pid=42,
            shared_storage=shared_storage,
        )
        config = {}
        tell_manager = Mock(name='tell_manager')
        with patch.object(worker_module, '_pid_exists', return_value=False):
            with pytest.raises(worker_module.WorkerError):
                worker_module.watch_NEMO(parsed_args, config, tell_manager)


class TestLogMsg:
    """Unit tests for _log_msg() function.
    """
    def test_shared_storage(self, worker_module):
        tell_manager = Mock(name='tell_manager')
        with patch.object(worker_module, 'logger') as m_logger:
            worker_module._log_msg(
                'msg', 'info', tell_manager, shared_storage=True)
        m_logger.log.assert_called_once_with(20, 'msg')
        assert not tell_manager.called

    def test_not_shared_storage(self, worker_module):
        tell_manager = Mock(name='tell_manager')
        with patch.object(worker_module, 'logger') as m_logger:
            worker_module._log_msg(
                'msg', 'info', tell_manager, shared_storage=False)
        m_logger.log.assert_called_once_with(20, 'msg')
        tell_manager.assert_called_once_with('log.info', 'msg')


class TestPidExists:
    """Unit tests for _pid_exists() function.
    """
    def test_negative_pid(self, worker_module):
        pid_exists = worker_module._pid_exists(-1)
        assert not pid_exists

    def test_zero_pid(self, worker_module):
        with pytest.raises(ValueError):
            worker_module._pid_exists(0)

    @patch.object(worker_module().os, 'kill', return_value=None)
    def test_pid_exists(self, m_kill, worker_module):
        pid_exists = worker_module._pid_exists(42)
        assert pid_exists

    @patch.object(worker_module().os, 'kill', side_effect=ProcessLookupError)
    def test_no_such_pid(self, m_kill, worker_module):
        pid_exists = worker_module._pid_exists(42)
        assert not pid_exists

    @patch.object(worker_module().os, 'kill', side_effect=PermissionError)
    def test_pid_permission_error(self, m_kill, worker_module):
        pid_exists = worker_module._pid_exists(42)
        assert pid_exists

    @patch.object(worker_module().os, 'kill', side_effect=OSError)
    def test_oserror(self, m_kill, worker_module):
        with pytest.raises(OSError):
            worker_module._pid_exists(42)
