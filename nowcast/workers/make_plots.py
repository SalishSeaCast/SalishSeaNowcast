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

"""Salish Sea NEMO nowcast worker that produces the ssh and weather
plot files from run results.
"""
import argparse
import datetime
from glob import glob
import logging
import os
import shutil
import traceback

import arrow
import matplotlib
import netCDF4 as nc
import scipy.io as sio
import zmq

matplotlib.use('Agg')
from salishsea_tools.nowcast import (
    figures,
    lib,
    research_VENUS,
    research_ferries,
)


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


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
    logger.debug(
        '{0.plot_type} {0.run_type}: running in process {pid}'
        .format(parsed_args, pid=os.getpid()))
    logger.debug(
        '{0.plot_type} {0.run_type}: read config from {0.config_file}'
        .format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = make_plots(
            parsed_args.run_date, parsed_args.run_type,
            parsed_args.plot_type, config,
            socket)
        logger.info(
            '{0.plot_type} plots for {0.run_type} completed'
            .format(parsed_args), extra={
                'run_type': parsed_args.run_type,
                'plot_type': parsed_args.plot_type,
                'date': parsed_args.run_date,
            })
        # Exchange success messages with the nowcast manager process
        msg_type = 'success {0.run_type} {0.plot_type}'.format(parsed_args)
        lib.tell_manager(
            worker_name, msg_type, config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            '{0.plot_type} plots failed for {0.run_type} failed'
            .format(parsed_args), extra={
                'run_type': parsed_args.run_type,
                'plot_type': parsed_args.plot_type,
                'date': parsed_args.run_date,
            })
        # Exchange failure messages with the nowcast manager process
        msg_type = 'failure {0.run_type} {0.plot_type}'.format(parsed_args)
        lib.tell_manager(worker_name, msg_type, config, logger, socket)
    except SystemExit:
        # Normal termination
        pass
    except:
        logger.critical(
            '{0.plot_type} {0.run_type}: unhandled exception:'
            .format(parsed_args))
        for line in traceback.format_exc().splitlines():
            logger.error(
                '{0.plot_type} {0.run_type}: {line}'
                .format(parsed_args, line=line))
        # Exchange crash messages with the nowcast manager process
        lib.tell_manager(worker_name, 'crash', config, logger, socket)
    # Finish up
    context.destroy()
    logger.debug(
        '{0.plot_type} {0.run_type}: task completed; shutting down'
        .format(parsed_args))


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        'run_type', choices=set(('nowcast', 'forecast', 'forecast2')),
        help='''
        Which results set to produce plot files for:
        "nowcast" means nowcast,
        "forecast" means forecast directly following nowcast,
        "forecast2" means the second forecast, following forecast
        ''')
    parser.add_argument(
        'plot_type', choices=set(('publish', 'research', 'comparison')),
        help='''
        Which type of plots to produce:
        "publish" means ssh, weather and other approved plots for publishing,
        "research" means tracers, currents and other research plots
        "comparison" means ferry salinity plots
        ''')
    parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=arrow.now().date(),
        help='''
        Date of the run to download results files from;
        use YYYY-MM-DD format.
        Defaults to %(default)s.
        ''',
    )
    return parser


def make_plots(run_date, run_type, plot_type, config, socket):
    # set-up, read from config file
    results_home = config['run']['results archive'][run_type]
    results_dir = os.path.join(
        results_home, run_date.strftime('%d%b%y').lower())
    model_path = config['weather']['ops_dir']
    if run_type in ['forecast', 'forecast2']:
        model_path = os.path.join(model_path, 'fcst/')
    bathy = nc.Dataset(config['bathymetry'])
    coastline = sio.loadmat('/ocean/rich/more/mmapbase/bcgeo/PNW.mat')
    mesh_mask = nc.Dataset(
        '/data/nsoontie/MEOPAR/NEMO-forcing/grid/mesh_mask_SalishSea2.nc')

    # configure plot directory for saving
    dmy = run_date.strftime('%d%b%y').lower()
    plots_dir = os.path.join(results_home, dmy, 'figures')
    lib.mkdir(plots_dir, logger, grp_name='sallen')

    if plot_type == 'publish':
        make_publish_plots(
            dmy, model_path, bathy, results_dir, plots_dir, coastline)
    elif plot_type == 'comparison':
        make_comparisons_plots(
            dmy, model_path, bathy, results_dir, plots_dir, coastline)
    else:
        make_research_plots(
            dmy, model_path, bathy, results_dir, plots_dir, coastline,
            mesh_mask)

    # Fix permissions on image files and copy them to salishsea site
    # prep directory
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
    if plot_type == 'publish' and run_type in ('forecast', 'forecast2'):
        summary_plot = os.path.join(
            config['web']['www_path'],
            os.path.basename(config['web']['site_repo_url']),
            config['web']['site_storm_surge_plot_path'],
            '.'.join((config['web']['site_storm_surge_plot'], 'png'))
            )
        f = '{plot_name}_{date}.png'.format(
            plot_name=config['web']['site_storm_surge_plot'],
            date=dmy)
        shutil.copy2(os.path.join(plots_dir, f), summary_plot)
        checklist['Most recent summary plot'] = summary_plot

    return checklist


