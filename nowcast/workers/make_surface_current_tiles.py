#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""SalishSeaCast worker that produces tiles of surface current visualization
images for the web site from run results.

The tile specifications and initial code implementation were provided by IOS.
"""
import datetime
from glob import glob
import logging
import math
import multiprocessing
import os
from pathlib import Path
from queue import Empty
import shlex
import subprocess

import arrow
from matplotlib.backend_bases import FigureCanvasBase
from nemo_nowcast import NowcastWorker
import netCDF4
from PyPDF2 import PdfFileMerger
import pytz

from nowcast import lib
from nowcast.figures.publish import surface_current_tiles
from nowcast.figures.surface_current_domain import tile_coords_dic

NAME = "make_surface_current_tiles"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_surface_current_tiles --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast-green", "forecast", "forecast2"},
        help="""
        Type of run to produce plots for:
        'forecast' means forecast physics-only runs,
        'forecast2' means forecast2 preliminary forecast physics-only runs,
        'nowcast-green' means nowcast-green run-of-record runs 
        (primarily used to generate tiles for a past date from archival run results)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to symlink files for.",
    )
    worker.cli.add_argument(
        "--nprocs",
        type=int,
        default=math.floor(multiprocessing.cpu_count() / 2),
        help=(
            "Maximum number of concurrent figure creation processes allowed. "
            "Defaults to 1/2 the number of cores detected."
        ),
    )

    worker.run(make_surface_current_tiles, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"surface current tile figures for {parsed_args.run_date.format('YYYY-MM-DD')} "
        f"{parsed_args.run_type} completed"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"surface current tile figures production for {parsed_args.run_date.format('YYYY-MM-DD')} "
        f"{parsed_args.run_type} failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def make_surface_current_tiles(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    num_procs = parsed_args.nprocs
    dmy = run_date.format("DDMMMYY").lower()
    dmym1 = run_date.replace(days=-1).format("DDMMMYY").lower()
    ## TODO: Change to get results from ERDDAP rolling forecast for run_type == forecast*
    results_dir0 = (
        Path(
            config["results archive"]["nowcast-green"],
            run_date.shift(days=+2).format("DDMMMYY").lower(),
        )
        if run_type == "nowcast-green"
        else Path(config["results archive"][run_type], dmy)
    )
    if run_type == "nowcast-green":
        results_dirm1 = Path(
            config["results archive"]["nowcast-green"],
            run_date.shift(days=+1).format("DDMMMYY").lower(),
        )
        results_dirm2 = Path(
            config["results archive"]["nowcast-green"],
            run_date.format("DDMMMYY").lower(),
        )

    if run_type == "forecast":
        results_dirm1 = Path(config["results archive"]["nowcast"], dmy)
        results_dirm2 = Path(config["results archive"]["nowcast"], dmym1)

    if run_type == "forecast2":
        results_dirm1 = Path(config["results archive"]["forecast"], dmy)
        results_dirm2 = Path(config["results archive"]["nowcast"], dmy)

    grid_dir = Path(config["figures"]["grid dir"])
    coordf = grid_dir / config["run types"][run_type]["coordinates"]
    mesh_maskf = grid_dir / config["run types"][run_type]["mesh mask"]
    bathyf = grid_dir / config["run types"][run_type]["bathymetry"]
    storage_path = Path(
        config["figures"]["surface current tiles"]["storage path"], run_type, dmy
    )
    lib.mkdir(storage_path, logger, grp_name=config["file group"])

    # Loop over last 48h and this forecast{,2}
    for results_dir in [results_dirm2, results_dirm1, results_dir0]:

        u_list = glob(os.fspath(results_dir) + "/SalishSea_1h_*_grid_U.nc")
        v_list = glob(os.fspath(results_dir) + "/SalishSea_1h_*_grid_V.nc")

        Uf = Path(u_list[0])
        Vf = Path(v_list[0])

        with netCDF4.Dataset(Uf) as dsU:
            max_time_index = dsU.dimensions["time_counter"].size
            units = dsU.variables["time_counter"].units
            calendar = dsU.variables["time_counter"].calendar
            sec = dsU.variables["time_counter"][:]

        expansion_factor = 0.1  # 10% overlap for each tile

        logger.debug(f"creating figures using {num_procs} concurrent process(es)")
        # Add tasks to a joinable queue
        q = multiprocessing.JoinableQueue()
        for t_index in range(max_time_index):
            task = (
                t_index,
                sec,
                units,
                calendar,
                run_date,
                Uf,
                Vf,
                coordf,
                mesh_maskf,
                bathyf,
                tile_coords_dic,
                expansion_factor,
                storage_path,
            )
            q.put(task)
        # Spawn a set of worker processes
        procs = []
        for i in range(num_procs):
            p = multiprocessing.Process(target=_process_time_slice, args=(q,))
            procs.append(p)
        # Start each one
        for p in procs:
            p.start()
        # Wait until they complete
        for p in procs:
            p.join()
        # Close the queue
        q.close()

    _pdf_concatenate(storage_path, tile_coords_dic)

    checklist = {
        run_type: {
            "run date": run_date.format("YYYY-MM-DD"),
            "png": sorted(
                [os.fspath(f) for f in storage_path.iterdir() if f.suffix == ".png"]
            ),
            "pdf": sorted(
                [os.fspath(f) for f in storage_path.iterdir() if f.suffix == ".pdf"]
            ),
        }
    }
    return checklist


def _process_time_slice(q):
    """
    This is the worker function that gets called for each task in the multiprocessing queue.
    """
    while True:
        try:
            task = q.get_nowait()
            _callMakeFigure(*task)
            q.task_done()
        except Empty:
            break


def _callMakeFigure(
    t_index,
    sec,
    units,
    calendar,
    run_date,
    Uf,
    Vf,
    coordf,
    mesh_maskf,
    bathyf,
    tile_coords_dic,
    expansion_factor,
    storage_path,
):
    """
    Calls the make_figure() function in the surface_currents_tiles module for time index t_index.
    make_figure() function is called once to produce figures with website theme and called again
    to produce figures in pdf format.
    """
    date_stamp = _getTimeFileName(sec[t_index], units, calendar)

    # make website theme version
    fig_list, tile_names = surface_current_tiles.make_figure(
        run_date,
        t_index,
        Uf,
        Vf,
        coordf,
        mesh_maskf,
        bathyf,
        tile_coords_dic,
        expansion_factor,
    )
    _render_figures(fig_list, tile_names, storage_path, date_stamp, "png")
    del fig_list

    # make pdf version
    fig_list, tile_names = surface_current_tiles.make_figure(
        run_date,
        t_index,
        Uf,
        Vf,
        coordf,
        mesh_maskf,
        bathyf,
        tile_coords_dic,
        expansion_factor,
        theme=None,
    )
    _render_figures(fig_list, tile_names, storage_path, date_stamp, "pdf")
    del fig_list


def _getTimeFileName(sec, units, calendar):
    """
    Constructs UTC timestamp for the figure file name.
    """
    dt = netCDF4.num2date(sec, units, calendar=calendar)
    dt_utc = datetime.datetime.combine(
        dt.date(), dt.time(), pytz.utc
    )  # add timezone to utc time
    fmt = "%Y%m%d_%H%M%S"

    time_utc = dt_utc.strftime(fmt)

    return time_utc


def _render_figures(fig_list, tile_names, storage_path, date_stamp, file_type):
    for fig, name in zip(fig_list, tile_names):
        ftile = "surface_currents_tile{:02d}_{}_UTC.{}".format(
            int(name[4:]), date_stamp, file_type
        )
        outfile = Path(storage_path, ftile)
        FigureCanvasBase(fig).print_figure(
            os.fspath(outfile), facecolor=fig.get_facecolor()
        )
        logger.info(f"{outfile} saved")


def _pdf_concatenate(path, tile_coords_dic):
    """
    For each tile combine the time series of pdf files into one file.
    Delete the individual pdf files, leaving only the per tile files.
    Shrink the merged pdf files.
    """
    for tile in tile_coords_dic:
        result = (path / tile).with_suffix(".pdf")
        logger.info(f"concatenating {tile} pdf files into: {result}")
        merger = PdfFileMerger()
        for pdf in sorted(path.glob(f"surface_currents_{tile}*.pdf")):
            merger.append(os.fspath(pdf))
            logger.debug(f"added {pdf}")
            pdf.unlink()
            logger.debug(f"deleted {pdf}")
        merger.write(os.fspath(result))
        logger.info(f"saved {result}")
        merger.close()
        _pdf_shrink(result)


def _pdf_shrink(filename):
    """
    Strategy borrowed from make_plots.py to shrink pdf file
    """
    logger.info(f"Starting PDF shrinking of: {filename}")
    tmpfilename = filename.with_suffix(".temp")
    pdftocairo = Path(os.environ["NOWCAST_ENV"], "bin", "pdftocairo")
    cmd = f"{pdftocairo} -pdf {filename} {tmpfilename}"
    logger.debug(f"running subprocess: {cmd}")
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if proc.stdout:
            logger.debug(proc.stdout)
        tmpfilename.rename(filename)
        logger.info(f"shrank {filename}")
    except subprocess.CalledProcessError as e:
        logger.warning("PDF shrinking failed, proceeding with unshrunk PDF")
        logger.debug(f"pdftocairo return code: {e.returncode}")
        if e.output:
            logger.debug(e.output)


if __name__ == "__main__":
    main()  # pragma: no cover
