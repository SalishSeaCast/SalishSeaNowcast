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
from pathlib import Path

import arrow
import dask.distributed
import numpy
from nemo_nowcast import NowcastWorker
import xarray


NAME = "grib_to_netcdf"
logger = logging.getLogger(NAME)

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
    var_names = config["weather"]["download"]["2.5 km"]["variables"]
    dask_client = dask.distributed.Client(config["weather"]["dask cluster"])
    match run_type:
        case "nowcast+":
            logger.info(
                f"creating NEMO-atmos forcing files for {run_date.format('YYYY-MM-DD')} "
                f"nowcast and forecast runs"
            )
            # run_date dataset is composed of pieces from 3 grib forecast hours:
            #   hours 5-6 from 18Z forecast of previous day
            #   hours 1-12 from 00Z forecast of run_date day
            #   hours 1-11 from 12Z forecast of run_date day
            fcst_hr, fcst_step_range = "18", (5, 6)
            nemo_ds_18 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
                run_date_offset=-1,
            )
            fcst_hr, fcst_step_range = "00", (1, 12)
            nemo_ds_00 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
                first_step_is_offset=False,
            )
            fcst_hr, fcst_step_range = "12", (1, 11)
            nemo_ds_12 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
                first_step_is_offset=False,
            )
            nemo_ds = xarray.combine_by_coords((nemo_ds_18, nemo_ds_00, nemo_ds_12))
            nc_file = _write_netcdf(nemo_ds, run_date, run_date, run_type, config)
            _update_checklist(nc_file, checklist)

            # run_date + 1 dataset is composed of hours 11-35 from 12Z forecast
            fcst_hr, fcst_step_range = "12", (11, 35)
            nemo_ds_fcst_day_1 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
            )
            nc_file = _write_netcdf(
                nemo_ds_fcst_day_1,
                run_date.shift(days=+1),
                run_date,
                run_type,
                config,
                fcst=True,
            )
            _update_checklist(nc_file, checklist, fcst=True)

            # run_date + 2 dataset is composed of hours 35-48 from 12Z forecast
            fcst_hr, fcst_step_range = "12", (35, 48)
            nemo_ds_fcst_day_2 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
            )
            nc_file = _write_netcdf(
                nemo_ds_fcst_day_2,
                run_date.shift(days=+2),
                run_date,
                run_type,
                config,
                fcst=True,
            )
            _update_checklist(nc_file, checklist, fcst=True)

        case "forecast2":
            logger.info(
                f"creating NEMO-atmos forcing files for {run_date.format('YYYY-MM-DD')} "
                f"forecast2 run"
            )
            # run_date + 1 dataset is composed of hours 17-41 from 06Z forecast
            fcst_hr, fcst_step_range = "06", (17, 41)
            nemo_ds_fcst_day_1 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
            )
            nc_file = _write_netcdf(
                nemo_ds_fcst_day_1,
                run_date.shift(days=+1),
                run_date,
                run_type,
                config,
                fcst=True,
            )
            _update_checklist(nc_file, checklist, fcst=True)

            # run_date + 2 dataset is composed of hours 41-48 from 06Z forecast
            fcst_hr, fcst_step_range = "06", (41, 48)
            nemo_ds_fcst_day_2 = _calc_nemo_ds(
                var_names,
                run_date,
                fcst_hr,
                fcst_step_range,
                config,
            )
            nc_file = _write_netcdf(
                nemo_ds_fcst_day_2,
                run_date.shift(days=+2),
                run_date,
                run_type,
                config,
                fcst=True,
            )
            _update_checklist(nc_file, checklist, fcst=True)
    dask_client.close()
    return checklist


