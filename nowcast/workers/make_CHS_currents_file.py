# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""SalishSeaCast worker that average, unstaggers and rotates the near
surface velocities, and writes them out in an nc file for CHS to use
"""
import logging
import os
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker
from nowcast import lib
from salishsea_tools import viz_tools
import xarray

NAME = 'make_CHS_currents_file'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_CHS_currents_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'run_type',
        choices={'nowcast', 'forecast', 'forecast2'},
        help='''
        Type of run the velocities come from:
        'nowcast' means velocities stored in nowcast-blue directory
        'forecast' means velocities stored in forecast directory
        'forecast2' means velocities stored in forecast2 directory
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date to process the velocities for.'
    )
    worker.run(make_CHS_currents_file, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'Made CHS currents file for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'for {parsed_args.run_type}',
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
        f'Making CHS currents file for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'failed for {parsed_args.run_type}',
    )
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def make_CHS_currents_file(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    if run_type == 'nowcast':
        start_date = run_date.format("YYYYMMDD")
        end_date = run_date.format("YYYYMMDD")
    elif run_type == 'forecast':
        start_date = run_date.shift(days=1).format("YYYYMMDD")
        end_date = run_date.shift(days=2).format("YYYYMMDD")
    elif run_type == 'forecast2':
        start_date = run_date.shift(days=2).format("YYYYMMDD")
        end_date = run_date.shift(days=3).format("YYYYMMDD")

    grid_dir = Path(config['figures']['grid dir'])
    meshfilename = grid_dir / config['run types'][run_type]['mesh mask']

    run_type_results = Path(config['results archive'][run_type])
    results_dir = run_date.format('DDMMMYY').lower()
    src_dir = run_type_results / results_dir
    ufile = f'SalishSea_1h_{start_date}_{end_date}_grid_U.nc'
    vfile = f'SalishSea_1h_{start_date}_{end_date}_grid_V.nc'

    urot5, vrot5, urot10, vrot10 = _read_avg_unstagger_rotate(
        meshfilename, src_dir, ufile, vfile, run_type
    )

    CHS_currents_filename = _write_netcdf(
        src_dir, urot5, vrot5, urot10, vrot10, run_type
    )

    lib.fix_perms(CHS_currents_filename, grp_name=config['file group'])

    checklist = {
        run_type: {
            'filename': CHS_currents_filename,
            'run date': run_date.format('YYYY-MM-DD'),
        }
    }
    return checklist


def _read_avg_unstagger_rotate(meshfilename, src_dir, ufile, vfile, run_type):
    """
    :param str meshfilename:
    :param :py:class:`pathlib.Path` src_dir:
    :param str: ufile:
    :param str: vfile:
    :param str: run_type:

    :return: 4_tuple of data arrays
               urot5: east velocity averaged over top 5 grid cells
               vrot5: north velocity averaged over top 5 grid cells
               urot10: east velocity averaged over top 10 grid cells
               vrot10: north velocity averaged over top 5 grid cells
    """
    mesh = xarray.open_dataset(meshfilename)
    uds = xarray.open_dataset(src_dir / ufile)
    uupper = uds.vozocrtx.isel(depthu=slice(5)).where(
        mesh.umask.isel(z=slice(5)).rename({
            'z': 'depthu'
        })
    ).mean('depthu')
    ufull = uds.vozocrtx.isel(depthu=slice(10)).where(
        mesh.umask.isel(z=slice(10)).rename({
            'z': 'depthu'
        })
    ).mean('depthu')

    logger.debug(
        f'{run_type}: u velocity read and averaged from {src_dir/ufile}'
    )

    vds = xarray.open_dataset(src_dir / vfile)
    vupper = vds.vomecrty.isel(depthv=slice(5)).where(
        mesh.vmask.isel(z=slice(5)).rename({
            'z': 'depthv'
        })
    ).mean('depthv')
    vfull = vds.vomecrty.isel(depthv=slice(10)).where(
        mesh.vmask.isel(z=slice(10)).rename({
            'z': 'depthv'
        })
    ).mean('depthv')

    logger.debug(
        f'{run_type}: v velocity read and averaged from {src_dir/ufile}'
    )

    u5 = viz_tools.unstagger_xarray(uupper[:, :, :, 0], 'x')
    v5 = viz_tools.unstagger_xarray(vupper[:, :, :, 0], 'y')
    u10 = viz_tools.unstagger_xarray(ufull[:, :, :, 0], 'x')
    v10 = viz_tools.unstagger_xarray(vfull[:, :, :, 0], 'y')

    urot5, vrot5 = viz_tools.rotate_vel(u5, v5, origin='grid')
    urot10, vrot10 = viz_tools.rotate_vel(u10, v10, origin='grid')

    logger.debug(f'{run_type}: velocities unstaggered and rotated')

    return urot5, vrot5, urot10, vrot10


def _write_netcdf(src_dir, urot5, vrot5, urot10, vrot10, run_type):
    """
    :param :py:class:`pathlib.Path` src_dir:
    :param :py:class:`xarray.DataArray` urot5:
    :param :py:class:`xarray.DataArray` vrot5:
    :param :py:class:`xarray.DataArray` urot10:
    :param :py:class:`xarray.DataArray` vrot10:
    :param str: run_type:

    :return: str CHS_currents_filename
    """

    myds = xarray.Dataset(
        data_vars={
            'VelEast5': urot5,
            'VelNorth5': vrot5,
            'VelEast10': urot10,
            'VelNorth10': vrot10,
        },
        coords=urot5.coords
    )

    myds.VelEast5.attrs = {
        'long_name':
            'Upper 5 grid levels East Velocity',
        'standard_name':
            'eastward_sea_water_velocity_upper_5_grid_levels',
        'ioos_category':
            'currents',
        'comment':
            'Average velocity over the upper 5 grid levels, nominally 5 m',
        'units':
            'm/s'
    }
    myds.VelNorth5.attrs = {
        'long_name':
            'Upper 5 grid levels North Velocity',
        'standard_name':
            'northward_sea_water_velocity_upper_5_grid_levels',
        'ioos_category':
            'currents',
        'comment':
            'Average velocity over the upper 5 grid levels, nominally 5 m',
        'units':
            'm/s'
    }
    myds.VelEast10.attrs = {
        'long_name':
            'Upper 10 grid levels East Velocity',
        'standard_name':
            'eastward_sea_water_velocity_upper_10_grid_levels',
        'ioos_category':
            'currents',
        'comment':
            'Average velocity over the upper 10 grid levels, nominally 10 m',
        'units':
            'm/s'
    }
    myds.VelNorth10.attrs = {
        'long_name':
            'Upper 10 grid levels North Velocity',
        'standard_name':
            'northward_sea_water_velocity_upper_10_grid_levels',
        'ioos_category':
            'currents',
        'comment':
            'Average velocity over the upper 10 grid levels, nominally 10 m',
        'units':
            'm/s'
    }

    myds = myds.drop('time_centered')
    myds = myds.rename({'time_counter': 'time', 'x': 'gridX', 'y': 'gridY'})

    encoding = {
        'time': {
            'units': 'minutes since 1970-01-01 00:00',
            'dtype': float
        },
        'VelEast5': {
            'zlib': True,
            'complevel': 4
        },
        'VelNorth5': {
            'zlib': True,
            'complevel': 4
        },
        'VelEast10': {
            'zlib': True,
            'complevel': 4
        },
        'VelNorth10': {
            'zlib': True,
            'complevel': 4
        },
    }

    myds.attrs = {
        'creation_date':
            str(arrow.now()),
        'history':
            'CHS currents file made by nowcast worker: make_CHS_currents_file.py'
    }

    myds.coords['time'].attrs = {
        'axis': 'T',
        'comment':
            'time values are UTC at the centre of the intervals over which the '
            'calculated model results are averaged',
        'ioos_category': 'Time',
        'long_name': 'Time axis',
        'standard_name': 'time',
        'time_origin': '1970-01-01 00:00',
    }

    myds.coords['gridX'].attrs = {
        'ioos_category': 'location',
        'long_name': 'gridX',
        'axis': 'X',
        'units': 'count'
    }
    myds.coords['gridY'].attrs = {
        'ioos_category': 'location',
        'long_name': 'gridY',
        'axis': 'Y',
        'units': 'count'
    }

    filename = src_dir / 'CHS_currents.nc'
    myds.to_netcdf(filename, encoding=encoding, unlimited_dims=('time',))

    logger.debug(f'{run_type}: netcdf file written: {filename}')

    return os.fspath(filename)


if __name__ == '__main__':
    main()  # pragma: no cover
