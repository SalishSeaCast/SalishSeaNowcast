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

"""Unit tests for Salish Sea NEMO nowcast NowcastManager class.
"""
import logging
from unittest.mock import (
    Mock,
    mock_open,
    patch,
)

import pytest
import yaml
import zmq


@pytest.fixture
def mgr_module():
    from nowcast import nowcast_mgr
    return nowcast_mgr


@pytest.fixture
def mgr_class():
    from nowcast.nowcast_mgr import NowcastManager
    return NowcastManager


@pytest.fixture
def mgr(mgr_class):
    return mgr_class()


@patch.object(mgr_module(), 'NowcastManager')
def test_main(m_mgr, mgr_module):
    """Unit test for nowcast_mgr.main function.
    """
    mgr_module.main()
    assert m_mgr().run.called


class TestNowcastManagerConstructor:
    """Unit tests for NowcastManager.__init__ method.
    """
    def test_name(self):
        p_get_module_name = patch.object(
            mgr_module().lib, 'get_module_name', return_value='nowcast_mgr',
        )
        with p_get_module_name:
            mgr = mgr_class()()
        assert mgr.name == 'nowcast_mgr'

    def test_logger(self, mgr):
        p_get_module_name = patch.object(
            mgr_module().lib, 'get_module_name', return_value='nowcast_mgr',
        )
        with p_get_module_name:
            mgr = mgr_class()()
        assert mgr.logger.name == 'nowcast_mgr'

    def test_worker_loggers(self, mgr):
        assert mgr.worker_loggers == {}

    def test_context(self, mgr):
        assert isinstance(mgr.context, zmq.Context)

    def test_checklist(self, mgr):
        assert mgr.checklist == {}


@pytest.mark.parametrize('worker', [
    'download_weather',
    'get_NeahBay_ssh',
    'make_runoff_file',
    'grib_to_netcdf',
    'upload_forcing',
    'make_forcing_links',
    'run_NEMO',
    'watch_NEMO',
    'download_results',
    'make_plots',
    'make_site_page',
    'push_to_web',
])
def test_after_actions(worker, mgr):
    """Unit tests for NowcastManager.acter_actions property.
    """
    assert worker in mgr._after_actions


class TestNowcastManagerRun:
    """Unit tests for NowcastManager.run method.
    """
    def test_parsed_args(self, mgr):
        mgr._cli = Mock(name='_cli')
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr.parsed_args == mgr._cli()

    def test_config(self, mgr):
        mgr._cli = Mock(name='_cli')
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr.config == mgr._load_config()

    def test_prep_logging(self, mgr):
        mgr._cli = Mock(name='_cli')
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr._prep_logging.called

    def test_install_signal_handlers(self, mgr):
        mgr._cli = Mock(name='_cli')
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._install_signal_handlers = Mock(name='_install_signal_handlers')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr._install_signal_handlers.called

    def test_socket(self, mgr):
        mgr._cli = Mock(name='_cli')
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr._socket == mgr._prep_messaging()

    def test_load_checklist(self, mgr):
        mgr._cli = Mock(name='_cli', return_value=Mock(ignore_checklist=False))
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr._load_checklist.called

    def test_no_load_checklist(self, mgr):
        mgr._cli = Mock(name='_cli', return_value=Mock(ignore_checklist=True))
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert not mgr._load_checklist.called

    def test_process_messages(self, mgr):
        mgr._cli = Mock(name='_cli')
        mgr._load_config = Mock(name='_load_config')
        mgr._prep_logging = Mock(name='_prep_logging')
        mgr._prep_messaging = Mock(name='_prep_messaging')
        mgr._load_checklist = Mock(name='_load_checklist')
        mgr._process_messages = Mock(name='_process_messages')
        mgr.run()
        assert mgr._process_messages.called


class TestLoadConfig:
    """Unit tests for NowcastManager._load_config method.
    """
    @patch.object(mgr_module().lib, 'load_config')
    def test_load_config(self, m_load_config, mgr):
        mgr.parsed_args = Mock(config_file='nowcast.yaml')
        mgr._load_config()
        m_load_config.assert_called_once_with('nowcast.yaml')

    @patch.object(mgr_module().lib, 'load_config')
    def test_load_config_console_logging(self, m_load_config, mgr):
        mgr.parsed_args = Mock(config_file='nowcast.yaml', debug=True)
        m_load_config.return_value = {'logging': {}}
        config = mgr._load_config()
        assert config['logging']['console']


