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

"""Salish Sea NEMO nowcast worker that blends EC Data for the Fraser River at
Hope with Climatology for all other rivers and generates runoff file.
"""
from __future__ import division

import argparse
import logging
import os
import traceback

import arrow
import netCDF4 as NC
import numpy as np
import yaml
import zmq

from salishsea_tools import rivertools
from salishsea_tools.nowcast import lib


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


#: Rivers runoff forcing file name template
FILENAME_TMPL = 'RFraserCElse_{:y%Ym%md%d}.nc'


def main():
    # Prepare the worker
    base_parser = lib.basic_arg_parser(
        worker_name, description=__doc__, add_help=False)
    parser = configure_argparser(
        prog=base_parser.prog,
        description=base_parser.description,
        parents=[base_parser],
    )
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.debug('running in process {}'.format(os.getpid()))
    logger.debug('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = make_runoff_file(parsed_args.run_date, config)
        logger.info(
            'Creation of runoff file from Fraser at Hope '
            'and climatology elsewhere completed')
        # Exchange success messages with nowcast manager process
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        # Exchange failure messages with nowcast manager process
        logger.critical('Rivers runoff file creation failed')
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


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        '--run-date', type=lib.arrow_date, default=arrow.now(),
        help='''
        Date of the run to upload files from;
        use YYYY-MM-DD format.
        Defaults to %(default)s.
        ''',
    )
    return parser


def make_runoff_file(run_date, config):
    """Create a rivers runoff file from real-time Fraser River at Hope
    average flow yesterday and climatology for all of the other rivers.
    """
    # Find yesterday
    now = run_date.floor('day')
    yesterday = now.replace(days=-1)
    # Find history of fraser flow
    fraserflow = get_fraser_at_hope(config)
    # Select yesterday's value
    step1 = fraserflow[fraserflow[:, 0] == yesterday.year]
    step2 = step1[step1[:, 1] == yesterday.month]
    step3 = step2[step2[:, 2] == yesterday.day]
    FlowAtHope = step3[0, 3]
    # Get climatology
    criverflow, lat, lon, riverdepth = get_river_climatology(config)
    # Interpolate to today
    driverflow = calculate_daily_flow(yesterday, criverflow)
    logger.debug(
        'Getting file for {yesterday}'
        .format(yesterday=yesterday.format('YYYY-MM-DD')))
    # Get Fraser Watershed Climatology without Fraser
    otherratio, fraserratio, nonFraser, afterHope = fraser_climatology(config)
    # Calculate combined runoff
    pd = rivertools.get_watershed_prop_dict('fraser')
    runoff = fraser_correction(
        pd, FlowAtHope, yesterday, afterHope, nonFraser, fraserratio,
        otherratio, driverflow)
    # and make the file
    directory = config['rivers']['rivers_dir']
    # set up filename to follow NEMO conventions
    filename = FILENAME_TMPL.format(yesterday.date())
    filepath = os.path.join(directory, filename)
    write_file(filepath, yesterday, runoff, lat, lon, riverdepth)
    logger.debug(
        'File written to {directory}/{filename}'
        .format(directory=directory, filename=filename))
    return filepath


def get_fraser_at_hope(config):
    """Read Fraser Flow data at Hope from ECget file
    """
    filename = config['rivers']['ECget Fraser flow']
    fraserflow = np.loadtxt(filename)
    return fraserflow


def get_river_climatology(config):
    """Read the monthly climatology that we will use for all the other rivers.
    """
    # Open monthly climatology
    filename = config['rivers']['monthly climatology']
    clim_rivers = NC.Dataset(filename)
    criverflow = clim_rivers.variables['rorunoff']
    # Get other variables so we can put them in new files
    lat = clim_rivers.variables['nav_lat']
    lon = clim_rivers.variables['nav_lon']
    riverdepth = clim_rivers.variables['rodepth']
    return criverflow, lat, lon, riverdepth


