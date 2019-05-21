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
"""Unit tests for SalishSeaCast run_NEMO_hindcast worker.
"""
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

import nowcast.ssh_sftp
from nowcast.workers import run_NEMO_hindcast


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
            run:
                hindcast hosts:
                    cedar:
                        ssh key: SalishSeaNEMO-nowcast_id_rsa
                        users: allen,dlatorne
                        scratch dir: scratch/
                        run prep dir: runs/
                        salishsea cmd: bin/salishsea
            """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.run_NEMO_hindcast.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        args, kwargs = m_worker.call_args
        assert args == ("run_NEMO_hindcast",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_full_month_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("--full-month",)
        assert kwargs["action"] == "store_true"
        assert "help" in kwargs

    def test_add_prev_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("--prev-run-date",)
        assert kwargs["default"] is None
        assert "help" in kwargs

    def test_add_walltime_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[3]
        assert args == ("--walltime",)
        assert kwargs["default"] is None
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_hindcast.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            run_NEMO_hindcast.run_NEMO_hindcast,
            run_NEMO_hindcast.success,
            run_NEMO_hindcast.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "run_NEMO_hindcast" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["run_NEMO_hindcast"]
        assert msg_registry["checklist key"] == "NEMO run"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["run_NEMO_hindcast"]
        assert msg in msg_registry

    def test_optimum_hindcast_section(self, prod_config):
        optimum_hindcast = prod_config["run"]["hindcast hosts"]["optimum-hindcast"]
        assert optimum_hindcast["ssh key"] == "SalishSeaNEMO-nowcast_id_rsa"
        assert optimum_hindcast["users"] == "sallen,dlatorne"
        assert (
            optimum_hindcast["scratch dir"]
            == "/scratch/sallen/dlatorne/hindcast_v201812"
        )
        assert (
            optimum_hindcast["run prep dir"]
            == "/home/sallen/dlatorne/SalishSeaCast/hindcast-sys/runs"
        )
        assert (
            optimum_hindcast["salishsea cmd"]
            == "/home/sallen/dlatorne/.conda/envs/salishseacast/bin/salishsea"
        )


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(host_name="cedar")
        msg_type = run_NEMO_hindcast.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success"


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(host_name="cedar")
        msg_type = run_NEMO_hindcast.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure"


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_agrif.ssh_sftp.sftp",
    return_value=(Mock(name="ssh_client"), Mock(name="sftp_client")),
)
@patch(
    "nowcast.workers.run_NEMO_hindcast._get_prev_run_queue_info",
    autospec=True,
    return_value=(arrow.get("2018-01-01"), 12_345_678),
)
@patch("nowcast.workers.run_NEMO_hindcast._get_prev_run_namelist_info")
@patch("nowcast.workers.run_NEMO_hindcast._edit_namelist_time", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast._edit_run_desc", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast._launch_run", autospec=True)
class TestRunNEMO_Hindcast:
    """Unit tests for run_NEMO_hindcast() function.
    """

    @pytest.mark.parametrize("full_month", [True, False])
    def test_checklist_run_date_in_future(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        m_logger,
        full_month,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="cedar",
            full_month=full_month,
            prev_run_date=arrow.get("2019-01-11"),
        )
        with patch("nowcast.workers.run_NEMO_hindcast.arrow.now") as m_now:
            m_now.return_value = arrow.get("2019-01-30")
            checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)
        expected = {"hindcast": {"host": "cedar", "run id": "None"}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "full_month, prev_run_date, expected_run_id",
        [
            (True, arrow.get("2018-01-01"), "01feb18hindcast"),
            (False, arrow.get("2018-07-01"), "11jul18hindcast"),
            (False, arrow.get("2018-07-11"), "21jul18hindcast"),
            (False, arrow.get("2018-07-21"), "01aug18hindcast"),  # 31 day mo
            (False, arrow.get("2018-06-21"), "01jul18hindcast"),  # 30 day mo
            (False, arrow.get("2018-02-21"), "01mar18hindcast"),  # feb
            (False, arrow.get("2016-02-21"), "01mar16hindcast"),  # leap year
            (False, arrow.get("2017-12-21"), "01jan18hindcast"),  # year end
        ],
    )
    def test_checklist_with_prev_run_date(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        m_logger,
        full_month,
        prev_run_date,
        expected_run_id,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="cedar",
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=None,
        )
        checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)
        expected = {"hindcast": {"host": "cedar", "run id": expected_run_id}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "full_month, prev_run_date, expected_run_id",
        [
            (True, arrow.get("2018-01-01"), "01feb18hindcast"),
            (False, arrow.get("2018-07-01"), "11jul18hindcast"),
            (False, arrow.get("2018-07-11"), "21jul18hindcast"),
            (False, arrow.get("2018-07-21"), "01aug18hindcast"),  # 31 day mo
            (False, arrow.get("2018-06-21"), "01jul18hindcast"),  # 30 day mo
            (False, arrow.get("2018-02-21"), "01mar18hindcast"),  # feb
            (False, arrow.get("2016-02-21"), "01mar16hindcast"),  # leap year
            (False, arrow.get("2017-12-21"), "01jan18hindcast"),  # year end
        ],
    )
    def test_checklist_without_prev_run_date(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        m_logger,
        full_month,
        prev_run_date,
        expected_run_id,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="cedar", full_month=full_month, prev_run_date=None, walltime=None
        )
        m_get_prev_run_queue_info.return_value = (prev_run_date, 12_345_678)
        checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)
        expected = {"hindcast": {"host": "cedar", "run id": expected_run_id}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "full_month, prev_run_date, expected_run_date, expected_run_days",
        [
            (True, arrow.get("2018-01-01"), arrow.get("2018-02-01"), 28),  # 28d run
            (True, arrow.get("2016-01-01"), arrow.get("2016-02-01"), 29),  # 29d run
            (True, arrow.get("2018-02-01"), arrow.get("2018-03-01"), 31),  # 31d run
            (True, arrow.get("2018-03-01"), arrow.get("2018-04-01"), 30),  # 30d run
            (False, arrow.get("2018-07-01"), arrow.get("2018-07-11"), 10),  # 10d run
            (False, arrow.get("2018-07-11"), arrow.get("2018-07-21"), 11),  # 11d run
            (False, arrow.get("2018-02-11"), arrow.get("2018-02-21"), 8),  # 8d run
            (False, arrow.get("2016-02-11"), arrow.get("2016-02-21"), 9),  # 9d run
            (False, arrow.get("2018-07-21"), arrow.get("2018-08-01"), 10),  # 31 day mo
            (False, arrow.get("2018-06-21"), arrow.get("2018-07-01"), 10),  # 30 day mo
            (False, arrow.get("2018-02-21"), arrow.get("2018-03-01"), 10),  # feb
            (False, arrow.get("2016-02-21"), arrow.get("2016-03-01"), 10),  # leap year
            (False, arrow.get("2017-12-21"), arrow.get("2018-01-01"), 10),  # year end
        ],
    )
    def test_edit_namelist_time_run_date(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        m_logger,
        full_month,
        prev_run_date,
        expected_run_date,
        expected_run_days,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="cedar",
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=None,
        )
        run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)
        m_edit_namelist_time.assert_called_once_with(
            m_sftp()[1],
            "cedar",
            m_get_prev_run_namelist_info(),
            expected_run_date,
            expected_run_days,
            config,
        )

    @pytest.mark.parametrize(
        "full_month, prev_run_date, walltime, expected_run_date, expected_walltime",
        [
            (
                True,
                arrow.get("2018-07-01"),
                None,
                arrow.get("2018-08-01"),
                "12:00:00",
            ),  # default
            (
                True,
                arrow.get("2018-07-01"),
                "15:00:00",
                arrow.get("2018-08-01"),
                "15:00:00",
            ),
            (
                False,
                arrow.get("2018-07-01"),
                None,
                arrow.get("2018-07-11"),
                "06:00:00",
            ),  # default
            (
                False,
                arrow.get("2018-07-01"),
                "09:00:00",
                arrow.get("2018-07-11"),
                "09:00:00",
            ),
        ],
    )
    def test_edit_run_desc_walltime(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        m_logger,
        full_month,
        prev_run_date,
        walltime,
        expected_run_date,
        expected_walltime,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="cedar",
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=walltime,
        )
        run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)
        m_edit_run_desc.assert_called_once_with(
            m_sftp()[1],
            "cedar",
            prev_run_date,
            m_get_prev_run_namelist_info(),
            expected_run_date,
            expected_walltime,
            config,
        )


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
class TestGetPrevRunQueueInfo:
    """Unit tests for _get_prev_run_queue_info() function.
    """

    def test_no_job_found_on_queue(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_exec_cmd.return_value = "header\n"
        m_ssh_client = Mock(name="ssh_client")
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_prev_run_queue_info(m_ssh_client, "cedar", config)
        assert m_logger.error.called

    def test_found_prev_hindcast_job(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_exec_cmd.return_value = "header\n" "12345678 01may18hindcast\n"
        m_ssh_client = Mock(name="ssh_client")
        prev_run_date, job_id = run_NEMO_hindcast._get_prev_run_queue_info(
            m_ssh_client, "cedar", config
        )
        assert prev_run_date == arrow.get("2018-05-01")
        assert job_id == 12_345_678
        assert m_logger.info.called

    def test_no_prev_hindcast_job_found(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_exec_cmd.return_value = "header\n" "12345678 07may18nowcast-agrif\n"
        m_ssh_client = Mock(name="ssh_client")
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_prev_run_queue_info(m_ssh_client, "cedar", config)
        assert m_logger.error.called


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.f90nml.read", autospec=True)
class TestGetPrevRunNamelistInfo:
    """Unit test for _get_prev_run_namelist_info() function.
    """

    def test_get_prev_run_namelist_info(
        self, m_f90nml_read, m_ssh_exec_cmd, m_logger, config
    ):
        m_ssh_client = Mock(name="ssh_client")
        m_sftp_client = Mock(name="sftp_client")
        m_ssh_exec_cmd.return_value = "scratch/01may18hindcast_xxx/namelist_cfg\n"
        p_named_tmp_file = patch(
            "nowcast.workers.run_NEMO_hindcast.tempfile.NamedTemporaryFile",
            autospec=True,
        )
        m_f90nml_read.return_value = {
            "namrun": {"nn_itend": 2_717_280},
            "namdom": {"rn_rdt": 40.0},
        }
        with p_named_tmp_file as m_named_tmp_file:
            prev_namelist_info = run_NEMO_hindcast._get_prev_run_namelist_info(
                m_ssh_client, m_sftp_client, "cedar", arrow.get("2018-05-01"), config
            )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client, "ls -d scratch/01may18*/namelist_cfg", "cedar", m_logger
        )
        m_sftp_client.get.assert_called_once_with(
            "scratch/01may18hindcast_xxx/namelist_cfg",
            m_named_tmp_file().__enter__().name,
        )
        assert m_logger.info.called
        assert prev_namelist_info == SimpleNamespace(itend=2_717_280, rdt=40.0)


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.f90nml.patch", autospec=True)
class TestEditNamelistTime:
    """Unit tests for _edit_namelist_time() function.
    """

    def test_download_namelist_time(self, m_patch, m_logger, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            m_sftp_client,
            "cedar",
            prev_namelist_info,
            arrow.get("2018-02-01"),
            28,
            config,
        )
        m_sftp_client.get.assert_called_once_with(
            "runs/namelist.time", "/tmp/hindcast.namelist.time"
        )

    @pytest.mark.parametrize(
        "run_date, run_days, expected_itend, expected_stocklist",
        [
            (
                arrow.get("2018-03-01"),
                31,
                2_784_240,
                [2_738_880, 2_760_480, 2_784_240, 0, 0, 0, 0, 0, 0, 0],
            ),  # 31 day month
            (
                arrow.get("2018-02-01"),
                28,
                2_777_760,
                [2_738_880, 2_760_480, 2_777_760, 0, 0, 0, 0, 0, 0, 0],
            ),  # February
            (
                arrow.get("2016-02-01"),
                29,
                2_779_920,
                [2_738_880, 2_760_480, 2_779_920, 0, 0, 0, 0, 0, 0, 0],
            ),  # leap year
            (
                arrow.get("2018-04-01"),
                30,
                2_782_080,
                [2_738_880, 2_760_480, 2_782_080, 0, 0, 0, 0, 0, 0, 0],
            ),  # 30 day month
            (
                arrow.get("2018-04-01"),
                10,
                2_738_880,
                [2_738_880, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 10d run
            (
                arrow.get("2018-04-11"),
                10,
                2_738_880,
                [2_738_880, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 10d run
            (
                arrow.get("2018-02-21"),
                8,
                2_734_560,
                [2_734_560, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 8d run
            (
                arrow.get("2016-02-21"),
                9,
                2_736_720,
                [2_736_720, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 9d run
            (
                arrow.get("2018-03-21"),
                11,
                2_741_040,
                [2_741_040, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 11d run
        ],
    )
    def test_patch_namelist_time(
        self,
        m_patch,
        m_logger,
        run_date,
        run_days,
        expected_itend,
        expected_stocklist,
        config,
    ):
        sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            sftp_client, "cedar", prev_namelist_info, run_date, run_days, config
        )
        m_patch.assert_called_once_with(
            "/tmp/hindcast.namelist.time",
            {
                "namrun": {
                    "nn_it000": 2_717_280 + 1,
                    "nn_itend": expected_itend,
                    "nn_date0": int(run_date.format("YYYYMMDD")),
                    "nn_stocklist": expected_stocklist,
                }
            },
            "/tmp/patched_hindcast.namelist.time",
        )

    def test_upload_namelist_time(self, m_patch, m_logger, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        run_NEMO_hindcast._edit_namelist_time(
            m_sftp_client,
            "cedar",
            prev_namelist_info,
            arrow.get("2018-02-01"),
            28,
            config,
        )
        m_sftp_client.put.assert_called_once_with(
            "/tmp/patched_hindcast.namelist.time", "runs/namelist.time"
        )


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
@patch(
    "nowcast.workers.run_NEMO_agrif.yaml.safe_load",
    return_value={
        "run_id": "",
        "restart": {"restart.nc": "", "restart_trc.nc": ""},
        "walltime": "06:00:00",
    },
    autospec=True,
)
class TestEditRunDesc:
    """Unit tests for _edit_run_desc() function.
    """

    def test_download_run_desc_template(self, m_safe_load, m_logger, tmpdir, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure("hindcast_tmpl.yaml")
        run_NEMO_hindcast._edit_run_desc(
            m_sftp_client,
            "cedar",
            arrow.get("2018-01-01"),
            prev_namelist_info,
            arrow.get("2018-02-01"),
            "03:00:00",
            config,
            yaml_tmpl=Path(str(yaml_tmpl)),
        )
        m_sftp_client.get.assert_called_once_with(
            "runs/hindcast_template.yaml", yaml_tmpl
        )

    @pytest.mark.parametrize("walltime", ["03:00:00", "08:30:00", "12:00:00"])
    @patch("nowcast.workers.run_NEMO_hindcast.yaml.safe_dump", autospec=True)
    def test_edit_run_desc(
        self, m_safe_dump, m_safe_load, m_logger, walltime, tmpdir, config
    ):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure("hindcast_tmpl.yaml")
        with patch("nowcast.workers.run_NEMO_hindcast.Path.open") as m_open:
            run_NEMO_hindcast._edit_run_desc(
                m_sftp_client,
                "cedar",
                arrow.get("2018-05-01"),
                prev_namelist_info,
                arrow.get("2018-06-01"),
                walltime,
                config,
                yaml_tmpl=Path(str(yaml_tmpl)),
            )
        m_safe_dump.assert_called_once_with(
            {
                "run_id": "01jun18hindcast",
                "restart": {
                    "restart.nc": "scratch/01may18/SalishSea_02717280_restart.nc",
                    "restart_trc.nc": "scratch/01may18/SalishSea_02717280_restart_trc.nc",
                },
                "walltime": walltime,
            },
            m_open().__enter__(),
            default_flow_style=False,
        )

    def test_upload_run_desc(self, m_safe_load, m_logger, tmpdir, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure("hindcast_tmpl.yaml")
        run_NEMO_hindcast._edit_run_desc(
            m_sftp_client,
            "cedar",
            arrow.get("2018-01-01"),
            prev_namelist_info,
            arrow.get("2018-02-01"),
            "03:00:00",
            config,
            yaml_tmpl=Path(str(yaml_tmpl)),
        )
        m_sftp_client.put.assert_called_once_with(
            yaml_tmpl, "runs/01feb18hindcast.yaml"
        )


@patch("nowcast.workers.run_NEMO_hindcast.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
class TestLaunchRun:
    """Unit tests for _launch_run() function.
    """

    def test_launch_run(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_client = Mock(name="ssh_client")
        run_NEMO_hindcast._launch_run(
            m_ssh_client, "cedar", "01may18hindcast", prev_job_id=None, config=config
        )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            "bin/salishsea run runs/01may18hindcast.yaml scratch/01may18 "
            "--deflate --max-deflate-jobs 48",
            "cedar",
            m_logger,
        )

    def test_launch_run_with_prev_job_id(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_client = Mock(name="ssh_client")
        run_NEMO_hindcast._launch_run(
            m_ssh_client,
            "cedar",
            "01may18hindcast",
            prev_job_id=12_345_678,
            config=config,
        )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            "bin/salishsea run runs/01may18hindcast.yaml scratch/01may18 "
            "--deflate --max-deflate-jobs 48 "
            "--waitjob 12345678 --nocheck-initial-conditions",
            "cedar",
            m_logger,
        )

    def test_ssh_error(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_client = Mock(name="ssh_client")
        m_ssh_exec_cmd.side_effect = nowcast.ssh_sftp.SSHCommandError(
            "cmd", "stdout", "stderr"
        )
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._launch_run(
                m_ssh_client,
                "cedar",
                "01may18hindcast",
                prev_job_id=None,
                config=config,
            )
        m_logger.error.assert_called_once_with("stderr")
