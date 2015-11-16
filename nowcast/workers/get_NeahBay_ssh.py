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

"""Salish Sea NEMO nowcast worker that scrapes NOAA Neah Bay storm surge
forecast site and generates western open boundary conditions ssh files.
"""
import argparse
import datetime
import logging
import os
import shutil
import traceback

from bs4 import BeautifulSoup
import pytz
import matplotlib
import netCDF4 as nc
import numpy as np
import pandas as pd
import zmq

from salishsea_tools import nc_tools

from nowcast import (
    figures,
    lib,
)


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()

#: Neah Bay sea surface height forcing file name template
FILENAME_TMPL = 'ssh_{:y%Ym%md%d}.nc'


URL = (
    'http://www.nws.noaa.gov/mdl/etsurge/index.php'
    '?page=stn&region=wc&datum=msl&list=&map=0-48&type=both&stn=waneah')


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
        checklist = getNBssh(parsed_args.run_type, config)
        logger.info(
            'Neah Bay sea surface height web scraping '
            'and file creation completed',
            extra={'run_type': parsed_args.run_type})
        # Exchange success messages with the nowcast manager process
        msg_type = 'success {.run_type}'.format(parsed_args)
        lib.tell_manager(
            worker_name, msg_type, config, logger, socket, checklist)
    except lib.WorkerError:
        logger.error(
            'Neah Bay sea surface height web scraping '
            'and file creation failed',
            extra={'run_type': parsed_args.run_type})
        # Exchange failure messages with the nowcast manager process
        msg_type = 'failure {.run_type}'.format(parsed_args)
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
        'run_type', choices=set(('nowcast', 'forecast', 'forecast2')),
        help='Type of run to execute.'
    )
    return parser


def getNBssh(run_type, config):
    """Generate sea surface height forcing files from the Neah Bay
    storm surge website.
    """
    fB = nc.Dataset(config['bathymetry'])
    lats = fB.variables['nav_lat'][:]
    lons = fB.variables['nav_lon'][:]
    fB.close()
    logger.debug(
        'loaded lats & lons from {bathymetry}'.format(**config),
        extra={'run_type': run_type})
    # Scrape the surge data from the website into a text file,
    # store the file in the run results directory,
    # and load the data for processing into netCDF4 files
    utc_now = datetime.datetime.now(pytz.timezone('UTC'))
    textfile = read_website(config['ssh']['ssh_dir'])
    lib.fix_perms(textfile, grp_name=config['file group'])
    data = load_surge_data(textfile)
    checklist = {'txt': os.path.basename(textfile)}
    # Store a copy of the text file in the run results directory so that
    # there is definitive record of the sea surface height data that was
    # used for the run
    run_date = utc_now_to_run_date(utc_now, run_type)
    results_dir = os.path.join(
        config['run']['results archive'][run_type],
        run_date.strftime('%d%b%y').lower())
    lib.mkdir(
        results_dir, logger, grp_name=config['file group'], exist_ok=True)
    shutil.copy2(textfile, results_dir)
    # Process the dates to find days with a full prediction
    dates = np.array(data.date.values)
    # Check if today is Jan or Dec
    isDec, isJan = False, False
    if utc_now.month == 1:
        isJan = True
    if utc_now.month == 12:
        isDec = True
    for i in range(dates.shape[0]):
        dates[i] = to_datetime(dates[i], utc_now.year, isDec, isJan)
    dates_list = list_full_days(dates)
    # Set up plotting
    fig, ax = setup_plotting()
    # Loop through full days and save netcdf
    ip = 0
    for d in dates_list:
        surges, tc, forecast_flag = retrieve_surge(d, dates, data)
        # Plotting
        if ip < 3:
            ax.plot(surges, '-o', lw=2, label=d.strftime('%d-%b-%Y'))
        ip = ip + 1
        filepath = save_netcdf(
            d, tc, surges, forecast_flag, textfile,
            config['ssh']['ssh_dir'], lats, lons)
        filename = os.path.basename(filepath)
        lib.fix_perms(filename, grp_name=config['file group'])
        if forecast_flag:
            if 'fcst' in checklist:
                checklist['fcst'].append(filename)
            else:
                checklist['fcst'] = [filename]
        else:
            checklist['obs'] = filename
    ax.legend(loc=4)
    image_file = os.path.join(
        os.path.dirname(config['logging']['log_files']['debug']), 'NBssh.png')
    figures.save_image(fig, image_file)
    lib.fix_perms(image_file, grp_name=config['file group'])
    return checklist


