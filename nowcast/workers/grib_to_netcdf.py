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

"""Salish Sea NEMO nowcast worker that collects weather forecast results
from hourly GRIB2 files and produces day-long NEMO atmospheric forceing
netCDF files.
"""
from __future__ import division

from collections import OrderedDict
import argparse
import glob
import logging
import os
import subprocess
import traceback

import arrow
import matplotlib
import netCDF4 as nc
import numpy as np
import zmq

from nowcast import (
    figures,
    lib,
)


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)
wgrib2_logger = logging.getLogger('wgrib2')

context = zmq.Context()


# Corners of sub-region of GEM 2.5km operational forecast grid
# that enclose the watersheds (other than the Fraser River)
# that are used to calculate river flows for runoff forcing files
# for the Salish Sea NEMO model.
# The Fraser is excluded because real-time gauge data at Hope are
# available for it.
IST, IEN = 110, 365
JST, JEN = 20, 285
# Position of Sandheads
SandI, SandJ = 151, 136

#: Weather forcing file name template
FILENAME_TMPL = 'ops_{:y%Ym%md%d}.nc'


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
    configure_wgrib2_logging(config)
    logger.debug('running in process {}'.format(os.getpid()))
    logger.debug('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = grib_to_netcdf(parsed_args.runtype,
                                   parsed_args.run_date, config)
        logger.info('NEMO-atmos forcing file completed for run type {.runtype}'
                    .format(parsed_args),
                    extra={'run_type': parsed_args.runtype})
        # Exchange success messages with the nowcast manager process
        msg_type = '{} {}'.format('success', parsed_args.runtype)
        lib.tell_manager(
            worker_name, msg_type, config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            'NEMO-atmos forcing file failed for run type {.runtype}'
            .format(parsed_args), extra={'run_type': parsed_args.runtype})
        # Exchange failure messages with the nowcast manager process
        msg_type = '{} {}'.format('failure', parsed_args.runtype)
        lib.tell_manager(worker_name, msg_type, config, logger, socket)
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
        'runtype', choices=set(('nowcast+', 'forecast2')),
        help='''Type of run to produce netCDF files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run.''',
    )
    parser.add_argument(
        '--run-date', type=lib.arrow_date, default=arrow.now(),
        help='''
        Date of the run to make the grib files for;
        use YYYY-MM-DD format.
        Note: for forecast2 use the date it would usually run on
        Defaults to %(default)s.
        ''',
    )
    return parser


def configure_wgrib2_logging(config):
    wgrib2_logger.setLevel(logging.DEBUG)
    log_file = os.path.join(
        os.path.dirname(config['config_file']),
        config['logging']['wgrib2_log_file'])
    handler = logging.FileHandler(log_file, mode='w')
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        config['logging']['message_format'],
        datefmt=config['logging']['datetime_format'])
    handler.setFormatter(formatter)
    wgrib2_logger.addHandler(handler)


