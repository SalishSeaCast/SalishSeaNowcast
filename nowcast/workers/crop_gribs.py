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


"""SalishSeaCast worker that loads ECCC MSC 2.5 km rotated lat-lon continental grid HRDPS GRIB2
files, crops them to the subdomain needed for SalishSeaCast NEMO forcing, and writes them to
new GRIB2 files.
"""
# Development notebook:
#
# * https://github.com/SalishSeaCast/analysis-doug/tree/main/notebooks/continental-HRDPS/crop-grib-to-SSC-domain.ipynb.ipynb


import logging
import os
import warnings
from pathlib import Path

import arrow
import watchdog.observers
import watchdog.events
import xarray
from cfgrib import xarray_to_grib
from nemo_nowcast import NowcastWorker


NAME = "crop_gribs"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.crop_gribs --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "forecast",
        choices={"00", "06", "12", "18"},
        help="Name of forecast to crop files in.",
    )
    worker.cli.add_date_option(
        "--fcst-date",
        default=arrow.now().floor("day"),
        help="Forecast date to crop files in.",
    )
    worker.cli.add_argument(
        "--var-hour",
        type=int,
        help="forecast hour to crop file for specific variable in; must be used with --var",
    )
    worker.cli.add_argument(
        "--var",
        dest="msc_var_name",
        help="forecast variable to crop file for; must be used with --var-hour",
    )
    worker.run(crop_gribs, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.fcst_date.format("YYYY-MM-DD")
    logger.info(f"{ymd} {parsed_args.forecast} GRIBs cropping complete")
    msg_type = f"success {parsed_args.forecast}"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.fcst_date.format("YYYY-MM-DD")
    logger.critical(f"{ymd} {parsed_args.forecast} GRIBs cropping failed")
    msg_type = f"failure {parsed_args.forecast}"
    return msg_type


def crop_gribs(parsed_args, config, *args):
    """Collect weather forecast results from hourly GRIB2 files
    and produces day-long NEMO atmospheric forcing netCDF files.
    """
    checklist = {}
    fcst_hr = parsed_args.forecast
    fcst_date = parsed_args.fcst_date
    var_hour = parsed_args.var_hour
    msc_var_name = parsed_args.msc_var_name
    logger.info(
        f"cropping {fcst_date.format('YYYY-MM-DD')} ECCC HRDPS 2.5km continental "
        f"{fcst_hr}Z GRIB files to SalishSeaCast subdomain"
    )

    eccc_file_tmpl = config["weather"]["download"]["2.5 km"]["ECCC file template"]
    var_names = config["weather"]["download"]["2.5 km"]["variables"]
    fcst_dur = var_hour or config["weather"]["download"]["2.5 km"]["forecast duration"]
    msc_var_names = [vars[0] for vars in var_names]
    eccc_grib_files = _calc_grib_file_paths(
        eccc_file_tmpl,
        fcst_date,
        fcst_hr,
        fcst_dur,
        msc_var_names,
        config,
        msc_var_name,
    )

    if msc_var_name and var_hour:
        # Crop a single variable-hour file
        eccc_grib_file = eccc_grib_files.pop()
        _write_ssc_grib_file(eccc_grib_file, config)
        logger.info(
            f"finished cropping ECCC grib file to SalishSeaCast subdomain: {eccc_grib_file}"
        )
        checklist[fcst_hr] = "cropped to SalishSeaCast subdomain"
        return checklist

    handler = _GribFileEventHandler(eccc_grib_files, config)
    observer = watchdog.observers.Observer()
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    fcst_yyyymmdd = fcst_date.format("YYYYMMDD")
    grib_fcst_dir = grib_dir / Path(fcst_yyyymmdd, fcst_hr)
    observer.schedule(handler, os.fspath(grib_fcst_dir), recursive=True)
    logger.info(f"starting to watch for ECCC grib files to crop in {grib_fcst_dir}/")
    observer.start()
    while eccc_grib_files:
        # We need to have a timeout on the observer thread so that the status
        # of the ECCC grib files set gets checked, otherwise the worker never
        # finishes because the main thread is blocked by the observer thread.
        observer.join(timeout=0.5)
    observer.stop()
    observer.join()
    logger.info(
        f"finished cropping ECCC grib files to SalishSeaCast subdomain in {grib_fcst_dir}/"
    )
    checklist[fcst_hr] = "cropped to SalishSeaCast subdomain"
    return checklist


def _calc_grib_file_paths(
    file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var_names, config, msc_var_name=None
):
    """
    :param str file_tmpl:
    :param :py:class:`arrow.Arrow` fcst_date:
    :param str fcst_hr:
    :param int fcst_dur:
    :param list msc_var_names:
    :param :py:class:`nemo_nowcast.Config` config:
    :param msc_var_name:

    :rtype: set
    """
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    fcst_yyyymmdd = fcst_date.format("YYYYMMDD")
    logger.debug(
        f"creating ECCC GRIB file paths list for {fcst_yyyymmdd} {fcst_hr}Z forecast"
    )
    fcst_steps_start = 1
    if msc_var_name:
        msc_var_names = [msc_var_name]
        fcst_steps_start = fcst_dur
    grib_files = set()
    for msc_var in msc_var_names:
        for fcst_step in range(fcst_steps_start, fcst_dur + 1):
            grib_hr_dir = grib_dir / Path(fcst_yyyymmdd, fcst_hr, f"{fcst_step:03d}")
            grib_file = file_tmpl.format(
                date=fcst_yyyymmdd,
                forecast=fcst_hr,
                variable=msc_var,
                hour=f"{fcst_step:03d}",
            )
            grib_files.add(grib_hr_dir / grib_file)
    return grib_files


def _write_ssc_grib_file(eccc_grib_file, config):
    """
    :param :py:class:`pathlib.Path` eccc_grib_file:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    y_min, y_max = config["weather"]["download"]["2.5 km"]["lat indices"]
    x_min, x_max = config["weather"]["download"]["2.5 km"]["lon indices"]
    # We need 1 point more than the final domain size to facilitate calculation of the
    # grid rotation angle for the wind components
    y_slice = slice(y_min, y_max + 1)
    x_slice = slice(x_min, x_max + 1)
    ny, nx = y_max - y_min + 1, x_max - x_min + 1

    with xarray.open_dataset(
        eccc_grib_file, engine="cfgrib", backend_kwargs={"indexpath": ""}
    ) as eccc_ds:
        ssc_ds = eccc_ds.sel(y=y_slice, x=x_slice)

    # **NOTE:** This is brittle if the ECCC HRDPS file name convention changes
    msc_var = eccc_grib_file.stem.split("HRDPS_")[1].split("_RLatLon")[0]
    vars = config["weather"]["download"]["2.5 km"]["variables"]
    for var in vars:
        if var[0] == msc_var:
            grib_var = var[1]
            break

    ssc_ds[grib_var].attrs.update(
        {
            "GRIB_numberOfPoints": nx * ny,
            "GRIB_Nx": nx,
            "GRIB_Ny": ny,
        }
    )
    ssc_grib_file = (
        f"{eccc_grib_file.parent / eccc_grib_file.stem}_SSC{eccc_grib_file.suffix}"
    )
    _xarray_to_grib(ssc_ds, ssc_grib_file)

    logger.debug(f"wrote GRIB file cropped to SalishSeaCast subdomain: {ssc_grib_file}")


def _xarray_to_grib(ssc_ds, ssc_grib_file):
    """Write GRIB file.

    This is a separate function to facilitate unit testing of _write_ssc_grib_file().

    :param :py:class:`xarray.Dataset` ssc_ds:
    :param :py:class:`pathlib.Path` ssc_grib_file:
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        xarray_to_grib.to_grib(ssc_ds, ssc_grib_file)


class _GribFileEventHandler(watchdog.events.FileSystemEventHandler):
    """watchdog file system event handler that detects completion of HRDPS file moves
    from the downloads directory into the atmospheric forcing tree.
    """

    def __init__(self, eccc_grib_files, config):
        super().__init__()
        self.eccc_grib_files = eccc_grib_files
        self.config = config

    def on_closed(self, event):
        super().on_closed(event)
        if Path(event.src_path) in self.eccc_grib_files:
            eccc_grib_file = Path(event.src_path)
            _write_ssc_grib_file(eccc_grib_file, self.config)
            self.eccc_grib_files.remove(eccc_grib_file)
            logger.debug(
                f"observer thread files remaining to process: {len(self.eccc_grib_files)}"
            )


if __name__ == "__main__":
    main()  # pragma: no cover