class TestPrepLogging:
    """Unit tests for NowcastManager._prep_logging method.
    """
    @patch.object(mgr_module().lib, 'configure_logging')
    def test_prep_logging(self, m_config_logging, mgr):
        mgr.parsed_args = Mock(name='parsed_args')
        mgr.config = {
            'config_file': 'nowcast.yaml',
            'logging': {
                'checklist_log_file': 'nowcast_checklist.log',
                'message_format': '%(asctime)s %(levelname)s %(message)s',
                'datetime_format': '%Y-%m-%d %H:%M:%S',
                'backup_count': 7,
            }
        }
        p_RotatingFileHandler = patch.object(
            mgr_module().logging.handlers, 'RotatingFileHandler')
        with p_RotatingFileHandler:
            mgr._prep_logging()
        m_config_logging.assert_called_once_with(
            mgr.config, mgr.logger, mgr.parsed_args.debug)

    @patch.object(mgr_module().lib, 'configure_logging')
    def test_prep_logging_info_msgs(self, m_config_logging, mgr):
        mgr.parsed_args = Mock(name='parsed_args')
        mgr.config = {
            'config_file': 'nowcast.yaml',
            'logging': {
                'checklist_log_file': 'nowcast_checklist.log',
                'message_format': '%(asctime)s %(levelname)s %(message)s',
                'datetime_format': '%Y-%m-%d %H:%M:%S',
                'backup_count': 7,
            }
        }
        mgr.logger = Mock(name='logger')
        p_RotatingFileHandler = patch.object(
            mgr_module().logging.handlers, 'RotatingFileHandler')
        with p_RotatingFileHandler:
            mgr._prep_logging()
        assert mgr.logger.info.call_count == 1

    @patch.object(mgr_module().lib, 'configure_logging')
    def test_prep_logging_debug_msgs(self, m_config_logging, mgr):
        mgr.parsed_args = Mock(name='parsed_args')
        mgr.config = {
            'config_file': 'nowcast.yaml',
            'logging': {
                'checklist_log_file': 'nowcast_checklist.log',
                'message_format': '%(asctime)s %(levelname)s %(message)s',
                'datetime_format': '%Y-%m-%d %H:%M:%S',
                'backup_count': 7,
            }
        }
        mgr.logger = Mock(name='logger')
        p_RotatingFileHandler = patch.object(
            mgr_module().logging.handlers, 'RotatingFileHandler')
        with p_RotatingFileHandler:
            mgr._prep_logging()
        assert mgr.logger.debug.call_count == 1


def test_prep_messaging(mgr):
    """Unit test for NowcastManager._prep_messaging method.
    """
    mgr.config = {'zmq': {'ports': {'backend': 6665}}}
    mgr.context.socket = Mock(name='socket')
    socket = mgr._prep_messaging()
    socket.connect.assert_called_once_with('tcp://localhost:6665')


class TestLoadChecklist:
    """Unit tests for NowcastManager._load_checklist method.
    """
    def test_load_checklist(self, mgr):
        p_open = patch.object(mgr_module(), 'open', mock_open(), create=True)
        mgr.config = {'checklist file': 'nowcast_checklist.yaml'}
        with p_open as m_open:
            mgr._load_checklist()
        m_open.assert_called_once_with('nowcast_checklist.yaml', 'rt')

    def test_load_checklist_filenotfounderror(self, mgr):
        mgr.config = {'checklist file': 'nowcast_checklist.yaml'}
        mgr.logger = Mock(name='logger')
        mgr._load_checklist()
        mgr.logger.warning.assert_called_with('running with empty checklist')


class TestProcessMessages:
    """Unit tests for NowcastManager._process_messages method.
    """
    ## TODO: Need to figure out how to break out of a while True loop