def _calc_nemo_ds(
    var_names,
    run_date,
    fcst_hr,
    fcst_step_range,
    config,
    run_date_offset=0,
    first_step_is_offset=True,
):
    """
    :param list var_names:
    :param :py:class:`arrow.Arrow`. run_date:
    :param tuple fcst_step_range:
    :param dict config:
    :param int run_date_offset:
    :param boolean first_step_is_offset:

    :rtype: :py:class:`xarray.Dataset`
    """
    fcst_date = run_date.shift(days=run_date_offset)
    logger.debug(
        f"creating NEMO forcing dataset from {fcst_date.format('YYYYMMDD')} {fcst_hr}Z "
        f"forecast hours {fcst_step_range[0]:03d} to {fcst_step_range[1]:03d}"
    )
    nemo_datasets = {}
    for msc_var, grib_var, nemo_var in var_names:
        grib_files = _calc_grib_file_paths(
            fcst_date,
            fcst_hr,
            fcst_step_range,
            msc_var,
            config,
        )
        nemo_datasets[nemo_var] = _calc_nemo_var_ds(
            grib_var, nemo_var, grib_files, config
        )
    nemo_ds = xarray.combine_by_coords(
        nemo_datasets.values(), combine_attrs="drop_conflicts"
    )
    nemo_ds = _calc_earth_ref_winds(nemo_ds)
    nemo_ds = _apportion_accumulation_vars(nemo_ds, first_step_is_offset, config)
    _improve_metadata(nemo_ds, config)
    return nemo_ds


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
    logger.debug(
        f"creating {msc_var} GRIB file paths list for {fcst_yyyymmdd} {fcst_hr}Z forecast hours "
        f"{fcst_step_range[0]:03d} to {fcst_step_range[1]:03d}"
    )
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
    logger.debug(f"creating {nemo_var} dataset from {grib_var} GRIB files")
    y_min, y_max = config["weather"]["download"]["2.5 km"]["lon indices"]
    x_min, x_max = config["weather"]["download"]["2.5 km"]["lat indices"]
    # We need 1 point more than the final domain size to facilitate calculation of the
    # grid rotation angle for the wind components
    y_slice = slice(y_min, y_max + 1)
    x_slice = slice(x_min, x_max + 1)
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
            "nav_lon": grib_ds.longitude,
            "nav_lat": grib_ds.latitude,
        },
        attrs=grib_ds.attrs,
    )
    nemo_ds.nav_lon.data = nemo_ds.nav_lon.data + 360
    nemo_ds = nemo_ds.drop_vars(["time", "longitude", "latitude"])
    return nemo_ds


def _calc_earth_ref_winds(nemo_ds):
    """Rotate wind components to earth-reference.

    :param :py:class:`xarray.Dataset` nemo_ds:

    :rtype: :py:class:`xarray.Dataset`
    """
    logger.debug("calculating earth-referenced wind components")
    x_angles = _calc_grid_angle(
        nemo_ds.nav_lat.data[:-1, :-1],
        nemo_ds.nav_lon.data[:-1, :-1],
        nemo_ds.nav_lat.data[:-1, 1:],
        nemo_ds.nav_lon.data[:-1, 1:],
        "x",
    )
    y_angles = _calc_grid_angle(
        nemo_ds.nav_lat.data[:-1, :-1],
        nemo_ds.nav_lon.data[:-1, :-1],
        nemo_ds.nav_lat.data[1:, :-1],
        nemo_ds.nav_lon.data[1:, :-1],
        "y",
    )
    angles = (x_angles + y_angles) / 2
    u_wind_grid = nemo_ds.u_wind[:, :-1, :-1].data
    v_wind_grid = nemo_ds.v_wind[:, :-1, :-1].data
    u_wind_earth = u_wind_grid * numpy.cos(angles) - v_wind_grid * numpy.sin(angles)
    v_wind_earth = u_wind_grid * numpy.sin(angles) + v_wind_grid * numpy.cos(angles)
    trimmed_ds = xarray.Dataset(
        data_vars={var: nemo_ds[var][:, :-1, :-1] for var in nemo_ds.data_vars},
        coords={
            "time_counter": nemo_ds.time_counter,
            "y": nemo_ds.y[:-1],
            "x": nemo_ds.x[:-1],
            "nav_lon": nemo_ds.nav_lon[:-1, :-1],
            "nav_lat": nemo_ds.nav_lat[:-1, :-1],
        },
        attrs=nemo_ds.attrs,
    )
    trimmed_ds.u_wind.data = u_wind_earth
    trimmed_ds.v_wind.data = v_wind_earth
    return trimmed_ds


def _calc_grid_angle(lat1, lon1, lat2, lon2, direction):
    """Calculate the angle (in radians) of rotation of the grid.

    Based on: https://www.movable-type.co.uk/scripts/latlong.html?from=49.243824,-121.887340&to=49.227648,-121.89631
    Susan changed the algorithm from the link above so that it is NOT bearing but the angle
    (which increases counter-clockwise) from due east.

    :param :py:class:`numpy.ndarray` lat1:
    :param :py:class:`numpy.ndarray` lon1:
    :param :py:class:`numpy.ndarray` lat2:
    :param :py:class:`numpy.ndarray` lon2:
    :param str direction: "x" or "y"

    :rtype: :py:class:`numpy.ndarray`
    """
    lat1 = numpy.deg2rad(lat1)
    lat2 = numpy.deg2rad(lat2)
    del_lon = numpy.deg2rad(lon2) - numpy.deg2rad(lon1)
    y_component = numpy.sin(del_lon) * numpy.cos(lat2)
    x_component = numpy.cos(lat1) * numpy.sin(lat2) - numpy.sin(lat1) * numpy.cos(
        lat2
    ) * numpy.cos(del_lon)
    da = numpy.pi / 2 if direction == "x" else 0
    return numpy.arctan2(-y_component, x_component) + da


