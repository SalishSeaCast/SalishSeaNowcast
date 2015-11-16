# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Unit tests for Salish Sea NEMO nowcast NowcastWorker class.
"""
import argparse

from unittest.mock import (
    Mock,
    patch,
)
import pytest
import zmq


@pytest.fixture
def worker_module():
    from nowcast import nowcast_worker
    return nowcast_worker


@pytest.fixture
def worker_class():
    from nowcast.nowcast_worker import NowcastWorker
    return NowcastWorker


@pytest.fixture
def worker(worker_class):
    return worker_class('name', 'description')


class TestNowcastWorkerConstructor:
    """Unit tests for NowcastWorker.__init__ method.
    """
    def test_name(self, worker):
        assert worker.name == 'name'

    def test_description(self, worker):
        assert worker.description == 'description'

    def test_logger(self, worker):
        assert worker.logger.name == 'name'

    def test_context(self, worker):
        assert isinstance(worker.context, zmq.Context)

    def test_arg_parser(self, worker):
        assert isinstance(worker.arg_parser, argparse.ArgumentParser)


@patch.object(worker_module().argparse, 'ArgumentParser')
def test_add_argument(m_arg_parser, worker):
    """add_argument() wraps argparse.ArgumentParser.add_argument()
    """
    worker.add_argument(
        '--yesterday', action='store_true',
        help="Download forecast files for previous day's date."
    )
    m_arg_parser().add_argument.assert_called_once_with(
        '--yesterday', action='store_true',
        help="Download forecast files for previous day's date."
    )


class TestNowcastWorkerRun:
    """Unit tests for NowcastWorker.run method.
    """
    def test_worker_func(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert worker.worker_func == m_worker_func

    def test_success_func(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert worker.success == m_success

    def test_failure_func(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert worker.failure == m_failure

    def test_parsed_args(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(name='parse_args')
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        worker.arg_parser.parse_args.assert_called_once_with()

    def test_config(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config as m_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert worker.config == m_load_config()

    def test_configure_logging(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_config_logging as m_config_logging, p_init_zmq:
            worker.run(m_worker_func, m_success, m_failure)
        m_config_logging.assert_called_once_with(
            worker.config, worker.logger, worker.parsed_args.debug)

    def test_logging_debug(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        m_logger_debug = Mock(name='logger.debug')
        worker.logger.debug = m_logger_debug
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert m_logger_debug.call_count == 2

    def test_install_signal_handlers(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_inst_sig_handlers = patch.object(
            worker_module().lib, 'install_signal_handlers')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_inst_sig_handlers as m_inst_sig_handlers:
            with p_init_zmq, p_config_logging:
                worker.run(m_worker_func, m_success, m_failure)
        m_inst_sig_handlers.assert_called_once_with(
            worker.logger, worker.context)

    def test_socket(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq as m_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert worker.socket == m_init_zmq()

    def test_do_work(self, worker):
        m_worker_func = Mock(name='worker_func')
        m_success = Mock(name='success')
        m_failure = Mock(name='failure')
        worker.arg_parser.parse_args = Mock(
            name='parse_args',
            config_file='nowcast.yaml',
            debug=False)
        p_load_config = patch.object(worker_module().lib, 'load_config')
        p_init_zmq = patch.object(
            worker_module().lib, 'init_zmq_req_rep_worker')
        p_config_logging = patch.object(
            worker_module().lib, 'configure_logging')
        worker._do_work = Mock(name='_do_work')
        with p_load_config, p_init_zmq, p_config_logging:
            worker.run(m_worker_func, m_success, m_failure)
        assert worker._do_work.call_count == 1


class TestNowcastWorkerDoWork:
    """Unit tests for NowcastWorker._do_work method.
    """
    def test_worker_func(self, worker):
        worker.parsed_args = m_parsed_args = Mock(name='parsed_args')
        worker.config = m_config = Mock(name='config')
        worker.socket = Mock(name='socket')
        worker.worker_func = Mock(name='worker_func')
        with patch.object(worker_module().lib, 'tell_manager'):
            worker._do_work()
        worker.worker_func.assert_called_once_with(m_parsed_args, m_config)

    def test_success_func(self, worker):
        worker.parsed_args = m_parsed_args = Mock(name='parsed_args')
        worker.config = Mock(name='config')
        worker.logger = Mock(name='logger')
        worker.socket = Mock(name='socket')
        worker.worker_func = Mock(name='worker_func')
        worker.success = Mock(name='success')
        with patch.object(worker_module().lib, 'tell_manager'):
            worker._do_work()
        worker.success.assert_called_once_with(m_parsed_args)

    def test_success_tell_manager(self, worker):
        worker.parsed_args = Mock(name='parsed_args')
        worker.config = m_config = Mock(name='config')
        worker.logger = m_logger = Mock(name='logger')
        worker.socket = m_socket = Mock(name='socket')
        worker.worker_func = Mock(name='worker_func', return_value='checklist')
        worker.success = Mock(name='success', return_value='success')
        p_tell_mgr = patch.object(worker_module().lib, 'tell_manager')
        with p_tell_mgr as m_tell_mgr:
            worker._do_work()
        m_tell_mgr.assert_called_once_with(
            'name', 'success', m_config, m_logger, m_socket, 'checklist')

    def test_failure_func(self, worker):
        from nowcast import lib
        worker.parsed_args = m_parsed_args = Mock(name='parsed_args')
        worker.config = Mock(name='config')
        worker.logger = Mock(name='logger')
        worker.socket = Mock(name='socket')
        worker.worker_func = Mock(
            name='worker_func', side_effect=lib.WorkerError)
        worker.failure = Mock(name='failure')
        with patch.object(worker_module().lib, 'tell_manager'):
            worker._do_work()
        worker.failure.assert_called_once_with(m_parsed_args)

    def test_failure_tell_manager(self, worker):
        from nowcast import lib
        worker.parsed_args = Mock(name='parsed_args')
        worker.config = m_config = Mock(name='config')
        worker.logger = m_logger = Mock(name='logger')
        worker.socket = m_socket = Mock(name='socket')
        worker.worker_func = Mock(
            name='worker_func', side_effect=lib.WorkerError)
        worker.failure = Mock(name='failure', return_value='failure')
        p_tell_mgr = patch.object(worker_module().lib, 'tell_manager')
        with p_tell_mgr as m_tell_mgr:
            worker._do_work()
        m_tell_mgr.assert_called_once_with(
            'name', 'failure', m_config, m_logger, m_socket)

    def test_system_exit_context_destroy(self, worker):
        worker.parsed_args = Mock(name='parsed_args')
        worker.config = Mock(name='config')
        worker.context = Mock(name='context')
        worker.worker_func = Mock(
            name='worker_func', side_effect=SystemExit)
        worker._do_work()
        assert worker.context.destroy.call_count == 1

    def test_logger_debug_task_completed(self, worker):
        worker.parsed_args = Mock(name='parsed_args')
        worker.config = Mock(name='config')
        worker.logger = Mock(name='logger')
        worker.context = Mock(name='context')
        worker.worker_func = Mock(
            name='worker_func', side_effect=SystemExit)
        worker._do_work()
        worker.logger.debug.assert_called_once_with(
            'task completed; shutting down')
