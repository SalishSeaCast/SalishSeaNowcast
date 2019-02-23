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
"""Unit tests for Salish Sea NEMO nowcast ping_erddap worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import nemo_nowcast
import pytest

from nowcast.workers import ping_erddap


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
erddap:
  flag dir: tmp_flag_dir/
  datasetIDs:
    download_weather:
      - ubcSSaSurfaceAtmosphereFieldsV1
    SCVIP-CTD:
      - ubcONCSCVIPCTD15mV1
    SEVIP-CTD:
      - ubcONCSEVIPCTD15mV1
    LSBBL-CTD:
      - ubcONCLSBBLCTD15mV1
    USDDL-CTD:
      - ubcONCUSDDLCTD15mV1
    TWDP-ferry:
      - ubcONCTWDP1mV1
    VFPA-HADCP:
      - ubcVFPA2ndNarrowsCurrent2sV1
    nowcast-green:
      - ubcSSg3DBiologyFields1hV17-02
      - ubcSSg3DuGridFields1hV17-02
    nemo-forecast:
      - ubcSSfSandyCoveSSH10mV17-02
    wwatch3-forecast:
      - ubcSSf2DWaveFields30mV17-02
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.ping_erddap.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        ping_erddap.main()
        args, kwargs = m_worker.call_args
        assert args == ("ping_erddap",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        ping_erddap.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_dataset_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        ping_erddap.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("dataset",)
        assert kwargs["choices"] == {
            "download_weather",
            "SCVIP-CTD",
            "SEVIP-CTD",
            "USDDL-CTD",
            "TWDP-ferry",
            "VFPA-HADCP",
            "nowcast-green",
            "nemo-forecast",
            "wwatch3-forecast",
        }
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        ping_erddap.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            ping_erddap.ping_erddap,
            ping_erddap.success,
            ping_erddap.failure,
        )


@pytest.mark.parametrize(
    "dataset",
    [
        "download_weather",
        "SCVIP-CTD",
        "SEVIP-CTD",
        "USDDL-CTD",
        "TWDP-ferry",
        "VFPA-HADCP",
        "nowcast-green",
        "nemo-forecast",
        "wwatch3-forecast",
    ],
)
@patch("nowcast.workers.ping_erddap.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, dataset):
        parsed_args = SimpleNamespace(dataset=dataset)
        msg_type = ping_erddap.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {dataset}"


@pytest.mark.parametrize(
    "dataset",
    [
        "download_weather",
        "SCVIP-CTD",
        "SEVIP-CTD",
        "USDDL-CTD",
        "TWDP-ferry",
        "VFPA-HADCP",
        "nowcast-green",
        "nemo-forecast",
        "wwatch3-forecast",
    ],
)
@patch("nowcast.workers.ping_erddap.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, dataset):
        parsed_args = SimpleNamespace(dataset=dataset)
        msg_type = ping_erddap.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {dataset}"


@patch("nowcast.workers.ping_erddap.logger", autospec=True)
class TestPingErddap:
    """Unit tests for ping_erddap() function.
    """

    @pytest.mark.parametrize(
        "dataset",
        [
            "download_weather",
            "SCVIP-CTD",
            "SEVIP-CTD",
            "USDDL-CTD",
            "TWDP-ferry",
            "VFPA-HADCP",
            "nowcast-green",
            "nemo-forecast",
            "wwatch3-forecast",
        ],
    )
    def test_ping_erddap(self, m_logger, dataset, tmpdir, config):
        parsed_args = SimpleNamespace(dataset=dataset)
        tmp_flag_dir = tmpdir.ensure_dir("flag")
        with patch.dict(config["erddap"], {"flag dir": str(tmp_flag_dir)}):
            checklist = ping_erddap.ping_erddap(parsed_args, config)
        dataset_ids = config["erddap"]["datasetIDs"][dataset]
        for i, dataset_id in enumerate(dataset_ids):
            assert tmp_flag_dir.join(dataset_id).exists
            expected = call(f"{tmp_flag_dir.join(dataset_id)} touched")
            assert m_logger.debug.call_args_list[i] == expected
        expected = {dataset: config["erddap"]["datasetIDs"][dataset]}
        assert checklist == expected

    def test_no_datasetID(self, m_logger, tmpdir, config):
        parsed_args = SimpleNamespace(dataset="nowcast-green")
        tmp_flag_dir = tmpdir.ensure_dir("flag")
        with patch.dict(config["erddap"], {"flag dir": str(tmp_flag_dir)}):
            with patch.dict(config["erddap"]["datasetIDs"], {"nowcast-green": []}):
                checklist = ping_erddap.ping_erddap(parsed_args, config)
        assert not m_logger.debug.called
        assert checklist == {"nowcast-green": []}
