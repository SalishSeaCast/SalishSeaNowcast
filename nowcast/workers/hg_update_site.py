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

"""Salish Sea nowcast worker that updates (or creates) the
nowcast system clone of the salishsea.eos.ubc.ca static site repo
in preparation for a build of the site content.
"""
import logging
from pathlib import Path
import shlex

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.run(hg_update_site, success, failure)


def success(parsed_args):
    logger.info('hg updated salishsea-site repo')
    return 'success'


def failure(parsed_args):
    logger.critical('hg update of salishsea-site repo failed')
    return 'failure'


def hg_update_site(parsed_args, config, *args):
    repo_url = config['web']['site_repo_url']
    repo_name = repo_url.rsplit('/')[-1]
    www_path = Path(config['web']['www_path'])
    if (www_path/repo_name).exists():
        cmd = 'hg pull --update --cwd {repo}'.format(repo=www_path/repo_name)
        logger.debug('pulling updates from {}'.format(repo_url))
    else:
        cmd = (
            'hg clone {repo_url} {repo}'
            .format(repo_url=repo_url, repo=www_path/repo_name))
        logger.debug('cloning {}'.format(repo_url))
    lib.run_in_subprocess(shlex.split(cmd), logger.debug, logger.error)
    logger.info('hg updated {repo}'.format(repo=www_path/repo_name))
    return www_path/repo_name


if __name__ == '__main__':
    main()