def grib_to_netcdf(runtype, rundate, config):
    """Collect weather forecast results from hourly GRIB2 files
    and produces day-long NEMO atmospheric forcing netCDF files.
    """

    if runtype == 'nowcast+':
        (fcst_section_hrs_arr, zerostart, length, subdirectory,
         yearmonthday) = define_forecast_segments_nowcast(rundate)
    elif runtype == 'forecast2':
        (fcst_section_hrs_arr, zerostart, length, subdirectory,
         yearmonthday) = define_forecast_segments_forecast2(rundate)

    # set-up plotting
    fig, axs = set_up_plotting()
    checklist = {}
    ip = 0
    for fcst_section_hrs, zstart, flen, subdir, ymd in zip(
            fcst_section_hrs_arr, zerostart, length, subdirectory,
            yearmonthday):
        rotate_grib_wind(config, fcst_section_hrs)
        collect_grib_scalars(config, fcst_section_hrs)
        outgrib, outzeros = concat_hourly_gribs(config, ymd, fcst_section_hrs)
        outgrib, outzeros = crop_to_watersheds(
            config, ymd, IST, IEN, JST, JEN, outgrib, outzeros)
        outnetcdf, out0netcdf = make_netCDF_files(
            config, ymd, subdir, outgrib, outzeros)
        calc_instantaneous(outnetcdf, out0netcdf, ymd, flen, zstart,
                           axs)
        change_to_NEMO_variable_names(outnetcdf, axs, ip)
        ip += 1

        netCDF4_deflate(outnetcdf)
        lib.fix_perms(outnetcdf, grp_name=config['file group'])
        if subdir in checklist:
            checklist[subdir].append(os.path.basename(outnetcdf))
        else:
            if subdir:
                checklist[subdir] = [os.path.basename(outnetcdf)]
            else:
                checklist.update({subdir: os.path.basename(outnetcdf)})
    axs[2, 0].legend(loc='upper left')
    image_file = os.path.join(
        os.path.dirname(config['logging']['log_files']['debug']), 'wg.png')
    figures.save_image(fig, image_file)
    lib.fix_perms(image_file, grp_name=config['file group'])
    return checklist


def define_forecast_segments_nowcast(rundate):
    """Define segments of forecasts to build into working weather files
    for nowcast and a following forecast
    """

    today = rundate
    yesterday = today.replace(days=-1)
    tomorrow = today.replace(days=+1)
    nextday = today.replace(days=+2)
    fcst_section_hrs_arr = [OrderedDict() for x in range(3)]

    # today
    p1 = os.path.join(yesterday.format('YYYYMMDD'), '18')
    p2 = os.path.join(today.format('YYYYMMDD'), '00')
    p3 = os.path.join(today.format('YYYYMMDD'), '12')
    logger.debug('forecast sections: {} {} {}'.format(p1, p2, p3))
    fcst_section_hrs_arr[0] = OrderedDict([
        # (part, (dir, real start hr, forecast start hr, end hr))
        ('section 1', (p1, -1, 24-18-1, 24-18+0)),
        ('section 2', (p2, 1, 1-0, 12-0)),
        ('section 3', (p3, 13, 13-12, 23-12)),
    ])
    zerostart = [[1, 13]]
    length = [24]
    subdirectory = ['']
    yearmonthday = [today.strftime('y%Ym%md%d')]

    # tomorrow (forecast)
    p1 = os.path.join(today.format('YYYYMMDD'), '12')
    logger.debug('tomorrow forecast section: {}'.format(p1))
    fcst_section_hrs_arr[1] = OrderedDict([
        # (part, (dir, start hr, end hr))
        ('section 1', (p1, -1, 24-12-1, 24+23-12)),
    ])
    zerostart.append([])
    length.append(24)
    subdirectory.append('fcst')
    yearmonthday.append(tomorrow.strftime('y%Ym%md%d'))

    # next day (forecast)
    p1 = os.path.join(today.format('YYYYMMDD'), '12')
    logger.debug('next day forecast section: {}'.format(p1))
    fcst_section_hrs_arr[2] = OrderedDict([
        # (part, (dir, start hr, end hr))
        ('section 1', (p1, -1, 24+24-12-1, 24+24+12-12)),
    ])
    zerostart.append([])
    length.append(13)
    subdirectory.append('fcst')
    yearmonthday.append(nextday.strftime('y%Ym%md%d'))
    return (fcst_section_hrs_arr, zerostart, length, subdirectory,
            yearmonthday)