class TestMessageHandler:
    """Unit tests for NowcastManager._message_handler method.
    """
    def test_handle_undefined_msg(self, mgr):
        mgr.config = {'msg_types': {'worker': {}}}
        mgr._handle_undefined_msg = Mock(name='_handle_undefined_msg')
        mgr._log_received_msg = Mock(name='_log_received_msg')
        message = {'source': 'worker', 'msg_type': 'foo', 'payload': ''}
        reply, next_steps = mgr._message_handler(yaml.dump(message))
        mgr._handle_undefined_msg.assert_called_once_with('worker', 'foo')
        assert reply == mgr._handle_undefined_msg()
        assert next_steps is None
        assert not mgr._log_received_msg.called

    def test_need_msg(self, mgr):
        mgr.config = {'msg_types': {'worker': {'need': ''}}}
        mgr._handle_need_msg = Mock(name='_handle_need_msg')
        mgr._log_received_msg = Mock(name='_log_received_msg')
        message = {'source': 'worker', 'msg_type': 'need', 'payload': 'bar'}
        reply, next_steps = mgr._message_handler(yaml.dump(message))
        mgr._log_received_msg.assert_called_once_with('worker', 'need')
        mgr._handle_need_msg.assert_called_once_with('bar')
        assert reply == mgr._handle_need_msg()
        assert next_steps is None

    def test_log_msg(self, mgr):
        mgr.config = {'msg_types': {'worker': {'log': ''}}}
        mgr._handle_log_msg = Mock(name='_handle_log_msg')
        mgr._log_received_msg = Mock(name='_log_received_msg')
        message = {'source': 'worker', 'msg_type': 'log', 'payload': 'bar'}
        reply, next_steps = mgr._message_handler(yaml.dump(message))
        mgr._log_received_msg.assert_called_once_with('worker', 'log')
        mgr._handle_log_msg.assert_called_once_with('worker', 'log', 'bar')
        assert reply == mgr._handle_log_msg()
        assert next_steps is None

    def test_action_msg(self, mgr):
        mgr.config = {'msg_types': {'worker': {'foo': ''}}}
        mgr._handle_action_msg = Mock(
            name='_handle_action_msg', return_value=('reply', ['actions']))
        mgr._log_received_msg = Mock(name='_log_received_msg')
        message = {'source': 'worker', 'msg_type': 'foo', 'payload': 'bar'}
        reply, next_steps = mgr._message_handler(yaml.dump(message))
        mgr._log_received_msg.assert_called_once_with('worker', 'foo')
        mgr._handle_action_msg.assert_called_once_with('worker', 'foo', 'bar')
        assert reply, next_steps == ('reply', ['actions'])


def test_handle_undefined_msg(mgr):
    """Unit test for NowcastManager._handle_undefined_msg method.
    """
    mgr.name = 'nowcast_mgr'
    mgr.logger = Mock(name='logger')
    reply = mgr._handle_undefined_msg('worker', 'foo')
    assert mgr.logger.warning.call_count == 1
    expected = yaml.dump({
        'source': 'nowcast_mgr', 'msg_type': 'undefined msg', 'payload': None,
    })
    assert reply == expected


def test_log_received_msg(mgr):
    """Unit test for NowcastManager._log_received_msg method.
    """
    mgr.config = {'msg_types': {'worker': {'foo': 'bar'}}}
    mgr.logger = Mock(name='logger')
    mgr._log_received_msg('worker', 'foo')
    assert mgr.logger.debug.call_count == 1


def test_handle_need_msg(mgr):
    """Unit test for NowcastManager._handle_need_msg method.
    """
    mgr.name = 'nowcast_mgr'
    mgr.checklist = {'foo': 'bar'}
    reply = mgr._handle_need_msg('foo')
    expected = yaml.dump({
        'source': 'nowcast_mgr', 'msg_type': 'ack', 'payload': 'bar',
    })
    assert reply == expected


def test_handle_log_msg(mgr):
    """Unit test for NowcastManager._handle_log_msg method.
    """
    mgr.name = 'nowcast_mgr'
    mgr.worker_loggers = {'worker': Mock(name='worker_logger')}
    reply = mgr._handle_log_msg('worker', 'log.info', 'foo')
    mgr.worker_loggers['worker'].log.assert_called_once_with(
        logging.INFO, 'foo')
    expected = yaml.dump({
        'source': 'nowcast_mgr', 'msg_type': 'ack', 'payload': None,
        })
    assert reply == expected


