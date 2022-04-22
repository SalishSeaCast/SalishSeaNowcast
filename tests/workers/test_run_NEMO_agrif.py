#  Copyright 2013 – present by the SalishSeaCast Project contributors
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
"""Unit tests for SalishSeaCast run_NEMO_agrif worker.
"""
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

import nowcast.ssh_sftp
from nowcast.workers import run_NEMO_agrif


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                run:
                  enabled hosts:
                    orcinus:
                      ssh key: SalishSeaNEMO-nowcast_id_rsa
                      scratch dir: scratch/nowcast-agrif
                      run prep dir: nowcast-agrif-sys/runs
                      salishsea cmd: .local/bin/salishsea

                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.run_NEMO_agrif.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_agrif.main()
        args, kwargs = m_worker.call_args
        assert args == ("run_NEMO_agrif",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_agrif.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_agrif.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_agrif.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast-agrif"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_agrif.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_NEMO_agrif.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            run_NEMO_agrif.run_NEMO_agrif,
            run_NEMO_agrif.success,
            run_NEMO_agrif.failure,
        )


@patch("nowcast.workers.run_NEMO_agrif.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(
            host_name="orcinus", run_date=arrow.get("2018-04-30")
        )
        msg_type = run_NEMO_agrif.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success"


@patch("nowcast.workers.run_NEMO_agrif.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(
            host_name="orcinus", run_date=arrow.get("2018-04-30")
        )
        msg_type = run_NEMO_agrif.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure"


@patch("nowcast.workers.run_NEMO_agrif.logger", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_agrif.ssh_sftp.sftp",
    return_value=(Mock(name="ssh_client"), Mock(name="sftp_client")),
    autospec=True,
)
@patch("nowcast.workers.run_NEMO_agrif._get_prev_run_namelists_info", autospec=True)
@patch("nowcast.workers.run_NEMO_agrif._edit_namelist_times", autospec=True)
@patch("nowcast.workers.run_NEMO_agrif._edit_run_desc", autospec=True)
@patch(
    "nowcast.workers.run_NEMO_agrif._launch_run",
    return_value=(
        "30apr18nowcast-agrif_2018-05-01T142532.335255-0700",
        "9332731.orca2.ibb",
    ),
    autospec=True,
)
class TestRunNEMO_AGRIF:
    """Unit test for run_NEMO_agrif() function."""

    def test_checklist(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_times,
        _get_prev_run_namelists_info,
        m_sftp,
        m_logger,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="orcinus", run_date=arrow.get("2018-04-30")
        )
        checklist = run_NEMO_agrif.run_NEMO_agrif(parsed_args, config)
        expected = {
            "nowcast-agrif": {
                "host": "orcinus",
                "run id": "30apr18nowcast-agrif",
                "run dir": "30apr18nowcast-agrif_2018-05-01T142532.335255-0700",
                "job id": "9332731.orca2.ibb",
                "run date": "2018-04-30",
            }
        }
        assert checklist == expected


