#  Copyright 2013 – present by the SalishSeaCast Project contributors
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

# SPDX-License-Identifier: Apache-2.0


"""SalishSeaCast runoff file generation worker for v201702 bathymetry.

Blend Environment Canada river gauge data for the Fraser River at Hope with climatology for the
Fraser downstream of Hope,
and climatology for all the other modelled rivers to generate the runoff forcing file.
"""

import importlib
import logging
import os
from pathlib import Path

import arrow
import netCDF4 as NC
import numpy as np
import yaml
from nemo_nowcast import NowcastWorker
from salishsea_tools import rivertools

NAME = "make_201702_runoff_file"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_201702_runoff_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to produce runoff file for.",
    )
    worker.run(make_201702_runoff_file, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.info(
        f"{ymd} runoff file creation from Fraser at Hope and climatology "
        f"elsewhere complete"
    )
    return "success"


def failure(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.critical(f"{ymd} runoff file creation failed")
    return "failure"


def make_201702_runoff_file(parsed_args, config, *args):
    """Create a rivers runoff file for the v201702 bathymetry from real-time Fraser River at Hope
    average flow yesterday and climatology for all the other rivers.
    """
    yesterday = parsed_args.run_date.shift(days=-1)
    # Find history of fraser flow
    fraserflow = _get_fraser_at_hope(config)
    # Select yesterday's value
    year_data = fraserflow[fraserflow[:, 0] == yesterday.year]
    month_data = year_data[year_data[:, 1] == yesterday.month]
    day_data = month_data[month_data[:, 2] == yesterday.day]
    flow_at_hope = day_data[0, 3]
    # Get Fraser Watershed Climatology without Fraser
    otherratio, fraserratio, nonFraser, afterHope = _fraser_climatology(config)

    bathy_version = "v201702"
    logger.info(f"calculating runoff forcing for b201702 bathymetry")
    # Get climatology
    climatology_file = Path(
        config["rivers"]["bathy params"][bathy_version]["monthly climatology"]
    )
    criverflow, area = _get_river_climatology(climatology_file)
    # Interpolate to today
    driverflow = _calculate_daily_flow(yesterday, criverflow)
    logger.debug(f'calculated flow for {yesterday.format("YYYY-MM-DD")}')
    # Calculate combined runoff and write file
    directory = Path(config["rivers"]["rivers dir"])
    filename_tmpls = config["rivers"]["bathy params"][bathy_version]["file template"]
    prop_dict = importlib.import_module(
        config["rivers"]["bathy params"][bathy_version]["prop_dict module"]
    ).prop_dict
    filepath = _combine_runoff(
        prop_dict,
        flow_at_hope,
        yesterday,
        afterHope,
        nonFraser,
        fraserratio,
        otherratio,
        driverflow,
        area,
        directory,
        filename_tmpls,
    )
    checklist = {bathy_version: os.fspath(filepath)}
    return checklist


def _get_fraser_at_hope(config):
    """Read daily average discharge data for Fraser at Hope from ECget file."""
    filename = Path(config["rivers"]["SOG river files"]["Fraser"])
    fraserflow = np.loadtxt(os.fspath(filename))
    logger.debug(f"read Fraser at Hope data from {filename}")
    return fraserflow


def _get_river_climatology(filename):
    """Read the monthly climatology that we will use for all the other rivers."""
    # Open monthly climatology
    clim_rivers = NC.Dataset(filename)
    criverflow = clim_rivers.variables["rorunoff"]
    area = clim_rivers.variables["area"]
    logger.debug(f"read monthly climatology for all other rivers from {filename}")
    return criverflow, area


def _calculate_daily_flow(yesterday, criverflow):
    """Interpolate the daily values from the monthly values."""
    pyear, nyear = yesterday.year, yesterday.year
    if yesterday.day < 16:
        prevmonth = yesterday.month - 1
        if prevmonth == 0:  # handle January
            prevmonth = 12
            pyear = pyear - 1
        nextmonth = yesterday.month
    else:
        prevmonth = yesterday.month
        nextmonth = yesterday.month + 1
        if nextmonth == 13:  # handle December
            nextmonth = 1
            nyear = nyear + 1
    fp = yesterday - arrow.get(pyear, prevmonth, 15)
    fn = arrow.get(nyear, nextmonth, 15) - yesterday
    ft = fp + fn
    fp = fp.days / ft.days
    fn = fn.days / ft.days
    driverflow = fn * criverflow[prevmonth - 1] + fp * criverflow[nextmonth - 1]
    return driverflow


def _fraser_climatology(config):
    """Read in the Fraser climatology separated from Hope flow."""
    fraser_climatology_file = Path(
        config["rivers"]["bathy params"]["v201702"]["Fraser climatology"]
    )
    with fraser_climatology_file.open("rt") as f:
        fraser_climatology = yaml.safe_load(f)
    logger.debug(f"read Fraser climatology from {fraser_climatology_file}")
    otherratio = fraser_climatology["Ratio that is not Fraser"]
    fraserratio = fraser_climatology["Ratio that is Fraser"]
    nonFraser = np.array(fraser_climatology["non Fraser by Month"])
    afterHope = np.array(fraser_climatology["after Hope by Month"])
    return otherratio, fraserratio, nonFraser, afterHope


def _fraser_correction(
    pd,
    fraserflux,
    yesterday,
    afterHope,
    NonFraser,
    fraserratio,
    otherratio,
    runoff,
    area,
):
    """For the Fraser Basin only, replace basic values with the new
    climatology after Hope and the observed values for Hope.
    Note, we are changing runoff and ensuring river depth is not 0.
    """
    for key, river in pd.items():
        if "Fraser" in key:
            flux = _calculate_daily_flow(yesterday, afterHope) + fraserflux
            subarea = fraserratio
        elif "Zero" in key:
            flux = 0.0
            subarea = 1.0  # to avoid division by zero
        else:
            flux = _calculate_daily_flow(yesterday, NonFraser)
            subarea = otherratio
        runoff = rivertools.fill_runoff_array(
            flux * river["prop"] / subarea,
            river["i"],
            river["di"],
            river["j"],
            river["dj"],
            river["depth"],
            runoff,
            np.empty_like(runoff),
            area,
        )[0]
    return runoff


def _combine_runoff(
    prop_dict,
    flow_at_hope,
    yesterday,
    afterHope,
    nonFraser,
    fraserratio,
    otherratio,
    driverflow,
    area,
    directory,
    filename_tmpl,
):
    """
    :param :py:class:`pathlib.Path` directory:
    """
    pd = prop_dict["fraser"]

    runoff = _fraser_correction(
        pd,
        flow_at_hope,
        yesterday,
        afterHope,
        nonFraser,
        fraserratio,
        otherratio,
        driverflow,
        area,
    )
    # set up filename to follow NEMO conventions
    filepath = directory / filename_tmpl.format(yesterday.date())
    _write_file(filepath, yesterday, runoff)
    logger.debug(f"wrote file to {filepath}")
    return filepath


def _write_file(filepath, yesterday, flow):
    """Create the rivers runoff netCDF4 file."""
    with NC.Dataset(os.fspath(filepath), "w") as nemo:
        nemo.description = "Real Fraser Values, Daily Climatology for Other Rivers"
        # Dimensions
        ymax, xmax = flow.shape
        nemo.createDimension("x", xmax)
        nemo.createDimension("y", ymax)
        nemo.createDimension("time_counter", None)
        # Time
        time_counter = nemo.createVariable(
            "time_counter", "float32", "time_counter", zlib=True
        )
        time_counter.units = "non-dim"
        time_counter = [1]
        # Runoff
        rorunoff = nemo.createVariable(
            "rorunoff", "float32", ("time_counter", "y", "x"), zlib=True
        )
        rorunoff._Fillvalue = 0.0
        rorunoff._missing_value = 0.0
        rorunoff._units = "kg m-2 s-1"
        rorunoff[0, :] = flow


if __name__ == "__main__":
    main()  # pragma: no cover
