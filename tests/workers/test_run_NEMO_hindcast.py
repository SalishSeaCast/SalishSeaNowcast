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
import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, call, Mock

import arrow
import nemo_nowcast
import pytest

import nowcast.ssh_sftp
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

    def test_add_full_month_option(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('--full-month',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_add_prev_run_date_option(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ('--prev-run-date',)
        assert kwargs['default'] is None
        assert 'help' in kwargs

    def test_add_walltime_option(self, m_worker):
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[3]
        assert args == ('--walltime',)
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
    'nowcast.workers.watch_NEMO_agrif.ssh_sftp.sftp',
    return_value=(Mock(name='ssh_client'), Mock(name='sftp_client')),
)
@patch(
    'nowcast.workers.run_NEMO_hindcast._get_prev_run_queue_info',
    autospec=True,
    return_value=(arrow.get('2018-01-01'), 12345678)
)
@patch(
    'nowcast.workers.run_NEMO_hindcast._get_prev_run_namelist_info',
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
                    'ssh key': 'SalishSeaNEMO-nowcast_id_rsa',
                    'users': 'allen,dlatorne',
                    'scratch dir': '/scratch/dlatorne/hindcast',
                    'salishsea cmd': 'hindcast-sys/hincast-env/bin/salishsea',
                }
            }
        }
    }

    @pytest.mark.parametrize('full_month', [True, False])
    def test_checklist_run_date_in_future(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_sftp,
        m_logger, full_month
    ):
        parsed_args = SimpleNamespace(
            host_name='cedar',
            full_month=full_month,
            prev_run_date=arrow.get('2018-06-01')
        )
        with patch('nowcast.workers.run_NEMO_hindcast.arrow.now') as m_now:
            m_now.return_value = arrow.get('2018-06-08')
            checklist = run_NEMO_hindcast.run_NEMO_hindcast(
                parsed_args, self.config
            )
        expected = {
            'hindcast': {
                'host': 'cedar',
                'run id': 'None',
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        'full_month, prev_run_date, expected_run_id',
        [
            (True, arrow.get('2018-01-01'), '01feb18hindcast'),
            (False, arrow.get('2018-07-01'), '11jul18hindcast'),
            (False, arrow.get('2018-07-11'), '21jul18hindcast'),
            (False, arrow.get('2018-07-21'), '01aug18hindcast'),  # 31 day mo
            (False, arrow.get('2018-06-21'), '01jul18hindcast'),  # 30 day mo
            (False, arrow.get('2018-02-21'), '01mar18hindcast'),  # feb
            (False, arrow.get('2016-02-21'), '01mar16hindcast'),  # leap year
            (False, arrow.get('2017-12-21'), '01jan18hindcast'),  # year end
        ]
    )
    def test_checklist_with_prev_run_date(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_sftp,
        m_logger, full_month, prev_run_date, expected_run_id
    ):
        parsed_args = SimpleNamespace(
            host_name='cedar',
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=None,
        )
        checklist = run_NEMO_hindcast.run_NEMO_hindcast(
            parsed_args, self.config
        )
        expected = {
            'hindcast': {
                'host': 'cedar',
                'run id': expected_run_id,
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        'full_month, prev_run_date, expected_run_id',
        [
            (True, arrow.get('2018-01-01'), '01feb18hindcast'),
            (False, arrow.get('2018-07-01'), '11jul18hindcast'),
            (False, arrow.get('2018-07-11'), '21jul18hindcast'),
            (False, arrow.get('2018-07-21'), '01aug18hindcast'),  # 31 day mo
            (False, arrow.get('2018-06-21'), '01jul18hindcast'),  # 30 day mo
            (False, arrow.get('2018-02-21'), '01mar18hindcast'),  # feb
            (False, arrow.get('2016-02-21'), '01mar16hindcast'),  # leap year
            (False, arrow.get('2017-12-21'), '01jan18hindcast'),  # year end
        ]
    )
    def test_checklist_without_prev_run_date(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_sftp,
        m_logger, full_month, prev_run_date, expected_run_id
    ):
        parsed_args = SimpleNamespace(
            host_name='cedar',
            full_month=full_month,
            prev_run_date=None,
            walltime=None,
        )
        m_get_prev_run_queue_info.return_value = (prev_run_date, 12345678)
        checklist = run_NEMO_hindcast.run_NEMO_hindcast(
            parsed_args, self.config
        )
        expected = {
            'hindcast': {
                'host': 'cedar',
                'run id': expected_run_id,
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        'full_month, prev_run_date, expected_run_date, expected_run_days',
        [
            (True, arrow.get('2018-01-01'), arrow.get('2018-02-01'),
             28),  # 28d run
            (True, arrow.get('2016-01-01'), arrow.get('2016-02-01'),
             29),  # 29d run
            (True, arrow.get('2018-02-01'), arrow.get('2018-03-01'),
             31),  # 31d run
            (True, arrow.get('2018-03-01'), arrow.get('2018-04-01'),
             30),  # 30d run
            (False, arrow.get('2018-07-01'), arrow.get('2018-07-11'),
             10),  # 10d run
            (False, arrow.get('2018-07-11'), arrow.get('2018-07-21'),
             11),  # 11d run
            (False, arrow.get('2018-02-11'), arrow.get('2018-02-21'),
             8),  # 8d run
            (False, arrow.get('2016-02-11'), arrow.get('2016-02-21'),
             9),  # 9d run
            (False, arrow.get('2018-07-21'), arrow.get('2018-08-01'),
             10),  # 31 day mo
            (False, arrow.get('2018-06-21'), arrow.get('2018-07-01'),
             10),  # 30 day mo
            (False, arrow.get('2018-02-21'), arrow.get('2018-03-01'),
             10),  # feb
            (False, arrow.get('2016-02-21'), arrow.get('2016-03-01'),
             10),  # leap year
            (False, arrow.get('2017-12-21'), arrow.get('2018-01-01'),
             10),  # year end
        ]
    )
    def test_edit_namelist_time_run_date(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_sftp,
        m_logger, full_month, prev_run_date, expected_run_date,
        expected_run_days
    ):
        parsed_args = SimpleNamespace(
            host_name='cedar',
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=None,
        )
        run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, self.config)
        m_edit_namelist_time.assert_called_once_with(
            m_sftp()[1], 'cedar', m_get_prev_run_namelist_info(),
            expected_run_date, expected_run_days, self.config
        )

    @pytest.mark.parametrize(
        'full_month, prev_run_date, walltime, expected_run_date, expected_walltime',
        [
            (
                True, arrow.get('2018-07-01'), None, arrow.get('2018-08-01'),
                '08:30:00'
            ),  # default
            (
                True, arrow.get('2018-07-01'), '12:00:00',
                arrow.get('2018-08-01'), '12:00:00'
            ),
            (
                False, arrow.get('2018-07-01'), None, arrow.get('2018-07-11'),
                '03:00:00'
            ),  # default
            (
                False, arrow.get('2018-07-01'), '06:00:00',
                arrow.get('2018-07-11'), '06:00:00'
            ),
        ]
    )
    def test_edit_run_desc_walltime(
        self, m_launch_run, m_edit_run_desc, m_edit_namelist_time,
        m_get_prev_run_namelist_info, m_get_prev_run_queue_info, m_sftp,
        m_logger, full_month, prev_run_date, walltime, expected_run_date,
        expected_walltime
    ):
        parsed_args = SimpleNamespace(
            host_name='cedar',
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=walltime,
        )
        run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, self.config)
        m_edit_run_desc.assert_called_once_with(
            m_sftp()[1], 'cedar', prev_run_date,
            m_get_prev_run_namelist_info(), expected_run_date,
            expected_walltime, self.config
        )


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch(
    'nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command',
    autospec=True
)
class TestGetPrevRunQueueInfo:
    """Unit tests for _get_prev_run_queue_info() function.
    """

    config = {
        'run': {
            'hindcast hosts': {
                'cedar': {
                    'users': 'allen,dlatorne',
                }
            }
        }
    }

    def test_no_job_found_on_queue(self, m_ssh_exec_cmd, m_logger):
        m_ssh_exec_cmd.return_value = 'header\n'
        m_ssh_client = Mock(name='ssh_client')
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_prev_run_queue_info(
                m_ssh_client, 'cedar', self.config
            )
        assert m_logger.error.called

    def test_found_prev_hindcast_job(self, m_ssh_exec_cmd, m_logger):
        m_ssh_exec_cmd.return_value = ('header\n' '12345678 01may18hindcast\n')
        m_ssh_client = Mock(name='ssh_client')
        prev_run_date, job_id = run_NEMO_hindcast._get_prev_run_queue_info(
            m_ssh_client, 'cedar', self.config
        )
        assert prev_run_date == arrow.get('2018-05-01')
        assert job_id == 12345678
        assert m_logger.info.called

    def test_no_prev_hindcast_job_found(self, m_ssh_exec_cmd, m_logger):
        m_ssh_exec_cmd.return_value = (
            'header\n'
            '12345678 07may18nowcast-agrif\n'
        )
        m_ssh_client = Mock(name='ssh_client')
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_prev_run_queue_info(
                m_ssh_client, 'cedar', self.config
            )
        assert m_logger.error.called


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch(
    'nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command',
    autospec=True
)
@patch('nowcast.workers.run_NEMO_hindcast.f90nml.read', autospec=True)
class TestGetPrevRunNamelistInfo:
    """Unit test for _get_prev_run_namelist_info() function.
    """

    config = {
        'run': {
            'hindcast hosts': {
                'cedar': {
                    'scratch dir': '/scratch/dlatorne/hindcast',
                }
            }
        }
    }

    def test_get_prev_run_namelist_info(
        self, m_f90nml_read, m_ssh_exec_cmd, m_logger
    ):
        m_ssh_client = Mock(name='ssh_client')
        m_sftp_client = Mock(name='sftp_client')
        m_ssh_exec_cmd.return_value = (
            '/scratch/dlatorne/hindcast/01may18hindcast_xxx/namelist_cfg\n'
        )
        p_named_tmp_file = patch(
            'nowcast.workers.run_NEMO_hindcast.tempfile.NamedTemporaryFile',
            autospec=True
        )
        m_f90nml_read.return_value = {
            'namrun': {
                'nn_itend': 2717280
            },
            'namdom': {
                'rn_rdt': 40.0
            },
        }
        with p_named_tmp_file as m_named_tmp_file:
            prev_namelist_info = run_NEMO_hindcast._get_prev_run_namelist_info(
                m_ssh_client, m_sftp_client, 'cedar', arrow.get('2018-05-01'),
                self.config
            )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            'ls -d /scratch/dlatorne/hindcast/01may18*/namelist_cfg', 'cedar',
            m_logger
        )
        m_sftp_client.get.assert_called_once_with(
            '/scratch/dlatorne/hindcast/01may18hindcast_xxx/namelist_cfg',
            m_named_tmp_file().__enter__().name
        )
        assert m_logger.info.called
        assert prev_namelist_info == SimpleNamespace(itend=2717280, rdt=40.0)


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
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

    def test_download_namelist_time(self, m_patch, m_logger):
        m_sftp_client = Mock(name='sftp_client')
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            m_sftp_client, 'cedar', prev_namelist_info,
            arrow.get('2018-02-01'), 28, self.config
        )
        m_sftp_client.get.assert_called_once_with(
            'hindcast-sys/runs/namelist.time', '/tmp/hindcast.namelist.time'
        )

    @pytest.mark.parametrize(
        'run_date, run_days, expected_itend, expected_stocklist',
        [
            (
                arrow.get('2018-03-01'), 31, 2784240,
                [2738880, 2760480, 2784240, 0, 0, 0, 0, 0, 0, 0]
            ),  # 31 day month
            (
                arrow.get('2018-02-01'), 28, 2777760,
                [2738880, 2760480, 2777760, 0, 0, 0, 0, 0, 0, 0]
            ),  # February
            (
                arrow.get('2016-02-01'), 29, 2779920,
                [2738880, 2760480, 2779920, 0, 0, 0, 0, 0, 0, 0]
            ),  # leap year
            (
                arrow.get('2018-04-01'), 30, 2782080,
                [2738880, 2760480, 2782080, 0, 0, 0, 0, 0, 0, 0]
            ),  # 30 day month
            (
                arrow.get('2018-04-01'), 10, 2738880,
                [2738880, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ),  # 10d run
            (
                arrow.get('2018-04-11'), 10, 2738880,
                [2738880, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ),  # 10d run
            (
                arrow.get('2018-02-21'), 8, 2734560,
                [2734560, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ),  # 8d run
            (
                arrow.get('2016-02-21'), 9, 2736720,
                [2736720, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ),  # 9d run
            (
                arrow.get('2018-03-21'), 11, 2741040,
                [2741040, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            ),  # 11d run
        ]
    )
    def test_patch_namelist_time(
        self, m_patch, m_logger, run_date, run_days, expected_itend,
        expected_stocklist
    ):
        sftp_client = Mock(name='sftp_client')
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            sftp_client, 'cedar', prev_namelist_info, run_date, run_days,
            self.config
        )
        m_patch.assert_called_once_with(
            '/tmp/hindcast.namelist.time', {
                'namrun': {
                    'nn_it000': 2717280 + 1,
                    'nn_itend': expected_itend,
                    'nn_date0': int(run_date.format('YYYYMMDD')),
                    'nn_stocklist': expected_stocklist,
                }
            }, '/tmp/patched_hindcast.namelist.time'
        )

    def test_upload_namelist_time(self, m_patch, m_logger):
        m_sftp_client = Mock(name='sftp_client')
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            m_sftp_client, 'cedar', prev_namelist_info,
            arrow.get('2018-02-01'), 28, self.config
        )
        m_sftp_client.put.assert_called_once_with(
            '/tmp/patched_hindcast.namelist.time',
            'hindcast-sys/runs/namelist.time'
        )


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch(
    'nowcast.workers.run_NEMO_agrif.yaml.safe_load',
    return_value={
        'run_id': '',
        'restart': {
            'restart.nc': '',
            'restart_trc.nc': '',
        },
        'walltime': '06:00:00',
    },
    autospec=True
)
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

    def test_download_run_desc_template(self, m_safe_load, m_logger, tmpdir):
        m_sftp_client = Mock(name='sftp_client')
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure('hindcast_tmpl.yaml')
        run_NEMO_hindcast._edit_run_desc(
            m_sftp_client,
            'cedar',
            arrow.get('2018-01-01'),
            prev_namelist_info,
            arrow.get('2018-02-01'),
            '03:00:00',
            self.config,
            yaml_tmpl=Path(str(yaml_tmpl))
        )
        m_sftp_client.get.assert_called_once_with(
            'hindcast-sys/runs/hindcast_template.yaml', yaml_tmpl
        )

    @pytest.mark.parametrize('walltime', ['03:00:00', '08:30:00', '12:00:00'])
    @patch('nowcast.workers.run_NEMO_hindcast.yaml.safe_dump', autospec=True)
    def test_edit_run_desc(
        self, m_safe_dump, m_safe_load, m_logger, walltime, tmpdir
    ):
        m_sftp_client = Mock(name='sftp_client')
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure('hindcast_tmpl.yaml')
        with patch('nowcast.workers.run_NEMO_hindcast.Path.open') as m_open:
            run_NEMO_hindcast._edit_run_desc(
                m_sftp_client,
                'cedar',
                arrow.get('2018-05-01'),
                prev_namelist_info,
                arrow.get('2018-06-01'),
                walltime,
                self.config,
                yaml_tmpl=Path(str(yaml_tmpl))
            )
        m_safe_dump.assert_called_once_with({
            'run_id': '01jun18hindcast',
            'restart': {
                'restart.nc':
                    '/scratch/dlatorne/hindcast/01may18/SalishSea_02717280_restart.nc',
                'restart_trc.nc':
                    '/scratch/dlatorne/hindcast/01may18/SalishSea_02717280_restart_trc.nc',
            },
            'walltime': walltime,
        },
                                            m_open().__enter__(),
                                            default_flow_style=False)

    def test_upload_run_desc(self, m_safe_load, m_logger, tmpdir):
        m_sftp_client = Mock(name='sftp_client')
        prev_namelist_info = SimpleNamespace(itend=2717280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure('hindcast_tmpl.yaml')
        run_NEMO_hindcast._edit_run_desc(
            m_sftp_client,
            'cedar',
            arrow.get('2018-01-01'),
            prev_namelist_info,
            arrow.get('2018-02-01'),
            '03:00:00',
            self.config,
            yaml_tmpl=Path(str(yaml_tmpl))
        )
        m_sftp_client.put.assert_called_once_with(
            yaml_tmpl, 'hindcast-sys/runs/01feb18hindcast.yaml'
        )


@patch('nowcast.workers.run_NEMO_hindcast.logger', autospec=True)
@patch(
    'nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command',
    autospec=True
)
class TestLaunchRun:
    """Unit tests for _launch_run() function.
    """

    config = {
        'run': {
            'hindcast hosts': {
                'cedar': {
                    'scratch dir': 'scratch',
                    'run prep dir': 'runs',
                    'salishsea cmd': 'bin/salishsea',
                }
            }
        }
    }

    def test_launch_run(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name='ssh_client')
        run_NEMO_hindcast._launch_run(
            m_ssh_client,
            'cedar',
            '01may18hindcast',
            prev_job_id=None,
            config=self.config
        )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            'bin/salishsea run runs/01may18hindcast.yaml scratch/01may18',
            'cedar', m_logger
        )

    def test_launch_run_with_prev_job_id(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name='ssh_client')
        run_NEMO_hindcast._launch_run(
            m_ssh_client,
            'cedar',
            '01may18hindcast',
            prev_job_id=12345678,
            config=self.config
        )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            'bin/salishsea run runs/01may18hindcast.yaml scratch/01may18 '
            '--waitjob 12345678 --nocheck-initial-conditions', 'cedar',
            m_logger
        )

    def test_ssh_error(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name='ssh_client')
        m_ssh_exec_cmd.side_effect = nowcast.ssh_sftp.SSHCommandError(
            'cmd', 'stdout', 'stderr'
        )
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._launch_run(
                m_ssh_client,
                'cedar',
                '01may18hindcast',
                prev_job_id=None,
                config=self.config
            )
        m_logger.error.assert_called_once_with('stderr')