def _apportion_accumulation_vars(nemo_ds, first_step_is_offset, config):
    """Apportion variables that hold quantities (e.g. precipitation, short & long wave radiation)
    accumulated over 24 hours in the GRIB files to hourly values.

    Also, when the first time step is the "previous" value for the apportioning
    (first_step_isOffset=True), drop that time step from the dataset.
    It is no longer needed for the accumulation variables,
    and always was excess baggage for the other variables.

    :param :py:class:`xarray.Dataset` nemo_ds:
    :param boolean first_step_is_offset:
    :param dict config:

    :rtype: :py:class:`xarray.Dataset`

    """
    accum_vars = config["weather"]["download"]["2.5 km"]["accumulation variables"]
    logger.debug(f"apportioning {', '.join(accum_vars)} accumulation variables")
    data_vars = (
        {var: nemo_ds[var][1:] for var in nemo_ds.data_vars}
        if first_step_is_offset
        else {var: nemo_ds[var] for var in nemo_ds.data_vars}
    )
    time_counter = (
        nemo_ds.time_counter[1:] if first_step_is_offset else nemo_ds.time_counter
    )
    apportioned_ds = xarray.Dataset(
        data_vars=data_vars,
        coords={
            "time_counter": time_counter,
            "y": nemo_ds.y,
            "x": nemo_ds.x,
            "nav_lon": nemo_ds.nav_lon,
            "nav_lat": nemo_ds.nav_lat,
        },
        attrs=nemo_ds.attrs,
    )
    for var in accum_vars:
        apportioned_data = nemo_ds[var][1:].data - nemo_ds[var][0:-1].data
        if first_step_is_offset:
            apportioned_ds[var].data = apportioned_data
        else:
            apportioned_ds[var].data[1:] = apportioned_data
        apportioned_ds[var].data /= 3600
    return apportioned_ds


def _improve_metadata(nemo_ds, config):
    """
    :param :py:class:`xarray.Dataset` nemo_ds:
    :param dict config:
    """
    nemo_ds.time_counter.attrs.update(
        {
            "axis": "T",
            "ioos_category": "Time",
            "long_name": "Time Axis",
            "standard_name": "time",
            "time_origin": "01-JAN-1970 00:00",
        }
    )
    nemo_ds.y.attrs.update(
        {
            "ioos_category": "location",
            "long_name": "Y",
            "standard_name": "y",
            "units": "count",
            "comment": (
                "Y values are grid indices in the model y-direction; "
                "geo-location data for the SalishSeaCast sub-domain of the ECCC MSC "
                "2.5km resolution HRDPS continental model grid is available in the "
                "ubcSSaSurfaceAtmosphereFieldsV22-02 dataset."
            ),
        },
    )
    nemo_ds.x.attrs.update(
        {
            "ioos_category": "location",
            "long_name": "X",
            "standard_name": "x",
            "units": "count",
            "comment": (
                "X values are grid indices in the model x-direction; "
                "geo-location data for the SalishSeaCast sub-domain of the ECCC MSC "
                "2.5km resolution HRDPS continental model grid is available in the "
                "ubcSSaSurfaceAtmosphereFieldsV22-02 dataset."
            ),
        }
    )
    nemo_ds.nav_lon.attrs.update(
        {
            "ioos_category": "location",
            "long_name": "Longitude",
        }
    )
    nemo_ds.nav_lat.attrs.update(
        {
            "ioos_category": "location",
            "long_name": "Latitude",
        }
    )
    nemo_var_names = [
        name[2] for name in config["weather"]["download"]["2.5 km"]["variables"]
    ]
    for nemo_var in nemo_var_names:
        nemo_ds[nemo_var].attrs.update(
            {
                "GRIB_numberOfPoints": "43700LL",
                "GRIB_Nx": "230LL",
                "GRIB_Ny": "190LL",
                "ioos_category": "atmospheric",
            }
        )
    nemo_ds.LHTFL_surface.attrs.update(
        {
            "standard_name": "surface_downward_latent_heat_flux",
            "units": "W m-2",
            "comment": "For Vancouver Harbour and Lower Fraser River FVCOM model",
        }
    )
    nemo_ds.PRATE_surface.attrs.update(
        {
            "standard_name": "precipitation_flux",
            "units": "kg m-2 s-1",
            "comment": "For Vancouver Harbour and Lower Fraser River FVCOM model",
        }
    )
    nemo_ds.RH_2maboveground.attrs.update(
        {
            "standard_name": "relative_humidity",
            "units": "%",
            "comment": "For Vancouver Harbour and Lower Fraser River FVCOM model",
        }
    )
    nemo_ds.atmpres.attrs.update(
        {
            "standard_name": "air_pressure_at_mean_sea_level",
            "long_name": "Air Pressure at MSL",
            "units": "Pa",
        }
    )
    nemo_ds.precip.attrs.update(
        {
            "standard_name": "precipitation_flux",
            "long_name": "Precipitation Flux",
            "units": "kg m-2 s-1",
        }
    )
    nemo_ds.qair.attrs.update(
        {
            "standard_name": "specific_humidity",
            "long_name": "Specific Humidity at 2m",
            "units": "kg kg-1",
        }
    )
    nemo_ds.solar.attrs.update(
        {
            "standard_name": "surface_downwelling_shortwave_flux_in_air",
            "long_name": "Downward Short-Wave (Solar) Radiation Flux",
            "units": "W m-2",
        }
    )
    nemo_ds.tair.attrs.update(
        {
            "standard_name": "air_temperature",
            "long_name": "Air Temperature at 2m",
            "units": "K",
        }
    )
    nemo_ds.therm_rad.attrs.update(
        {
            "standard_name": "surface_downwelling_longwave_flux_in_air",
            "long_name": "Downward Long-Wave (Thermal) Radiation Flux",
            "units": "W m-2",
        }
    )
    nemo_ds.u_wind.attrs.update(
        {
            "standard_name": "eastward_wind",
            "long_name": "U-Component of Wind at 10m",
            "units": "m s-1",
        }
    )
    nemo_ds.v_wind.attrs.update(
        {
            "standard_name": "northward_wind",
            "long_name": "V-Component of Wind at 10m",
            "units": "m s-1",
        }
    )
    nemo_ds.attrs.update(
        {
            "title": "HRDPS, Salish Sea, Atmospheric Forcing Fields, Hourly, v22-02",
            "project": "UBC EOAS SalishSeaCast",
            "institution": "UBC EOAS",
            "institution_fullname": "Earth, Ocean & Atmospheric Sciences, University of British Columbia",
            "creator_name": "SalishSeaCast Project Contributors",
            "creator_email": "sallen at eoas.ubc.ca",
            "creator_url": "https://salishsea.eos.ubc.ca",
            "drawLandMask": "over",
            "coverage_content_type": "modelResult",
        }
    )


