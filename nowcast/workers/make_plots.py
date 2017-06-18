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

"""Salish Sea NEMO nowcast worker that produces visualization images for
the web site from run results.
"""
import datetime
from glob import glob
import logging
import os
from pathlib import Path
import shlex
import subprocess

# **IMPORTANT**: matplotlib must be imported before anything else that uses it
# because of the matplotlib.use() call below
import matplotlib
## TODO: Get rid of matplotlib.use() call; see issue #19
matplotlib.use('Agg')
import matplotlib.pyplot

import arrow
import cmocean
from nemo_nowcast import NowcastWorker
import netCDF4 as nc
import scipy.io as sio
import xarray as xr

from nowcast import lib
from nowcast.figures.research import (
    time_series_plots,
    tracer_thalweg_and_surface,
    tracer_thalweg_and_surface_hourly
)
from nowcast.figures.comparison import compare_venus_ctd
from nowcast.figures.publish import (
    pt_atkinson_tide,
    storm_surge_alerts,
    storm_surge_alerts_thumbnail,
    compare_tide_prediction_max_ssh,
)
# Legacy figures code
from nowcast.figures import (
    figures,
    research_VENUS,
    research_ferries,
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
        'run_type',
        choices={'nowcast', 'nowcast-green', 'forecast', 'forecast2'},
        help='''
        Type of run to produce plots for:
        'nowcast' means nowcast physics-only runs,
        'nowcast-green' means nowcast-green physics/biology runs
        'forecast' means forecast physics-only runs,
        'forecast2' means forecast2 preliminary forecast physics-only runs.
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
    worker.cli.add_argument(
        '--test-figure',
        help='''Identifier for a single figure to do a test on.
        The identifier may be the svg_name of the figure used in make_plots
        (e.g. SH_wind is the svg_name of figures stored as SH_wind_{ddmmmyy}.svg),
        the name of the website figure module
        (e.g. storm_surge_alerts is the module name of 
        nowcast.figures.publish.storm_surge_alerts),
        or name of the figure function for legacy nowcast.figures.figures
        functions
        (e.g. SandHeads_winds is the function name of
        nowcast.figures.figures.SandHeads_winds).
        The figure will be rendered in
        /results/nowcast-sys/figures/test/{run_type}/{ddmmmyy}/ so that it is
        accessible in a browser at 
        https://salishsea.eos.ubc.ca/{run_type}/{ddmmmyy}/{svg_name}_{ddmmyy}.svg
        '''
    )
    worker.run(make_plots, success, failure)


def success(parsed_args):
    logger.info(
        f'{parsed_args.plot_type} plots for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'{parsed_args.run_type} completed',
        extra={
            'run_type': parsed_args.run_type,
            'plot_type': parsed_args.plot_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = f'success {parsed_args.run_type} {parsed_args.plot_type}'
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.plot_type} plots failed for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} {parsed_args.run_type} '
        f'failed',
        extra={
            'run_type': parsed_args.run_type,
            'plot_type': parsed_args.plot_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = f'failure {parsed_args.run_type} {parsed_args.plot_type}'
    return msg_type


def make_plots(parsed_args, config, *args):
    run_date = parsed_args.run_date
    dmy = run_date.format('DDMMMYY').lower()
    timezone = config['figures']['timezone']
    run_type = parsed_args.run_type
    plot_type = parsed_args.plot_type
    test_figure_id = parsed_args.test_figure
    dev_results_home = config['results archive']['nowcast-dev']
    weather_path = config['weather']['ops dir']
    if run_type in ['forecast', 'forecast2']:
        weather_path = os.path.join(weather_path, 'fcst/')
    results_dir = os.path.join(config['results archive'][run_type], dmy)
    grid_dir = Path(config['figures']['grid dir'])
    bathy = nc.Dataset(
        os.fspath(grid_dir / config['run types'][run_type]['bathymetry']))
    mesh_mask = nc.Dataset(
        os.fspath(grid_dir / config['run types'][run_type]['mesh mask']))
    dev_mesh_mask = nc.Dataset(
        os.fspath(grid_dir / config['run types']['nowcast-dev']['mesh mask']))
    coastline = sio.loadmat(config['figures']['coastline'])

    if run_type == 'nowcast' and plot_type == 'research':
        fig_functions = _prep_nowcast_research_fig_functions(
            bathy, mesh_mask, results_dir)
    if run_type == 'nowcast-green' and plot_type == 'research':
        fig_functions = _prep_nowcast_green_research_fig_functions(
            bathy, mesh_mask, results_dir)
    if run_type == 'nowcast' and plot_type == 'comparison':
        fig_functions = _prep_comparison_fig_functions(
            config, bathy, coastline, weather_path, mesh_mask, dev_mesh_mask,
            results_dir, dev_results_home, dmy, timezone
        )
    if plot_type == 'publish':
        fig_functions = _prep_publish_fig_functions(
            config, bathy, coastline, weather_path, results_dir, timezone
        )

    checklist = _render_figures(
        config, run_type, plot_type, dmy, fig_functions, test_figure_id
    )
    return checklist


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


def _prep_nowcast_research_fig_functions(bathy, mesh_mask, results_dir):
    grid_T_day = _results_dataset('1d', 'grid_T', results_dir)
    grid_U_day = _results_dataset('1d', 'grid_U', results_dir)
    grid_V_day = _results_dataset('1d', 'grid_V', results_dir)
    grid_central = _results_dataset_gridded('central', results_dir)
    grid_east = _results_dataset_gridded('east', results_dir)
    fig_functions = {
        'Salinity_on_thalweg': {
            'function': figures.thalweg_salinity,
            'args': (grid_T_day, mesh_mask, bathy),
            'kwargs': {
                'thalweg_pts_file':
                    '/results/nowcast-sys/tools/bathymetry/'
                    'thalweg_working.txt'
            }
        },
        'Temperature_on_thalweg': {
            'function': figures.thalweg_temperature,
            'args': (grid_T_day, mesh_mask, bathy),
            'kwargs': {
                'thalweg_pts_file':
                    '/results/nowcast-sys/tools/bathymetry/'
                    'thalweg_working.txt'
            }
        },
        'T_S_Currents_on_surface': {
            'function': figures.plot_surface,
            'args': (grid_T_day, grid_U_day, grid_V_day, bathy),
        },
        'Currents_at_VENUS_Central': {
            'function': research_VENUS.plot_vel_NE_gridded,
            'args': ('Central', grid_central),
        },
        'Currents_at_VENUS_East': {
            'function': research_VENUS.plot_vel_NE_gridded,
            'args': ('East', grid_east),
        }
    }
    return fig_functions


def _prep_nowcast_green_research_fig_functions(bathy, mesh_mask, results_dir):
    ptrc_T_hr = _results_dataset('1h', 'ptrc_T', results_dir)
    place = 'S3'
    phys_dataset = xr.open_dataset('https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSg3DTracerFields1hV17-02')
    bio_dataset =  xr.open_dataset('https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSg3DBiologyFields1hV17-02')
    fig_functions = {
        'nitrate_thalweg_and_surface': {
            'function': tracer_thalweg_and_surface.make_figure,
            'args': (ptrc_T_hr.variables['nitrate'], bathy, mesh_mask),
            'kwargs': {'cmap': cmocean.cm.matter, 'depth_integrated': False}
        },
        'nitrate_diatoms_timeseries':{
            'function':time_series_plots.make_figure,
            'args':(bio_dataset,'nitrate','diatoms',place)
            },
        'mesozoo_microzoo_timeseries':{
            'function':time_series_plots.make_figure,
            'args':(bio_dataset,'mesozooplankton','microzooplankton',place)
            },
        'mesodinium_flagellates_timeseries':{
            'function':time_series_plots.make_figure,
            'args':(bio_dataset,'ciliates','flagellates',place)
            },
        'temperature_salinity_timeseries':{
            'function':time_series_plots.make_figure,
            'args':(phys_dataset,'temperature','salinity',place)
            },
    }
    clevels_thalweg, clevels_surface = (
        tracer_thalweg_and_surface_hourly.clevels(
            ptrc_T_hr.variables['nitrate'], mesh_mask, depth_integrated=False))
    for hr in range(24):
        key = f'nitrate_thalweg_and_surface_hourly_h{hr:02d}'
        fig_functions[key] = {
            'function': tracer_thalweg_and_surface_hourly.make_figure,
            'args': (
                hr, ptrc_T_hr.variables['nitrate'], bathy, mesh_mask,
                clevels_thalweg, clevels_surface),
            'kwargs': {'cmap': cmocean.cm.matter, 'depth_integrated': False},
            'format': 'png'
        } 
    return fig_functions


def _prep_comparison_fig_functions(
    config, bathy, coastline, weather_path,
    mesh_mask, dev_mesh_mask, results_dir, dev_results_home, dmy, timezone
):
    ferry_data_dir = config['observations']['ferry data']
    dev_results_dir = os.path.join(dev_results_home, dmy)
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    dev_grid_T_hr = _results_dataset('1h', 'grid_T', dev_results_dir)
    grid_central = _results_dataset_gridded('central', results_dir)
    grid_obs_central = sio.loadmat(
        '/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPcentral.mat')
    grid_east = _results_dataset_gridded('east', results_dir)
    grid_obs_east = sio.loadmat(
        '/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPeast.mat')
    grid_ddl = _results_dataset_gridded('delta', results_dir)
    grid_obs_ddl = sio.loadmat(
        '/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPddl.mat')
    adcp_datetime = (
        datetime.datetime.strptime(dmy, '%d%b%y').replace(minute=45))
    fig_functions = {
        'SH_wind': {
            ## TODO: Fix stormtools.py:403: RuntimeWarning:
            ##  invalid value encountered in less
            ##  wind_dir = wind_dir + 360 * (wind_dir < 0)
            'function': figures.SandHeads_winds,
            'args': (grid_T_hr, bathy, weather_path, coastline)
        },
        'Compare_VENUS_East': {
            'function': compare_venus_ctd.make_figure,
            'args': (
                'East node', grid_T_hr, dev_grid_T_hr, timezone, mesh_mask,
                dev_mesh_mask)
        },
        'HB_DB_ferry_salinity': {
            'function': research_ferries.salinity_ferry_route,
            'args': (ferry_data_dir, grid_T_hr, bathy, 'HB_DB', dmy)
        },
        'TW_DP_ferry_salinity': {
            'function': research_ferries.salinity_ferry_route,
            'args': (ferry_data_dir, grid_T_hr, bathy, 'TW_DP', dmy)
        },
        'TW_SB_ferry_salinity': {
            'function': research_ferries.salinity_ferry_route,
            'args': (ferry_data_dir, grid_T_hr, bathy, 'TW_SB', dmy)
        },
        'Compare_VENUS_Central': {
            'function': compare_venus_ctd.make_figure,
            'args': (
                'Central node', grid_T_hr, dev_grid_T_hr, timezone,
                mesh_mask, dev_mesh_mask)
        },
        'Compare_VENUS_Delta_BBL': {
            'function': compare_venus_ctd.make_figure,
            'args': (
                'Delta BBL node', grid_T_hr, dev_grid_T_hr, timezone,
                mesh_mask, dev_mesh_mask)
        },
        'Compare_VENUS_Delta_DDL': {
            'function': compare_venus_ctd.make_figure,
            'args': (
                'Delta DDL node', grid_T_hr, dev_grid_T_hr, timezone,
                mesh_mask, dev_mesh_mask)
        },
        'Central_ADCP': {
            'function': research_VENUS.plotADCP,
            'args': (
                grid_central, grid_obs_central, adcp_datetime, 'Central',
                [0, 285])
        },
        'Central_depavADCP': {
            'function': research_VENUS.plotdepavADCP,
            'args': (
                grid_central, grid_obs_central, adcp_datetime, 'Central')
        },
        'Central_timeavADCP': {
            'function': research_VENUS.plottimeavADCP,
            'args': (
                grid_central, grid_obs_central, adcp_datetime, 'Central')
        },
        'East_ADCP': {
            'function': research_VENUS.plotADCP,
            'args': (
                grid_east, grid_obs_east, adcp_datetime, 'East', [0, 150])
        },
        'East_depavADCP': {
            'function': research_VENUS.plotdepavADCP,
            'args': (grid_east, grid_obs_east, adcp_datetime, 'East')
        },
        'East_timeavADCP': {
            'function': research_VENUS.plottimeavADCP,
            'args': (grid_east, grid_obs_east, adcp_datetime, 'East')
        },
        'ddl_ADCP': {
            'function': research_VENUS.plotADCP,
            'args': (grid_ddl, grid_obs_ddl, adcp_datetime, 'ddl', [0, 148])
        },
        'ddl_depavADCP': {
            'function': research_VENUS.plotdepavADCP,
            'args': (grid_ddl, grid_obs_ddl, adcp_datetime, 'ddl')
        },
        'ddl_timeavADCP': {
            'function': research_VENUS.plottimeavADCP,
            'args': (grid_ddl, grid_obs_ddl, adcp_datetime, 'ddl')
        }
    }
    return fig_functions


def _prep_publish_fig_functions(
    config, bathy, coastline, weather_path, results_dir, timezone
):
    tidal_predictions = config['ssh']['tidal predictions']
    grid_T_hr = _results_dataset('1h', 'grid_T', results_dir)
    names = [
        'Point Atkinson', 'Victoria', 'Campbell River', 'Cherry Point',
        'Friday Harbor', 'Neah Bay', 'Nanaimo', 'SandHeads'
    ]
    filepath_tmpl = os.path.join(results_dir, '{}.nc')
    grids_15m = {
        name: nc.Dataset(filepath_tmpl.format(name.replace(' ', '')))
        for name in names
    }
    fig_functions = {
        'Website_thumbnail': {
            'function': storm_surge_alerts_thumbnail.make_figure,
            'args': (grids_15m, weather_path, coastline, tidal_predictions),
            'format': 'png'
        },
        'Threshold_website': {
            'function': storm_surge_alerts.make_figure,
            'args': (grids_15m, weather_path, coastline, tidal_predictions)
        },
        'PA_tidal_predictions': {
            'function': pt_atkinson_tide.make_figure,
            'args': (grid_T_hr, tidal_predictions, timezone)
        },
        'Vic_maxSSH': {
            'function': compare_tide_prediction_max_ssh.make_figure,
            'args': (
                'Victoria', grid_T_hr, grids_15m, bathy, weather_path,
                tidal_predictions, timezone)
        },
        'PA_maxSSH': {
            'function': compare_tide_prediction_max_ssh.make_figure,
            'args': (
                'Point Atkinson', grid_T_hr, grids_15m, bathy, weather_path,
                tidal_predictions, timezone)
        },
        'CR_maxSSH': {
            'function': compare_tide_prediction_max_ssh.make_figure,
            'args': (
                'Campbell River', grid_T_hr, grids_15m, bathy, weather_path,
                tidal_predictions, timezone)
        },
        'Nan_maxSSH': {
            'function': compare_tide_prediction_max_ssh.make_figure,
            'args': (
                'Nanaimo', grid_T_hr, grids_15m, bathy, weather_path,
                tidal_predictions, timezone)
        },
        'CP_maxSSH': {
            'function': compare_tide_prediction_max_ssh.make_figure,
            'args': (
                'Cherry Point', grid_T_hr, grids_15m, bathy, weather_path,
                tidal_predictions, timezone)
        },
        'NOAA_ssh': {
            'function': figures.compare_water_levels,
            'args': (grid_T_hr, bathy, grids_15m, coastline)
        },
        'WaterLevel_Thresholds': {
            ## TODO: Fix hardcoded path in figure function:
            ## '/data/nsoontie/MEOPAR/analysis/Nancy/tides/PA_observations
            # /ptatkin_rt.dat'
            'function': figures.plot_thresholds_all,
            'args': (
                grid_T_hr, bathy, grids_15m, weather_path, coastline,
                tidal_predictions)
        },
        'SH_wind': {
            'function': figures.SandHeads_winds,
            'args': (grid_T_hr, bathy, weather_path, coastline)
        },
        'Avg_wind_vectors': {
            'function': figures.winds_average_max,
            'args': (grid_T_hr, bathy, weather_path, coastline),
            'kwargs': {'station': 'all', 'wind_type': 'average'}
        },
        'Wind_vectors_at_max': {
            ## TODO: Fix figures.py:840: FutureWarning:
            ## elementwise comparison failed; returning scalar instead,
            ## but in the future will perform elementwise comparison
            'function': figures.winds_average_max,
            'args': (grid_T_hr, bathy, weather_path, coastline),
            'kwargs': {'station': 'all', 'wind_type': 'max'}
        },
    }
    return fig_functions


def _render_figures(
    config, run_type, plot_type, dmy, fig_functions, test_figure_id
):
    checklist = {}
    fig_files = []
    for svg_name, func in fig_functions.items():
        fig_func = func['function']
        args = func.get('args', [])
        kwargs = func.get('kwargs', {})
        fig_save_format = func.get('format', 'svg')
        test_figure = False
        if test_figure_id:
            test_figure = any((
                svg_name == test_figure_id,
                fig_func.__module__.endswith(f'{plot_type}.{test_figure_id}'),
                # legacy: for figures.figures module functions
                fig_func.__name__ == test_figure_id,
            ))
            if not test_figure:
                continue
        logger.debug(f'starting {fig_func.__module__}.{fig_func.__name__}')
        try:
            fig = _calc_figure(fig_func, args, kwargs)
        except (FileNotFoundError, IndexError, KeyError, TypeError):
            # **IMPORTANT**: the collection of exception above must match those
            # handled in the _calc_figure() function
            continue
        if test_figure:
            fig_files_dir = Path(config['figures']['test path'], run_type, dmy)
            fig_files_dir.mkdir(parents=True, exist_ok=True)
        else:
            fig_files_dir = Path(
                config['figures']['storage path'], run_type, dmy)
            lib.mkdir(
                os.fspath(fig_files_dir), logger, grp_name=config['file group'])
        filename = fig_files_dir / f'{svg_name}_{dmy}.{fig_save_format}'
        fig.savefig(
            os.fspath(filename), facecolor=fig.get_facecolor(),
            bbox_inches='tight')
        logger.info(f'{filename} saved')
        matplotlib.pyplot.close(fig)
        if fig_save_format is 'svg':
            logger.debug(f'starting SVG scouring of {filename}')
            tmpfilename = filename.with_suffix('.scour')
            cmd = f'scour {filename} {tmpfilename}'
            logger.debug(f'running subprocess: {cmd}')
            try:
                proc = subprocess.run(
                    shlex.split(cmd), check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    universal_newlines=True)
            except subprocess.CalledProcessError as e:
                logger.warning(
                    'SVG scouring failed, proceeding with unscoured figure')
                logger.debug(f'scour return code: {e.returncode}')
                if e.output:
                    logger.debug(e.output)
                continue
            logger.debug(proc.stdout)
            tmpfilename.rename(filename)
            logger.info(f'{filename} scoured')
        lib.fix_perms(os.fspath(filename), grp_name=config['file group'])
        fig_files.append(os.fspath(filename))
        fig_path = _render_storm_surge_alerts_thumbnail(
            config, run_type, plot_type, dmy, fig, svg_name, fig_save_format,
            test_figure
        )
        if checklist is not None:
            checklist['storm surge alerts thumbnail'] = fig_path
    checklist[f'{run_type} {plot_type}'] = fig_files
    return checklist


def _calc_figure(fig_func, args, kwargs):
    try:
        fig = fig_func(*args, **kwargs)
    except FileNotFoundError as e:
        if fig_func.__name__.endswith('salinity_ferry_route'):
            logger.warning(
                f'{args[3]} ferry route salinity comparison figure '
                f'failed: {e}')
        else:
            logger.error(
                f'unexpected FileNotFoundError in {fig_func.__name__}:',
                exc_info=True)
        raise
    except IndexError:
        adcp_plot_funcs = ('plotADCP', 'plotdepavADCP', 'plottimeavADCP')
        if fig_func.__name__.endswith(adcp_plot_funcs):
            logger.warning(
                f'VENUS {args[3]} ADCP comparison figure failed: '
                f'No observations available')
        else:
            logger.error(
                f'unexpected IndexError in {fig_func.__name__}:', exc_info=True)
        raise
    except KeyError:
        if fig_func.__name__.endswith('salinity_ferry_route'):
            logger.warning(
                f'{args[3]} ferry route salinity comparison figure '
                f'failed: No observations found in .mat file')
        else:
            logger.error(
                f'unexpected KeyError in {fig_func.__name__}:', exc_info=True)
        raise
    except TypeError:
        if fig_func.__module__.endswith('compare_venus_ctd'):
            logger.warning(
                f'VENUS {args[0]} CTD comparison figure failed: '
                f'No observations available')
        else:
            logger.error(
                f'unexpected TypeError in {fig_func.__name__}:', exc_info=True)
        raise
    return fig


def _render_storm_surge_alerts_thumbnail(
    config, run_type, plot_type, dmy, fig, svg_name, fig_save_format,
    test_figure
):
    """Undated storm surge alerts thumbnail for storm-surge/index.html page
    :param fig_save_format: 
    """
    now = arrow.now()
    today_dmy = now.format('DDMMMYY').lower()
    yesterday_dmy = now.replace(days=-1).format('DDMMMYY').lower()
    thumbnail_root = config['figures']['storm surge alerts thumbnail']
    if not all((
            plot_type == 'publish',
            svg_name == thumbnail_root,
            any((
                        run_type == 'forecast' and dmy == today_dmy,
                        run_type == 'forecast2' and dmy == yesterday_dmy,
            ))
    )):
        return
    if test_figure:
        dest_dir = Path(
            config['figures']['test path'],
            config['figures']['storm surge info portal path'])
        dest_dir.mkdir(parents=True, exist_ok=True)
    else:
        dest_dir = Path(
            config['figures']['storage path'],
            config['figures']['storm surge info portal path'])
    undated_thumbnail = dest_dir / f'{thumbnail_root}.{fig_save_format}'
    fig.savefig(
        os.fspath(undated_thumbnail), facecolor=fig.get_facecolor(),
        bbox_inches='tight')
    lib.fix_perms(
        os.fspath(undated_thumbnail), grp_name=config['file group'])
    logger.info(f'{undated_thumbnail} saved')
    return os.fspath(undated_thumbnail)


if __name__ == '__main__':
    main()
