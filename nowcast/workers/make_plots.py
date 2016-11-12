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

"""Salish Sea NEMO nowcast worker that produces visualization images for
the web site from run results.
"""
import datetime
from glob import glob
import logging
import os
import shutil

import arrow
import matplotlib
matplotlib.use('Agg')
from nemo_nowcast import NowcastWorker
import netCDF4 as nc
import scipy.io as sio

from nowcast import lib
from nowcast.figures import (
    figures,
    research_VENUS,
    research_ferries,
)
from nowcast.figures.comparison import compare_venus_ctd
from nowcast.figures.publish import (
    pt_atkinson_tide,
    storm_surge_alerts,
    storm_surge_alerts_thumbnail,
    compare_tide_prediction_max_ssh,
)


NAME = 'make_plots'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_plots --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'run_type', choices={'nowcast', 'forecast', 'forecast2'},
        help='''
        Type of run to symlink files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        ''',
    )
    worker.cli.add_argument(
        'plot_type', choices={'publish', 'research', 'comparison'},
        help='''
        Which type of plots to produce:
        "publish" means ssh, weather and other approved plots for publishing,
        "research" means tracers, currents and other research plots
        "comparison" means ferry salinity plots
        '''
    )
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='Date of the run to symlink files for.'
    )
    worker.run(make_plots, success, failure)


