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
"""Unit tests for SalishSeaCast run_NEMO_hindcast worker.
"""
from types import SimpleNamespace
from unittest.mock import patch, call

import arrow
import nemo_nowcast

from nowcast.workers import run_NEMO_hindcast


@patch(
    'nowcast.workers.run_NEMO_hindcast.NowcastWorker',
    spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker.call_args
        assert args == ('run_NEMO_hindcast',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        run_NEMO_hindcast.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_prev_run_date_option(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('--prev-run-date',)
        assert kwargs['default'] is None
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            run_NEMO_hindcast.run_NEMO_hindcast,
            run_NEMO_hindcast.success,
            run_NEMO_hindcast.failure,
        )


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(host_name='cedar')
        run_NEMO_hindcast.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(host_name='cedar')
        msg_type = run_NEMO_hindcast.success(parsed_args)
        assert msg_type == f'success'


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger):
        parsed_args = SimpleNamespace(host_name='cedar')
        run_NEMO_hindcast.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(host_name='cedar')
        msg_type = run_NEMO_hindcast.failure(parsed_args)
        assert msg_type == f'failure'


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch(
    'nowcast.workers.run_NEMO_hindcast._get_prev_run_queue_info',
    autospec=True,
    return_value=(arrow.get('2018-01-01'), 12345678)
)
@patch(
    'nowcast.workers.run_NEMO_hindcast._get_prev_run_namelist_info',
    autospec=True
)
@patch('nowcast.workers.run_NEMO_hindcast._edit_namelist_time', autospec=True)
@patch('nowcast.workers.run_NEMO_hindcast._edit_run_desc', autospec=True)
@patch('nowcast.workers.run_NEMO_hindcast._launch_run', autospec=True)
class TestRunNEMO_Hindcast:
    """Unit tests for run_NEMO_hindcast() function.
    """

    config = {
        'run': {
            'hindcast hosts': {
                'cedar': {
                    'users': 'allen,dlatorne',
                    'scratch dir': '/scratch/dlatorne/hindcast',
                    'salishsea cmd': 'hindcast-sys/hincast-env/bin/salishsea',
                }
            }
        }
    }

    def test_checklist_with_prev_run_date(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_logger
    ):
        parsed_args = SimpleNamespace(
            host_name='cedar', prev_run_date=arrow.get('2018-01-01')
        )
        checklist = run_NEMO_hindcast.run_NEMO_hindcast(
            parsed_args, self.config
        )
        expected = {
            'hindcast': {
                'host': 'cedar',
                'run id': '01feb18hindcast',
            }
        }
        assert checklist == expected

    def test_checklist_without_prev_run_date(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_logger
    ):
        parsed_args = SimpleNamespace(host_name='cedar', prev_run_date=None)
        checklist = run_NEMO_hindcast.run_NEMO_hindcast(
            parsed_args, self.config
        )
        expected = {
            'hindcast': {
                'host': 'cedar',
                'run id': '01feb18hindcast',
            }
        }
        assert checklist == expected


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch('nowcast.workers.run_NEMO_hindcast._cmd_in_subprocess', autospec=True)
@patch('nowcast.workers.run_NEMO_hindcast.f90nml.patch', autospec=True)
class TestEditNamelistTime:
    """Unit tests for _edit_namelist_time() function.
    """

    config = {
        'run': {
            'hindcast hosts': {
                'cedar': {
                    'run prep dir': 'hindcast-sys/runs',
                }
            }
        }
    }

    def test_download_namelist_time(
        self, m_patch, m_cmd_in_subprocess, m_logger
    ):
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            'cedar', prev_namelist_info, arrow.get('2018-02-01'), self.config
        )
        assert m_cmd_in_subprocess.call_args_list[0] == call(
            'scp cedar:hindcast-sys/runs/namelist.time '
            '/tmp/hindcast.namelist.time'
        )

    def test_patch_namelist_time(self, m_patch, m_cmd_in_subprocess, m_logger):
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            'cedar', prev_namelist_info, arrow.get('2018-02-01'), self.config
        )
        m_patch.assert_called_once_with(
            '/tmp/hindcast.namelist.time', {
                'namrun': {
                    'nn_it000':
                        2717280 + 1,
                    'nn_itend':
                        2777760,
                    'nn_date0':
                        20180201,
                    'nn_stocklist': [
                        2738880, 2760480, 2777760, 0, 0, 0, 0, 0, 0, 0
                    ],
                }
            }, '/tmp/patched_hindcast.namelist.time'
        )

    def test_upload_namelist_time(
        self, m_patch, m_cmd_in_subprocess, m_logger
    ):
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            'cedar', prev_namelist_info, arrow.get('2018-02-01'), self.config
        )
        assert m_cmd_in_subprocess.call_args_list[1] == call(
            'scp /tmp/patched_hindcast.namelist.time '
            'cedar:hindcast-sys/runs/patched_namelist.time'
        )


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch('nowcast.workers.run_NEMO_hindcast._cmd_in_subprocess', autospec=True)
class TestEditRunDesc:
    """Unit tests for _edit_run_desc() function.
    """

    config = {
        'run': {
            'hindcast hosts': {
                'cedar': {
                    'scratch dir': '/scratch/dlatorne/hindcast',
                    'run prep dir': 'hindcast-sys/runs',
                }
            }
        }
    }

    def test_download_run_desc_template(self, m_cmd_in_subprocess, m_logger):
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_run_desc(
            'cedar', arrow.get('2018-01-01'), prev_namelist_info,
            arrow.get('2018-02-01'), self.config
        )
        assert m_cmd_in_subprocess.call_args_list[0] == call(
            'scp cedar:hindcast-sys/runs/hindcast_template.yaml '
            '/tmp/hindcast.namelist.time'
        )

    def test_upload_run_desc_template(self, m_cmd_in_subprocess, m_logger):
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_run_desc(
            'cedar', arrow.get('2018-01-01'), prev_namelist_info,
            arrow.get('2018-02-01'), self.config
        )
        assert m_cmd_in_subprocess.call_args_list[1] == call(
            'scp /tmp/patched_hindcast.namelist.time '
            'cedar:hindcast-sys/runs/01feb18hindcast.yaml'
        )