def calculate_daily_flow(yesterday, criverflow):
    """Interpolate the daily values from the monthly values.
    """
    pyear, nyear = yesterday.year, yesterday.year
    if yesterday.day < 16:
        prevmonth = yesterday.month-1
        if prevmonth == 0:  # handle January
            prevmonth = 12
            pyear = pyear - 1
        nextmonth = yesterday.month
    else:
        prevmonth = yesterday.month
        nextmonth = yesterday.month + 1
        if nextmonth == 13:  # handle December
            nextmonth = 1
            nyear = nyear + 1
    fp = yesterday - arrow.get(pyear, prevmonth, 15)
    fn = arrow.get(nyear, nextmonth, 15) - yesterday
    ft = fp+fn
    fp = fp.days/ft.days
    fn = fn.days/ft.days
    driverflow = fn*criverflow[prevmonth-1] + fp*criverflow[nextmonth-1]
    return driverflow


def fraser_climatology(config):
    """Read in the Fraser climatology separated from Hope flow.
    """
    with open(config['rivers']['Fraser climatology']) as f:
        fraser_climatology_separation = yaml.safe_load(f)
    otherratio = fraser_climatology_separation['Ratio that is not Fraser']
    fraserratio = fraser_climatology_separation['Ratio that is Fraser']
    nonFraser = np.array(fraser_climatology_separation['non Fraser by Month'])
    afterHope = np.array(fraser_climatology_separation['after Hope by Month'])
    return otherratio, fraserratio, nonFraser, afterHope


def fraser_correction(
    pd, fraserflux, yesterday, afterHope, NonFraser, fraserratio, otherratio,
    runoff
):
    """For the Fraser Basin only, replace basic values with the new
    climatology after Hope and the observed values for Hope.
    Note, we are changing runoff only and not using/changing river depth.
    """
    for key, river in pd.items():
        if "Fraser" in key:
            flux = calculate_daily_flow(yesterday, afterHope) + fraserflux
            subarea = fraserratio
        else:
            flux = calculate_daily_flow(yesterday, NonFraser)
            subarea = otherratio
        runoff = rivertools.fill_runoff_array(
            flux*river['prop']/subarea,
            river['i'], river['di'],
            river['j'], river['dj'],
            river['depth'], runoff, np.empty_like(runoff))[0]
    return runoff


def write_file(filepath, yesterday, flow, lat, lon, riverdepth):
    """Create the rivers runoff netCDF4 file.
    """
    nemo = NC.Dataset(filepath, 'w')
    nemo.description = 'Real Fraser Values, Daily Climatology for Other Rivers'
    # Dimensions
    ymax, xmax = lat.shape
    nemo.createDimension('x', xmax)
    nemo.createDimension('y', ymax)
    nemo.createDimension('time_counter', None)
    # Variables
    # Latitude and longitude
    nav_lat = nemo.createVariable('nav_lat', 'float32', ('y', 'x'), zlib=True)
    nav_lat[:] = lat[:]
    nav_lon = nemo.createVariable('nav_lon', 'float32', ('y', 'x'), zlib=True)
    nav_lon[:] = lon[:]
    # Time
    time_counter = nemo.createVariable(
        'time_counter', 'float32', ('time_counter'), zlib=True)
    time_counter.units = 'non-dim'
    time_counter = [1]
    # Runoff
    rorunoff = nemo.createVariable(
        'rorunoff', 'float32', ('time_counter', 'y', 'x'), zlib=True)
    rorunoff._Fillvalue = 0.
    rorunoff._missing_value = 0.
    rorunoff._units = 'kg m-2 s-1'
    rorunoff[0, :] = flow
    # Depth
    rodepth = nemo.createVariable('rodepth', 'float32', ('y', 'x'), zlib=True)
    rodepth._Fillvalue = -1.
    rodepth.missing_value = -1.
    rodepth.units = 'm'
    rodepth = riverdepth
    nemo.close()


if __name__ == '__main__':
    main()
