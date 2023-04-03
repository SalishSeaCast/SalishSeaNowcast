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
import warnings
from pathlib import Path

import arrow
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
    forecast = parsed_args.forecast
    fcst_date = parsed_args.fcst_date
    logger.info(
        f"cropping {fcst_date.format('YYYY-MM-DD')} ECCC HRDPS 2.5km continental "
        f"{forecast}Z GRIB files to SalishSeaCast subdomain"
    )
    eccc_file_tmpl = config["weather"]["download"]["2.5 km"]["ECCC file template"]
    ssc_file_tmpl = config["weather"]["download"]["2.5 km"]["SSC cropped file template"]
    var_names = config["weather"]["download"]["2.5 km"]["variables"]
    fcst_dur = config["weather"]["download"]["2.5 km"]["forecast duration"]
    for msc_var, grib_var, _ in var_names:
        eccc_grib_files = _calc_grib_file_paths(
            eccc_file_tmpl, fcst_date, forecast, fcst_dur, msc_var, config
        )
        ssc_grib_files = _calc_grib_file_paths(
            ssc_file_tmpl, fcst_date, forecast, fcst_dur, msc_var, config
        )
        _write_ssc_grib_files(
            msc_var, grib_var, eccc_grib_files, ssc_grib_files, config
        )
    checklist[forecast] = "cropped to SalishSeaCast subdomain"
    return checklist


def _calc_grib_file_paths(file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var, config):
    """
    :param str file_tmpl:
    :param :py:class:`arrow.Arrow` fcst_date:
    :param str fcst_hr:
    :param int fcst_dur:
    :param str msc_var:
    :rtype: list
    """
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    fcst_yyyymmdd = fcst_date.format("YYYYMMDD")
    grib_domain = "ECCC" if "SSC" not in file_tmpl else "SSC"
    logger.debug(
        f"creating {msc_var} {grib_domain} GRIB file paths list for "
        f"{fcst_yyyymmdd} {fcst_hr}Z forecast"
    )
    grib_files = []
    for fcst_step in range(1, fcst_dur + 1):
        grib_hr_dir = grib_dir / Path(fcst_yyyymmdd, fcst_hr, f"{fcst_step:03d}")
        grib_file = file_tmpl.format(
            date=fcst_yyyymmdd,
            forecast=fcst_hr,
            variable=msc_var,
            hour=f"{fcst_step:03d}",
        )
        grib_files.append(grib_hr_dir / grib_file)
    return grib_files


def _write_ssc_grib_files(msc_var, grib_var, eccc_grib_files, ssc_grib_files, config):
    """
    :param str msc_var:
    :param str grib_var:
    :param list eccc_grib_files:
    :param list ssc_grib_files:
    :param dict config:
    """
    y_min, y_max = config["weather"]["download"]["2.5 km"]["lat indices"]
    x_min, x_max = config["weather"]["download"]["2.5 km"]["lon indices"]
    # We need 1 point more than the final domain size to facilitate calculation of the
    # grid rotation angle for the wind components
    y_slice = slice(y_min, y_max + 1)
    x_slice = slice(x_min, x_max + 1)
    ny, nx = y_max - y_min + 1, x_max - x_min + 1
    for eccc_grib_file, ssc_grib_file in zip(eccc_grib_files, ssc_grib_files):
        with xarray.open_dataset(
            eccc_grib_file, engine="cfgrib", backend_kwargs={"indexpath": ""}
        ) as eccc_ds:
            ssc_ds = eccc_ds.sel(y=y_slice, x=x_slice)
        ssc_ds[grib_var].attrs.update(
            {
                "GRIB_numberOfPoints": nx * ny,
                "GRIB_Nx": nx,
                "GRIB_Ny": ny,
            }
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            xarray_to_grib.to_grib(ssc_ds, ssc_grib_file)
        logger.debug(
            f"wrote {msc_var} GRIB file cropped to SalishSeaCast subdomain: {ssc_grib_file}"
        )


if __name__ == "__main__":
    main()  # pragma: no cover
