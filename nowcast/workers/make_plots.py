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
import netCDF4 as nc
import scipy.io as sio

matplotlib.use('Agg')
from nowcast import (
    figures,
    lib,
    research_VENUS,
    research_ferries,
)
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'run_type', choices=set(('nowcast', 'forecast', 'forecast2')),
        help='''
        Type of run to symlink files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        ''',
    )
    worker.arg_parser.add_argument(
        'plot_type', choices=set(('publish', 'research', 'comparison')),
        help='''
        Which type of plots to produce:
        "publish" means ssh, weather and other approved plots for publishing,
        "research" means tracers, currents and other research plots
        "comparison" means ferry salinity plots
        '''
    )
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date of the run to symlink files for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.run(make_plots, success, failure)


def success(parsed_args):
    logger.info(
        '{0.plot_type} plots for {0.run_type} completed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'plot_type': parsed_args.plot_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {0.run_type} {0.plot_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.plot_type} plots failed for {0.run_type} failed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'plot_type': parsed_args.plot_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {0.run_type} {0.plot_type}'.format(parsed_args)
    return msg_type


def make_plots(parsed_args, config):
    run_date = parsed_args.run_date
    dmy = run_date.format('DDMMMYY').lower()
    run_type = parsed_args.run_type
    plot_type = parsed_args.plot_type
    results_home = config['run']['results archive'][run_type]
    plots_dir = os.path.join(results_home, dmy, 'figures')
    lib.mkdir(plots_dir, logger, grp_name='sallen')
    _make_plot_files(
        config, run_type, plot_type, dmy, results_home, plots_dir)
    checklist = _copy_plots_to_www_path(
        config, run_type, plot_type, dmy, plots_dir)
    if plot_type == 'publish' and run_type in ('forecast', 'forecast2'):
        summary_plot = _install_storm_surge_summary_plot(
            config, dmy, plots_dir)
        checklist['Most recent summary plot'] = summary_plot
    return checklist


def _make_plot_files(
    config, run_type, plot_type, dmy, results_home, plots_dir,
):
    make_plots_funcs = {
        'publish': _make_publish_plots,
        'research': _make_research_plots,
        'comparison': _make_comparisons_plots,
    }
    model_path = config['weather']['ops_dir']
    if run_type in ['forecast', 'forecast2']:
        model_path = os.path.join(model_path, 'fcst/')
    results_dir = os.path.join(results_home, dmy)
    bathy = nc.Dataset(config['bathymetry'])
    coastline = sio.loadmat(config['coastline'])
    mesh_mask = nc.Dataset(config['mesh_mask'])
    tidal_predictions = config['ssh']['tidal_predictions']
    make_plots_funcs[plot_type](
        dmy, model_path, bathy, results_dir, plots_dir, coastline,
        tidal_predictions=tidal_predictions,
        mesh_mask=mesh_mask,
    )


def _copy_plots_to_www_path(config, run_type, plot_type, dmy, plots_dir):
    www_plots_path = os.path.join(
        config['web']['www_path'],
        os.path.basename(config['web']['site_repo_url']),
        config['web']['site_plots_path'],
        run_type,
        dmy)
    lib.mkdir(www_plots_path, logger, grp_name=config['file group'])
    for f in glob(os.path.join(plots_dir, '*')):
        lib.fix_perms(f, grp_name=config['file group'])
        shutil.copy2(f, www_plots_path)
    checklist = {' '.join((run_type, plot_type)):
                 glob(os.path.join(www_plots_path, '*'))}
    return checklist


def _install_storm_surge_summary_plot(config, dmy, plots_dir):
    site_storm_surge_plot_name = config['web']['site_storm_surge_plot']
    dmy_plot = '{plot_name}_{dmy}.png'.format(
        plot_name=site_storm_surge_plot_name,
        dmy=dmy)
    summary_plot = os.path.join(
        config['web']['www_path'],
        os.path.basename(config['web']['site_repo_url']),
        config['web']['site_storm_surge_plot_path'],
        '{plot_name}.png'
        .format(plot_name=config['web']['site_storm_surge_plot']))
    shutil.copy2(os.path.join(plots_dir, dmy_plot), summary_plot)
    return summary_plot


def _make_publish_plots(
    dmy, model_path, bathy, results_dir, plots_dir, coastline,
    tidal_predictions, **kwargs
):
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    names = ['Point Atkinson', 'Victoria', 'Campbell River', 'Cherry Point',
             'Friday Harbor', 'Neah Bay', 'Nanaimo', 'Sandheads']
    filepath_tmpl = os.path.join(results_dir, '{}.nc')
    grids_15m = {
        name: nc.Dataset(filepath_tmpl.format(name.replace(' ', '')))
        for name in names
    }

    fig = figures.website_thumbnail(
        bathy, grid_T_hr, grids_15m, model_path, coastline, tidal_predictions)
    filename = os.path.join(
        plots_dir, 'Website_thumbnail_{date}.png'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.plot_threshold_website(
        bathy, grid_T_hr, grids_15m, model_path, coastline, tidal_predictions)
    filename = os.path.join(
        plots_dir, 'Threshold_website_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.PA_tidal_predictions(grid_T_hr, tidal_predictions)
    filename = os.path.join(
        plots_dir, 'PA_tidal_predictions_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, tidal_predictions,
        name='Victoria')
    filename = os.path.join(
        plots_dir, 'Vic_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, tidal_predictions,
        name='Point Atkinson')
    filename = os.path.join(
        plots_dir, 'PA_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, tidal_predictions,
        name='Campbell River')
    filename = os.path.join(
        plots_dir, 'CR_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, tidal_predictions,
        name='Nanaimo')
    filename = os.path.join(
        plots_dir, 'Nan_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, tidal_predictions,
        name='Cherry Point')
    filename = os.path.join(
        plots_dir, 'CP_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_water_levels(grid_T_hr, bathy, grids_15m, coastline)
    filename = os.path.join(
        plots_dir, 'NOAA_ssh_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.plot_thresholds_all(grid_T_hr, bathy, grids_15m, model_path,
                                      coastline)
    filename = os.path.join(
        plots_dir, 'WaterLevel_Thresholds_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.Sandheads_winds(grid_T_hr, bathy, model_path, coastline)
    filename = os.path.join(
        plots_dir, 'SH_wind_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.winds_average_max(
        grid_T_hr, bathy, model_path, coastline,
        station='all', wind_type='average')
    filename = os.path.join(
        plots_dir, 'Avg_wind_vectors_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.winds_average_max(
        grid_T_hr, bathy, model_path, coastline,
        station='all', wind_type='max')
    filename = os.path.join(
        plots_dir, 'Wind_vectors_at_max_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())


def _make_comparisons_plots(
    dmy, model_path, bathy, results_dir, plots_dir, coastline, **kwargs
):
    """Make the plots we wish to look at for comparisons purposes.
    """
    # get the results
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    grid_c = _results_dataset_gridded('central', results_dir)
    grid_e = _results_dataset_gridded('east', results_dir)
    grid_d = _results_dataset_gridded('delta', results_dir)

    # ONC ADCP data
    grid_oc = sio.loadmat('/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPcentral.mat')
    grid_oe = sio.loadmat('/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPeast.mat')
    grid_od = sio.loadmat('/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPddl.mat')

    # do the plots
    # Ferry plots
    fig = research_ferries.salinity_ferry_route('HBDB')
    filename = os.path.join(
        plots_dir, 'HBDB_ferry_salinity_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = research_ferries.salinity_ferry_route('TWDP')
    filename = os.path.join(
        plots_dir, 'TWDP_ferry_salinity_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = research_ferries.salinity_ferry_route('TWSB')
    filename = os.path.join(
        plots_dir, 'TWSB_ferry_salinity_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

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

        fig = research_VENUS.plotdepavADCP(
            model, obs, date, name)
        filename = os.path.join(
            plots_dir, '{station}_depavADCP_{date}.svg'.format(station=name,
                                                               date=dmy))
        fig.savefig(filename, facecolor=fig.get_facecolor())

        fig = research_VENUS.plottimeavADCP(
            model, obs, date, name)
        filename = os.path.join(
            plots_dir, '{station}_timeavADCP_{date}.svg'.format(station=name,
                                                                date=dmy))
        fig.savefig(filename, facecolor=fig.get_facecolor())

    # This will overwrite the images made previously
    # Sandheads winds
    fig = figures.Sandheads_winds(grid_T_hr, bathy, model_path, coastline)
    filename = os.path.join(
        plots_dir, 'SH_wind_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    # VENUS bottom temperature and salinity
    fig = research_VENUS.compare_VENUS('East', grid_T_hr, bathy)
    filename = os.path.join(
        plots_dir, 'Compare_VENUS_East_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = research_VENUS.compare_VENUS('Central', grid_T_hr, bathy)
    filename = os.path.join(
        plots_dir, 'Compare_VENUS_Central_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')


def _make_research_plots(
    dmy, model_path, bathy, results_dir, plots_dir, coastline, mesh_mask,
    **kwargs
):
    """Make the plots we wish to look at for research purposes.
    """

    # get the results
    grid_T_dy = _results_dataset('1d', 'grid_T', results_dir)
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    grid_U_dy = _results_dataset('1d', 'grid_U', results_dir)
    grid_V_dy = _results_dataset('1d', 'grid_V', results_dir)
    grid_c = _results_dataset_gridded(
        'central', results_dir)
    grid_e = _results_dataset_gridded('east', results_dir)

    # do the plots
    fig = figures.thalweg_salinity(grid_T_dy, mesh_mask, bathy)
    filename = os.path.join(
        plots_dir, 'Salinity_on_thalweg_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.thalweg_temperature(grid_T_dy, mesh_mask, bathy)
    filename = os.path.join(
        plots_dir, 'Temperature_on_thalweg_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.plot_surface(grid_T_dy, grid_U_dy, grid_V_dy, bathy)
    filename = os.path.join(
        plots_dir, 'T_S_Currents_on_surface_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = research_VENUS.compare_VENUS('East', grid_T_hr, bathy)
    filename = os.path.join(
        plots_dir, 'Compare_VENUS_East_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = research_VENUS.compare_VENUS('Central', grid_T_hr, bathy)
    filename = os.path.join(
        plots_dir, 'Compare_VENUS_Central_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = research_VENUS.plot_vel_NE_gridded('Central', grid_c)
    filename = os.path.join(
        plots_dir, 'Currents_at_VENUS_Central_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = research_VENUS.plot_vel_NE_gridded('East', grid_e)
    filename = os.path.join(
        plots_dir, 'Currents_at_VENUS_East_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')


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
