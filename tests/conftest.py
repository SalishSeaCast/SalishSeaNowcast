#  Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""Fixture for SalishSeaCast test suite.
"""
from pathlib import Path
from unittest.mock import patch

import nemo_nowcast
import pytest


@pytest.fixture()
def base_config(tmpdir):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment containing elements
    required by all unit tests.
    """
    p = tmpdir.join("config.yaml")
    p.write(
        """
# Items required by the Config instance        
checklist file: nowcast_checklist.yaml
python: python
logging:
  handlers: []

"""
    )
    config_ = nemo_nowcast.Config()
    config_.load(str(p))
    return config_


@pytest.fixture()
def prod_config(tmpdir):
    """:py:class:`nemo_nowcast.Config` instance from production config YAML file to use for
    testing its contents.
    """
    prod_config_ = nemo_nowcast.Config()
    p_logs_dir = tmpdir.ensure_dir("nowcast_logs")
    p_env_dir = tmpdir.ensure_dir("nowcast-env")
    p_environ = patch.dict(
        nemo_nowcast.config.os.environ,
        {"NOWCAST_LOGS": str(p_logs_dir), "NOWCAST_ENV": str(p_env_dir)},
    )
    prod_config_file = (Path(__file__).parent / "../config/nowcast.yaml").resolve()
    with p_environ:
        prod_config_.load(prod_config_file)
    return prod_config_