class TestHandleActionMsg:
    """Unit tests for NowcastManager._handle_action_msg method.
    """
    def test_handle_action_msg_reply(self, mgr):
        mgr.name = 'nowcast_mgr'
        mgr._after_download_weather = Mock(name='_after_download_weather')
        reply, next_steps = mgr._handle_action_msg(
            'download_weather', 'success 00', True)
        expected = yaml.dump({
            'source': 'nowcast_mgr', 'msg_type': 'ack', 'payload': None,
            })
        assert reply == expected

    def test_handle_action_msg_next_steps(self, mgr):
        mgr.name = 'nowcast_mgr'
        mgr._after_download_weather = Mock(name='_after_download_weather')
        reply, next_steps = mgr._handle_action_msg(
            'download_weather', 'success 00', True)
        mgr._after_download_weather.assert_called_once_with(
            'success 00', True)
        assert next_steps == mgr._after_download_weather()


class TestAfterDownloadWeather:
    """Unit tests for the NowcastManager._after_download_weather method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure 00',
        'failure 06',
        'failure 12',
        'failure 18',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.config = {'run_types': []}
        actions = mgr._after_download_weather(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success 00',
        'success 06',
        'success 12',
        'success 18',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.config = {'run_types': []}
        actions = mgr._after_download_weather(msg_type, 'payload')
        expected = (
            mgr._update_checklist, ['download_weather', 'weather', 'payload'],
        )
        assert actions[0] == expected

    def test_success_06_launch_make_runoff_file_worker(self, mgr):
        mgr.config = {'run_types': []}
        actions = mgr._after_download_weather('success 06', 'payload')
        expected = (mgr._launch_worker, ['make_runoff_file'])
        assert actions[1] == expected

    @pytest.mark.parametrize('index, worker, worker_args', [
        (1, 'get_NeahBay_ssh', 'nowcast'),
        (2, 'grib_to_netcdf', 'nowcast+'),
    ])
    def test_success_12_launch_workers(self, index, worker, worker_args, mgr):
        mgr.config = {'run_types': ['nowcast']}
        actions = mgr._after_download_weather('success 12', 'payload')
        expected = (mgr._launch_worker, [worker, [worker_args]],)
        assert actions[index] == expected

    @pytest.mark.parametrize('index, worker, worker_args', [
        (2, 'get_NeahBay_ssh', 'forecast2'),
        (3, 'grib_to_netcdf', 'forecast2'),
    ])
    def test_success_06_launch_workers(self, index, worker, worker_args, mgr):
        mgr.config = {'run_types': ['forecast2']}
        actions = mgr._after_download_weather('success 06', 'payload')
        expected = (mgr._launch_worker, [worker, [worker_args]],)
        assert actions[index] == expected


class TestAfterGetNeahBaySSH:
    """Unit tests for the NowcastManager._after_get_NeahBay_ssh method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        actions = mgr._after_get_NeahBay_ssh(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success nowcast',
        'success forecast',
        'success forecast2',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        actions = mgr._after_get_NeahBay_ssh(msg_type, 'payload')
        expected = (
            mgr._update_checklist,
            ['get_NeahBay_ssh', 'Neah Bay ssh', 'payload'],
        )
        assert actions[0] == expected

    @pytest.mark.parametrize('host_type, host_name', [
        ('hpc host', 'orcinus-nowcast'),
        ('cloud host', 'west.cloud-nowcast'),
    ])
    def test_success_forecast_launch_upload_forcing_worker(
        self, host_type, host_name, mgr,
    ):
        mgr.config = {'run_types': ['forecast'], 'run': {host_type: host_name}}
        actions = mgr._after_get_NeahBay_ssh('success forecast', 'payload')
        expected = (
            mgr._launch_worker, ['upload_forcing', [host_name, 'ssh']],
        )
        assert actions[1] == expected


class TestAfterMakeRunoffFile:
    """Unit tests for the NowcastManager._after_make_runoff_file method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        actions = mgr._after_make_runoff_file(msg_type, 'payload')
        assert actions is None

    def test_update_checklist_on_success(self, mgr):
        actions = mgr._after_make_runoff_file('success', 'payload')
        expected = (
            mgr._update_checklist, ['make_runoff_file', 'rivers', 'payload'],
        )
        assert actions[0] == expected


class TestAfterGRIBtoNetCDF:
    """Unit tests for the NowcastManager._after_grib_to_netcdf method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        actions = mgr._after_grib_to_netcdf(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success nowcast+',
        'success forecast2',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        actions = mgr._after_grib_to_netcdf(msg_type, 'payload')
        expected = (
            mgr._update_checklist,
            ['grib_to_netcdf', 'weather forcing', 'payload'],
        )
        assert actions[0] == expected

    @pytest.mark.parametrize('host_type, host_name, run_type', [
        ('hpc host', 'orcinus-nowcast', 'nowcast+'),
        ('hpc host', 'orcinus-nowcast', 'forecast2'),
        ('cloud host', 'west.cloud-nowcast', 'nowcast+'),
        ('cloud host', 'west.cloud-nowcast', 'forecast2'),
    ])
    def test_success_launch_upload_forcing_worker(
        self, host_type, host_name, run_type, mgr,
    ):
        mgr.config = {
            'run_types': ['nowcast', 'forecast', 'forecast2', 'nowcast-green'],
            'run': {host_type: host_name}
        }
        actions = mgr._after_grib_to_netcdf(
            'success {}'.format(run_type), 'payload')
        expected = (
            mgr._launch_worker, ['upload_forcing', [host_name, run_type]],
        )
        assert actions[1] == expected
        assert len(actions) == 2

    def test_success_nowcastp_launch_make_forcing_links_nowcast_green(
        self, mgr,
    ):
        mgr.config = {
            'run_types': ['nowcast', 'forecast', 'forecast2', 'nowcast-green'],
            'run': {
                'cloud host': 'west.cloud-nowcast',
                'nowcast-green host': 'salish-nowcast',
            },
        }
        actions = mgr._after_grib_to_netcdf('success nowcast+', 'payload')
        expected = (
            mgr._launch_worker,
            ['make_forcing_links',
             ['salish-nowcast', 'nowcast-green', '--shared-storage']]
        )
        assert actions[2] == expected
        assert len(actions) == 3


class TestAfterUploadForcing:
    """Unit tests for the NowcastManager._after_upload_forcing method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
        'failure ssh',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        actions = mgr._after_upload_forcing(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success nowcast+',
        'success forecast2',
        'success ssh',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        payload = {'west.cloud': True}
        actions = mgr._after_upload_forcing(msg_type, payload)
        expected = (
            mgr._update_checklist,
            ['upload_forcing', 'forcing upload', payload],
        )
        assert actions[0] == expected

    @pytest.mark.parametrize('msg_type, upload_run_type', [
        ('success nowcast+', 'nowcast+'),
        ('success forecast2', 'forecast2'),
        ('success ssh', 'ssh'),
    ])
    def test_success_launch_make_forcing_links_worker(
        self, msg_type, upload_run_type, mgr,
    ):
        mgr.config = {
            'run_types': ['nowcast', 'forecast', 'forecast2'],
        }
        payload = {'west.cloud': True}
        actions = mgr._after_upload_forcing(msg_type, payload)
        expected = (
            mgr._launch_worker,
            ['make_forcing_links', ['west.cloud', upload_run_type]]
        )
        assert actions[1] == expected

    @pytest.mark.parametrize('msg_type', [
        'success nowcast+',
        'success forecast2',
        'success ssh',
    ])
    def test_success_run_type_disabled(self, msg_type, mgr):
        mgr.config = {'run_types': []}
        payload = {'west.cloud': True}
        actions = mgr._after_upload_forcing(msg_type, payload)
        assert len(actions) == 1


class TestAfterMakeForcingLinks:
    """Unit tests for the NowcastManager._after_make_forcing_links method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
        'failure ssh',
        'failure nowcast-green',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        actions = mgr._after_make_forcing_links(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success nowcast+',
        'success forecast2',
        'success ssh',
        'success nowcast-green',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.config = {'run_types': [], 'run': []}
        payload = {'west.cloud': True}
        actions = mgr._after_make_forcing_links(msg_type, payload)
        expected = (
            mgr._update_checklist,
            ['make_forcing_links', 'forcing links', payload]
        )
        assert actions[0] == expected

    @patch.object(mgr_module().lib, 'configure_logging')
    def test_success_configure_run_loggers(self, m_config_logging, mgr):
        mgr.config = {'run': {'cloud host': 'west.cloud'}}
        mgr.parsed_args = Mock(debug=False)
        payload = {'west.cloud': True}
        mgr._after_make_forcing_links('success nowcast+', payload)
        assert mgr.worker_loggers['run_NEMO'].name == 'run_NEMO'
        assert mgr.worker_loggers['watch_NEMO'].name == 'watch_NEMO'
        assert m_config_logging.call_count == 2

    @pytest.mark.parametrize('msg_type, run_type', [
        ('success nowcast+', 'nowcast'),
        ('success forecast2', 'forecast2'),
        ('success ssh', 'forecast'),
    ])
    def test_success_launch_run_NEMO_worker(self, msg_type, run_type, mgr):
        mgr.config = {'run': {'cloud host': 'west.cloud'}}
        mgr.parsed_args = Mock(debug=False)
        payload = {'west.cloud': True}
        with patch.object(mgr_module().lib, 'configure_logging'):
            actions = mgr._after_make_forcing_links(msg_type, payload)
        expected = (mgr._launch_worker, ['run_NEMO', [run_type], 'west.cloud'])
        assert actions[1] == expected


class TestAfterRunNEMO:
    """Unit tests for the NowcastManager._after_run_NEMO method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.worker_loggers = {
            'run_NEMO': Mock(name='logger', handlers=[Mock(name='handler')])
        }
        actions = mgr._after_run_NEMO(msg_type, 'payload')
        assert actions is None

    def test_update_checklist_on_success(self, mgr):
        mgr.worker_loggers = {
            'run_NEMO': Mock(name='logger', handlers=[Mock(name='handler')])
        }
        actions = mgr._after_run_NEMO('success', 'payload')
        expected = (
            mgr._update_checklist, ['run_NEMO', 'NEMO run', 'payload'],
        )
        assert actions[0] == expected

    def test_remove_worker_logger_handlers(self, mgr):
        m_handler = Mock(name='handler')
        m_worker_logger = Mock(name='logger', handlers=[m_handler])
        mgr.worker_loggers = {'run_NEMO': m_worker_logger}
        mgr._after_run_NEMO('success', 'payload')
        m_worker_logger.removeHandler.assert_called_once_with(m_handler)


class TestAfterWatchNEMO:
    """Unit tests for the NowcastManager._after_watch_NEMO method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.worker_loggers = {
            'watch_NEMO': Mock(name='logger', handlers=[Mock(name='handler')])
        }
        actions = mgr._after_watch_NEMO(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type, payload', [
        ('success nowcast', {'nowcast': {'run date': '2015-11-25'}}),
        ('success forecast', {'forecast': {'run date': '2015-11-25'}}),
        ('success forecast2', {'forecast2': {'run date': '2015-11-25'}}),
    ])
    def test_update_checklist_on_success(self, msg_type, payload, mgr):
        mgr.config = {'run': {'cloud host': 'west.cloud'}}
        mgr.worker_loggers = {
            'watch_NEMO': Mock(name='logger', handlers=[Mock(name='handler')])
        }
        actions = mgr._after_watch_NEMO(msg_type, payload)
        expected = (
            mgr._update_checklist, ['watch_NEMO', 'NEMO run', payload],
        )
        assert actions[0] == expected

    def test_remove_worker_logger_handlers(self, mgr):
        mgr.config = {'run': {'cloud host': 'west.cloud'}}
        m_handler = Mock(name='handler')
        m_worker_logger = Mock(name='logger', handlers=[m_handler])
        mgr.worker_loggers = {'watch_NEMO': m_worker_logger}
        payload = {'nowcast': {'run date': '2015-11-25'}}
        mgr._after_watch_NEMO('success nowcast', payload)
        m_worker_logger.removeHandler.assert_called_once_with(m_handler)

    @pytest.mark.parametrize('msg_type, run_type, payload', [
        ('success nowcast', 'nowcast',
            {'nowcast': {'run date': '2015-11-25'}}),
        ('success forecast', 'forecast',
            {'forecast': {'run date': '2015-11-25'}}),
        ('success forecast2', 'forecast2',
            {'forecast2': {'run date': '2015-11-25'}}),
    ])
    def test_success_launch_download_results_worker(
        self, msg_type, run_type, payload, mgr,
    ):
        mgr.config = {'run': {'cloud host': 'west.cloud'}}
        mgr.worker_loggers = {
            'watch_NEMO': Mock(name='logger', handlers=[Mock(name='handler')])
        }
        actions = mgr._after_watch_NEMO(msg_type, payload)
        expected = (
            mgr._launch_worker,
            ['download_results',
                ['west.cloud', run_type, '--run-date', '2015-11-25']],
        )
        assert actions[-1] == expected

    def test_success_nowcast_launch_get_NeahBay_ssh_worker(self, mgr):
        mgr.config = {'run': {'cloud host': 'west.cloud'}}
        mgr.worker_loggers = {
            'watch_NEMO': Mock(name='logger', handlers=[Mock(name='handler')])
        }
        payload = {'nowcast': {'run date': '2015-11-25'}}
        actions = mgr._after_watch_NEMO('success nowcast', payload)
        expected = (mgr._launch_worker, ['get_NeahBay_ssh', ['forecast']])
        assert actions[1] == expected


class TestAfterDownloadResults:
    """Unit tests for the NowcastManager._after_download_results method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        actions = mgr._after_download_results(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success nowcast',
        'success forecast',
        'success forecast2',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.checklist = {
            'NEMO run': {
                'nowcast': {'run date': '2015-11-24'},
                'forecast': {'run date': '2015-11-24'},
                'forecast2': {'run date': '2015-11-24'},
            },
        }
        actions = mgr._after_download_results(msg_type, 'payload')
        expected = (
            mgr._update_checklist,
            ['download_results', 'results files', 'payload'],
        )
        assert actions[0] == expected

    @pytest.mark.parametrize('msg_type, run_type, plot_type', [
        ('success nowcast', 'nowcast', 'research'),
        ('success forecast', 'forecast', 'publish'),
        ('success forecast2', 'forecast2', 'publish'),
    ])
    def test_success_launch_make_plot_worker(
        self, msg_type, run_type, plot_type, mgr,
    ):
        mgr.checklist = {
            'NEMO run': {
                'nowcast': {'run date': '2015-11-24'},
                'forecast': {'run date': '2015-11-24'},
                'forecast2': {'run date': '2015-11-24'},
            },
        }
        actions = mgr._after_download_results(msg_type, 'payload')
        expected = (
            mgr._launch_worker,
            ['make_plots', [run_type, plot_type, '--run-date', '2015-11-24']],
        )
        assert actions[1] == expected


class TestAfterMakePlots:
    """Unit tests for the NowcastManager._after_make_plots method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast research',
        'failure nowcast publish',
        'failure nowcast comparison',
        'failure forecast publish',
        'failure forecast2 publish',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        actions = mgr._after_make_plots(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success nowcast research',
        'success nowcast publish',
        'success nowcast comparison',
        'success forecast publish',
        'success forecast2 publish',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.checklist = {
            'NEMO run': {
                'nowcast': {'run date': '2015-11-25'},
                'forecast': {'run date': '2015-11-25'},
                'forecast2': {'run date': '2015-11-25'},
            },
        }
        actions = mgr._after_make_plots(msg_type, 'payload')
        expected = (mgr._update_checklist, ['make_plots', 'plots', 'payload'])
        assert actions[0] == expected

    @pytest.mark.parametrize('msg_type', [
        'success nowcast research',
        'success nowcast publish',
        'success nowcast comparison',
        'success forecast publish',
        'success forecast2 publish',
    ])
    def test_success_launch_make_site_page_worker(self, msg_type, mgr):
        _, run_type, page_type = msg_type.split()
        mgr.checklist = {
            'NEMO run': {
                'nowcast': {'run date': '2015-11-25'},
                'forecast': {'run date': '2015-11-25'},
                'forecast2': {'run date': '2015-11-25'},
            },
        }
        actions = mgr._after_make_plots(msg_type, 'payload')
        expected = (
            mgr._launch_worker,
            ['make_site_page', [run_type, page_type,
             '--run-date', '2015-11-25']],
        )
        assert actions[1] == expected


class TestAfterMakeSitePage:
    """Unit tests for the NowcastManager._after_make_site_page method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure index',
        'failure research',
        'failure publish',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        actions = mgr._after_make_site_page(msg_type, 'payload')
        assert actions is None

    @pytest.mark.parametrize('msg_type', [
        'success index',
        'success research',
        'success publish',
    ])
    def test_update_checklist_on_success(self, msg_type, mgr):
        mgr.checklist = {
            'NEMO run': {
                'nowcast': {'run date': '2015-11-25'},
                'forecast': {'run date': '2015-11-25'},
                'forecast2': {'run date': '2015-11-25'},
            },
        }
        actions = mgr._after_make_site_page(msg_type, 'payload')
        expected = (
            mgr._update_checklist,
            ['make_site_page', 'salishsea site pages', 'payload'],
        )
        assert actions[0] == expected

    @pytest.mark.parametrize('msg_type', [
        'success index',
        'success publish',
    ])
    def test_success_launch_push_to_web_worker(self, msg_type, mgr):
        actions = mgr._after_make_site_page(msg_type, 'payload')
        expected = (mgr._launch_worker, ['push_to_web'])
        assert actions[1] == expected

    def test_success_research_launch_make_plots_worker_nowcast_publish(
        self, mgr
    ):
        mgr.checklist = {
            'NEMO run': {
                'nowcast': {'run date': '2015-11-25'},
                'forecast': {'run date': '2015-11-25'},
                'forecast2': {'run date': '2015-11-25'},
            },
        }
        actions = mgr._after_make_site_page('success research', 'payload')
        expected = (
            mgr._launch_worker,
            ['make_plots', ['nowcast', 'publish', '--run-date', '2015-11-25']],
        )
        assert actions[1] == expected


class TestAfterPushToWeb:
    """Unit tests for the NowcastManager._after_push_to_web method.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_action_msg_types(self, msg_type, mgr):
        mgr.checklist = {'salishsea site pages': {}}
        actions = mgr._after_push_to_web(msg_type, 'payload')
        assert actions is None

    def test_update_checklist_on_success(self, mgr):
        mgr.checklist = {'salishsea site pages': {}}
        actions = mgr._after_push_to_web('success', 'payload')
        expected = (
            mgr._update_checklist,
            ['push_to_web', 'push to salishsea site', 'payload'],
        )
        assert actions[0] == expected

    def test_finish_the_day(self, mgr):
        mgr.checklist = {'salishsea site pages': {'finish the day': True}}
        actions = mgr._after_push_to_web('success', 'payload')
        expected = (mgr._finish_the_day, [])
        assert actions[1] == expected


class TestUpdateChecklist:
    """Unit tests for the NowcastManager._update_checklist method.
    """
    def test_update_existing_value(self, mgr):
        mgr.checklist = {'foo': 'bar'}
        mgr._write_checklist_to_disk = Mock(name='_write_checklist_to_disk')
        mgr._update_checklist('worker', 'foo', 'baz')
        assert mgr.checklist['foo'] == 'baz'

    def test_keyerror_adds_key_and_value(self, mgr):
        mgr.checklist = {'foo': 'bar'}
        mgr._write_checklist_to_disk = Mock(name='_write_checklist_to_disk')
        mgr._update_checklist('worker', 'fop', 'baz')
        assert mgr.checklist == {'foo': 'bar', 'fop': 'baz'}

    def test_log_info_msg(self, mgr):
        mgr._write_checklist_to_disk = Mock(name='_write_checklist_to_disk')
        mgr.logger = Mock(name='logger')
        mgr._update_checklist('worker', 'foo', 'baz')
        mgr.logger.info.assert_called_once_with(
            'checklist updated with foo items from worker worker')

    def test_yaml_dump_checklist_to_disk(self, mgr):
        mgr._write_checklist_to_disk = Mock(name='_write_checklist_to_disk')
        mgr._update_checklist('worker', 'foo', 'baz')
        mgr._write_checklist_to_disk.assert_called_once_with()


class TestFinishTheDay:
    """Unit tests for the NowcastManager._finish_the_day method.
    """
    def test_checklist_is_logged(self, mgr):
        mgr.checklist = {'foo': 'bar'}
        mgr.checklist_logger = Mock(name='checklist_logger')
        mgr._rotate_log_files = Mock(name='_rotate_log_files')
        with patch.object(mgr, '_write_checklist_to_disk'):
            mgr._finish_the_day()
        mgr.checklist_logger.info.assert_called_once_with(
            "checklist:\n{'foo': 'bar'}")

    def test_checklist_cleared_and_written_to_disk(self, mgr):
        mgr.checklist = {'foo': 'bar'}
        mgr.checklist_logger = Mock(name='checklist_logger')
        mgr._write_checklist_to_disk = Mock(name='_write_checklist_to_disk')
        mgr._rotate_log_files = Mock(name='_rotate_log_files')
        mgr._finish_the_day()
        assert mgr.checklist == {}
        mgr._write_checklist_to_disk.assert_called_once_with()

    def test_rotate_log_files(self, mgr):
        mgr.checklist_logger = Mock(name='checklist_logger')
        mgr._rotate_log_files = Mock(name='_rotate_log_files')
        with patch.object(mgr, '_write_checklist_to_disk'):
            mgr._finish_the_day()
        mgr._rotate_log_files.assert_called_once_with()