@patch("nowcast.workers.run_NEMO_agrif.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_agrif.f90nml.patch", autospec=True)
class TestEditNamelistTimes:
    """
    Unit tests for _edit_namelist_times() function.
    """

    def test_download_namelist_times(self, m_patch, m_logger, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_run_namelists_info = SimpleNamespace(itend=2_363_040, rdt=40)
        run_date = arrow.get("2018-04-30")
        run_NEMO_agrif._edit_namelist_times(
            m_sftp_client, "orcinus", prev_run_namelists_info, run_date, config
        )
        assert m_sftp_client.get.call_args_list == [
            call(
                "nowcast-agrif-sys/runs/namelist.time",
                "/tmp/nowcast-agrif.namelist.time",
            ),
            call(
                "nowcast-agrif-sys/runs/namelist.time.BS",
                "/tmp/nowcast-agrif.namelist.time.BS",
            ),
        ]

    def test_patch_namelist_times(self, m_patch, m_logger, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_run_namelists_info = SimpleNamespace(itend=2_363_040, rdt=40)
        run_date = arrow.get("2018-04-30")
        run_NEMO_agrif._edit_namelist_times(
            m_sftp_client, "orcinus", prev_run_namelists_info, run_date, config
        )
        assert m_patch.call_args_list == [
            call(
                "/tmp/nowcast-agrif.namelist.time",
                {
                    "namrun": {
                        "nn_it000": 2_363_041,
                        "nn_itend": 2_365_200,
                        "nn_date0": 20_180_430,
                    }
                },
                "/tmp/patched_nowcast-agrif.namelist.time",
            ),
            call(
                "/tmp/nowcast-agrif.namelist.time.BS",
                {"namrun": {"nn_date0": 20_180_430}},
                "/tmp/patched_nowcast-agrif.namelist.time.BS",
            ),
        ]

    def test_upload_namelist_times(self, m_patch, m_logger, config):
        m_sftp_client = Mock(name="sftp_client")
        prev_run_namelists_info = SimpleNamespace(itend=2_363_040, rdt=40)
        run_date = arrow.get("2018-04-30")
        run_NEMO_agrif._edit_namelist_times(
            m_sftp_client, "orcinus", prev_run_namelists_info, run_date, config
        )
        assert m_sftp_client.put.call_args_list == [
            call(
                "/tmp/patched_nowcast-agrif.namelist.time",
                "nowcast-agrif-sys/runs/namelist.time",
            ),
            call(
                "/tmp/patched_nowcast-agrif.namelist.time.BS",
                "nowcast-agrif-sys/runs/namelist.time.BS",
            ),
        ]


@patch("nowcast.workers.run_NEMO_agrif.logger", autospec=True)
@patch(
    "nowcast.workers.run_NEMO_agrif.yaml.safe_load",
    return_value={
        "run_id": "",
        "restart": {
            "restart.nc": "",
            "restart_trc.nc": "",
            "AGRIF_1": {"restart.nc": "", "restart_trc.nc": ""},
        },
    },
    autospec=True,
)
class TestEditRunDesc:
    """
    Unit tests for __edit_run_desc() function.
    """

    def test_download_run_desc_template(self, m_safe_load, m_logger, config, tmpdir):
        m_sftp_client = Mock(name="sftp_client")
        prev_run_namelists_info = SimpleNamespace(itend=2_363_040, rdt=40)
        setattr(prev_run_namelists_info, "1_rdt", 20)
        yaml_tmpl = tmpdir.ensure("nowcast-agrif_template.yaml")
        run_NEMO_agrif._edit_run_desc(
            m_sftp_client,
            "orcinus",
            prev_run_namelists_info,
            "30apr18nowcast-agrif",
            arrow.get("2018-04-30"),
            config,
            yaml_tmpl=yaml_tmpl,
        )
        m_sftp_client.get.assert_called_once_with(
            "nowcast-agrif-sys/runs/nowcast-agrif_template.yaml",
            "/tmp/nowcast-agrif_template.yaml",
        )

    @patch("nowcast.workers.run_NEMO_agrif.yaml.safe_dump", autospec=True)
    def test_edit_run_desc(self, m_safe_dump, m_safe_load, m_logger, config, tmpdir):
        m_sftp_client = Mock(name="sftp_client")
        prev_run_namelists_info = SimpleNamespace(itend=2_363_040, rdt=40)
        setattr(prev_run_namelists_info, "1_rdt", 20)
        yaml_tmpl = tmpdir.ensure("nowcast-agrif_template.yaml")
        with patch("nowcast.workers.run_NEMO_agrif.Path.open") as m_open:
            run_NEMO_agrif._edit_run_desc(
                m_sftp_client,
                "orcinus",
                prev_run_namelists_info,
                "30apr18nowcast-agrif",
                arrow.get("2018-04-30"),
                config,
                yaml_tmpl=yaml_tmpl,
            )
        m_safe_dump.assert_called_once_with(
            {
                "run_id": "30apr18nowcast-agrif",
                "restart": {
                    "restart.nc": "scratch/nowcast-agrif/29apr18/SalishSea_02363040_restart.nc",
                    "restart_trc.nc": "scratch/nowcast-agrif/29apr18/SalishSea_02363040_restart_trc.nc",
                    "AGRIF_1": {
                        "restart.nc": "scratch/nowcast-agrif/29apr18/1_SalishSea_04726080_restart.nc",
                        "restart_trc.nc": "scratch/nowcast-agrif/29apr18/1_SalishSea_04726080_restart_trc.nc",
                    },
                },
            },
            m_open().__enter__(),
            default_flow_style=False,
        )

    def test_upload_run_desc(self, m_safe_load, m_logger, config, tmpdir):
        m_sftp_client = Mock(name="sftp_client")
        prev_run_namelists_info = SimpleNamespace(itend=2_363_040, rdt=40)
        setattr(prev_run_namelists_info, "1_rdt", 20)
        yaml_tmpl = tmpdir.ensure("nowcast-agrif_template.yaml")
        run_NEMO_agrif._edit_run_desc(
            m_sftp_client,
            "orcinus",
            prev_run_namelists_info,
            "30apr18nowcast-agrif",
            arrow.get("2018-04-30"),
            config,
            yaml_tmpl=yaml_tmpl,
        )
        m_sftp_client.put.assert_called_once_with(
            "/tmp/nowcast-agrif_template.yaml",
            "nowcast-agrif-sys/runs/30apr18nowcast-agrif.yaml",
        )


@patch("nowcast.workers.run_NEMO_agrif.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_agrif.ssh_sftp.ssh_exec_command", autospec=True)
class TestLaunchRun:
    """
    Unit tests for _launch_run() function.
    """

    def test_launch_run(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_client = Mock(name="ssh_client")
        run_id = "30apr18nowcast-agrif"
        m_ssh_exec_cmd.return_value = (
            f"nemo_cmd.prepare WARNING: uncommitted changes in SS-run-sets\n"
            f"salishsea_cmd.run INFO: run directory "
            f"scratch/nowcast-agrif/{run_id}_2018-05-03T110532.335255-0700\n"
            f"salishsea_cmd.run INFO: 9332731.orca2.ibb\n\n"
        )
        run_dir, job_id = run_NEMO_agrif._launch_run(
            m_ssh_client, "orcinus", run_id, config
        )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            f".local/bin/salishsea run "
            f"nowcast-agrif-sys/runs/{run_id}.yaml "
            f"scratch/nowcast-agrif/30apr18 --debug",
            "orcinus",
            m_logger,
        )
        expected = f"scratch/nowcast-agrif/{run_id}_2018-05-03T110532.335255-0700"
        assert run_dir == expected
        assert job_id == "9332731.orca2.ibb"

    def test_ssh_error(self, m_ssh_exec_cmd, m_logger, config):
        m_ssh_client = Mock(name="ssh_client")
        m_ssh_exec_cmd.side_effect = nowcast.ssh_sftp.SSHCommandError(
            "cmd", "stdout", "stderr"
        )
        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_agrif._launch_run(
                m_ssh_client, "orcinus", "30apr18nowcast-agrif", config
            )
        m_logger.error.assert_called_once_with("stderr")
