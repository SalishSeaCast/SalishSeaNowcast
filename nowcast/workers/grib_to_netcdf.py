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


"""SalishSeaCast worker that generates weather forcing file from GRIB2 forecast files.

Collect weather forecast results from hourly GRIB2 files and produce
day-long NEMO atmospheric forcing netCDF files.

Development notebooks are in:

* https://github.com/SalishSeaCast/analysis-doug/tree/main/notebooks/continental-HRDPS
* https://github.com/SalishSeaCast/tools/tree/main/I_ForcingFiles/Atmos
"""
import functools
import logging
import os
from pathlib import Path

import arrow
import matplotlib.backends.backend_agg
import matplotlib.figure
import netCDF4 as nc
import numpy as np
from nemo_nowcast import NowcastWorker, WorkerError
import xarray

from nowcast import lib

NAME = "grib_to_netcdf"
logger = logging.getLogger(NAME)
wgrib2_logger = logging.getLogger("wgrib2")

# TODO: move these constants to config YAMl file
# Position of Sand Heads
SandI, SandJ = 118, 108


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.grib_to_netcdf --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast+", "forecast2"},
        help="""
        Type of run to produce netCDF files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run.
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to produce netCDF files for.",
    )
    worker.run(grib_to_netcdf, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.info(f"{ymd} NEMO-atmos forcing file for {parsed_args.run_type} created")
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.critical(
        f"{ymd} NEMO-atmos forcing file creation for {parsed_args.run_type} failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def grib_to_netcdf(parsed_args, config, *args):
    """Collect weather forecast results from hourly GRIB2 files
    and produces day-long NEMO atmospheric forcing netCDF files.
    """
    checklist = {}
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    nemo_datasets = {}
    match run_type:
        case "nowcast+":
            logger.info(
                f"creating NEMO-atmos forcing files for {run_date.format('YYYY-MM-DD')} "
                f"nowcast and forecast runs"
            )
            var_names = config["weather"]["download"]["2.5 km"]["variables"]
            # run_date dataset is composed of pieces from 3 grib forecast hours
            # run_date + 1 dataset is composed of hours 11-35 from 12Z forecast
            for msc_var, grib_var, nemo_var in var_names:
                grib_files = _calc_grib_file_paths(
                    run_date,
                    "12",
                    (11, 35),
                    msc_var,
                    config,
                )
                nemo_datasets[nemo_var] = _calc_nemo_var_ds(
                    grib_var, nemo_var, grib_files, config
                )
            nemo_ds = xarray.combine_by_coords(
                nemo_datasets.values(), combine_attrs="drop_conflicts"
            )
            _apportion_accumulation_vars(nemo_ds, config)

            # rotate wind components to earth-reference

            # clean up dataset attrs
            fcst = True
            fcst_date = run_date.shift(days=+1)
            nc_file = _write_netcdf(nemo_ds, fcst_date, config, fcst)
            if fcst:
                if "fcst" not in checklist:
                    checklist["fcst"] = [nc_file.name]
                else:
                    checklist["fcst"].append(nc_file.name)
            else:
                checklist["nowcast"] = nc_file.name

            # run_date + 2 dataset is composed of hours 35-48 from 12Z forecast
        case "forecast2":
            logger.info(
                f"creating NEMO-atmos forcing files for {run_date.format('YYYY-MM-DD')} "
                f"forecast2 run"
            )
            # run_date + 1 dataset is composed of hours 17-41 from 06Z forecast
            # run_date + 2 dataset is composed of hours 41-48 from 06Z forecast
    return checklist

    match parsed_args.run_type:
        case "nowcast+":
            segments = _define_forecast_segments_nowcast(run_date)
        case "forecast2":
            segments = _define_forecast_segments_forecast2(run_date)

    ip = 0
    # prep monitoring image
    fig, axs = _set_up_plotting()
    for fcst_section_hrs, zstart, flen, subdir, ymd in zip(*segments):
        _rotate_grib_wind(fcst_section_hrs, config)
        _collect_grib_scalars(fcst_section_hrs, config)
        outgrib, outzeros = _concat_hourly_gribs(ymd, fcst_section_hrs, config)
        outgrib, outzeros = _crop_to_watersheds(
            ymd, IST, IEN, JST, JEN, outgrib, outzeros, config
        )
        outnetcdf, out0netcdf = _make_netCDF_files(
            config, ymd, subdir, outgrib, outzeros
        )
        _calc_instantaneous(outnetcdf, out0netcdf, ymd, flen, zstart, axs)
        _change_to_NEMO_variable_names(outnetcdf, axs, ip)
        ip += 1

        _netCDF4_deflate(outnetcdf)
        lib.fix_perms(outnetcdf, grp_name=config["file group"])
        if subdir in checklist:
            checklist[subdir].append(os.path.basename(outnetcdf))
        else:
            if subdir:
                checklist[subdir] = [os.path.basename(outnetcdf)]
            else:
                checklist.update({subdir: os.path.basename(outnetcdf)})

    axs[2, 0].legend(loc="upper left")
    image_file = config["weather"]["monitoring image"]
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
    canvas.print_figure(image_file)
    lib.fix_perms(image_file, grp_name=config["file group"])
    return checklist


def _calc_grib_file_paths(fcst_date, fcst_hr, fcst_step_range, msc_var, config):
    """
    :param :py:class:`arrow.Arrow` fcst_date:
    :param str fcst_hr:
    :param tuple fcst_step_range:
    :param str msc_var:
    :param dict config:

    :rtype: list
    """
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    file_tmpl = config["weather"]["download"]["2.5 km"]["file template"]
    fcst_yyyymmdd = fcst_date.format("YYYYMMDD")
    grib_files = []
    start, stop = fcst_step_range
    for fcst_step in range(start, stop + 1):
        grib_hr_dir = grib_dir / Path(fcst_yyyymmdd, fcst_hr, f"{fcst_step:03d}")
        grib_file = file_tmpl.format(
            date=fcst_yyyymmdd,
            forecast=fcst_hr,
            variable=msc_var,
            hour=f"{fcst_step:03d}",
        )
        grib_files.append(grib_hr_dir / grib_file)
    return grib_files


def _trim_grib(ds, y_slice, x_slice):
    """Preprocessing function for xarray.open_mfdataset().

    :param :py:class:`xarray.Dataset` ds:
    :param :py:class:`slice` y_slice:
    :param :py:class:`slice` x_slice:

    :rtype: :py:class:`xarray.Dataset`
    """
    # Select region of interest
    ds = ds.sel(y=y_slice, x=x_slice)
    # Drop coordinates that we don't need
    keep_coords = ("time", "step", "latitude", "longitude")
    ds = ds.reset_coords(
        [coord for coord in ds.coords if coord not in keep_coords],
        drop=True,
    )
    return ds


def _calc_nemo_var_ds(grib_var, nemo_var, grib_files, config):
    """
    :param str grib_var:
    :param str nemo_var:
    :param list grib_files:
    :param dict config:

    :rtype: :py:class:`xarray.Dataset`
    """
    y_slice = slice(*config["weather"]["download"]["2.5 km"]["lon indices"])
    x_slice = slice(*config["weather"]["download"]["2.5 km"]["lat indices"])
    _partial_trim_grib = functools.partial(_trim_grib, y_slice=y_slice, x_slice=x_slice)
    grib_ds = xarray.open_mfdataset(
        grib_files,
        preprocess=_partial_trim_grib,
        combine="nested",
        concat_dim="step",
        engine="cfgrib",
    )
    time_counter = grib_ds.step.values + grib_ds.time.values
    nemo_da = xarray.DataArray(
        data=grib_ds[grib_var].data,
        coords={
            "time_counter": time_counter,
            "y": grib_ds.y,
            "x": grib_ds.x,
        },
        attrs=grib_ds[grib_var].attrs,
    )
    nemo_ds = xarray.Dataset(
        data_vars={
            nemo_var: nemo_da,
        },
        coords={
            "time_counter": time_counter,
            "y": grib_ds.y,
            "x": grib_ds.x,
            "nav_lon": (["y", "x"], grib_ds.longitude.data),
            "nav_lat": (["y", "x"], grib_ds.latitude.data),
        },
        attrs=grib_ds.attrs,
    )
    return nemo_ds


def _apportion_accumulation_vars(nemo_ds, config):
    """Apportion variables that hold quantities (e.g. precipitation, short & long vwave radiation)
    accumulated over 24 hours in the GRIB files to hourly values.

    Also, drop the first time step from the dataset. It is the "previous" value for the
    apportioning (and excess baggage for the other variables), so no longer needed.

    :param :py:class:`xarray.Dataset` nemo_ds:
    :param dict config:

    :rtype: :py:class:`xarray.Dataset` nemo_ds

    """
    accum_vars = config["weather"]["download"]["2.5 km"]["accumulation variables"]
    # TODO: handle case of datasets that span forecasts, meaning that the "previous" value for
    #       the apportioning isn't the first time step
    apportioned_vars = {}
    for var in nemo_ds.data_vars:
        apportioned_vars[var] = nemo_ds[var][1:]
        if var in accum_vars:
            apportioned_vars[var].data = nemo_ds[var][1:].data - nemo_ds[var][0:-1].data
    apportioned_ds = xarray.Dataset(
        data_vars=apportioned_vars,
        coords={
            "time_counter": nemo_ds.time_counter[1:],
            "y": nemo_ds.y,
            "x": nemo_ds.x,
            "nav_lon": nemo_ds.nav_lon,
            "nav_lat": nemo_ds.nav_lat,
        },
        attrs=nemo_ds.attrs,
    )
    return apportioned_ds


def _write_netcdf(nemo_ds, file_date, config, fcst=False):
    """
    :param :py:class:`xarray.Dataset` nemo_ds:
    :param :py:class:`arrow.Arrow` file_date:
    :param dict config:
    :param boolean fcst:

    :rtype: :py:class:`pathlib.Path`
    """
    encoding = {
        "time_counter": {"units": "seconds since 1970-01-01 00:00", "dtype": float},
    }
    encoding.update({var: {"zlib": True, "complevel": 4} for var in nemo_ds.data_vars})
    ops_dir = Path(config["weather"]["ops dir"])
    nc_file_tmpl = config["weather"]["file template"]
    nc_filename = nc_file_tmpl.format(file_date.date())
    nc_file = Path("fcst/", nc_filename) if fcst else Path(nc_filename)
    _to_netcdf(nemo_ds, encoding, ops_dir / nc_file)
    return nc_file


def _to_netcdf(nemo_ds, encoding, nc_file_path):
    """This function is separate to facilitate testing the calling function.

    :param :py:class:`xarray.Dataset` nemo_ds:
    :param dict encoding:
    :param :py:class:`pathlib.Path` nc_file_path:
    """
    nemo_ds.to_netcdf(nc_file_path, encoding=encoding, unlimited_dims=("time_counter",))


def _define_forecast_segments_nowcast(run_date):
    """Define segments of forecasts to build into working weather files
    for nowcast and a following forecast

    :param :py:class:`arrow.Arrow` run_date:

    :rtype: tuple
    """

    today = run_date
    today_yyyymmdd = today.format("YYYYMMDD")
    yesterday = today.shift(days=-1)
    tomorrow = today.shift(days=+1)
    next_day = today.shift(days=+2)
    nemo_yyyymmdd = "[y]YYYY[m]MM[d]DD"
    fcst_section_hrs_list = [{}, {}, {}]

    # today
    p1 = Path(yesterday.format("YYYYMMDD"), "18")
    p2 = Path(today_yyyymmdd, "00")
    p3 = Path(today_yyyymmdd, "12")
    logger.debug(f"forecast sections: {p1} {p2} {p3}")
    fcst_section_hrs_list[0] = {
        # part: (dir, real start hr, forecast start hr, end hr)
        "section 1": (os.fspath(p1), -1, (24 - 18 - 1), (24 - 18 + 0)),
        "section 2": (os.fspath(p2), 1, (1 - 0), (12 - 0)),
        "section 3": (os.fspath(p3), 13, (13 - 12), (23 - 12)),
    }
    zero_starts = [[1, 13]]
    lengths = [24]
    subdirectories = [""]
    # TODO: refactor to today.date() for compatibility with config["weather"]["file template']
    yearmonthdays = [today.format(nemo_yyyymmdd)]

    # tomorrow (forecast)
    p1 = Path(today_yyyymmdd, "12")
    logger.debug(f"tomorrow forecast section: {p1}")
    fcst_section_hrs_list[1] = {
        # part: (dir, start hr, end hr)
        "section 1": (os.fspath(p1), -1, (24 - 12 - 1), (24 + 23 - 12)),
    }
    zero_starts.append([])
    lengths.append(24)
    subdirectories.append("fcst")
    yearmonthdays.append(tomorrow.format(nemo_yyyymmdd))

    # next day (forecast)
    p1 = Path(today_yyyymmdd, "12")
    logger.debug(f"next day forecast section: {p1}")
    fcst_section_hrs_list[2] = {
        # part: (dir, start hr, end hr)
        "section 1": (os.fspath(p1), -1, (24 + 24 - 12 - 1), (24 + 24 + 12 - 12)),
    }
    zero_starts.append([])
    lengths.append(13)
    subdirectories.append("fcst")
    yearmonthdays.append(next_day.format(nemo_yyyymmdd))

    return (fcst_section_hrs_list, zero_starts, lengths, subdirectories, yearmonthdays)


def _define_forecast_segments_forecast2(run_date):
    """Define segments of forecasts to build into working weather files
    for the extended forecast i.e. forecast2

    :param :py:class:`arrow.Arrow` run_date:

    :rtype: tuple
    """

    # today is the day after this nowcast/forecast sequence started
    today = run_date
    today_yyyymmdd = today.format("YYYYMMDD")
    tomorrow = today.shift(days=+1)
    nextday = today.shift(days=+2)
    nemo_yyyymmdd = "[y]YYYY[m]MM[d]DD"

    fcst_section_hrs_list = [{}, {}]

    # tomorrow
    p1 = Path(today_yyyymmdd, "06")
    logger.debug(f"forecast section: {p1}")
    fcst_section_hrs_list[0] = {
        # part:(dir, start hr, end hr)
        "section 1": (os.fspath(p1), -1, (24 - 6 - 1), (24 + 23 - 6)),
    }
    zero_starts = [[]]
    lengths = [24]
    subdirectories = ["fcst"]
    # TODO: refactor to today.date() for compatibility with config["weather"]["file template']
    yearmonthdays = [tomorrow.format(nemo_yyyymmdd)]

    # nextday
    p1 = Path(today_yyyymmdd, "06")
    logger.debug(f"next day forecast section: {p1}")
    fcst_section_hrs_list[1] = {
        # part: (dir, start hr, end hr)
        "section 1": (os.fspath(p1), -1, (24 + 24 - 6 - 1), (24 + 24 + 6 - 6)),
    }
    zero_starts.append([])
    lengths.append(7)
    subdirectories.append("fcst")
    yearmonthdays.append(nextday.format(nemo_yyyymmdd))

    return (fcst_section_hrs_list, zero_starts, lengths, subdirectories, yearmonthdays)


def _wgrib2_append(in_file, out_file):
    """Run the equivalent of the command-line:
         wgrib2 in_file -append -grib out_file

    :param :py:class:`pathlib.Path` in_file:
    :param :py:class:`pathlib.Path` out_file:
    """
    args = "-append -grib"
    infile = os.fspath(in_file)
    outfile = os.fspath(out_file)
    # pywgrib2_xr.wgrib() args must be strings,
    # and files must be freed after use to close them
    pywgrib2_xr.wgrib(infile, *args.split(), outfile)
    pywgrib2_xr.free_files(infile, outfile)


def _rotate_grib_wind(fcst_section_hrs, config):
    """Use wgrib2 to consolidate each hour's u and v wind components into a
    single file and then rotate the wind direction to geographical coordinates.

    :param dict fcst_section_hrs:
    :param dict config:
    """
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    grid_desc = config["weather"]["grid desc"]
    for day_fcst, _, start_hr, end_hr in fcst_section_hrs.values():
        for fhour in range(start_hr, end_hr + 1):
            # Set up directories and files
            sfhour = f"{fhour:03d}"
            outuv = grib_dir / Path(day_fcst, sfhour, "UV.grib")
            outuvrot = grib_dir / Path(day_fcst, sfhour, "UVrot.grib")

            # Delete residual instances of files that are created so that
            # function can be re-run cleanly
            outuv.unlink(missing_ok=True)
            outuvrot.unlink(missing_ok=True)

            # Consolidate u and v wind component values into one file
            grib_vars = config["weather"]["download"]["2.5 km"]["grib variables"]
            wind_var_names = [
                var_name
                for var_name in grib_vars
                if var_name.startswith("UGRD") or var_name.startswith("VGRD")
            ]
            hour_dir = grib_dir / Path(day_fcst, sfhour)
            for wind_var in wind_var_names:
                wind_file = list(hour_dir.glob(f"*{wind_var}*.grib2"))[0]
                _wgrib2_append(wind_file, outuv)

            # Remap wind vectors from grid to earth orientation
            args = f"-new_grid_winds earth -new_grid {grid_desc}"
            infile = os.fspath(outuv)
            outfile = os.fspath(outuvrot)
            # pywgrib2_xr.wgrib() args must be strings,
            # and files must be freed after use to close them
            pywgrib2_xr.wgrib(infile, *args.split(), outfile)
            pywgrib2_xr.free_files(infile, outfile)
            outuv.unlink(missing_ok=True)
    logger.debug("consolidated and rotated wind components")


def _collect_grib_scalars(fcst_section_hrs, config):
    """Use wgrib2 to consolidate each hour's scalar variables into a single file.

    :param dict fcst_section_hrs:
    :param dict config:
    """
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    for day_fcst, _, start_hr, end_hr in fcst_section_hrs.values():
        for fhour in range(start_hr, end_hr + 1):
            # Set up directories and files
            sfhour = f"{fhour:03d}"
            outscalar = grib_dir / Path(day_fcst, sfhour, "scalar.grib")

            # Delete residual instances of files that are created so that
            # function can be re-run cleanly
            outscalar.unlink(missing_ok=True)

            # Consolidate scalar variables into one file
            grib_vars = config["weather"]["download"]["2.5 km"]["grib variables"]
            scalar_var_names = [
                var_name
                for var_name in grib_vars
                if not (var_name.startswith("UGRD") or var_name.startswith("VGRD"))
            ]
            hour_dir = grib_dir / Path(day_fcst, sfhour)
            for var_name in scalar_var_names:
                var_file = list(hour_dir.glob(f"*{var_name}*.grib2"))[0]
                _wgrib2_append(var_file, outscalar)
    logger.debug("consolidated scalar variables")


def _concat_hourly_gribs(ymd, fcst_section_hrs, config):
    """Concatenate in hour order the wind velocity components
    and scalar variables from hourly files into a daily file.

    Also create the zero-hour file that is used to initialize the
    calculation of instantaneous values from the forecast accumulated
    values.

    :param str ymd:
    :param dict fcst_section_hrs:
    :param dict config:

    :rtype: tuple
    """
    grib_dir = Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
    ops_dir = Path(config["weather"]["ops dir"])
    outgrib = ops_dir / f"oper_allvar_{ymd}.grib"
    outzeros = ops_dir / f"oper_000_{ymd}.grib"

    # Delete residual instances of files that are created so that
    # function can be re-run cleanly
    outgrib.unlink(missing_ok=True)
    outzeros.unlink(missing_ok=True)

    for day_fcst, realstart, start_hr, end_hr in fcst_section_hrs.values():
        for fhour in range(start_hr, end_hr + 1):
            # Set up directories and files
            sfhour = f"{fhour:03d}"
            outuvrot = grib_dir / Path(day_fcst, sfhour, "UVrot.grib")
            outscalargrid = grib_dir / Path(day_fcst, sfhour, "scalar.grib")
            out_file = outzeros if fhour == start_hr and realstart == -1 else outgrib
            _wgrib2_append(outuvrot, out_file)
            outuvrot.unlink(missing_ok=True)
            _wgrib2_append(outscalargrid, out_file)
            outscalargrid.unlink(missing_ok=True)
    logger.debug(
        f"concatenated variables in hour order from hourly files to daily "
        f"file {outgrib}"
    )
    logger.debug(
        f"created zero-hour file for initialization of accumulated -> "
        f"instantaneous values calculations: {outzeros}"
    )
    return outgrib, outzeros


def _crop_to_watersheds(ymd, ist, ien, jst, jen, outgrib, outzeros, config):
    """Crop the grid to the sub-region of GEM 2.5km operational forecast
    grid that encloses the SalishSeaCast NEMO model grid.

    :param str ymd:
    :param int ist:
    :param int ien:
    :param int jst:
    :param int jen:
    :param :py:class:`pathlib.Path` outgrib:
    :param :py:class:`pathlib.Path` outzeros:
    :param dict config:

    :rtype: tuple
    """
    ops_dir = Path(config["weather"]["ops dir"])
    newgrib = ops_dir / f"oper_allvar_small_{ymd}.grib"
    newzeros = ops_dir / f"oper_000_small_{ymd}.grib"
    _wgrib2_crop(outgrib, ien, ist, jen, jst, newgrib)
    outgrib.unlink(missing_ok=True)
    logger.debug(f"cropped hourly file to watersheds sub-region: {newgrib}")
    _wgrib2_crop(outzeros, ien, ist, jen, jst, newzeros)
    outzeros.unlink(missing_ok=True)
    logger.debug(f"cropped zero-hour file to watersheds sub-region: {newzeros}")
    return newgrib, newzeros


def _wgrib2_crop(in_file, ien, ist, jen, jst, out_file):
    """Run the equivalent of the command-line:
         wgrib2 in_file -ijsmall_grib ist:ien jst:jen out_file

    :param :py:class:`pathlib.Path` in_file:
    :param int ien:
    :param int ist:
    :param int jen:
    :param int jst:
    :param :py:class:`pathlib.Path` out_file:

    :rtype: tuple
    """
    args = f"-ijsmall_grib {ist}:{ien} {jst}:{jen}"
    infile = os.fspath(in_file)
    outfile = os.fspath(out_file)
    # pywgrib2_xr.wgrib() args must be strings,
    # and files must be freed after use to close them
    pywgrib2_xr.wgrib(infile, *args.split(), outfile)
    pywgrib2_xr.free_files(infile, outfile)


def _make_netCDF_files(config, ymd, subdir, outgrib, outzeros):
    """Convert the GRIB files to netcdf (classic) files."""
    OPERdir = config["weather"]["ops dir"]
    # filename_tmpl = config["weather"]["file template"]
    # # TODO: Fix this - ymd is already formatted at "y%Ym%md%d"
    # #       so we have to hack the filename tmeplate
    # filename_tmpl.replace(":y%Ym%md%d", "ymd")
    # outnetcdf = os.path.join(OPERdir, subdir, filename_tmpl.format(ymd))
    outnetcdf = os.path.join(OPERdir, subdir, f"RlatLon_{ymd}.nc")
    out0netcdf = os.path.join(OPERdir, subdir, f"oper_000_{ymd}.nc")
    wgrib2 = config["weather"]["wgrib2"]
    cmd = [wgrib2, outgrib, "-netcdf", outnetcdf]
    lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
    logger.debug(f"created hourly netCDF classic file: {outnetcdf}")
    lib.fix_perms(outnetcdf, grp_name=config["file group"])
    cmd = [wgrib2, outzeros, "-netcdf", out0netcdf]
    lib.run_in_subprocess(cmd, wgrib2_logger.debug, logger.error)
    logger.debug(f"created zero-hour netCDF classic file: {out0netcdf}")
    os.remove(outgrib)
    os.remove(outzeros)
    return outnetcdf, out0netcdf


def _calc_instantaneous(outnetcdf, out0netcdf, ymd, flen, zstart, axs):
    """Calculate instantaneous values from the forecast accumulated values
    for the precipitation and radiation variables.
    """
    data = nc.Dataset(outnetcdf, "r+")
    data0 = nc.Dataset(out0netcdf, "r")
    acc_vars = ("APCP_surface", "DSWRF_surface", "DLWRF_surface")
    acc_values = {"acc": {}, "zero": {}, "inst": {}}
    for var in acc_vars:
        acc_values["acc"][var] = data.variables[var][:]
        acc_values["zero"][var] = data0.variables[var][:]
        acc_values["inst"][var] = np.empty_like(acc_values["acc"][var])
    data0.close()
    os.remove(out0netcdf)

    axs[1, 0].plot(acc_values["acc"]["APCP_surface"][:, SandI, SandJ], "o-")

    for var in acc_vars:
        acc_values["inst"][var][0] = (
            acc_values["acc"][var][0] - acc_values["zero"][var][0]
        ) / 3600
        for realhour in range(1, flen):
            if realhour in zstart:
                acc_values["inst"][var][realhour] = (
                    acc_values["acc"][var][realhour] / 3600
                )
            else:
                acc_values["inst"][var][realhour] = (
                    acc_values["acc"][var][realhour]
                    - acc_values["acc"][var][realhour - 1]
                ) / 3600

    axs[1, 1].plot(acc_values["inst"]["APCP_surface"][:, SandI, SandJ], "o-", label=ymd)

    for var in acc_vars:
        data.variables[var][:] = acc_values["inst"][var][:]
    data.close()
    logger.debug(
        "calculated instantaneous values from forecast accumulated values "
        "for precipitation and long- & short-wave radiation"
    )


def _change_to_NEMO_variable_names(outnetcdf, axs, ip):
    """Rename variables to match NEMO naming conventions."""
    data = nc.Dataset(outnetcdf, "r+")
    data.renameDimension("time", "time_counter")
    data.renameVariable("latitude", "nav_lat")
    data.renameVariable("longitude", "nav_lon")
    data.renameVariable("time", "time_counter")
    time_counter = data.variables["time_counter"]
    time_counter.time_origin = arrow.get("1970-01-01 00:00:00").format(
        "YYYY-MMM-DD HH:mm:ss"
    )
    data.renameVariable("UGRD_10maboveground", "u_wind")
    data.renameVariable("VGRD_10maboveground", "v_wind")
    data.renameVariable("DSWRF_surface", "solar")
    data.renameVariable("SPFH_2maboveground", "qair")
    data.renameVariable("DLWRF_surface", "therm_rad")
    data.renameVariable("TMP_2maboveground", "tair")
    data.renameVariable("PRMSL_meansealevel", "atmpres")
    data.renameVariable("APCP_surface", "precip")
    data.renameVariable("TCDC_surface", "percentcloud")
    logger.debug("changed variable names to their NEMO names")

    Temp = data.variables["tair"][:]
    axs[0, ip].pcolormesh(Temp[0])
    axs[0, ip].set_xlim([0, Temp.shape[2]])
    axs[0, ip].set_ylim([0, Temp.shape[1]])
    axs[0, ip].plot(SandI, SandJ, "wo")

    if ip == 0:
        label = "day 1"
    elif ip == 1:
        label = "day 2"
    else:
        label = "day 3"
    humid = data.variables["qair"][:]
    axs[1, 2].plot(humid[:, SandI, SandJ], "-o")
    solar = data.variables["solar"][:]
    axs[2, 0].plot(solar[:, SandI, SandJ], "-o", label=label)
    longwave = data.variables["therm_rad"][:]
    axs[2, 1].plot(longwave[:, SandI, SandJ], "-o")
    pres = data.variables["atmpres"][:]
    axs[2, 2].plot(pres[:, SandI, SandJ], "-o")
    uwind = data.variables["u_wind"][:]
    axs[3, 0].plot(uwind[:, SandI, SandJ], "-o")
    vwind = data.variables["v_wind"][:]
    axs[3, 1].plot(vwind[:, SandI, SandJ], "-o")
    axs[3, 2].plot(
        np.sqrt(uwind[:, SandI, SandJ] ** 2 + vwind[:, SandI, SandJ] ** 2), "-o"
    )

    data.close()


def _netCDF4_deflate(outnetcdf):
    """Run ncks in a subprocess to convert outnetcdf to netCDF4 format
    with it variables compressed with Lempel-Ziv deflation.
    """
    cmd = ["ncks", "-4", "-L4", "-O", outnetcdf, outnetcdf]
    try:
        lib.run_in_subprocess(cmd, logger.debug, logger.error)
        logger.debug(f"netCDF4 deflated {outnetcdf}")
    except WorkerError:
        raise


def _set_up_plotting():
    fig = matplotlib.figure.Figure(figsize=(10, 15))
    axs = np.empty((4, 3), dtype="object")
    axs[0, 0] = fig.add_subplot(4, 3, 1)
    axs[0, 0].set_title("Air Temp. 0 hr")
    axs[0, 1] = fig.add_subplot(4, 3, 2)
    axs[0, 1].set_title("Air Temp. +1 day")
    axs[0, 2] = fig.add_subplot(4, 3, 3)
    axs[0, 2].set_title("Air Temp. +2 days")
    axs[1, 0] = fig.add_subplot(4, 3, 4)
    axs[1, 0].set_title("Accumulated Precip")
    axs[1, 1] = fig.add_subplot(4, 3, 5)
    axs[1, 1].set_title("Instant. Precip")
    axs[1, 2] = fig.add_subplot(4, 3, 6)
    axs[1, 2].set_title("Humidity")
    axs[2, 0] = fig.add_subplot(4, 3, 7)
    axs[2, 0].set_title("Solar Rad")
    axs[2, 1] = fig.add_subplot(4, 3, 8)
    axs[2, 1].set_title("Longwave Down")
    axs[2, 2] = fig.add_subplot(4, 3, 9)
    axs[2, 2].set_title("Sea Level Pres")
    axs[3, 0] = fig.add_subplot(4, 3, 10)
    axs[3, 0].set_title("u wind")
    axs[3, 1] = fig.add_subplot(4, 3, 11)
    axs[3, 1].set_title("v wind")
    axs[3, 2] = fig.add_subplot(4, 3, 12)
    axs[3, 2].set_title("Wind Speed")
    return fig, axs


if __name__ == "__main__":
    main()
