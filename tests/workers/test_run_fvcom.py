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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM run_fvcom worker.
"""
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import run_fvcom


@pytest.fixture(scope='function')
def config():
    """
    nowcast.yaml config object section for FVCOM VHFR runs.

    :return: :py:class:`nemo_nowcast.Config`-like dict
    :rtype: dict
    """
    return {
        'vhfr fvcom runs': {
            'case name':
                'vhfr_low_v2',
            'run prep dir':
                'fvcom-runs/',
            'fvcom grid': {
                'grid dir': 'VHFR-FVCOM-config/grid/',
                'grid file': 'vhfr_low_v2_utm10_grd.dat',
                'depths file': 'vhfr_low_v2_utm10_dep.dat',
                'sigma file': 'vhfr_low_v2_sigma.dat',
                'coriolis file': 'vhfr_low_v2_utm10_cor.dat',
                'sponge file': 'vhfr_low_v2_nospg_spg.dat',
                'obc nodes file': 'vhfr_low_v2_obc.dat',
            },
            'input dir':
                'fvcom-runs/input/',
            'output station timeseries':
                'VHFR-FVCOM-config/output/vhfr_low_v2_utm10_station.dat',
            'number of processors':
                32,
            'mpi hosts file':
                '${HOME}/mpi_hosts.fvcom',
            'fvc_cmd':
                'bin/fvc',
            'run types': {
                'nowcast': {
                    'results': 'SalishSea/fvcom-nowcast/',
                },
                'forecast': {
                    'results': 'SalishSea/fvcom-forecast/',
                }
            }
        }
    }


@patch(
    'nowcast.workers.run_fvcom.NowcastWorker', spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        run_fvcom.main()
        args, kwargs = m_worker.call_args
        assert args == ('run_fvcom',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        run_fvcom.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'nowcast', 'forecast'}
        assert 'help' in kwargs

    def test_add_run_date_option(self, m_worker):
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        run_fvcom.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            run_fvcom.run_fvcom,
            run_fvcom.success,
            run_fvcom.failure,
        )


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        run_fvcom.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        msg_type = run_fvcom.success(parsed_args)
        assert msg_type == f'success {run_type}'


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        run_fvcom.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        msg_type = run_fvcom.failure(parsed_args)
        assert msg_type == f'failure {run_type}'


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
@patch('nowcast.workers.run_fvcom._create_run_desc_file')
@patch('nowcast.workers.run_fvcom.fvcom_cmd.api.prepare')
@patch('nowcast.workers.run_fvcom._prep_fvcom_input_dir')
@patch('nowcast.workers.run_fvcom.shutil.copy2', autospec=True)
@patch('nowcast.workers.run_fvcom._create_run_script')
@patch('nowcast.workers.run_fvcom._launch_run_script')
class TestRunFVCOM:
    """Unit tests for run_fvcom() function.
    """

    def test_checklist(
        self, m_launch, m_crs, m_copy2, m_pfid, m_prep, m_crdf, m_logger,
        run_type, config
    ):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        tmp_run_dir = (
            '/fvcom-runs/29nov17vhfr-{run_type}_2017-11-29T183043.555919-0700'
        )
        m_prep.return_value = tmp_run_dir
        checklist = run_fvcom.run_fvcom(parsed_args, config)
        expected = {
            run_type: {
                'host': 'west.cloud',
                'run dir': tmp_run_dir,
                'run exec cmd': m_launch(),
                'run date': '2017-11-29',
            }
        }
        assert checklist == expected


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
@patch('nowcast.workers.run_fvcom.yaml.dump', autospec=True)
@patch('nowcast.workers.run_fvcom._run_description')
class TestCreateRunDescFile:
    """Unit tests for _create_fun_desc_file() function.
    """

    def test_run_desc_file_path(
        self, m_run_desc, m_yaml_dump, m_logger, run_type, config
    ):
        run_date = arrow.get('2017-12-11')
        with patch('nowcast.workers.run_fvcom.Path.open') as m_open:
            run_desc_file_path = run_fvcom._create_run_desc_file(
                run_date, run_type, config
            )
        expected = Path(f'fvcom-runs/11dec17fvcom-{run_type}.yaml')
        assert run_desc_file_path == expected

    def test_run_desc_yaml_dump(
        self, m_run_desc, m_yaml_dump, m_logger, run_type, config, tmpdir
    ):
        run_date = arrow.get('2017-12-12')
        run_prep_dir = Path(str(tmpdir.ensure_dir('nowcast-sys/fvcom-runs')))
        with patch('nowcast.workers.run_fvcom.Path.open') as m_open:
            run_desc_file_path = run_fvcom._create_run_desc_file(
                run_date, run_type, config
            )
            m_yaml_dump.assert_called_once_with(
                m_run_desc(), m_open().__enter__(), default_flow_style=False
            )


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
class TestRunDescription:
    """Unit tests for _run_description() function.
    """

    def test_run_desc(self, m_logger, run_type, config, tmpdir):
        run_id = f'11dec17fvcom-{run_type}'
        fvcom_repo_dir = Path(str(tmpdir.ensure_dir('nowcast-sys/FVCOM41')))
        run_prep_dir = Path(str(tmpdir.ensure_dir('nowcast-sys/fvcom-runs')))
        p_config = patch.dict(
            config['vhfr fvcom runs'], {
                'run prep dir': run_prep_dir,
                'FVCOM exe path': fvcom_repo_dir,
            }
        )
        with p_config:
            run_desc = run_fvcom._run_description(run_id, run_prep_dir, config)
        expected = {
            'run_id': run_id,
            'casename': 'vhfr_low_v2',
            'nproc': 32,
            'paths': {
                'FVCOM': os.fspath(fvcom_repo_dir),
                'runs directory': os.fspath(run_prep_dir),
                'input': os.fspath(run_prep_dir / 'input')
            },
            'namelist': os.fspath(run_prep_dir / 'vhfr_low_v2_run.nml'),
        }
        assert run_desc == expected


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
class TestPrepFVCOM_InputDir:
    """Unit test for _prep_fvcom_input_dir() function.
    """

    def test_prep_fvcom_input_dir(self, m_logger, run_type, config, tmpdir):
        with patch('nowcast.workers.run_fvcom.Path.symlink_to') as m_limk:
            run_fvcom._prep_fvcom_input_dir(config)


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.logger', autospec=True)
@patch(
    'nowcast.workers.run_fvcom._build_script',
    return_value='script',
    autospec=True
)
class TestCreateRunScript:
    """Unit tests for _create_run_script() function.
    """

    def test_run_script_path(
        self, m_bld_script, m_logger, run_type, config, tmpdir
    ):
        tmp_run_dir = tmpdir.ensure_dir('tmp_run_dir')
        run_script_path = run_fvcom._create_run_script(
            arrow.get('2017-12-20'), run_type, Path(str(tmp_run_dir)),
            Path(f'20dec17fvcom-{run_type}.yaml'), config
        )
        expected = Path(str(tmp_run_dir.join('VHFR_FVCOM.sh')))
        assert run_script_path == expected


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.yaml.load', autospec=True)
class TestBuildScript:
    """Unit tests for _build_script() function.
    """

    def test_script(self, m_yaml_load, run_type, config, tmpdir):
        tmp_run_dir = tmpdir.ensure_dir('tmp_run_dir')
        run_desc_file_path = tmp_run_dir.ensure(
            f'20dec17fvcom-{run_type}.yaml'
        )
        m_yaml_load.return_value = {
            'run_id': f'20dec17fvcom-{run_type}',
        }
        results_dir = tmpdir.ensure_dir(
            config['vhfr fvcom runs']['run types'][run_type]['results']
        )
        script = run_fvcom._build_script(
            Path(str(tmp_run_dir)), Path(str(run_desc_file_path)),
            Path(str(results_dir)) / '20dec17', config
        )
        expected = '''#!/bin/bash

        RUN_ID="20dec17fvcom-{run_type}"
        RUN_DESC="20dec17fvcom-{run_type}.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}"
        MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts.fvcom"
        GATHER="bin/fvc gather"
        
        mkdir -p ${{RESULTS_DIR}}

        cd ${{WORK_DIR}}
        echo "working dir: $(pwd)" >>${{RESULTS_DIR}}/stdout

        echo "Starting run at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{MPIRUN}} -np 32 --bind-to-core ./fvcom \
--casename=vhfr_low_v2 --logfile=./fvcom.log \
>>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr
        echo "Ended run at $(date)" >>${{RESULTS_DIR}}/stdout

        echo "Results gathering started at $(date)" >>${{RESULTS_DIR}}/stdout
        ${{GATHER}} ${{RESULTS_DIR}} --debug >>${{RESULTS_DIR}}/stdout
        echo "Results gathering ended at $(date)" >>${{RESULTS_DIR}}/stdout
        
        chmod g+rwx ${{RESULTS_DIR}}
        chmod g+rw ${{RESULTS_DIR}}/*
        chmod o+rx ${{RESULTS_DIR}}
        chmod o+r ${{RESULTS_DIR}}/*

        echo "Deleting run directory" >>${{RESULTS_DIR}}/stdout
        rmdir $(pwd)
        echo "Finished at $(date)" >>${{RESULTS_DIR}}/stdout
        '''.format(
            run_type=run_type,
            tmp_run_dir=tmp_run_dir,
            results_dir=results_dir / '20dec17',
        )
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
class TestDefinitions:
    """Unit tests for _definitions() function.
    """

    def test_definitions(self, run_type, config, tmpdir):
        run_desc_file_path = tmpdir.ensure(f'21dec17fvcom-{run_type}.yaml')
        run_desc = {'run_id': f'21dec17fvcom-{run_type}'}
        tmp_run_dir = tmpdir.ensure_dir('tmp_run_dir')
        results_dir = tmpdir.ensure_dir(f'SalishSea/fvcom-{run_type}/21dec17/')
        defns = run_fvcom._definitions(
            run_desc, Path(str(tmp_run_dir)), Path(str(run_desc_file_path)),
            Path(str(results_dir)), config
        )
        expected = '''RUN_ID="21dec17fvcom-{run_type}"
        RUN_DESC="21dec17fvcom-{run_type}.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}"
        MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts.fvcom"
        GATHER="bin/fvc gather"
        '''.format(
            run_type=run_type,
            tmp_run_dir=tmp_run_dir,
            results_dir=results_dir,
        )
        defns = defns.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert defns[i].strip() == line.strip()


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
class TestExecute:
    """Unit tests for _execute() function.
    """

    def test_execute(self, run_type, config):
        script = run_fvcom._execute(config)
        expected = '''mkdir -p ${RESULTS_DIR}

        cd ${WORK_DIR}
        echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout

        echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout
        ${MPIRUN} -np 32 --bind-to-core ./fvcom \
--casename=vhfr_low_v2 --logfile=./fvcom.log \
>>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr
        echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout

        echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout
        ${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout
        echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout
        '''
        script = script.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert script[i].strip() == line.strip()


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.run_fvcom.subprocess.Popen', autospec=True)
@patch('nowcast.workers.run_fvcom.subprocess.run', autospec=True)
class TestLaunchRunScript:
    """Unit tests for _launch_run_script() function.
    """

    def test_launch_run_script(self, m_run, m_popen, run_type):
        run_fvcom._launch_run_script(run_type, 'VHFR_FVCOM.sh', 'west.cloud')
        m_popen.assert_called_once_with(['bash', 'VHFR_FVCOM.sh'])

    def test_find_run_process_id(self, m_run, m_popen, run_type):
        run_fvcom._launch_run_script(run_type, 'VHFR_FVCOM.sh', 'west.cloud')
        m_run.assert_called_once_with(
            ['pgrep', '--newest', '--exact', '--full', 'bash VHFR_FVCOM.sh'],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True
        )

    def test_run_exec_cmd(self, m_run, m_popen, run_type):
        run_exec_cmd = run_fvcom._launch_run_script(
            run_type, 'VHFR_FVCOM.sh', 'west.cloud'
        )
        assert run_exec_cmd == 'bash VHFR_FVCOM.sh'