def _write_netcdf(nemo_ds, file_date, run_date, run_type, config, fcst=False):
    """
    :param :py:class:`xarray.Dataset` nemo_ds:
    :param :py:class:`arrow.Arrow` file_date:
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type:
    :param dict config:
    :param boolean fcst:

    :rtype: :py:class:`pathlib.Path`
    """
    encoding = {
        "time_counter": {
            "calendar": "gregorian",
            "units": "seconds since 1970-01-01 00:00",
            "dtype": float,
        },
    }
    encoding.update({var: {"zlib": True, "complevel": 4} for var in nemo_ds.data_vars})
    ops_dir = Path(config["weather"]["ops dir"])
    nc_file_tmpl = config["weather"]["file template"]
    nc_filename = nc_file_tmpl.format(file_date.date())
    nc_file = Path("fcst/", nc_filename) if fcst else Path(nc_filename)
    nemo_ds.attrs.update(
        {
            "history": (
                f"[{arrow.now('local').format('ddd YYYY-MM-DD HH:mm:ss ZZ')}] "
                f"python3 -m nowcast.workers.grib_to_netcdf $NOWCAST_YAML "
                f"{run_type} --run-date {run_date.format('YYYY-MM-DD')}"
            ),
        }
    )
    _to_netcdf(nemo_ds, encoding, ops_dir / nc_file)
    logger.info(f"created {ops_dir / nc_file}")
    return nc_file


def _to_netcdf(nemo_ds, encoding, nc_file_path):
    """This function is separate to facilitate testing the calling function.

    :param :py:class:`xarray.Dataset` nemo_ds:
    :param dict encoding:
    :param :py:class:`pathlib.Path` nc_file_path:
    """
    nemo_ds.to_netcdf(nc_file_path, encoding=encoding, unlimited_dims=("time_counter",))


def _update_checklist(nc_file, checklist, fcst=False):
    """
    :param :py:class:`pathlib.Path` nc_file:
    :param dict checklist:
    :param boolean fcst:
    """
    if fcst:
        if "fcst" not in checklist:
            checklist["fcst"] = [nc_file.name]
        else:
            checklist["fcst"].append(nc_file.name)
    else:
        checklist["nowcast"] = nc_file.name


if __name__ == "__main__":
    main()