def define_forecast_segments_forecast2(rundate):
    """Define segments of forecasts to build into working weather files
    for the extend forecast i.e. forecast2
    """

    # today is the day after this nowcast/forecast sequence started
    today = rundate
    tomorrow = today.replace(days=+1)
    nextday = today.replace(days=+2)

    fcst_section_hrs_arr = [OrderedDict() for x in range(2)]

    # tomorrow
    p1 = os.path.join(today.format('YYYYMMDD'), '06')
    logger.info('forecast section: {}'.format(p1))
    fcst_section_hrs_arr[0] = OrderedDict([
        ('section 1', (p1, -1, 24-6-1, 24+23-6)),
    ])
    zerostart = [[]]
    length = [24]
    subdirectory = ['fcst']
    yearmonthday = [tomorrow.strftime('y%Ym%md%d')]

    # nextday
    p1 = os.path.join(today.format('YYYYMMDD'), '06')
    logger.info('next day forecast section: {}'.format(p1))
    fcst_section_hrs_arr[1] = OrderedDict([
        # (part, (dir, start hr, end hr))
        ('section 1', (p1, -1, 24+24-6-1, 24+24+6-6)),
    ])
    zerostart.append([])
    length.append(7)
    subdirectory.append('fcst')
    yearmonthday.append(nextday.strftime('y%Ym%md%d'))

    return (fcst_section_hrs_arr, zerostart, length, subdirectory,
            yearmonthday)


def rotate_grib_wind(config, fcst_section_hrs):
    """Use wgrib2 to consolidate each hour's u and v wind components into a
    single file and then rotate the wind direction to geographical
    coordinates.
    """
    GRIBdir = config['weather']['GRIB_dir']
    wgrib2 = config['weather']['wgrib2']
    grid_defn = config['weather']['grid_defn.pl']
    # grid_defn.pl expects to find wgrib2 in the pwd,
    # create a symbolic link to keep it happy (if its not already there)
    try:
        os.symlink(wgrib2, 'wgrib2')
    except OSError:
        pass
    for day_fcst, realstart, start_hr, end_hr in fcst_section_hrs.values():
        for fhour in range(start_hr, end_hr + 1):
            # Set up directories and files
            sfhour = '{:03d}'.format(fhour)
            outuv = os.path.join(GRIBdir, day_fcst, sfhour, 'UV.grib')
            outuvrot = os.path.join(GRIBdir, day_fcst, sfhour, 'UVrot.grib')
            # Delete residual instances of files that are created so that
            # function can be re-run cleanly
            try:
                os.remove(outuv)
            except OSError:
                pass
            try:
                os.remove(outuvrot)
            except OSError:
                pass
            # Consolidate u and v wind component values into one file
            for fpattern in ['*UGRD*', '*VGRD*']:
                fn = glob.glob(
                    os.path.join(GRIBdir, day_fcst, sfhour, fpattern))
                if os.stat(fn[0]).st_size == 0:
                    logger.critical('Problem, 0 size file {}'.format(fn[0]))
                    raise lib.WorkerError
                cmd = [wgrib2, fn[0], '-append', '-grib', outuv]
                lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
            # rotate
            GRIDspec = subprocess.check_output([grid_defn, outuv])
            cmd = [wgrib2, outuv]
            cmd.extend('-new_grid_winds earth'.split())
            cmd.append('-new_grid')
            cmd.extend(GRIDspec.split())
            cmd.append(outuvrot)
            lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
            os.remove(outuv)
    os.unlink('wgrib2')
    logger.debug('consolidated and rotated wind components')


