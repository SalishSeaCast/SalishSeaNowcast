# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Salish Sea NEMO nowcast worker that build the nowcast/forecast results
pages of the salishsea.eos.ubc.ca web site and pushes them to the site.
"""
import logging
import os
import subprocess
import traceback

import zmq

from salishsea_tools.nowcast import lib


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


def main():
    # Prepare the worker
    parser = lib.basic_arg_parser(worker_name, description=__doc__)
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.debug('running in process {}'.format(os.getpid()))
    logger.debug('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = push_to_web(config)
        logger.info(
            'results pages & figure files pushed to salishsea.eos.ubc.ca site')
        # Exchange success messages with the nowcast manager process
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical('push to aslishsea.eos.ubc.ca site failed')
        # Exchange failure messages with the nowcast manager process
        lib.tell_manager(worker_name, 'failure', config, logger, socket)
    except SystemExit:
        # Normal termination
        pass
    except:
        logger.critical('unhandled exception:')
        for line in traceback.format_exc().splitlines():
            logger.error(line)
        # Exchange crash messages with the nowcast manager process
        lib.tell_manager(worker_name, 'crash', config, logger, socket)
    # Finish up
    context.destroy()
    logger.debug('task completed; shutting down')


def push_to_web(config):
    repo_path = hg_update(
        config['web']['site_repo_url'], config['web']['www_path'])
    html_path = sphinx_build(repo_path)
    results_pages = [
        os.path.join(
            *config['web']['site_storm_surge_path'].split(os.path.sep)[1:]),
        os.path.join(
            *config['web']['site_nemo_results_path'].split(os.path.sep)[1:]),
    ]
    plots_paths = [
        os.path.join(
            *config['web']['site_storm_surge_plot_path']
            .split(os.path.sep)[1:]),
        os.path.join(
            *config['web']['site_plots_path'].split(os.path.sep)[1:]),
    ]
    rsync_to_site(
        html_path, results_pages, plots_paths, config['web']['server_path'])
    checklist = True
    return checklist


def hg_update(repo_url, www_path):
    """Pull changes from repo_url and update its clone in www_path.

    If the clone does not yet exist, create it.
    """
    repo_name = repo_url.rsplit('/')[-1]
    repo = os.path.join(www_path, repo_name)
    if os.path.exists(repo):
        cmd = ['hg', 'pull', '--update', '--cwd', repo]
        logger.debug('pulling updates from {}'.format(repo_url))
    else:
        cmd = ['hg', 'clone', repo_url, repo]
        logger.debug('cloning{}'.format(repo_url))
    lib.run_in_subprocess(cmd, logger.debug, logger.error)
    logger.info('hg updated {}'.format(repo))
    return repo


def sphinx_build(repo_path):
    """Do a clean build of the site by deleting the site/_build tree
    and then running sphinx-build.
    """
    site_path = os.path.join(repo_path, 'site')
    build_path = os.path.join(site_path, '_build')
    html_path = os.path.join(build_path, 'html')
    logger.debug('starting sphinx-build of {}'.format(site_path))
    cmd = 'rm -rf {}'.format(os.path.join(build_path, '*'))
    subprocess.check_call(cmd, shell=True)
    cmd = [
        'sphinx-build',
        '-b', 'html',
        '-d', os.path.join(build_path, 'doctrees'),
        '-E',
        site_path,
        html_path,
    ]
    lib.run_in_subprocess(cmd, logger.debug, logger.error)
    logger.info('finished sphinx-build of {}'.format(site_path))
    return html_path


def rsync_to_site(html_path, results_pages, plots_paths, server_path):
    """Push the results pages and plot files to the web server.
    """
    for results_path in results_pages:
        cmd = [
            'rsync', '-rRtv',
            '{}/./{}/'.format(html_path, results_path),
            server_path,
        ]
        lib.run_in_subprocess(cmd, logger.debug, logger.error)
        logger.info(
            'pushed {} results pages to {}/'.format(results_path, server_path))
    for plots_path in plots_paths:
        cmd = [
            'rsync', '-rRtv',
            '{}/./{}/'.format(html_path, plots_path),
            server_path,
        ]
        lib.run_in_subprocess(cmd, logger.debug, logger.error)
        logger.info('pushed {} plots to {}/'.format(plots_path, server_path))


if __name__ == '__main__':
    main()