def make_publish_plots(
    dmy, model_path, bathy, results_dir, plots_dir, coastline,
):
    """Make the plots we wish to publish.
    """

    # get the results
    grid_T_hr = results_dataset('1h', 'grid_T', results_dir)
    grids_15m = {}
    names = ['Point Atkinson', 'Victoria', 'Campbell River']
    for name in names:
        f = os.path.join(results_dir, '{}.nc'.format(name.replace(" ", "")))
        grids_15m[name] = nc.Dataset(f)

    # do the plots
    fig = figures.website_thumbnail(
        bathy, grid_T_hr, grids_15m, model_path, coastline)
    filename = os.path.join(
        plots_dir, 'Website_thumbnail_{date}.png'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.plot_threshold_website(
        bathy, grid_T_hr, grids_15m, model_path, coastline)
    filename = os.path.join(
        plots_dir, 'Threshold_website_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.PA_tidal_predictions(grid_T_hr)
    filename = os.path.join(
        plots_dir, 'PA_tidal_predictions_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, name='Victoria')
    filename = os.path.join(
        plots_dir, 'Vic_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path)
    filename = os.path.join(
        plots_dir, 'PA_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, name='Campbell River')
    filename = os.path.join(
        plots_dir, 'CR_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, name='Nanaimo')
    filename = os.path.join(
        plots_dir, 'Nan_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, grids_15m, model_path, name='Cherry Point')
    filename = os.path.join(
        plots_dir, 'CP_maxSSH_{date}.svg'.format(date=dmy))
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_water_levels(grid_T_hr, bathy, coastline)
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


def make_comparisons_plots(
    dmy, model_path, bathy, results_dir, plots_dir, coastline
):
    """Make the plots we wish to look at for comparisons purposes.
    """
    # get the results
    grid_T_dy = results_dataset('1d', 'grid_T', results_dir)
    grid_T_hr = results_dataset('1h', 'grid_T', results_dir)
    grid_U_dy = results_dataset('1d', 'grid_U', results_dir)
    grid_V_dy = results_dataset('1d', 'grid_V', results_dir)
    grid_c = results_dataset_gridded('central', results_dir)
    grid_e = results_dataset_gridded('east', results_dir)
    grid_d = results_dataset_gridded('ddl', results_dir)

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


def make_research_plots(
    dmy, model_path, bathy, results_dir, plots_dir, coastline, mesh_mask
):
    """Make the plots we wish to look at for research purposes.
    """

    # get the results
    grid_T_dy = results_dataset('1d', 'grid_T', results_dir)
    grid_T_hr = results_dataset('1h', 'grid_T', results_dir)
    grid_U_dy = results_dataset('1d', 'grid_U', results_dir)
    grid_V_dy = results_dataset('1d', 'grid_V', results_dir)
    grid_c = results_dataset_gridded(
        'central', results_dir)
    grid_e = results_dataset_gridded('east', results_dir)

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


def results_dataset(period, grid, results_dir):
    """Return the results dataset for period (e.g. 1h or 1d)
    and grid (e.g. grid_T, grid_U) from results_dir.
    """
    filename_pattern = 'SalishSea_{period}_*_{grid}.nc'
    filepaths = glob(os.path.join(
        results_dir, filename_pattern.format(period=period, grid=grid)))
    return nc.Dataset(filepaths[0])


def results_dataset_gridded(station, results_dir):
    """Return the results dataset for station (e.g. central or east)
     for the quarter hourly data from results_dir.
    """
    filename_pattern = 'VENUS_{station}_gridded.nc'
    filepaths = glob(os.path.join(
        results_dir, filename_pattern.format(station=station)))
    return nc.Dataset(filepaths[0])

if __name__ == '__main__':
    main()