def collect_grib_scalars(config, fcst_section_hrs):
    """Use wgrib2 and grid_defn.pl to consolidate each hour's scalar
    variables into an single file and then re-grid them to match the
    u and v wind components.
    """
    GRIBdir = config['weather']['GRIB_dir']
    wgrib2 = config['weather']['wgrib2']
    grid_defn = config['weather']['grid_defn.pl']
    # grid_defn.pl expects to find wgrib2 in the pwd,
    # create a symbolic link to keep it happy
    os.symlink(wgrib2, 'wgrib2')
    for day_fcst,  realstart, start_hr, end_hr in fcst_section_hrs.values():
        for fhour in range(start_hr, end_hr + 1):
            # Set up directories and files
            sfhour = '{:03d}'.format(fhour)
            outscalar = os.path.join(GRIBdir, day_fcst, sfhour, 'scalar.grib')
            outscalargrid = os.path.join(
                GRIBdir, day_fcst, sfhour, 'gscalar.grib')
            # Delete residual instances of files that are created so that
            # function can be re-run cleanly
            try:
                os.remove(outscalar)
            except OSError:
                pass
            try:
                os.remove(outscalargrid)
            except OSError:
                pass
            # Consolidate scalar variables into one file
            for fn in glob.glob(os.path.join(GRIBdir, day_fcst, sfhour, '*')):
                if not ('GRD' in fn) and ('CMC' in fn):
                    cmd = [wgrib2, fn, '-append', '-grib', outscalar]
                    lib.run_in_subprocess(
                        cmd, wgrib2_logger.debug, logger.error)
            #  Re-grid
            GRIDspec = subprocess.check_output([grid_defn, outscalar])
            cmd = [wgrib2, outscalar]
            cmd.append('-new_grid')
            cmd.extend(GRIDspec.split())
            cmd.append(outscalargrid)
            lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
            os.remove(outscalar)
    os.unlink('wgrib2')
    logger.debug('consolidated and re-gridded scalar variables')


def concat_hourly_gribs(config, ymd, fcst_section_hrs):
    """Concatenate in hour order the wind velocity components
    and scalar variables from hourly files into a daily file.

    Also create the zero-hour file that is used to initialize the
    calculation of instantaneous values from the forecast accumulated
    values.
    """
    GRIBdir = config['weather']['GRIB_dir']
    OPERdir = config['weather']['ops_dir']
    wgrib2 = config['weather']['wgrib2']
    outgrib = os.path.join(OPERdir, 'oper_allvar_{ymd}.grib'.format(ymd=ymd))
    outzeros = os.path.join(OPERdir, 'oper_000_{ymd}.grib'.format(ymd=ymd))

    # Delete residual instances of files that are created so that
    # function can be re-run cleanly
    try:
        os.remove(outgrib)
    except OSError:
        pass
    try:
        os.remove(outzeros)
    except OSError:
        pass
    for day_fcst,  realstart, start_hr, end_hr in fcst_section_hrs.values():
        for fhour in range(start_hr, end_hr + 1):
            # Set up directories and files
            sfhour = '{:03d}'.format(fhour)
            outuvrot = os.path.join(GRIBdir, day_fcst, sfhour, 'UVrot.grib')
            outscalargrid = os.path.join(
                GRIBdir, day_fcst, sfhour, 'gscalar.grib')
            if (fhour == start_hr and realstart == -1):
                cmd = [wgrib2, outuvrot, '-append', '-grib', outzeros]
                lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
                cmd = [wgrib2, outscalargrid, '-append', '-grib', outzeros]
                lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
            else:
                cmd = [wgrib2, outuvrot, '-append', '-grib', outgrib]
                lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
                cmd = [wgrib2, outscalargrid, '-append', '-grib', outgrib]
                lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
            os.remove(outuvrot)
            os.remove(outscalargrid)
    logger.debug(
        'concatenated variables in hour order from hourly files '
        'to daily file {}'.format(outgrib))
    logger.debug(
        'created zero-hour file for initialization of accumulated -> '
        'instantaneous values calculations: {}'.format(outzeros))
    return outgrib, outzeros


def crop_to_watersheds(config, ymd, ist, ien, jst, jen, outgrib,
                       outzeros):
    """Crop the grid to the sub-region of GEM 2.5km operational forecast
    grid that encloses the watersheds that are used to calculate river
    flows for runoff forcing files for the Salish Sea NEMO model.
    """
    OPERdir = config['weather']['ops_dir']
    wgrib2 = config['weather']['wgrib2']
    newgrib = os.path.join(
        OPERdir, 'oper_allvar_small_{ymd}.grib'.format(ymd=ymd))
    newzeros = os.path.join(
        OPERdir, 'oper_000_small_{ymd}.grib'.format(ymd=ymd))
    istr = '{ist}:{ien}'.format(ist=ist, ien=ien)
    jstr = '{jst}:{jen}'.format(jst=jst, jen=jen)
    cmd = [wgrib2, outgrib, '-ijsmall_grib', istr, jstr, newgrib]
    lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
    logger.debug(
        'cropped hourly file to watersheds sub-region: {}'
        .format(newgrib))
    cmd = [wgrib2, outzeros, '-ijsmall_grib', istr, jstr, newzeros]
    lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
    logger.debug(
        'cropped zero-hour file to watersheds sub-region: {}'
        .format(newgrib))
    os.remove(outgrib)
    os.remove(outzeros)
    return newgrib, newzeros


