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
"""SalishSeaCast worker that produces tiles of surface current visualization
images for the web site from run results.

The tile specifications and initial code implementation were provided by IOS.
"""
import logging

import netCDF4 as nc
import arrow
import pytz
import datetime
import time
from glob import glob
from pathlib import Path

import multiprocessing
from queue import Empty

import shlex
import subprocess


from matplotlib.backend_bases import FigureCanvasBase

import os
from nowcast.figures.publish import surface_current_tiles

# Get the tiles dict
from nowcast.figures.surface_current_domain import tile_coords_dic

from PyPDF2 import PdfFileMerger
from IPython import embed

from nemo_nowcast import NowcastWorker

NAME = 'make_surface_current_tiles'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_surface_current_tiles --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'run_type',
        choices={'forecast', 'forecast2'},
        help='''
        Type of run to produce plots for:
        'forecast' means forecast physics-only runs,
        'forecast2' means forecast2 preliminary forecast physics-only runs.
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date of the run to symlink files for.'
    )

    worker.run(make_surface_current_tiles, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info('surface current tile figures completed')
    msg_type = f'success'
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical('surface current tile figures production failed')
    msg_type = f'failure'
    return msg_type


def make_surface_current_tiles(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_date = parsed_args.run_date
    dmy = run_date.format('DDMMMYY').lower()
    dmym1 = run_date.replace(days=-1).format('DDMMMYY').lower()
    timezone = config['figures']['timezone']
    run_type = parsed_args.run_type  # forecast, forecast2

    results_dir0 = Path(config['results archive'][run_type], dmy)

    if run_type == 'forecast':
        results_dirm1 = Path(config['results archive']['nowcast'], dmy)
        results_dirm2 = Path(config['results archive']['nowcast'], dmym1)

    if run_type == 'forecast2':
        results_dirm1 = Path(config['results archive']['forecast'], dmy)
        results_dirm2 = Path(config['results archive']['nowcast'], dmy)

    grid_dir = Path(config['figures']['grid dir'])
    coordf = grid_dir / config['run types'][run_type]['coordinates']
    mesh_maskf = grid_dir / config['run types'][run_type]['mesh mask']
    bathyf = grid_dir / config['run types'][run_type]['bathymetry']
    storage_path = Path(
        config['figures']['surface current tiles']['storage path'], run_type,
        dmy
    )

    if not os.path.exists(storage_path):
        os.makedirs(storage_path)

    # Loop over last 48h and this forecast{,2}
    for results_dir in [results_dirm2, results_dirm1, results_dir0]:

        u_list = glob(os.fspath(results_dir) + '/SalishSea_1h_*_grid_U.nc')
        v_list = glob(os.fspath(results_dir) + '/SalishSea_1h_*_grid_V.nc')

        Vf = v_list[0]
        Uf = u_list[0]

        with nc.Dataset(Uf) as dsU:
            max_time_index = dsU.dimensions['time_counter'].size
            units = dsU.variables['time_counter'].units
            calendar = dsU.variables['time_counter'].calendar
            sec = dsU.variables['time_counter'][:]

        expansion_factor = 0.1  #10% overlap

        ######################################
        ##### BEGIN MULTIPROCESSING CODE #####
        ######################################
        # Add tasks to a joinable queue
        q = multiprocessing.JoinableQueue()
        for t_index in range(max_time_index):  #range(5,7):
            task = (t_index, sec, units, calendar, run_date, Vf, Uf, coordf, mesh_maskf, bathyf, tile_coords_dic, expansion_factor, storage_path)
            q.put(task)
        # Spawn a set of worker processes
        num_procs = 4
        procs = []
        for i in range(num_procs):
            name = str(i)
            p = multiprocessing.Process(target=_process_time_slice, args=(q,name))
            procs.append(p)
        # Start each one
        for p in procs:
            p.start()
        # Wait until they complete
        for p in procs:
            p.join()
        # Close the queue
        q.close()
        ######################################
        ###### END MULTIPROCESSING CODE ######
        ######################################

    tile_names = []
    for t in tile_coords_dic:
        tile_names += [t]

    _pdfMerger(storage_path, tile_names)

    config = {}
    return config

def _process_time_slice(q,name):
    while True:
        try:
            task = q.get_nowait()
            t_index, sec, units, calendar, run_date, Vf, Uf, coordf, mesh_maskf, bathyf, tile_coords_dic, expansion_factor, storage_path = task

            ######################################
            #### BEGIN INNER LOOP OVER TIME ######
            ######################################
            ## Here is the core of the work
            date_stamp = _getTimeFileName(sec[t_index], units, calendar)

            # make website theme version
            fig_list, tile_names = surface_current_tiles.make_figure(
                run_date, t_index, Vf, Uf, coordf, mesh_maskf, bathyf,
                tile_coords_dic, expansion_factor
            )
            _saveFigures(fig_list, tile_names, storage_path, date_stamp, "png")
            del fig_list

            # make pdf version - different thickness
            fig_list, tile_names = surface_current_tiles.make_figure(
                run_date,
                t_index,
                Vf,
                Uf,
                coordf,
                mesh_maskf,
                bathyf,
                tile_coords_dic,
                expansion_factor,
                theme=None
            )
            _saveFigures(fig_list, tile_names, storage_path, date_stamp, "pdf")
            del fig_list
            ######################################
            ###### END INNER LOOP OVER TIME ######
            ######################################

            q.task_done()

        except Empty:
            break

def _getTimeFileName(sec, units, calendar):
    dt = nc.num2date(sec, units, calendar=calendar)
    dt_utc = datetime.datetime.combine(dt.date(), dt.time(),
                                       pytz.utc)  #add timezone to utc time
    fmt = '%Y%m%d_%H%M%S'

    time_utc = dt_utc.strftime(fmt)

    return time_utc


def _saveFigures(
    fig_list,
    tile_names,
    storage_path,
    date_stamp,
    file_type,
):
    for fig, name in zip(fig_list, tile_names):
        ftile = "surface_currents_tile{:02d}_{}_UTC.{}".format(
            int(name[4:]), date_stamp, file_type
        )
        outfile = Path(storage_path, ftile)
        FigureCanvasBase(fig).print_figure(
            outfile.as_posix(), facecolor=fig.get_facecolor()
        )
        print(ftile)


def _pdfMerger(path, allTiles):
    for tile in allTiles:

        file_list = glob(
            os.fspath(path) + "/surface_currents_" + tile + "*.pdf"
        )
        file_list_sorted = sorted(file_list)
        result = os.fspath(path) + "/" + tile + ".pdf"
        print(result)

        merger = PdfFileMerger()

        for pdf in file_list_sorted:
           merger.append(pdf)

        merger.write(result)
        merger.close()

        _pdfShrink(Path(result))

    # ToDo: delete the per-time-per-tile pdfs

def _pdfShrink(filename):
    # Strategy borrowed from make_plots.py
    logger.debug(f'Starting PDF optimizing for {filename}')
    tmpfilename = filename.with_suffix('.temp')
    cmd = f'pdftocairo -pdf {filename} {tmpfilename}'
    logger.debug(f'running subprocess: {cmd}')
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        logger.debug(proc.stdout)
        tmpfilename.rename(filename)
        logger.info(f'{filename} shrunk')
    except subprocess.CalledProcessError as e:
        logger.warning(
            'PDF shrinking failed, proceeding with unshrunk PDF'
        )
        logger.debug(f'pdftocairo return code: {e.returncode}')
        if e.output:
            logger.debug(e.output)


if __name__ == '__main__':
    main()  # pragma: no cover
