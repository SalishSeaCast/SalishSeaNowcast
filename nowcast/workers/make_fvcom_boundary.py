# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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
"""Salish Sea FVCOM Vancouver Harbour and Fraser River model worker that
produces boundary condition files for the FVCOM model open boundary in the
Strait of Georgia from the Salish Sea NEMO model results.
"""
from datetime import timedelta
import logging
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

import arrow
from nemo_nowcast import NowcastWorker
import OPPTools

NAME = 'make_fvcom_boundary'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_fvcom_boundary --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to make boundary files on'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'nowcast', 'forecast'},
        help='''
        Type of run to make boundary files for:
        'nowcast' means run for present UTC day (after NEMO nowcast run)
        'forecast' means updated forecast run 
        (next 36h UTC, after NEMO forecast run)
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date to make boundary files for.'
    )
    worker.run(make_fvcom_boundary, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'FVCOM {parsed_args.run_type} run boundary condition file for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'created on {parsed_args.host_name}',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f'FVCOM {parsed_args.run_type} run boundary condition file creation'
        f' for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'failed on {parsed_args.host_name}',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def make_fvcom_boundary(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    logger.info(
        f'Creating VHFR FVCOM open boundary file for {run_type} run from '
        f'{run_date.format("YYYY-MM-DD")} NEMO run'
    )
    fvcom_input_dir = Path(config['vhfr fvcom runs']['input dir'])
    try:
        shutil.rmtree(fvcom_input_dir)
    except FileNotFoundError:
        # input/ directory doesn't exist, and that's what we wanted
        pass
    fvcom_input_dir.mkdir()
    bdy_file_tmpl = config['vhfr fvcom runs']['boundary file template']
    bdy_file = bdy_file_tmpl.format(
        run_type=run_type, yyyymmdd=run_date.format('YYYYMMDD')
    )
    coupling_dir = Path(config['vhfr fvcom runs']['coupling dir'])
    nemo_nz_nodes_file = Path(config['vhfr fvcom runs']['nemo nz nodes file'])
    fvcom_nz_nodes_file = Path(
        config['vhfr fvcom runs']['fvcom nz nodes file']
    )
    fvcom_nz_centroids_file = Path(
        config['vhfr fvcom runs']['fvcom nz centroids file']
    )
    interpolant_files = config['vhfr fvcom runs']['grid interpolant files']
    interpolants = SimpleNamespace()
    for attr, filename in interpolant_files.items():
        setattr(interpolants, attr, os.fspath(coupling_dir / filename))
    nemo_vert_wrights_file = Path(
        config['vhfr fvcom runs']['nemo vertical weights file']
    )
    nemo_azimuth_file = Path(config['vhfr fvcom runs']['nemo azimuth file'])
    grid_dir = Path(config['vhfr fvcom runs']['fvcom grid']['grid dir'])
    fvcom_grid_file = Path(
        config['vhfr fvcom runs']['fvcom grid']['grid file']
    )
    fvcom_depths_file = Path(
        config['vhfr fvcom runs']['fvcom grid']['depths file']
    )
    fvcom_sigma_file = Path(
        config['vhfr fvcom runs']['fvcom grid']['sigma file']
    )
    nemo_bdy_dir = Path(
        config['vhfr fvcom runs']['run types'][run_type]
        ['nemo boundary results']
    )
    time_start_offsets = {
        'nowcast': timedelta(hours=0),
        'forecast': timedelta(hours=24),
    }
    time_start = run_date + time_start_offsets[run_type]
    time_end_offsets = {
        'nowcast': timedelta(hours=24),
        'forecast': timedelta(hours=60),
    }
    time_end = run_date + time_end_offsets[run_type]
    OPPTools.nesting.make_type3_nesting_file(
        fout=os.fspath(fvcom_input_dir / bdy_file),
        fnest_nemo=os.fspath(coupling_dir / nemo_nz_nodes_file),
        fnest_nodes=os.fspath(coupling_dir / fvcom_nz_nodes_file),
        fnest_elems=os.fspath(coupling_dir / fvcom_nz_centroids_file),
        interp_uv=interpolants,
        nemo_vertical_weight_file=os.fspath(
            coupling_dir / nemo_vert_wrights_file
        ),
        nemo_azimuth_file=os.fspath(coupling_dir / nemo_azimuth_file),
        fgrd=os.fspath(grid_dir / fvcom_grid_file),
        fbathy=os.fspath(grid_dir / fvcom_depths_file),
        fsigma=os.fspath(grid_dir / fvcom_sigma_file),
        input_dir=os.fspath(nemo_bdy_dir),
        time_start=time_start.format('YYYY-MM-DD HH:mm:ss'),
        time_end=time_end.format('YYYY-MM-DD HH:mm:ss')
    )
    logger.debug(
        f'Stored VHFR FVCOM open boundary file: {fvcom_input_dir/bdy_file}'
    )
    checklist = os.fspath(fvcom_input_dir / bdy_file)
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover
