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

"""Unit tests for Salish Sea NEMO nowcast run_NEMO36 worker.
"""
from unittest.mock import (
    patch,
    Mock,
)

import arrow
import pytest


@pytest.fixture
def worker_module():
    from nowcast.workers import run_NEMO36
    return run_NEMO36


@pytest.fixture
def config():
    return {
        'bathymetry': 'bathy_meter_SalishSea.nc',
        'run_types': {
            'nowcast': 'SalishSea',
            'forecast': 'SalishSea',
            'forecast2': 'SalishSea',
            'nowcast-green': 'SOG',
        },
        'run': {
            'salish': {
                'run_prep_dir': '/nowcast-sys/nowcast/',
                'mpi decomposition': '3x5',
                'nowcast_dir': '/nowcast-sys/nowcast/',
                'results': {
                    'nowcast': '/results/SalishSea/nowcast/',
                    'nowcast-green': '/results/SalishSea/nowcast-green/',
                    'forecast': '/results/SalishSea/forecast/',
                    'forecast2': '/results/SalishSea/forecast2/',
                }}}
    }


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

    def test_add_run_date_arg(self, m_worker, worker_module, lib_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[2]
        assert args == ('--run-date',)
        assert kwargs['type'] == lib_module.arrow_date
        assert kwargs['default'] == arrow.now('Canada/Pacific').floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.run_NEMO,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-28'))
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-28'))
        msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success forecast2'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-28'))
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-28'))
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure forecast2'


class TestCalcNewNamelistLines:
    """Unit tests for _calc_new_namelist_lines() function.
    """
    @pytest.mark.parametrize(
        'run_type, run_date, prev_itend, dt_per_day, it000, itend, date0, '
        'restart', [
            ('nowcast', arrow.get('2015-12-30'), 2160, 2160, 2161, 4320,
                '20151230', 2160),
            ('nowcast-green', arrow.get('2015-12-30'), 2160, 2160, 2161, 4320,
                '20151230', 2160),
            ('forecast', arrow.get('2015-12-30'), 2160, 2160, 2161, 4860,
                '20151230', 2160),
            ('forecast2', arrow.get('2015-12-30'), 2700, 2160, 2161, 4860,
                '20151230', 2160),
        ])
    def test_calc_new_namelist_lines(
        self, run_date, run_type, prev_itend, dt_per_day, it000, itend, date0,
        restart, worker_module,
    ):
        lines = [
            '  nn_it000 = 1\n',
            '  nn_itend = 2160\n',
            '  nn_date0 = 20160102\n',
        ]
        new_lines, restart_timestep = worker_module._calc_new_namelist_lines(
            run_date, run_type, 1, prev_itend, dt_per_day, lines)
        assert new_lines == [
            '  nn_it000 = {}\n'.format(it000),
            '  nn_itend = {}\n'.format(itend),
            '  nn_date0 = {}\n'.format(date0),
        ]
        assert restart_timestep == restart


class TestGetNamelistValue:
    """Unit tests for _get_namelist_value() function.
    """
    def test_get_value(self, worker_module):
        lines = ['  nn_it000 = 8641  ! first time step\n']
        line_index, value = worker_module._get_namelist_value(
            'nn_it000', lines)
        assert line_index == 0
        assert value == str(8641)

    def test_get_last_occurrence(self, worker_module):
        lines = [
            '  nn_it000 = 8641  ! first time step\n',
            '  nn_it000 = 8642  ! last time step\n',
        ]
        line_index, value = worker_module._get_namelist_value(
            'nn_it000', lines)
        assert line_index == 1
        assert value == str(8642)

    def test_handle_empty_line(self, worker_module):
        lines = [
            '\n',
            '  nn_it000 = 8641  ! first time step\n',
            ]
        line_index, value = worker_module._get_namelist_value(
            'nn_it000', lines)
        assert line_index == 1
        assert value == str(8641)


