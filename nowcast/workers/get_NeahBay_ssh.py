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

"""Salish Sea NEMO nowcast Neah Bay sea surface height download worker.

Scrape the NOAA Neah Bay storm surge site for sea surface height
observations and forecast values,
and generate the western open boundary ssh files.
"""
import datetime
import logging
import os
import shutil

from bs4 import BeautifulSoup
import matplotlib.backends.backend_agg
import matplotlib.figure
from nemo_nowcast import (
    get_web_data,
    NowcastWorker,
)
from nemo_nowcast.fileutils import FilePerms
import netCDF4 as nc
import numpy as np
import pytz
from salishsea_tools import nc_tools

from nowcast import (
    lib,
    residuals,
)


NAME = 'get_NeahBay_ssh'
logger = logging.getLogger(NAME)


#: NOAA Neah Bay sea surface height observations & forecast site URL
URL = (
    'http://www.nws.noaa.gov/mdl/etsurge/index.php'
    '?page=stn&region=wc&datum=msl&list=&map=0-48&type=both&stn=waneah')


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.get_NeahBay_ssh --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'run_type', choices={'nowcast', 'forecast', 'forecast2'},
        help="""
        Type of run to prepare open boundary sea surface height file for.
        """,
    )
    worker.run(get_NeahBay_ssh, success, failure)


def success(parsed_args):
    logger.info(
        'Neah Bay sea surface height web scraping and open boundary file '
        'creation for {.run_type} complete'
        .format(parsed_args), extra={'run_type': parsed_args.run_type})
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        'Neah Bay sea surface height web scraping and open boundary file '
        'creation for {.run_type} failed'
        .format(parsed_args), extra={'run_type': parsed_args.run_type})
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def get_NeahBay_ssh(parsed_args, config, *args):
    """Generate sea surface height forcing files from the Neah Bay
    storm surge website.
    """
    run_type = parsed_args.run_type
    with nc.Dataset(config['coordinates']) as coordinates:
        lats = coordinates.variables['nav_lat'][:]
        lons = coordinates.variables['nav_lon'][:]
    logger.debug(
        'loaded lats & lons from {[coordinates]}'.format(config),
        extra={'run_type': run_type})
    # Scrape the surge data from the website into a text file,
    # store the file in the run results directory,
    # and load the data for processing into netCDF4 files
    utc_now = datetime.datetime.now(pytz.timezone('UTC'))
    textfile = _read_website(config['ssh']['ssh dir'])
    lib.fix_perms(textfile, grp_name=config['file group'])
    checklist = {'txt': os.path.basename(textfile)}
    # Store a copy of the text file in the run results directory so that
    # there is definitive record of the sea surface height data that was
    # used for the run
    run_date = _utc_now_to_run_date(utc_now, run_type)
    results_dir = os.path.join(
        config['results archive'][run_type],
        run_date.strftime('%d%b%y').lower())
    lib.mkdir(
        results_dir, logger, grp_name=config['file group'], exist_ok=True)
    shutil.copy2(textfile, results_dir)
    # Grab all surge data in the textfile
    dates, sshs, fflags = residuals.NeahBay_forcing_anom(
        textfile, run_date, config['ssh']['tidal predictions'])
    # Identify days with full ssh information
    dates_full = _list_full_days(dates, sshs, fflags)
    # Set up plotting
    fig, ax = _setup_plotting()
    # Loop through full days and save netcdf
    ip = 0
    for d in dates_full:
        tc, _, sshd, fflagd = _isolate_day(d, dates, sshs, fflags)
        forecast_flag = fflagd.any()
        # Plotting
        if ip < 3:
            ax.plot(sshd, '-o', lw=2, label=d.strftime('%d-%b-%Y'))
        ip = ip + 1
        filepath = _save_netcdf(
            d, tc, sshd, forecast_flag, textfile, config, lats, lons)
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
    try:
        image_file = (
            config['logging']['handlers']['get_NeahBay_ssh_png']['filename'])
    except KeyError:
        image_file = (
            config['logging']['publisher']['handlers']['get_NeahBay_ssh_png']
            ['filename'])
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
    canvas.print_figure(image_file)
    lib.fix_perms(image_file, grp_name=config['file group'])
    return checklist


def _read_website(save_path):
    """Read a website with Neah Bay storm surge predictions/observations.

    The data is stored in a file in save_path.

    Returns the filename.
    """
    html = get_web_data(URL, NAME)
    logger.debug(
        'downloaded Neah Bay storm surge observations & predictions from {}'
        .format(URL))
    # Parse the text table out of the HTML
    soup = BeautifulSoup(html, 'html.parser')
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
    os.chmod(filepath, FilePerms(user='rw', group='rw', other='r'))
    logger.debug(
        'observations & predictions table saved to {}'.format(filepath))
    return filepath


def _utc_now_to_run_date(utc_now, run_type):
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


def _save_netcdf(
    day, tc, surges, forecast_flag, textfile, config, lats, lons,
):
    """Save the surge for a given day in a netCDF4 file.
    """
    # Western open boundary (JdF) grid parameter values for NEMO
    startj, endj, r = 384, 471, 1
    lengthj = endj-startj

    # netCDF4 file setup
    save_path = config['ssh']['ssh dir']
    filename = config['ssh']['file template'].format(day)
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
        comment, 'generated by Salish Sea NEMO nowcast {} worker'.format(NAME)))
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
        'https://bitbucket.org/salishsea/tools/src/tip/SalishSeaNowcast/'
        'nowcast/workers/{}.py'.format(NAME))
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
    os.chmod(filepath, FilePerms(user='rw', group='rw', other='r'))
    logger.debug('saved western open boundary file {}'.format(filepath))
    return filepath


def _isolate_day(day, dates, surges, forecast_flags):
    """Return array of time_counter and datetime objects over a 24 hour
    period covering one full day.
    Returns the surge and forecast_flag for that day as well
    """
    tc = np.arange(24)
    dates_r = []
    surge_r = []
    flag_r = []
    for t, surge, flag in zip(dates, surges, forecast_flags):
        if t.month == day.month:
            if t.day == day.day:
                dates_r.append(t)
                surge_r.append(surge)
                flag_r.append(flag)
    return tc, np.array(dates_r), np.array(surge_r), np.array(flag_r)


def _list_full_days(dates, surges, forecast_flags):
    """Return a list of days that have a full 24 hour data set.
    """
    # Check if first day is a full day
    tc, ds, _, _ = _isolate_day(dates[0], dates, surges, forecast_flags)
    if ds.shape[0] == tc.shape[0]:
        start = dates[0]
    else:
        start = dates[0] + datetime.timedelta(days=1)
    start = datetime.datetime(
        start.year, start.month, start.day, tzinfo=pytz.timezone('UTC'))
    # Check if last day is a full day
    tc, ds, _, _ = _isolate_day(dates[-1], dates, surges, forecast_flags)
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


def _setup_plotting():
    fig = matplotlib.figure.Figure(figsize=(10, 4))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title('Neah Bay SSH')
    ax.set_ylim([-1, 1])
    ax.grid()
    ax.set_ylabel('Sea surface height (m)')
    return fig, ax


if __name__ == '__main__':
    main()  # pragma: no cover
