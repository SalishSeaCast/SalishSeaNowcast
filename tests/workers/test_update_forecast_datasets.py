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
"""Unit tests for Salish Sea NEMO nowcast update_forecast_datasets worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, call

import arrow
import pytest

from nowcast.workers import update_forecast_datasets


@patch('nowcast.workers.update_forecast_datasets.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        update_forecast_datasets.main()
        args, kwargs = m_worker.call_args
        assert args == ('update_forecast_datasets',)
        assert 'description' in kwargs

    def test_add_model_arg(self, m_worker):
        update_forecast_datasets.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('model',)
        assert kwargs['choices'] == {'nemo'}
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        update_forecast_datasets.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'forecast'}
        assert 'help' in kwargs

    def test_add_data_date_arg(self, m_worker):
        update_forecast_datasets.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        update_forecast_datasets.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            update_forecast_datasets.update_forecast_datasets,
            update_forecast_datasets.success, update_forecast_datasets.failure
        )
        assert args == expected


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets.logger')
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, model, run_type):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get('2017-11-10')
        )
        update_forecast_datasets.success(parsed_args)
        assert m_logger.info.called
        extra_value = m_logger.info.call_args[1]['extra']['model']
        assert extra_value == model
        extra_value = m_logger.info.call_args[1]['extra']['run_type']
        assert extra_value == run_type
        assert m_logger.info.call_args[1]['extra']['run_date'] == '2017-11-10'

    def test_success_msg_type(self, m_logger, model, run_type):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get('2017-11-10')
        )
        msg_type = update_forecast_datasets.success(parsed_args)
        assert msg_type == f'success {model} {run_type}'


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets.logger')
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger, model, run_type):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get('2017-11-10')
        )
        update_forecast_datasets.failure(parsed_args)
        assert m_logger.critical.called
        extra_value = m_logger.critical.call_args[1]['extra']['model']
        assert extra_value == model
        extra_value = m_logger.critical.call_args[1]['extra']['run_type']
        assert extra_value == run_type
        expected = '2017-11-10'
        assert m_logger.critical.call_args[1]['extra']['run_date'] == expected

    def test_failure_msg_type(self, m_logger, model, run_type):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get('2017-11-10')
        )
        msg_type = update_forecast_datasets.failure(parsed_args)
        assert msg_type == f'failure {model} {run_type}'


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets.logger')
class TestUpdateForecastDatasets:
    """Unit tests for update_forecast_datasets() function.
    """

    def test_checklist(self, m_logger, model, run_type, tmpdir):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get('2017-11-10')
        )
        config = {
            'results archive': {
                'nowcast': 'results/nowcast-blue/',
                'forecast': 'results/forecast/',
            },
            'rolling forecasts': {
                'days from past': 5,
                'nemo': {
                    'dest dir': 'rolling-forecasts/nemo/',
                }
            }
        }
        forecast_dir = tmpdir.ensure_dir(
            config['rolling forecasts'][model]['dest dir']
        )
        with patch.dict(
            config['rolling forecasts'][model], {
                'dest dir': str(forecast_dir)
            }
        ):
            checklist = update_forecast_datasets.update_forecast_datasets(
                parsed_args, config
            )
        expected = {model: {run_type: str(forecast_dir)}}
        assert checklist == expected


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets.logger')
class TestCreateNewForecastDir:
    """Unit test for _create_new_forecast_dir() function.
    """

    def test_new_forecast_dir(self, m_logger, model, run_type, tmpdir):
        forecast_dir = tmpdir.ensure_dir(f'rolling-forecasts/{model}')
        new_forecast_dir = update_forecast_datasets._create_new_forecast_dir(
            Path(forecast_dir), model, run_type
        )
        assert new_forecast_dir == Path(f'{forecast_dir}_new')


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets._symlink_results')
class TestAddPastDaysResults:
    """Unit test for _add_past_days_results() function.
    """

    def test_symlink_nowcast_days(
        self, m_symlink_results, model, run_type, tmpdir
    ):
        run_date = arrow.get('2017-11-11')
        days_from_past = 5
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f'rolling-forecasts/{model}_new'))
        )
        config = {'results archive': {'nowcast': 'results/nowcast-blue/'}}
        update_forecast_datasets._add_past_days_results(
            run_date, days_from_past, new_forecast_dir, model, run_type, config
        )
        expected = [
            call(
                Path('results/nowcast-blue/'), day, new_forecast_dir, day,
                model, run_type
            )
            for day in arrow.Arrow.
            range('day', run_date.replace(days=-days_from_past), run_date)
        ]
        assert m_symlink_results.call_args_list == expected


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets._symlink_results')
class TestAddForecastResults:
    """Unit test for _add_forecast_results() function.
    """

    def test_symlink_nowcast_days(
        self, m_symlink_results, model, run_type, tmpdir
    ):
        run_date = arrow.get('2017-11-11')
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f'rolling-forecasts/{model}_new'))
        )
        config = {'results archive': {run_type: f'results/{run_type}/'}}
        update_forecast_datasets._add_forecast_results(
            run_date, new_forecast_dir, model, run_type, config
        )
        m_symlink_results.assert_called_once_with(
            Path(f'results/{run_type}/'),
            run_date,
            new_forecast_dir,
            run_date.replace(days=+1),
            model,
            run_type
        )


@pytest.mark.parametrize('model, run_type', [
    ('nemo', 'forecast'),
])
@patch('nowcast.workers.update_forecast_datasets.logger')
class TestSymlinkResults:
    """Unit tests for _symlink_results() function.
    """

    def test_create_dest_dir(self, m_logger, model, run_type, tmpdir):
        forecast_day = arrow.get('2017-11-11')
        forecast_dir = tmpdir.ensure_dir(f'rolling-forecasts/{model}_new')
        update_forecast_datasets._symlink_results(
            Path(f'results/{run_type}/'),
            arrow.get('2017-11-10'),
            Path(str(forecast_dir)), forecast_day, model, run_type
        )
        assert forecast_dir.join('11nov17').check(dir=True)

    def test_symlink(self, m_logger, model, run_type, tmpdir):
        results_day = arrow.get('2017-11-10')
        results_archive = tmpdir.ensure_dir(f'results/{run_type}/')
        results_archive.ensure('10nov17/PointAtkinson.nc')
        forecast_day = arrow.get('2017-11-11')
        forecast_dir = tmpdir.ensure_dir(f'rolling-forecasts/{model}_new')
        update_forecast_datasets._symlink_results(
            Path(str(results_archive)), results_day,
            Path(str(forecast_dir)), forecast_day, model, run_type
        )
        assert forecast_dir.join('11nov17',
                                 'PointAtkinson.nc').check(link=True)