def success(parsed_args):
    logger.info(
        '{0.plot_type} plots for {run_date} {0.run_type} completed'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'plot_type': parsed_args.plot_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {0.run_type} {0.plot_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.plot_type} plots failed for {run_date} {0.run_type} failed'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'plot_type': parsed_args.plot_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {0.run_type} {0.plot_type}'.format(parsed_args)
    return msg_type


def make_plots(parsed_args, config, *args):
    run_date = parsed_args.run_date
    dmy = run_date.format('DDMMMYY').lower()
    run_type = parsed_args.run_type
    plot_type = parsed_args.plot_type
    results_home = config['results archive'][run_type]
    dev_results_home = config['results archive']['nowcast-green']
    plots_dir = os.path.join(results_home, dmy, 'figures')
    lib.mkdir(plots_dir, logger, grp_name=config['file group'])
    _make_plot_files(
        config, run_type, plot_type, dmy, results_home, dev_results_home,
        plots_dir)
    checklist = _copy_plots_to_figures_server(
        config, run_type, plot_type, dmy, plots_dir)
    return checklist


def _make_plot_files(
    config, run_type, plot_type, dmy, results_home, dev_results_home, plots_dir,
):
    make_plots_funcs = {
        'publish': _make_publish_plots,
        'research': _make_research_plots,
        'comparison': _make_comparisons_plots,
    }
    weather_path = config['weather']['ops dir']
    if run_type in ['forecast', 'forecast2']:
        weather_path = os.path.join(weather_path, 'fcst/')
    results_dir = os.path.join(results_home, dmy)
    dev_results_dir = os.path.join(dev_results_home, dmy)
    bathy = nc.Dataset(config['run types'][run_type]['bathymetry'])
    coastline = sio.loadmat(config['figures']['coastline'])
    mesh_mask = nc.Dataset(config['run types'][run_type]['mesh mask'])
    dev_mesh_mask = nc.Dataset(
        config['run types']['nowcast-green']['mesh mask'])
    tidal_predictions = config['ssh']['tidal predictions']
    ferry_data_dir = config['observations']['ferry data']
    make_plots_funcs[plot_type](
        dmy, weather_path, bathy, results_dir, plots_dir, coastline,
        tidal_predictions=tidal_predictions,
        timezone=config['figures']['timezone'],
        mesh_mask=mesh_mask,
        dev_mesh_mask=dev_mesh_mask,
        ferry_data_dir=ferry_data_dir,
        dev_results_dir=dev_results_dir,
    )


def _copy_plots_to_figures_server(config, run_type, plot_type, dmy, plots_dir):
    dest_dir = os.path.join(
        config['figures']['storage path'], run_type, dmy)
    lib.mkdir(dest_dir, logger, grp_name=config['file group'])
    for f in glob(os.path.join(plots_dir, '*')):
        lib.fix_perms(f, grp_name=config['file group'])
        try:
            shutil.copy2(f, dest_dir)
        except shutil.SameFileError:
            # File was probably copied into destination directory
            # by a prior run of the make_plots worker;
            # e.g. nowcast research before publish
            pass
    checklist = {
        ' '.join((run_type, plot_type)): glob(os.path.join(dest_dir, '*'))}
    # Undated storm surge alerts thumbnail for storm-surge/index.html page
    now = arrow.now()
    today_dmy = now.format('DDMMMYY').lower()
    yesterday_dmy = now.replace(days=-1).format('DDMMMYY').lower()
    if all((
            plot_type == 'publish',
            any((
                run_type == 'forecast' and dmy == today_dmy,
                run_type == 'forecast2' and dmy == yesterday_dmy,
            ))
    )):
        thumbnail_root = config['figures']['storm surge alerts thumbnail']
        dmy_thumbnail = (
            '{plot_name}_{dmy}.png'.format(plot_name=thumbnail_root, dmy=dmy))
        dest_dir = os.path.join(
            config['figures']['storage path'],
            config['figures']['storm surge info portal path'])
        undated_thumbnail = os.path.join(
            dest_dir, '{}.png'.format(thumbnail_root))
        shutil.copy2(os.path.join(plots_dir, dmy_thumbnail), undated_thumbnail)
        checklist['storm surge alerts thumbnail'] = undated_thumbnail
    return checklist


def _make_publish_plots(
    dmy, weather_path, bathy, results_dir, plots_dir, coastline,
    tidal_predictions, timezone, **kwargs
):
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    names = ['Point Atkinson', 'Victoria', 'Campbell River', 'Cherry Point',
             'Friday Harbor', 'Neah Bay', 'Nanaimo', 'Sandheads']
    filepath_tmpl = os.path.join(results_dir, '{}.nc')
    grids_15m = {
        name: nc.Dataset(filepath_tmpl.format(name.replace(' ', '')))
        for name in names
    }

    logger.debug('starting storm_surge_alerts_thumbnail()')
    fig = storm_surge_alerts_thumbnail.storm_surge_alerts_thumbnail(
        grids_15m, weather_path, coastline, tidal_predictions)
    filename = os.path.join(
        plots_dir, 'Website_thumbnail_{date}.png'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))

    logger.debug('starting storm_surge_alerts()')
    fig = storm_surge_alerts.storm_surge_alerts(
        grids_15m, weather_path, coastline, tidal_predictions)
    filename = os.path.join(
        plots_dir, 'Threshold_website_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))

    logger.debug('starting pt_atkinson_tide()')
    fig = pt_atkinson_tide.pt_atkinson_tide(
        grid_T_hr, tidal_predictions, timezone)
    filename = os.path.join(
        plots_dir, 'PA_tidal_predictions_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))

    tide_gauge_stns = (
        # stn name, figure filename prefix
        ('Victoria', 'Vic_maxSSH'),
        ('Point Atkinson', 'PA_maxSSH'),
        ('Campbell River', 'CR_maxSSH'),
        ('Nanaimo', 'Nan_maxSSH'),
        ('Cherry Point', 'CP_maxSSH'),
    )
    for stn_name, fig_file_prefix in tide_gauge_stns:
        logger.debug(
            'starting compare_tide_prediction_max_ssh() for {}'
            .format(stn_name))
        fig = compare_tide_prediction_max_ssh.compare_tide_prediction_max_ssh(
            stn_name, grid_T_hr, grids_15m, bathy, weather_path,
            tidal_predictions, timezone)
        filename = os.path.join(
            plots_dir, '{fig_file_prefix}_{date}.svg'
            .format(date=dmy, fig_file_prefix=fig_file_prefix))
        fig.savefig(
            filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
        logger.info('{} saved'.format(filename))

    logger.debug('starting figures.compare_water_levels()')
    fig = figures.compare_water_levels(grid_T_hr, bathy, grids_15m, coastline)
    filename = os.path.join(
        plots_dir, 'NOAA_ssh_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))

    logger.debug('starting figures.plot_thresholds_all()')
    fig = figures.plot_thresholds_all(
        grid_T_hr, bathy, grids_15m, weather_path, coastline,
        tidal_predictions)
    filename = os.path.join(
        plots_dir, 'WaterLevel_Thresholds_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))

    logger.debug('starting figures.Sandheads_winds()')
    fig = figures.Sandheads_winds(grid_T_hr, bathy, weather_path, coastline)
    filename = os.path.join(
        plots_dir, 'SH_wind_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))

    logger.debug('starting figures.winds_average_max()')
    fig = figures.winds_average_max(
        grid_T_hr, bathy, weather_path, coastline,
        station='all', wind_type='average')
    filename = os.path.join(
        plots_dir, 'Avg_wind_vectors_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))

    logger.debug('starting figures.winds_average_max()')
    fig = figures.winds_average_max(
        grid_T_hr, bathy, weather_path, coastline,
        station='all', wind_type='max')
    filename = os.path.join(
        plots_dir, 'Wind_vectors_at_max_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))


def _make_comparisons_plots(
    dmy, weather_path, bathy, results_dir, plots_dir, coastline,
    timezone, mesh_mask, dev_mesh_mask, ferry_data_dir, dev_results_dir,
    **kwargs
):
    """Make the plots we wish to look at for comparisons purposes.
    """
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    dev_grid_T_hr = _results_dataset('1h', 'grid_T', dev_results_dir)

    # Wind speed and direction at Sandheads
    fig = figures.Sandheads_winds(grid_T_hr, bathy, weather_path, coastline)
    filename = os.path.join(plots_dir, 'SH_wind_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())
    logger.info('{} saved'.format(filename))

    # Ferry routes surface salinity
    for ferry_route in ('HB_DB', 'TW_DP', 'TW_SB'):
        try:
            fig = research_ferries.salinity_ferry_route(
                ferry_data_dir, grid_T_hr, bathy, ferry_route, dmy)
            filename = os.path.join(
                plots_dir, '{route}_ferry_salinity_{date}.svg'
                .format(route=ferry_route, date=dmy))
            fig.savefig(filename, facecolor=fig.get_facecolor())
            logger.info('{} saved'.format(filename))
        except (KeyError, ValueError, FileNotFoundError) as e:
            # Observations missing salinity data,
            # or ferry data or run results (most likely the former)
            # file not found,
            # so abort plot creation
            logger.debug(
                'ferry salinity comparison figure for {} failed: {}'
                .format(ferry_route, e))

    # VENUS bottom temperature and salinity
    node_names = (
        'East node', 'Central node', 'Delta BBL node', 'Delta DDL node')
    for node_name in node_names:
        try:
            fig = compare_venus_ctd.compare_venus_ctd(
                node_name, grid_T_hr, dev_grid_T_hr, timezone, mesh_mask,
                dev_mesh_mask)
            filename = os.path.join(
                plots_dir, 'Compare_VENUS_{node}_{date}.svg'
                .format(node=node_name.rstrip(' node').replace(' ', '_'), date=dmy))
            fig.savefig(filename, facecolor=fig.get_facecolor())
            logger.info('{} saved'.format(filename))
        except TypeError:
            # Observations missing, so about figure creation
            logger.debug(
                'VENUS {} CTD comparison figure failed: '
                'No observations available'.format(node_name))


def _future_comparison_plots(
    dmy, weather_path, bathy, results_dir, plots_dir, coastline, adcp_dir,
    **kwargs
):
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)

    venus_nodes = {
        'Central': {
            'grid_15m': nc.Dataset(
                os.path.join(results_dir, 'VENUS_central_gridded.nc')),
            'grid_obs': sio.loadmat(os.path.join(adcp_dir, 'ADCPcentral.mat')),
        }
    }
    grid_c = _results_dataset_gridded('central', results_dir)
    grid_e = _results_dataset_gridded('east', results_dir)
    grid_d = _results_dataset_gridded('delta', results_dir)
    grid_oc = sio.loadmat('/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPcentral.mat')
    grid_oe = sio.loadmat('/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPeast.mat')
    grid_od = sio.loadmat('/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPddl.mat')

    # ADCP plots
    date = datetime.datetime.strptime(dmy, '%d%b%y')
    date = date.replace(minute=45)
    models = [grid_c, grid_e, grid_d]
    obs = [grid_oc, grid_oe, grid_od]
    names = ['Central', 'East', 'ddl']
    dranges = [[0, 285], [0, 150], [0, 148]]
    for model, obs, name, drange in zip(models, obs, names, dranges):
        fig = research_VENUS.plotADCP(
            model, obs, date, name, drange)
        filename = os.path.join(
            plots_dir, '{station}_ADCP_{date}.svg'.format(station=name,
                                                          date=dmy))
        fig.savefig(filename, facecolor=fig.get_facecolor())
        logger.info('{} saved'.format(filename))

        fig = research_VENUS.plotdepavADCP(
            model, obs, date, name)
        filename = os.path.join(
            plots_dir, '{station}_depavADCP_{date}.svg'.format(station=name,
                                                               date=dmy))
        fig.savefig(filename, facecolor=fig.get_facecolor())
        logger.info('{} saved'.format(filename))

        fig = research_VENUS.plottimeavADCP(
            model, obs, date, name)
        filename = os.path.join(
            plots_dir, '{station}_timeavADCP_{date}.svg'.format(station=name,
                                                                date=dmy))
        fig.savefig(filename, facecolor=fig.get_facecolor())
        logger.info('{} saved'.format(filename))


def _make_research_plots(
    dmy, weather_path, bathy, results_dir, plots_dir, coastline, mesh_mask,
    **kwargs
):
    """Make the plots we wish to look at for research purposes.
    """
    grid_T_dy = _results_dataset('1d', 'grid_T', results_dir)
    grid_U_dy = _results_dataset('1d', 'grid_U', results_dir)
    grid_V_dy = _results_dataset('1d', 'grid_V', results_dir)
    grid_c = _results_dataset_gridded('central', results_dir)
    grid_e = _results_dataset_gridded('east', results_dir)

    fig = figures.thalweg_salinity(grid_T_dy, mesh_mask, bathy)
    filename = os.path.join(
        plots_dir, 'Salinity_on_thalweg_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))

    fig = figures.thalweg_temperature(grid_T_dy, mesh_mask, bathy)
    filename = os.path.join(
        plots_dir, 'Temperature_on_thalweg_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))

    fig = figures.plot_surface(grid_T_dy, grid_U_dy, grid_V_dy, bathy)
    filename = os.path.join(
        plots_dir, 'T_S_Currents_on_surface_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))

    fig = research_VENUS.plot_vel_NE_gridded('Central', grid_c)
    filename = os.path.join(
        plots_dir, 'Currents_at_VENUS_Central_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))

    fig = research_VENUS.plot_vel_NE_gridded('East', grid_e)
    filename = os.path.join(
        plots_dir, 'Currents_at_VENUS_East_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')
    logger.info('{} saved'.format(filename))


def _results_dataset(period, grid, results_dir):
    """Return the results dataset for period (e.g. 1h or 1d)
    and grid (e.g. grid_T, grid_U) from results_dir.
    """
    filename_pattern = 'SalishSea_{period}_*_{grid}.nc'
    filepaths = glob(os.path.join(
        results_dir, filename_pattern.format(period=period, grid=grid)))
    return nc.Dataset(filepaths[0])


def _results_dataset_gridded(station, results_dir):
    """Return the results dataset for station (e.g. central or east)
    for the quarter hourly data from results_dir.
    """
    filename_pattern = 'VENUS_{station}_gridded.nc'
    filepaths = glob(os.path.join(
        results_dir, filename_pattern.format(station=station)))
    return nc.Dataset(filepaths[0])


if __name__ == '__main__':
    main()
