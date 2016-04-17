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

"""Salish Sea nowcast worker that that builds the nowcast/forecast results
pages of the salishsea.eos.ubc.ca web site.
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

__all__ = ['main', 'success', 'failure', 'sphinx_build']


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        '--clean', action='store_true',
        help='Do a clean build instead of just updating new/changed files.'
    )
    worker.run(sphinx_build, success, failure)


def success(parsed_args):
    logger.info('sphinx built salishsea site')
    return 'success'


def failure(parsed_args):
    logger.critical('sphinx build of salishsea site failed')
    return 'failure'


def sphinx_build(parsed_args, config, *args):
    repo_name = config['web']['site_repo_url'].rsplit('/')[-1]
    repo_path = Path(config['web']['www_path'], repo_name)
    if parsed_args.clean:
        cmd = 'rm -rf {}'.format(repo_path/'site'/'_build')
        logger.debug('running {} to cause a full site build'.format(cmd))
        try:
            subprocess.run(shlex.split(cmd), check=True)
        except subprocess.CalledProcessError as e:
            logger.error(
                '{} failed with exit code {.returncode}'.format(cmd, e))
            raise WorkerError
    logger.debug('starting sphinx-build of {}'.format(repo_path/'site'))
    cmd = (
        'sphinx-build -b html -d {doctrees} -E {rst_path} {html_path}'
        .format(
            doctrees=repo_path/'site'/'_build'/'doctrees',
            rst_path=repo_path/'site',
            html_path=repo_path/'site'/'_build'/'html'))
    lib.run_in_subprocess(shlex.split(cmd), logger.debug, logger.error)
    logger.info('finished sphinx-build of {}'.format(repo_path/'site'))
    return {str(repo_path/'site'/'_build'/'html') :True}


if __name__ == '__main__':
    main()  # pragma: no cover
