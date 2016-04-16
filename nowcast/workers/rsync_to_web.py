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

"""Salish Sea nowcast worker that that uses rsync to deploy the
nowcast/forecast results pages of the salishsea.eos.ubc.ca web site to the
web server.
"""
import logging
from pathlib import Path
import subprocess
import shlex

from nowcast import lib
from nowcast.nowcast_worker import (
    NowcastWorker,
    WorkerError,
)

__all__ = ['main', 'success', 'failure', 'rsync_to_web']


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.run(rsync_to_web, success, failure)


def success(parsed_args):
    logger.info('rsync-ed salishsea site pages to web')
    return 'success'


def failure(parsed_args):
    logger.critical('rsync of salishsea site pages to web failed')
    return 'failure'


def rsync_to_web(parsed_args, config, *args):
    checklist = {}
    repo_name = config['web']['site_repo_url'].rsplit('/')[-1]
    repo_path = Path(config['web']['www_path'], repo_name)
    site_path = Path(config['web']['www_site'])
    server_path = config['web']['server_path']
    for path in ('storm_surge_path', 'nemo_results_path'):
        results_path = config['web'][path]
        cmd = 'rsync -rRv {html_path}/./{results_path}/ {server_path}'.format(
            html_path=repo_path/'site'/'_build'/'html',
            results_path=results_path,
            server_path=server_path)
        lib.run_in_subprocess(shlex.split(cmd), logger.debug, logger.error)
        logger.info(
            'rsync-ed {} results pages to {}'.format(results_path, server_path))
        checklist[results_path] = True
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover

