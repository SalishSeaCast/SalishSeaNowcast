# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

"""Unit tests for Salish Sea NEMO nowcast hg_update_site worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import pytest


@pytest.fixture
def worker_module(scope='module'):
    from nowcast.workers import hg_update_site
    return hg_update_site


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

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.hg_update_site,
            worker_module.success,
            worker_module.failure,
        )


def test_success(worker_module):
    parsed_args = Mock()
    msg_typ = worker_module.success(parsed_args)
    assert msg_typ == 'success'


def test_failure(worker_module):
    parsed_args = Mock()
    msg_typ = worker_module.failure(parsed_args)
    assert msg_typ == 'failure'