def make_netCDF_files(config, ymd, subdir, outgrib, outzeros):
    """Convert the GRIB files to netcdf (classic) files.
    """
    OPERdir = config['weather']['ops_dir']
    wgrib2 = config['weather']['wgrib2']
    outnetcdf = os.path.join(OPERdir, subdir, 'ops_{ymd}.nc'.format(ymd=ymd))
    out0netcdf = os.path.join(OPERdir, subdir,
                              'oper_000_{ymd}.nc'.format(ymd=ymd))
    cmd = [wgrib2, outgrib, '-netcdf', outnetcdf]
    lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
    logger.debug(
        'created hourly netCDF classic file: {}'
        .format(outnetcdf))
    lib.fix_perms(outnetcdf, grp_name=config['file group'])
    cmd = [wgrib2, outzeros, '-netcdf', out0netcdf]
    lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
    logger.debug(
        'created zero-hour netCDF classic file: {}'
        .format(out0netcdf))
    os.remove(outgrib)
    os.remove(outzeros)
    return outnetcdf, out0netcdf


def calc_instantaneous(outnetcdf, out0netcdf, ymd, flen, zstart, axs):
    """Calculate instantaneous values from the forecast accumulated values
    for the precipitation and radiation variables.
    """
    data = nc.Dataset(outnetcdf, 'r+')
    data0 = nc.Dataset(out0netcdf, 'r')
    acc_vars = ('APCP_surface', 'DSWRF_surface', 'DLWRF_surface')
    acc_values = {
        'acc': {},
        'zero': {},
        'inst': {},
    }
    for var in acc_vars:
        acc_values['acc'][var] = data.variables[var][:]
        acc_values['zero'][var] = data0.variables[var][:]
        acc_values['inst'][var] = np.empty_like(acc_values['acc'][var])
    data0.close()
    os.remove(out0netcdf)

    axs[1, 0].plot(acc_values['acc']['APCP_surface'][:, SandI, SandJ], 'o-')

    for var in acc_vars:
        acc_values['inst'][var][0] = (
            acc_values['acc'][var][0] - acc_values['zero'][var][0]) / 3600
        for realhour in range(1, flen):
            if realhour in zstart:
                acc_values['inst'][var][realhour] = (
                    acc_values['acc'][var][realhour] / 3600)
            else:
                acc_values['inst'][var][realhour] = (
                    acc_values['acc'][var][realhour]
                    - acc_values['acc'][var][realhour-1]) / 3600

    axs[1, 1].plot(
        acc_values['inst']['APCP_surface'][:, SandI, SandJ], 'o-',
        label=ymd)

    for var in acc_vars:
        data.variables[var][:] = acc_values['inst'][var][:]
    data.close()
    logger.debug(
        'calculated instantaneous values from forecast accumulated values '
        'for precipitation and long- & short-wave radiation')