def read_website(save_path):
    """Read a website with Neah Bay storm surge predictions/observations.

    The data is stored in a file in save_path.

    Returns the filename.
    """
    html = lib.get_web_data(URL, logger)
    logger.debug(
        'downloaded Neah Bay storm surge observations & predictions from {}'
        .format(URL))
    # Parse the text table out of the HTML
    soup = BeautifulSoup(html)
    table = soup.find('pre').contents
    for line in table:
        line = line.replace('[', '')
        line = line.replace(']', '')
    logger.debug(
        'scraped observations & predictions table from downloaded HTML')
    # Save the table as a text file with the date it was generated as its name
    utc_now = datetime.datetime.now(pytz.timezone('UTC'))
    filepath = os.path.join(
        save_path, 'txt', 'sshNB_{:%Y-%m-%d_%H}.txt'.format(utc_now))
    with open(filepath, 'wt') as f:
        f.writelines(table)
    lib.fix_perms(filepath)
    logger.debug(
        'observations & predictions table saved to {}'.format(filepath))
    return filepath


def load_surge_data(filename):
    """Load the storm surge observations & predictions table from filename
    and return is as a Pandas DataFrame.
    """
    col_names = 'date surge tide obs fcst anom comment'.split()
    data = pd.read_csv(filename, skiprows=3, names=col_names, comment='#')
    data = data.dropna(how='all')
    logger.debug(
        'loaded observations & predictions table into Pandas DataFrame')
    return data


def utc_now_to_run_date(utc_now, run_type):
    """Calculate the run_date used for results directory naming from the
    present UTC time and run_type.

    The offsets used in the calculation are based on nominal start times
    of the NEMO runs less 2 hours.
    """
    offsets = {
        'nowcast': 16,
        'forecast': 18,
        'forecast2': 34,
    }
    return (utc_now - datetime.timedelta(hours=offsets[run_type])).date()


def save_netcdf(
    day, tc, surges, forecast_flag, textfile, save_path, lats, lons,
):
    """Save the surge for a given day in a netCDF4 file.
    """
    # Western open boundary (JdF) grid parameter values for NEMO
    startj, endj, r = 384, 471, 1
    lengthj = endj-startj

    # netCDF4 file setup
    filename = FILENAME_TMPL.format(day)
    if forecast_flag:
        filepath = os.path.join(save_path, 'fcst', filename)
        comment = 'Prediction from Neah Bay storm surge website'
    else:
        filepath = os.path.join(save_path, 'obs', filename)
        try:
            # Unlink file path in case it exists as a symlink to a fcst/
            # file created byh upload_forcing worker because there was
            # no obs/ file
            os.unlink(filepath)
        except OSError:
            # File path does not exist
            pass
        comment = 'Observation from Neah Bay storm surge website'
    comment = ' '.join((
        comment,
        'generated by Salish Sea NEMO nowcast {} worker'.format(worker_name),
        ))
    ssh_file = nc.Dataset(filepath, 'w')
    nc_tools.init_dataset_attrs(
        ssh_file,
        title='Neah Bay SSH hourly values',
        notebook_name='N/A',
        nc_filepath=filepath,
        comment=comment,
        quiet=True,
    )
    ssh_file.source = textfile
    ssh_file.references = (
        'https://bitbucket.org/salishsea/tools/src/tip/SalishSeaTools/'
        'salishsea_tools/nowcast/workers/{}.py'.format(worker_name))
    logger.debug('created western open boundary file {}'.format(filepath))

    # Create netCDF dimensions
    ssh_file.createDimension('time_counter', None)
    ssh_file.createDimension('yb', 1)
    ssh_file.createDimension('xbT', lengthj * r)

    # Create netCDF variables
    time_counter = ssh_file.createVariable(
        'time_counter', 'float32', ('time_counter'))
    time_counter.long_name = 'Time axis'
    time_counter.axis = 'T'
    time_counter.units = 'hour since 00:00:00 on {:%Y-%m-%d}'.format(day)
    # Latitudes and longitudes
    nav_lat = ssh_file.createVariable('nav_lat', 'float32', ('yb', 'xbT'))
    nav_lat.long_name = 'Latitude'
    nav_lat.units = 'degrees_north'
    nav_lon = ssh_file.createVariable('nav_lon', 'float32', ('yb', 'xbT'))
    nav_lon.long_name = 'Longitude'
    nav_lon.units = 'degrees_east'
    # Sea surface height
    sossheig = ssh_file.createVariable(
        'sossheig', 'float32', ('time_counter', 'yb', 'xbT'), zlib=True)
    sossheig.units = 'm'
    sossheig.long_name = 'Sea surface height'
    sossheig.grid = 'SalishSea2'
    # Baroclinic u and v velocity components
    vobtcrtx = ssh_file.createVariable(
        'vobtcrtx', 'float32', ('time_counter', 'yb', 'xbT'), zlib=True)
    vobtcrtx.units = 'm/s'
    vobtcrtx.long_name = 'Barotropic U Velocity'
    vobtcrtx.grid = 'SalishSea2'
    vobtcrty = ssh_file.createVariable(
        'vobtcrty', 'float32', ('time_counter', 'yb', 'xbT'), zlib=True)
    vobtcrty.units = 'm/s'
    vobtcrty.long_name = 'Barotropic V Velocity'
    vobtcrty.grid = 'SalishSea2'
    # Boundary description for NEMO
    nbidta = ssh_file.createVariable(
        'nbidta', 'int32', ('yb', 'xbT'), zlib=True)
    nbidta.long_name = 'i grid position'
    nbidta.units = 1
    nbjdta = ssh_file.createVariable(
        'nbjdta', 'int32', ('yb', 'xbT'), zlib=True)
    nbjdta.long_name = 'j grid position'
    nbjdta.units = 1
    nbrdta = ssh_file.createVariable(
        'nbrdta', 'int32', ('yb', 'xbT'), zlib=True)
    nbrdta.long_name = 'position from boundary'
    nbrdta.units = 1

    # Load values
    for ir in range(r):
        nav_lat[0, ir*lengthj:(ir+1)*lengthj] = lats[startj:endj, ir]
        nav_lon[0, ir*lengthj:(ir+1)*lengthj] = lons[startj:endj, ir]
        nbidta[0, ir*lengthj:(ir+1)*lengthj] = ir
        nbjdta[0, ir*lengthj:(ir+1)*lengthj] = range(startj, endj)
        nbrdta[0, ir*lengthj:(ir+1)*lengthj] = ir
    for ib in range(lengthj * r):
        sossheig[:, 0, ib] = surges
        time_counter[:] = tc + 1
        vobtcrtx[:, 0, ib] = np.zeros(len(surges))
        vobtcrty[:, 0, ib] = np.zeros(len(surges))
    ssh_file.close()
    lib.fix_perms(filepath)
    logger.debug('saved western open boundary file {}'.format(filepath))
    return filepath


