# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM make_fvcom_boundary
worker.
"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_fvcom_boundary


@patch(
    'nowcast.workers.make_fvcom_boundary.NowcastWorker',
    spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_fvcom_boundary',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        make_fvcom_boundary.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'nowcast', 'forecast'}
        assert 'help' in kwargs

    def test_add_run_date_option(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_boundary.make_fvcom_boundary,
            make_fvcom_boundary.success,
            make_fvcom_boundary.failure,
        )


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.make_fvcom_boundary.logger', autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        make_fvcom_boundary.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        msg_type = make_fvcom_boundary.success(parsed_args)
        assert msg_type == f'success {run_type}'


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.make_fvcom_boundary.logger', autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        make_fvcom_boundary.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        msg_type = make_fvcom_boundary.failure(parsed_args)
        assert msg_type == f'failure {run_type}'


@patch('nowcast.workers.make_fvcom_boundary.logger', autospec=True)
@patch(
    'nowcast.workers.make_fvcom_boundary.OPPTools.nesting.make_type3_nesting_file',
    autospec=True
)
class TestMakeFVCOMBoundary:
    """Unit tests for make_fvcom_boundary() function.
    """

    config = {
        'vhfr fvcom runs': {
            'run prep dir': 'fvcom-runs/',
            'coupling dir': 'VHFR-FVCOM-config/coupling_nemo_cut/',
            'nemo nz nodes file': 'nemo_nesting_zone_cut.txt',
            'fvcom nz nodes file': 'nesting-zone-utm10-nodes.txt',
            'fvcom nz centroids file': 'nesting-zone-utm10-centr.txt',
            'grid interpolant files': {
                'ui': 'interpolant_indices_u_i_cut.txt',
                'uj': 'interpolant_indices_u_j_cut.txt',
                'uw': 'interpolant_weights_u_cut.txt',
                'vi': 'interpolant_indices_v_i_cut.txt',
                'vj': 'interpolant_indices_v_j_cut.txt',
                'vw': 'interpolant_weights_v_cut.txt',
            },
            'nemo vertical weights file': 'nemo_vertical_weight_cut.mat',
            'nemo azimuth file': 'nemo_azimuth_cut.txt',
            'fvcom grid file': 'vhfr_low_v2_utm10_grd.dat',
            'fvcom depths file': 'vhfr_low_v2_utm10_dep.dat',
            'fvcom sigma file': 'vhfr_low_v2_sigma.dat',
            'input dir': 'fvcom-runs/input',
            'boundary file template': 'bdy_{run_type}_btrp_{yyyymmdd}.nc',
            'run types': {
                'nowcast': {
                    'nemo boundary results': 'SalishSea/nowcast/',
                },
                'forecast': {
                    'nemo boundary results': 'SalishSea/forecast/',
                },
            }
        }
    }

    @pytest.mark.parametrize('run_type', [
        'nowcast',
        'forecast',
    ])
    def test_checklist(self, m_mk_nest_file, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2018-01-08')
        )
        checklist = make_fvcom_boundary.make_fvcom_boundary(
            parsed_args, self.config
        )
        run_prep_dir = Path(self.config["vhfr fvcom runs"]["run prep dir"])
        expected = os.fspath(run_prep_dir / f'bdy_{run_type}_btrp_20180108.nc')
        assert checklist == expected

    @pytest.mark.parametrize(
        'run_type, time_start, time_end', [
            ('nowcast', '2018-01-07 23:55:00', '2018-01-09 00:05:00'),
            ('forecast', '2018-01-08 23:55:00', '2018-01-10 12:05:00'),
        ]
    )
    def test_make_type3_nesting_file(
        self, m_mk_nest_file, m_logger, run_type, time_start, time_end
    ):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2018-01-08')
        )
        checklist = make_fvcom_boundary.make_fvcom_boundary(
            parsed_args, self.config
        )
        run_prep_dir = Path(self.config["vhfr fvcom runs"]["run prep dir"])
        coupling_dir = Path(self.config["vhfr fvcom runs"]["coupling dir"])
        m_mk_nest_file.assert_called_once_with(
            fout=os.fspath(run_prep_dir / f'bdy_{run_type}_btrp_20180108.nc'),
            fnest_nemo=os.fspath(coupling_dir / 'nemo_nesting_zone_cut.txt'),
            fnest_nodes=os.fspath(
                coupling_dir / 'nesting-zone-utm10-nodes.txt'
            ),
            fnest_elems=os.fspath(
                coupling_dir / 'nesting-zone-utm10-centr.txt'
            ),
            interp_uv=SimpleNamespace(
                ui=os.fspath(coupling_dir / 'interpolant_indices_u_i_cut.txt'),
                uj=os.fspath(coupling_dir / 'interpolant_indices_u_j_cut.txt'),
                uw=os.fspath(coupling_dir / 'interpolant_weights_u_cut.txt'),
                vi=os.fspath(coupling_dir / 'interpolant_indices_v_i_cut.txt'),
                vj=os.fspath(coupling_dir / 'interpolant_indices_v_j_cut.txt'),
                vw=os.fspath(coupling_dir / 'interpolant_weights_v_cut.txt')
            ),
            nemo_vertical_weight_file=os.fspath(
                coupling_dir / 'nemo_vertical_weight_cut.mat'
            ),
            nemo_azimuth_file=os.fspath(coupling_dir / 'nemo_azimuth_cut.txt'),
            fgrd='fvcom-runs/vhfr_low_v2_utm10_grd.dat',
            fbathy='fvcom-runs/vhfr_low_v2_utm10_dep.dat',
            fsigma='fvcom-runs/vhfr_low_v2_sigma.dat',
            input_dir=f'SalishSea/{run_type}',
            time_start=time_start,
            time_end=time_end
        )
