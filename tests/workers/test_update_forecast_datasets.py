#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Unit tests for SalishSeaCast update_forecast_datasets worker.
"""
from pathlib import Path
import shlex
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import update_forecast_datasets


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
results archive:
  nowcast: results/nowcast-blue/
  forecast: results/forecast/
  forecast2: results/forecast2/

rolling forecasts:
  days from past: 5
  temporary results archives: /tmp/
  fvcom:
    most recent forecast dir: opp/fvcom/most_recent_forecast
  nemo:
    dest dir: rolling-forecasts/nemo/
  wwatch3:
    dest dir: rolling-forecasts/wwatch3/
    most recent forecast dir: opp/wwatch3/most_recent_forecast
    
wave forecasts:
  results archive:
    nowcast: opp/wwatch3/nowcast/
    forecast: opp/wwatch3/forecast/
    forecast2: opp/wwatch3/forecast2/
    
vhfr fvcom runs:
  results archive:
    nowcast: opp/fvcom/nowcast/
    forecast: opp/fvcom/forecast/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.update_forecast_datasets.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        update_forecast_datasets.main()
        args, kwargs = m_worker.call_args
        assert args == ("update_forecast_datasets",)
        assert "description" in kwargs

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        update_forecast_datasets.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_model_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        update_forecast_datasets.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("model",)
        assert kwargs["choices"] == {"fvcom", "nemo", "wwatch3"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        update_forecast_datasets.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_data_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        update_forecast_datasets.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        update_forecast_datasets.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            update_forecast_datasets.update_forecast_datasets,
            update_forecast_datasets.success,
            update_forecast_datasets.failure,
        )
        assert args == expected


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "update_forecast_datasets" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "update_forecast_datasets"
        ]
        assert msg_registry["checklist key"] == "update forecast datasets"

    @pytest.mark.parametrize(
        "msg",
        (
            "success fvcom forecast",
            "failure fvcom forecast",
            "success nemo forecast",
            "failure nemo forecast",
            "success nemo forecast2",
            "failure nemo forecast2",
            "success wwatch3 forecast",
            "failure wwatch3 forecast",
            "success wwatch3 forecast2",
            "failure wwatch3 forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "update_forecast_datasets"
        ]
        assert msg in msg_registry

    def test_results_archives(self, prod_config):
        fvcom_run_types = ("nowcast", "forecast")
        for run_type in fvcom_run_types:
            assert run_type in prod_config["vhfr fvcom runs"]["results archive"]
        nemo_run_types = ("nowcast", "forecast", "forecast2")
        for run_type in nemo_run_types:
            assert run_type in prod_config["results archive"]
        wwatch3_run_types = ("nowcast", "forecast", "forecast2")
        for run_type in wwatch3_run_types:
            assert run_type in prod_config["wave forecasts"]["results archive"]

    def test_rolling_foreacsts(self, prod_config):
        assert prod_config["rolling forecasts"]["days from past"] == 5
        assert prod_config["rolling forecasts"]["temporary results archives"] == "/tmp/"
        fvcom = prod_config["rolling forecasts"]["fvcom"]
        assert fvcom["most recent forecast dir"] == "/opp/fvcom/most_recent_forecast/"
        nemo = prod_config["rolling forecasts"]["nemo"]
        assert nemo["dest dir"] == "/results/SalishSea/rolling-forecasts/nemo/"
        wwatch3 = prod_config["rolling forecasts"]["wwatch3"]
        assert wwatch3["dest dir"] == "/results/SalishSea/rolling-forecasts/wwatch3/"
        assert (
            wwatch3["most recent forecast dir"] == "/opp/wwatch3/most_recent_forecast/"
        )


@pytest.mark.parametrize(
    "model, run_type",
    [
        ("fvcom", "forecast"),
        ("nemo", "forecast"),
        ("nemo", "forecast2"),
        ("wwatch3", "forecast"),
        ("wwatch3", "forecast2"),
    ],
)
@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, model, run_type):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        msg_type = update_forecast_datasets.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {model} {run_type}"


@pytest.mark.parametrize(
    "model, run_type",
    [
        ("fvcom", "forecast"),
        ("nemo", "forecast"),
        ("nemo", "forecast2"),
        ("wwatch3", "forecast"),
        ("wwatch3", "forecast2"),
    ],
)
@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, model, run_type):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        msg_type = update_forecast_datasets.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {model} {run_type}"


@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
@patch(
    "nowcast.workers.update_forecast_datasets._symlink_most_recent_forecast",
    autospec=True,
)
@patch(
    "nowcast.workers.update_forecast_datasets._update_rolling_forecast", autospec=True
)
class TestUpdateForecastDatasets:
    """Unit tests for update_forecast_datasets() function.
    """

    @pytest.mark.parametrize(
        "model, run_type",
        [("fvcom", "forecast"), ("wwatch3", "forecast"), ("wwatch3", "forecast2")],
    )
    def test_most_recent_forecast_checklist(
        self, m_upd_rf, m_symlink_mrf, m_logger, model, run_type, config, tmpdir
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-24")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        with patch.dict(
            config["rolling forecasts"],
            {
                "temporary results archives": str(tmp_forecast_results_archive),
                model: {"most recent forecast dir": str(most_recent_fcst_dir)},
            },
        ):
            checklist = update_forecast_datasets.update_forecast_datasets(
                parsed_args, config
            )
        expected = {model: {run_type: [str(most_recent_fcst_dir)]}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "model, run_type",
        [
            ("nemo", "forecast"),
            ("nemo", "forecast2"),
            ("wwatch3", "forecast"),
            ("wwatch3", "forecast2"),
        ],
    )
    def test_rolling_forecast_checklist(
        self, m_upd_rf, m_symlink_mrf, m_logger, model, run_type, config, tmpdir
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["dest dir"]
        )
        with patch.dict(
            config["rolling forecasts"],
            {
                "temporary results archives": str(tmp_forecast_results_archive),
                model: {"dest dir": str(rolling_fcst_dir)},
            },
        ):
            checklist = update_forecast_datasets.update_forecast_datasets(
                parsed_args, config
            )
        expected = {model: {run_type: [str(rolling_fcst_dir)]}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "model, run_type", [("wwatch3", "forecast"), ("wwatch3", "forecast2")]
    )
    def test_most_recent_and_rolling_forecast_checklist(
        self, m_upd_rf, m_symlink_mrf, m_logger, model, run_type, config, tmpdir
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["dest dir"]
        )
        with patch.dict(
            config["rolling forecasts"],
            {
                "temporary results archives": str(tmp_forecast_results_archive),
                model: {
                    "dest dir": str(rolling_fcst_dir),
                    "most recent forecast dir": str(most_recent_fcst_dir),
                },
            },
        ):
            checklist = update_forecast_datasets.update_forecast_datasets(
                parsed_args, config
            )
        expected = {
            model: {run_type: [str(most_recent_fcst_dir), str(rolling_fcst_dir)]}
        }
        assert checklist == expected


@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestSymlinkMostRecentForecast:
    """Unit tests for _symlink_most_recent_forecast() function.
    """

    @pytest.mark.parametrize(
        "model, run_type",
        [("fvcom", "forecast"), ("wwatch3", "forecast"), ("wwatch3", "forecast2")],
    )
    def test_unlink_prev_forecast_files(
        self, m_logger, model, run_type, config, tmpdir
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-25")
        )
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        prev_fcst_files = ("foo.nc", "bar.nc")
        for f in prev_fcst_files:
            most_recent_fcst_dir.ensure(f)
        update_forecast_datasets._symlink_most_recent_forecast(
            parsed_args.run_date,
            Path(str(most_recent_fcst_dir)),
            model,
            run_type,
            config,
        )
        for f in prev_fcst_files:
            assert not most_recent_fcst_dir.join(f).check(file=True)

    @pytest.mark.parametrize(
        "model, run_type",
        [("fvcom", "forecast"), ("wwatch3", "forecast"), ("wwatch3", "forecast2")],
    )
    def test_symlink_new_forecast_files(
        self, m_logger, model, run_type, config, tmpdir
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-25")
        )
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        runs = {"fvcom": "vhfr fvcom runs", "wwatch3": "wave forecasts"}
        results_archive = tmpdir.ensure_dir(
            config[runs[model]]["results archive"][run_type]
        )
        new_fcst_files = ["foo.nc", "foo_restart.nc", "bar.nc"]
        for f in new_fcst_files:
            results_archive.ensure_dir("25oct18").ensure(f)
        with patch.dict(
            config[runs[model]]["results archive"], {run_type: str(results_archive)}
        ):
            update_forecast_datasets._symlink_most_recent_forecast(
                parsed_args.run_date,
                Path(str(most_recent_fcst_dir)),
                model,
                run_type,
                config,
            )
        new_fcst_files.remove("foo_restart.nc")
        for f in new_fcst_files:
            assert most_recent_fcst_dir.join(f).check(link=True)
        assert not most_recent_fcst_dir.join("foo_restart.nc").check(link=True)


@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestUpdateRollingForecast:
    """Unit tests for _u[pdate_rolling_forecast() function.
    """

    @pytest.mark.parametrize(
        "model, run_type",
        [
            ("nemo", "forecast"),
            ("nemo", "forecast2"),
            ("wwatch3", "forecast"),
            ("wwatch3", "forecast2"),
        ],
    )
    def test_update_rolling_forecast(self, m_logger, model, run_type, config, tmpdir):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-25")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["dest dir"]
        )
        with patch.dict(
            config["rolling forecasts"],
            {
                "temporary results archives": str(tmp_forecast_results_archive),
                model: {"dest dir": str(rolling_fcst_dir)},
            },
        ):
            update_forecast_datasets._update_rolling_forecast(
                parsed_args.run_date,
                Path(str(rolling_fcst_dir)),
                model,
                run_type,
                config,
            )
        assert rolling_fcst_dir.check(dir=True)


@pytest.mark.parametrize(
    "model, run_type", [("nemo", "forecast"), ("nemo", "forecast2")]
)
@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestCreateNewForecastDir:
    """Unit test for _create_new_forecast_dir() function.
    """

    def test_new_forecast_dir(self, m_logger, model, run_type, tmpdir):
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}")
        new_forecast_dir = update_forecast_datasets._create_new_forecast_dir(
            Path(forecast_dir), model, run_type
        )
        assert new_forecast_dir == Path(f"{forecast_dir}_new")


@patch("nowcast.workers.update_forecast_datasets._symlink_results", autospec=True)
@patch(
    "nowcast.workers.update_forecast_datasets._extract_1st_forecast_day", autospec=True
)
class TestAddPastDaysResults:
    """Unit test for _add_past_days_results() function.
    """

    @pytest.mark.parametrize(
        "model, run_type, run_date, days_from_past, first_date",
        [
            ("nemo", "forecast", arrow.get("2017-11-11"), 5, arrow.get("2017-11-06")),
            ("nemo", "forecast2", arrow.get("2018-01-24"), 5, arrow.get("2018-01-20")),
        ],
    )
    def test_symlink_nemo_nowcast_days(
        self,
        m_ex_1st_fcst_day,
        m_symlink_results,
        model,
        run_type,
        run_date,
        days_from_past,
        first_date,
        config,
        tmpdir,
    ):
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f"rolling-forecasts/{model}_new"))
        )
        update_forecast_datasets._add_past_days_results(
            run_date, days_from_past, new_forecast_dir, model, run_type, config
        )
        expected = [
            call(
                Path("results/nowcast-blue/"),
                day,
                new_forecast_dir,
                day,
                model,
                run_type,
            )
            for day in arrow.Arrow.range("day", first_date, run_date)
        ]
        assert m_symlink_results.call_args_list == expected

    @pytest.mark.parametrize(
        "model, run_type, run_date, days_from_past, first_date",
        [
            (
                "wwatch3",
                "forecast",
                arrow.get("2018-04-11"),
                5,
                arrow.get("2018-04-06"),
            ),
            (
                "wwatch3",
                "forecast2",
                arrow.get("2018-04-11"),
                5,
                arrow.get("2018-04-07"),
            ),
        ],
    )
    def test_symlink_wwatch3_forecast_days(
        self,
        m_ex_1st_fcst_day,
        m_symlink_results,
        model,
        run_type,
        run_date,
        days_from_past,
        first_date,
        config,
        tmpdir,
    ):
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f"rolling-forecasts/{model}_new"))
        )
        update_forecast_datasets._add_past_days_results(
            run_date, days_from_past, new_forecast_dir, model, run_type, config
        )
        expected = [
            call(
                Path("opp/wwatch3/nowcast"), day, new_forecast_dir, day, model, run_type
            )
            for day in arrow.Arrow.range("day", first_date, run_date)
        ]
        assert m_symlink_results.call_args_list == expected


@patch("nowcast.workers.update_forecast_datasets._symlink_results")
@patch(
    "nowcast.workers.update_forecast_datasets._extract_1st_forecast_day", autospec=True
)
class TestAddForecastResults:
    """Unit tests for _add_forecast_results() function.
    """

    @pytest.mark.parametrize(
        "run_date, model, run_type, results_archive, forecast_date",
        [
            (
                arrow.get("2017-11-11"),
                "nemo",
                "forecast",
                Path(f"results/forecast/"),
                arrow.get("2017-11-12"),
            ),
            (
                arrow.get("2018-04-12"),
                "wwatch3",
                "forecast",
                Path(f"opp/wwatch3/forecast/"),
                arrow.get("2018-04-13"),
            ),
        ],
    )
    def test_symlink_forecast_run(
        self,
        m_ex_1st_fcst_day,
        m_symlink_results,
        run_date,
        model,
        run_type,
        results_archive,
        forecast_date,
        config,
        tmpdir,
    ):
        new_forecast_dir = Path(str(tmpdir.ensure_dir(f"rolling-forecasts/nemo_new")))
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            model,
            run_type,
            config,
        )
        m_symlink_results.assert_called_once_with(
            results_archive, run_date, new_forecast_dir, forecast_date, model, run_type
        )

    def test_wwatch3_symlink_forecast2_run(
        self, m_ex_1st_fcst_day, m_symlink_results, config, tmpdir
    ):
        run_date = arrow.get("2018-01-24")
        model = "wwatch3"
        run_type = "forecast2"
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f"rolling-forecasts/{model}_new"))
        )
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            model,
            run_type,
            config,
        )
        assert m_symlink_results.called_once_with(
            Path(f"opp/wwatch3/{run_type}"),
            run_date,
            new_forecast_dir,
            run_date,
            model,
            run_type,
        )

    def test_nemo_forecast2_extract_1st_forecast_day(
        self, m_ex_1st_fcst_day, m_symlink_results, config, tmpdir
    ):
        new_forecast_dir = Path(str(tmpdir.ensure_dir(f"rolling-forecasts/nemo_new")))
        run_date = arrow.get("2018-01-24")
        model = "nemo"
        run_type = "forecast2"
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            "nemo",
            run_type,
            config,
        )
        m_ex_1st_fcst_day.assert_called_once_with(
            Path("/tmp/nemo_forecast"), run_date, model, config
        )

    def test_nemo_symlink_forecast2_run(
        self, m_ex_1st_fcst_day, m_symlink_results, config, tmpdir
    ):
        new_forecast_dir = Path(str(tmpdir.ensure_dir(f"rolling-forecasts/nemo_new")))
        run_date = arrow.get("2018-01-24")
        model = "nemo"
        run_type = "forecast2"
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            model,
            run_type,
            config,
        )
        assert m_symlink_results.call_args_list == [
            call(
                Path(f"/tmp/nemo_forecast"),
                run_date.shift(days=+1),
                new_forecast_dir,
                run_date.shift(days=+1),
                model,
                run_type,
            ),
            call(
                Path(f"results/{run_type}/"),
                run_date,
                new_forecast_dir,
                run_date.shift(days=+2),
                model,
                run_type,
            ),
        ]


@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestExtract1stForecastDay:
    """Unit tests for _extract_1st_forecast_day() function.
    """

    def test_create_tmp_forecast_results_archive(self, m_logger, config, tmpdir):
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp_nemo_forecast")
        run_date = arrow.get("2018-01-24")
        model = "nemo"
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert Path(str(tmp_forecast_results_archive), "25jan18").exists()

    @patch("nowcast.workers.update_forecast_datasets.Path.glob", autospec=True)
    @patch("nowcast.workers.update_forecast_datasets.subprocess.run", autospec=True)
    def test_nemo_ncks_subprocess(self, m_run, m_glob, m_logger, config, tmpdir):
        model = "nemo"
        tmp_forecast_results_archive = tmpdir.ensure_dir(f"tmp_{model}_forecast")
        run_date = arrow.get("2018-01-24")
        m_glob.return_value = [
            # A 10min file that we want to operate on
            Path("results/forecast/24jan18/CampbellRiver.nc"),
            # A 1hr file that we want to operate on
            Path(
                "results/forecast/24jan18/" "SalishSea_1h_20180124_20180125_grid_T.nc"
            ),
            # Files that we don't want to operate on
            Path("results/forecast/24jan18/SalishSea_02702160_restart.nc"),
            Path(
                "results/forecast/24jan18/" "SalishSea_1d_20180124_20180125_grid_T.nc"
            ),
        ]
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert m_run.call_args_list == [
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time_counter,0,143 "
                    f"results/forecast/24jan18/CampbellRiver.nc "
                    f"{tmp_forecast_results_archive}/25jan18/CampbellRiver.nc"
                )
            ),
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time_counter,0,23 "
                    f"results/forecast/24jan18/"
                    f"SalishSea_1h_20180124_20180125_grid_T.nc "
                    f"{tmp_forecast_results_archive}/25jan18/"
                    f"SalishSea_1h_20180124_20180125_grid_T.nc"
                )
            ),
        ]

    @patch("nowcast.workers.update_forecast_datasets.Path.glob", autospec=True)
    @patch("nowcast.workers.update_forecast_datasets.subprocess.run", autospec=True)
    def test_wwatch3_ncks_subprocess(self, m_run, m_glob, m_logger, config, tmpdir):
        model = "wwatch3"
        tmp_forecast_results_archive = tmpdir.ensure_dir(f"tmp_{model}_forecast")
        run_date = arrow.get("2018-04-11")
        m_glob.return_value = [
            Path("opp/wwatch3/forecast/11apr18/" "SoG_ww3_fields_20180410_20180412.nc"),
            Path("opp/wwatch3/forecast/11apr18/" "SoG_ww3_points_20180410_20180412.nc"),
        ]
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert m_run.call_args_list == [
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time,0,47 "
                    f"opp/wwatch3/forecast/11apr18/"
                    f"SoG_ww3_fields_20180410_20180412.nc "
                    f"{tmp_forecast_results_archive}/11apr18/"
                    f"SoG_ww3_fields_20180410_20180412.nc"
                )
            ),
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time,0,143 "
                    f"opp/wwatch3/forecast/11apr18/"
                    f"SoG_ww3_points_20180410_20180412.nc "
                    f"{tmp_forecast_results_archive}/11apr18/"
                    f"SoG_ww3_points_20180410_20180412.nc"
                )
            ),
        ]


@pytest.mark.parametrize(
    "model, run_type", [("nemo", "forecast"), ("nemo", "forecast2")]
)
@patch("nowcast.workers.update_forecast_datasets.logger", autospec=True)
class TestSymlinkResults:
    """Unit tests for _symlink_results() function.
    """

    def test_create_dest_dir(self, m_logger, model, run_type, tmpdir):
        forecast_day = arrow.get("2017-11-11")
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}_new")
        update_forecast_datasets._symlink_results(
            Path(f"results/{run_type}/"),
            arrow.get("2017-11-10"),
            Path(str(forecast_dir)),
            forecast_day,
            model,
            run_type,
        )
        assert forecast_dir.join("11nov17").check(dir=True)

    def test_symlink(self, m_logger, model, run_type, tmpdir):
        results_day = arrow.get("2017-11-10")
        results_archive = tmpdir.ensure_dir(f"results/{run_type}/")
        results_archive.ensure("10nov17/PointAtkinson.nc")
        forecast_day = arrow.get("2017-11-11")
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}_new")
        update_forecast_datasets._symlink_results(
            Path(str(results_archive)),
            results_day,
            Path(str(forecast_dir)),
            forecast_day,
            model,
            run_type,
        )
        assert forecast_dir.join("11nov17", "PointAtkinson.nc").check(link=True)