class TestRunDescription:
    """Unit tests for _run_description() function.
    """
    def test_config_missing_results_dir(self, worker_module, config):
        run_date = arrow.get('2015-12-30')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type='nowcast')
        with patch.dict(config['run']['salish'], results={}):
            with pytest.raises(worker_module.WorkerError):
                worker_module._run_description(
                    run_date, 'nowcast', run_id, 2160, 'salish', config,
                    Mock(name='tell_manager'))

    @pytest.mark.parametrize('run_type, expected', [
        ('nowcast', 'SalishSea'),
        ('nowcast-green', 'SOG'),
        ('forecast', 'SalishSea'),
        ('forecast2', 'SalishSea'),
    ])
    def test_config_name(
        self, run_type, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-30')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['config_name'] == expected

    @pytest.mark.parametrize('run_type, expected', [
        ('nowcast', '31dec15nowcast'),
        ('nowcast-green', '31dec15nowcast-green'),
        ('forecast', '31dec15forecast'),
        ('forecast2', '31dec15forecast2'),
    ])
    def test_run_id(
        self, run_type, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['run_id'] == expected

    @pytest.mark.parametrize('run_type, expected', [
        ('nowcast', '3x5'),
    ])
    def test_mpi_decomposition(
        self, run_type, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['MPI decomposition'] == expected

    @pytest.mark.parametrize('run_type, expected', [
        ('nowcast-green', '16:00:00'),
    ])
    def test_walltime(
        self, run_type, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        with patch.dict(config['run']['salish'], walltime='16:00:00'):
            run_desc = worker_module._run_description(
                run_date, run_type, run_id, 2160, 'salish', config,
                Mock(name='tell_manager'))
        assert run_desc['walltime'] == expected

    @pytest.mark.parametrize('run_type, expected', [
        ('nowcast', None),
    ])
    def test_no_walltime(
        self, run_type, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['walltime'] == expected

    @pytest.mark.parametrize('run_type, path, expected', [
        ('nowcast', 'NEMO-code', '/nowcast-sys/nowcast/../NEMO-3.6-code'),
        ('nowcast-green', 'XIOS', '/nowcast-sys/nowcast/../XIOS-code'),
        ('forecast', 'forcing', '/nowcast-sys/nowcast/../NEMO-forcing'),
        ('forecast2', 'runs directory', '/nowcast-sys/nowcast/../SalishSea'),
    ])
    def test_paths(
        self, run_type, path, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['paths'][path] == expected

    @pytest.mark.parametrize('run_type, path, expected', [
        ('nowcast', 'coordinates', 'coordinates_seagrid_SalishSea.nc'),
    ])
    def test_grid_coordinates(
        self, run_type, path, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['grid'][path] == expected

    @pytest.mark.parametrize('run_type, path, expected', [
        ('nowcast', 'bathymetry', 'bathy_meter_SalishSea.nc'),
    ])
    def test_grid_bathymetry_default(
        self, run_type, path, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['grid'][path] == expected

    @pytest.mark.parametrize('run_type, path, expected', [
        ('nowcast-green', 'bathymetry', 'bathy_meter_SalishSea6.nc'),
    ])
    def test_grid_bathymetry_run_type(
        self, run_type, path, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        with patch.dict(config['run']['salish'], bathymetry=expected):
            run_desc = worker_module._run_description(
                run_date, run_type, run_id, 2160, 'salish', config,
                Mock(name='tell_manager'))
        assert run_desc['grid'][path] == expected

    @pytest.mark.parametrize('run_type, link_name, expected', [
        ('nowcast', 'NEMO-atmos', '/nowcast-sys/nowcast/NEMO-atmos'),
        ('forecast', 'open_boundaries',
         '/nowcast-sys/nowcast/open_boundaries'),
        ('forecast2', 'rivers', '/nowcast-sys/nowcast/rivers'),
        ('nowcast', 'restart.nc',
         '/results/SalishSea/nowcast/30dec15/'
         'SalishSea_00002160_restart.nc'),
        ('nowcast-green', 'restart_trc.nc',
         '/results/SalishSea/nowcast-green/30dec15/'
         'SalishSea_00002160_restart_trc.nc'),
    ])
    def test_forcing(
        self, run_type, link_name, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        assert run_desc['forcing'][link_name]['link to'] == expected

    @pytest.mark.parametrize('run_type, link_name, expected', [
        ('nowcast', 'NEMO-atmos', '/nowcast-sys/nowcast/NEMO-atmos'),
    ])
    def test_forcing_atmospheric_link_check(
        self, run_type, link_name, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        check_link_dict = run_desc['forcing'][link_name]['check link']
        assert check_link_dict['type'] == 'atmospheric'
        assert check_link_dict['namelist filename'] == 'namelist_cfg'

    def test_namelists(self, worker_module, config):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}nowcast'.format(dmy=dmy)
        run_desc = worker_module._run_description(
            run_date, 'nowcast', run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        expected = [
            './namelist.time',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.domain',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.surface',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.lateral',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.bottom',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.tracer',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.dynamics',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.vertical',
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist.compute',
        ]
        assert run_desc['namelists']['namelist_cfg'] == expected
        expected = [
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist_top_cfg'
        ]
        assert run_desc['namelists']['namelist_top_cfg'] == expected
        expected = [
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/namelist_pisces_cfg'
        ]
        assert run_desc['namelists']['namelist_pisces_cfg'] == expected

    def test_output(self, worker_module, config):
        run_date = arrow.get('2015-12-31')
        dmy = run_date.format('DDMMMYY').lower()
        run_id = '{dmy}nowcast'.format(dmy=dmy)
        run_desc = worker_module._run_description(
            run_date, 'nowcast', run_id, 2160, 'salish', config,
            Mock(name='tell_manager'))
        expected = (
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'domain_def.xml')
        assert run_desc['output']['domain'] == expected
        expected = (
            '/nowcast-sys/nowcast/../SS-run-sets/SalishSea/nemo3.6/'
            'nowcast/field_def.xml')
        assert run_desc['output']['fields'] == expected
        assert run_desc['output']['separate XIOS server']
        assert run_desc['output']['XIOS servers'] == 1