def change_to_NEMO_variable_names(outnetcdf, axs, ip):
    """Rename variables to match NEMO naming conventions.
    """
    data = nc.Dataset(outnetcdf, 'r+')
    data.renameDimension('time', 'time_counter')
    data.renameVariable('latitude', 'nav_lat')
    data.renameVariable('longitude', 'nav_lon')
    data.renameVariable('time', 'time_counter')
    data.renameVariable('UGRD_10maboveground', 'u_wind')
    data.renameVariable('VGRD_10maboveground', 'v_wind')
    data.renameVariable('DSWRF_surface', 'solar')
    data.renameVariable('SPFH_2maboveground', 'qair')
    data.renameVariable('DLWRF_surface', 'therm_rad')
    data.renameVariable('TMP_2maboveground', 'tair')
    data.renameVariable('PRMSL_meansealevel', 'atmpres')
    data.renameVariable('APCP_surface', 'precip')
    logger.debug('changed variable names to their NEMO names')

    Temp = data.variables['tair'][:]
    axs[0, ip].pcolormesh(Temp[0])
    axs[0, ip].set_xlim([0, Temp.shape[2]])
    axs[0, ip].set_ylim([0, Temp.shape[1]])
    axs[0, ip].plot(SandI, SandJ, 'wo')

    if ip == 0:
        label = "day 1"
    elif ip == 1:
        label = "day 2"
    else:
        label = "day 3"
    humid = data.variables['qair'][:]
    axs[1, 2].plot(humid[:, SandI, SandJ], '-o')
    solar = data.variables['solar'][:]
    axs[2, 0].plot(solar[:, SandI, SandJ], '-o', label=label)
    longwave = data.variables['therm_rad'][:]
    axs[2, 1].plot(longwave[:, SandI, SandJ], '-o')
    pres = data.variables['atmpres'][:]
    axs[2, 2].plot(pres[:, SandI, SandJ], '-o')
    uwind = data.variables['u_wind'][:]
    axs[3, 0].plot(uwind[:, SandI, SandJ], '-o')
    vwind = data.variables['v_wind'][:]
    axs[3, 1].plot(vwind[:, SandI, SandJ], '-o')
    axs[3, 2].plot(np.sqrt(
        uwind[:, SandI, SandJ]**2 + vwind[:, SandI, SandJ]**2), '-o')

    data.close()


def netCDF4_deflate(outnetcdf):
    """Run ncks in a subprocess to convert outnetcdf to netCDF4 format
    with it variables compressed with Lempel-Ziv deflation.
    """
    cmd = ['ncks', '-4', '-L4', '-O', outnetcdf, outnetcdf]
    try:
        lib.run_in_subprocess(cmd, logger.debug, logger.error)
        logger.debug('netCDF4 deflated {}'.format(outnetcdf))
    except lib.WorkerError:
        raise


def set_up_plotting():
    fig = matplotlib.figure.Figure(figsize=(10, 15))
    axs = np.empty((4, 3), dtype='object')
    axs[0, 0] = fig.add_subplot(4, 3, 1)
    axs[0, 0].set_title('Air Temp. 0 hr')
    axs[0, 1] = fig.add_subplot(4, 3, 2)
    axs[0, 1].set_title('Air Temp. +1 day')
    axs[0, 2] = fig.add_subplot(4, 3, 3)
    axs[0, 2].set_title('Air Temp. +2 days')
    axs[1, 0] = fig.add_subplot(4, 3, 4)
    axs[1, 0].set_title('Accumulated Precip')
    axs[1, 1] = fig.add_subplot(4, 3, 5)
    axs[1, 1].set_title('Instant. Precip')
    axs[1, 2] = fig.add_subplot(4, 3, 6)
    axs[1, 2].set_title('Humidity')
    axs[2, 0] = fig.add_subplot(4, 3, 7)
    axs[2, 0].set_title('Solar Rad')
    axs[2, 1] = fig.add_subplot(4, 3, 8)
    axs[2, 1].set_title('Longwave Down')
    axs[2, 2] = fig.add_subplot(4, 3, 9)
    axs[2, 2].set_title('Sea Level Pres')
    axs[3, 0] = fig.add_subplot(4, 3, 10)
    axs[3, 0].set_title('u wind')
    axs[3, 1] = fig.add_subplot(4, 3, 11)
    axs[3, 1].set_title('v wind')
    axs[3, 2] = fig.add_subplot(4, 3, 12)
    axs[3, 2].set_title('Wind Speed')
    return fig, axs


if __name__ == '__main__':
    main()
