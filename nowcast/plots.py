""" script to generate plots for a simulation
    Use: python plots.py sim_date mode
    Eg:  python plots.py 2015-03-06 nowcast generates plots for the
    March 6, 2015 nowcast. sim_date corresponds to the date simulated.
    plots are stored in a directory mode/run_dat, where run_date is the
    date the simulation was run.
"""

import datetime
from glob import glob
import logging
import os
import sys

import arrow
import matplotlib
import netCDF4 as nc
import scipy.io as sio

matplotlib.use('Agg')
from salishsea_tools.nowcast import (
    figures,
)

paths = {
    'nowcast': '/data/dlatorne/MEOPAR/SalishSea/nowcast/',
    'forecast': '/ocean/sallen/allen/research/MEOPAR/SalishSea/forecast/',
    'forecast2': '/ocean/sallen/allen/research'
                 '/MEOPAR/SalishSea/forecast2/'
}

model_path = '/ocean/sallen/allen/research/MEOPAR/Operational/'
coastline = sio.loadmat('/ocean/rich/more/mmapbase/bcgeo/PNW.mat')
bathy = nc.Dataset(
    '/data/nsoontie/MEOPAR/NEMO-forcing/grid/'
    'bathy_meter_SalishSea2.nc'
)


def main():
    sim_date = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d')
    mode = sys.argv[2]

    if mode == 'nowcast':
        # make_all_plots()
        run_date = sim_date
    elif mode == 'forecast':
        run_date = sim_date + datetime.timedelta(days=-1)
    elif mode == 'forecast2':
        run_date = sim_date + datetime.timedelta(days=-2)
    os.mkdir(os.path.join(mode, run_date.strftime('%d%b%y').lower()))

    dmy = run_date.strftime('%d%b%y').lower()
    plots_dir = os.path.join(mode, dmy)
    results_dir = os.path.join(paths[mode], dmy)

    if mode == 'nowcast':
        make_research_plots(
            dmy, model_path, bathy, results_dir, plots_dir, coastline
        )
    make_publish_plots(
        dmy, model_path, bathy, results_dir, plots_dir, coastline
    )


def make_research_plots(
    dmy,
    model_path,
    bathy,
    results_dir,
    plots_dir,
    coastline,
):
    """Make the plots we wish to look at for research purposes.
    """

    # get the results
    grid_T_dy = results_dataset('1d', 'grid_T', results_dir)
    grid_T_hr = results_dataset('1h', 'grid_T', results_dir)
    grid_U_dy = results_dataset('1d', 'grid_U', results_dir)
    grid_V_dy = results_dataset('1d', 'grid_V', results_dir)

    # do the plots
    fig = figures.thalweg_salinity(grid_T_dy)
    filename = os.path.join(plots_dir, f'Salinity_on_thalweg_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_VENUS('East', grid_T_hr, bathy)
    filename = os.path.join(plots_dir, f'Compare_VENUS_East_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_VENUS('Central', grid_T_hr, bathy)
    filename = os.path.join(plots_dir, f'Compare_VENUS_Central_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')


def make_publish_plots(
    dmy,
    model_path,
    bathy,
    results_dir,
    plots_dir,
    coastline,
):
    """Make the plots we wish to publish.
    """

    # get the results
    grid_T_hr = results_dataset('1h', 'grid_T', results_dir)

    # do the plots
    fig = figures.website_thumbnail(bathy, grid_T_hr, model_path, coastline)
    filename = os.path.join(plots_dir, f'Website_thumbnail_{dmy}.png')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.plot_threshold_website(
        bathy, grid_T_hr, model_path, coastline
    )
    filename = os.path.join(plots_dir, f'Threshold_website_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.PA_tidal_predictions(grid_T_hr)
    filename = os.path.join(plots_dir, f'PA_tidal_predictions_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, model_path, name='Victoria'
    )
    filename = os.path.join(plots_dir, f'Vic_maxSSH_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(grid_T_hr, bathy, model_path)
    filename = os.path.join(plots_dir, f'PA_maxSSH_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_tidalpredictions_maxSSH(
        grid_T_hr, bathy, model_path, name='Campbell River'
    )
    filename = os.path.join(plots_dir, f'CR_maxSSH_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor(), bbox_inches='tight')

    fig = figures.compare_water_levels(grid_T_hr, bathy, coastline)
    filename = os.path.join(plots_dir, f'NOAA_ssh_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.plot_thresholds_all(grid_T_hr, bathy, model_path, coastline)
    filename = os.path.join(plots_dir, f'WaterLevel_Thresholds_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.SandHeads_winds(grid_T_hr, bathy, model_path, coastline)
    filename = os.path.join(plots_dir, f'SH_wind_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.average_winds_at_station(
        grid_T_hr, bathy, model_path, coastline, station='all'
    )
    filename = os.path.join(plots_dir, f'Avg_wind_vectors_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor())

    fig = figures.winds_at_max_ssh(
        grid_T_hr, bathy, model_path, coastline, station='all'
    )
    filename = os.path.join(plots_dir, f'Wind_vectors_at_max_{dmy}.svg')
    fig.savefig(filename, facecolor=fig.get_facecolor())


def results_dataset(period, grid, results_dir):
    """Return the results dataset for period (e.g. 1h or 1d)
    and grid (e.g. grid_T, grid_U) from results_dir.
    """
    filename_pattern = 'SalishSea_{period}_*_{grid}.nc'
    print(results_dir)
    filepaths = glob(
        os.path.join(
            results_dir, filename_pattern.format(period=period, grid=grid)
        )
    )
    return nc.Dataset(filepaths[0])


main()