def retrieve_surge(day, dates, data):
    """Gather the surge information for a single day.

    Return the surges in metres, an array with time_counter,
    and a flag indicating if this day was a forecast.
    """
    # Initialize forecast flag and surge array
    forecast_flag = False
    surge = []
    # Load tides
    ttide = figures.get_tides('Neah Bay')
    # Grab list of times on this day
    tc, ds = isolate_day(day, dates)
    for d in ds:
        # Convert datetime to string for comparing with times in data
        daystr = d.strftime('%m/%d %HZ')
        tide = ttide.pred_all[ttide.time == d].item()
        obs = data.obs[data.date == daystr].item()
        fcst = data.fcst[data.date == daystr].item()
        if obs == 99.90:
            # Fall daylight savings
            if fcst == 99.90:
                try:
                    # No new forecast value, so persist the previous value
                    surge.append(surge[-1])
                except IndexError:
                    # No values yet, so initialize with zero
                    surge = [0]
            else:
                surge.append(feet_to_metres(fcst) - tide)
                forecast_flag = True
        else:
            surge.append(feet_to_metres(obs) - tide)
    return surge, tc, forecast_flag


def isolate_day(day, dates):
    """Return array of time_counter and datetime objects over a 24 hour
    period covering one full day.
    """
    tc = np.arange(24)
    dates_return = []
    for t in dates:
        if t.month == day.month:
            if t.day == day.day:
                dates_return.append(t)
    return tc, np.array(dates_return)


def list_full_days(dates):
    """Return a list of days that have a full 24 hour data set.
    """
    # Check if first day is a full day
    tc, ds = isolate_day(dates[0], dates)
    if ds.shape[0] == tc.shape[0]:
        start = dates[0]
    else:
        start = dates[0] + datetime.timedelta(days=1)
    start = datetime.datetime(
        start.year, start.month, start.day, tzinfo=pytz.timezone('UTC'))
    # Check if last day is a full day
    tc, ds = isolate_day(dates[-1], dates)
    if ds.shape[0] == tc.shape[0]:
        end = dates[-1]
    else:
        end = dates[-1] - datetime.timedelta(days=1)
    end = datetime.datetime(
        end.year, end.month, end.day, tzinfo=pytz.timezone('UTC'))
    # list of dates that are full
    dates_list = [
        start + datetime.timedelta(days=i) for i in range((end-start).days+1)]
    return dates_list


def to_datetime(datestr, year, isDec, isJan):
    """Convert the string given by datestr to a datetime object.

    The year is an argument because the datestr in the NOAA data doesn't
    have a year.
    Times are in UTC/GMT.

    Return a datetime representation of datestr.
    """
    dt = datetime.datetime.strptime(datestr, '%m/%d %HZ')
    # Dealing with year changes.
    if isDec and dt.month == 1:
        dt = dt.replace(year=year+1)
    elif isJan and dt.month == 12:
        dt = dt.replace(year=year-1)
    else:
        dt = dt.replace(year=year)
    dt = dt.replace(tzinfo=pytz.timezone('UTC'))
    return dt


def feet_to_metres(feet):
    metres = feet*0.3048
    return metres


def setup_plotting():
    fig = matplotlib.figure.Figure(figsize=(10, 4))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title('Neah Bay SSH')
    ax.set_ylim([-1, 1])
    ax.grid()
    ax.set_ylabel('Sea surface height (m)')
    return fig, ax


if __name__ == '__main__':
    main()
