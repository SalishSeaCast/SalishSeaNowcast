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
"""SalishSeaCast worker that generates a sea surface height boundary conditions file from
NOAA Neah Bay observation and forecast values.
"""
import datetime
import logging
import os
from pathlib import Path
import shutil

import arrow
import matplotlib.backends.backend_agg
import matplotlib.figure
from nemo_nowcast import NowcastWorker
import netCDF4
import numpy
import pytz
from salishsea_tools import nc_tools

from nowcast import lib, residuals

NAME = "make_ssh_files"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_ssh_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast2"},
        help="""
        Type of run to prepare open boundary sea surface height file for:
        'nowcast' means nowcast & forecast runs,
        'forecast2' means preliminary forecast run
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="""
        Date to prepare open boundary sea surface height file for.
        Defaults to today.
        """,
    )
    worker.cli.add_argument(
        "--text-file",
        type=Path,
        help="""
        Absolute path and file name of legacy file like sshNB_YYYY-MM-DD_HH.txt
        to process instead of CSV file from NOAA tarball.
        **This option is intended for hindcast boundary file creation and should be used with
        the --debug option.**
        """,
    )
    worker.cli.add_argument(
        "--archive", action="store_true", help="text-file is archive type"
    )
    worker.run(make_ssh_file, success, failure)
    return worker


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    logger.info(
        f"sea surface height boundary file for {run_date.format('YYYY-MM-DD')} {run_type} run created"
    )
    return f"success {run_type}"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    logger.critical(
        f"sea surface height boundary file for {run_date.format('YYYY-MM-DD')} {run_type} run creation failed"
    )
    return f"failure {run_type}"


def make_ssh_file(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_date = parsed_args.run_date
    yyyymmdd = run_date.format("YYYYMMDD")
    run_type = parsed_args.run_type
    ssh_forecast = "06" if run_type == "nowcast" else "00"
    logger.info(
        f"building {run_type} sea surface height boundary conditions file(s) from "
        f"{run_date.format('YYYY-MM-DD')} NOAA Neah Bay {ssh_forecast}Z "
        f"observation and forecast values"
    )
    ssh_dir = Path(config["ssh"]["ssh dir"])
    tar_file_tmpl = config["ssh"]["download"]["tar file template"]
    csv_file = Path(
        tar_file_tmpl.format(yyyymmdd=yyyymmdd, forecast=ssh_forecast)
    ).with_suffix(".csv")
    data_file = parsed_args.text_file or ssh_dir / "txt" / csv_file
    checklist = {run_type: {}}
    if parsed_args.text_file is None:
        # Store a copy of the CSV file from the NOAA tarball in the run results directory so that
        # there is definitive record of the sea surface height data that was used for the run
        _copy_csv_to_results_dir(data_file, run_date, run_type, config)
        checklist[run_type].update({"csv": os.fspath(data_file)})
    # Grab all sea surface height data in the NOAA data file
    tidal_preds_dir = Path(config["ssh"]["tidal predictions"])
    neah_bay_hourly_tides = config["ssh"]["neah bay hourly"]
    dates, sshs, fflags = residuals.NeahBay_forcing_anom(
        data_file,
        run_date.datetime
        if run_type == "nowcast"
        else run_date.shift(days=-1).datetime,
        tidal_preds_dir / neah_bay_hourly_tides,
        parsed_args.archive,
        parsed_args.text_file is None,
    )
    logger.debug(f"read sea surface height data from {data_file}")
    # Identify days with full ssh information
    dates_full = _list_full_days(dates, sshs, fflags)

    lons, lats = _get_lons_lats(config)

    if parsed_args.text_file is None:
        fig, ax = _setup_plot()

    # Loop through full days and save netcdf file(s)
    for ip, d in enumerate(dates_full):
        tc, _, sshd, fflagd = _isolate_day(d, dates, sshs, fflags)
        forecast_flag = fflagd.any()
        # Plotting
        if parsed_args.text_file is None and ip < 3:
            ax.plot(sshd, "-o", lw=2, label=d.strftime("%d-%b-%Y"))
        filepath = _save_netcdf(
            d, tc, sshd, forecast_flag, data_file, config, lats, lons
        )
        logger.info(f"wrote sea surface height boundary file: {filepath}")
        filename = os.path.basename(filepath)
        lib.fix_perms(filename, grp_name=config["file group"])
        if forecast_flag:
            if "fcst" not in checklist[run_type]:
                checklist[run_type].update({"fcst": [filepath]})
            else:
                checklist[run_type]["fcst"].append(filepath)
        else:
            checklist[run_type].update({"obs": filepath})

    _ensure_all_files_created(run_date, run_type, ssh_dir, checklist, config)

    if parsed_args.text_file is None:
        _render_plot(fig, ax, config)
    return checklist


def _copy_csv_to_results_dir(data_file, run_date, run_type, config):
    results_date = run_date if run_type == "nowcast" else run_date.shift(days=-1)
    results_dir = Path(
        config["results archive"][run_type], results_date.format("DDMMMYY").lower()
    )
    lib.mkdir(results_dir, logger, grp_name=config["file group"], exist_ok=True)
    shutil.copy2(data_file, results_dir)
    logger.debug(f"copied {data_file} to {results_dir}")


def _list_full_days(dates, surges, forecast_flags):
    """Return a list of days that have a full 24 hour data set."""
    # Check if first day is a full day
    tc, ds, _, _ = _isolate_day(dates[0], dates, surges, forecast_flags)
    if ds.shape[0] == tc.shape[0]:
        start = dates[0]
    else:
        start = dates[0] + datetime.timedelta(days=1)
    start = datetime.datetime(
        start.year, start.month, start.day, tzinfo=pytz.timezone("UTC")
    )
    # Check if last day is a full day
    tc, ds, _, _ = _isolate_day(dates[-1], dates, surges, forecast_flags)
    if ds.shape[0] == tc.shape[0]:
        end = dates[-1]
    else:
        end = dates[-1] - datetime.timedelta(days=1)
    end = datetime.datetime(end.year, end.month, end.day, tzinfo=pytz.timezone("UTC"))
    # list of dates that are full
    dates_list = [
        start + datetime.timedelta(days=i) for i in range((end - start).days + 1)
    ]
    return dates_list


def _isolate_day(day, dates, surges, forecast_flags):
    """Return array of time_counter and datetime objects over a 24 hour
    period covering one full day.
    Returns the surge and forecast_flag for that day as well
    """
    tc = numpy.arange(24)
    dates_r = []
    surge_r = []
    flag_r = []
    for t, surge, flag in zip(dates, surges, forecast_flags):
        if t.month == day.month:
            if t.day == day.day:
                dates_r.append(t)
                surge_r.append(surge)
                flag_r.append(flag)
    return tc, numpy.array(dates_r), numpy.array(surge_r), numpy.array(flag_r)


def _get_lons_lats(config):
    coords = Path(config["ssh"]["coordinates"])
    with netCDF4.Dataset(coords) as coordinates:
        lats = coordinates.variables["nav_lat"][:]
        lons = coordinates.variables["nav_lon"][:]
    logger.debug(f"loaded lats & lons from {coords}")
    return lons, lats


def _save_netcdf(day, tc, surges, forecast_flag, textfile, config, lats, lons):
    """Save the surge for a given day in a netCDF4 file."""
    # Western open boundary (JdF) grid parameter values for NEMO
    startj, endj, r = 370, 470, 1
    lengthj = endj - startj

    # netCDF4 file setup
    save_path = config["ssh"]["ssh dir"]
    filename = config["ssh"]["file template"].format(day)
    if forecast_flag:
        filepath = os.path.join(save_path, "fcst", filename)
        comment = "Prediction from Neah Bay storm surge website"
    else:
        filepath = os.path.join(save_path, "obs", filename)
        try:
            # Unlink file path in case it exists as a symlink to a fcst/
            # file created by upload_forcing worker because there was
            # no obs/ file
            os.unlink(filepath)
        except OSError:
            # File path does not exist
            pass
        comment = "Observation from Neah Bay storm surge website"
    comment = " ".join((comment, f"generated by SalishSeaCast {NAME} worker"))
    ssh_file = netCDF4.Dataset(filepath, "w")
    nc_tools.init_dataset_attrs(
        ssh_file,
        title="Neah Bay SSH hourly values",
        notebook_name="N/A",
        nc_filepath=filepath,
        comment=comment,
        quiet=True,
    )
    ssh_file.source = os.fspath(textfile)
    ssh_file.references = f"https://github.com/SalishSeaCast/SalishSeaNowcast/blob/main/nowcast/workers/{NAME}.py"
    logger.debug(f"created western open boundary file {filepath}")

    # Create netCDF dimensions
    ssh_file.createDimension("time_counter", None)
    ssh_file.createDimension("yb", 1)
    ssh_file.createDimension("xbT", lengthj * r)

    # Create netCDF variables
    time_counter = ssh_file.createVariable("time_counter", "float32", "time_counter")
    time_counter.long_name = "Time axis"
    time_counter.axis = "T"
    time_counter.units = f"hour since 00:00:00 on {day:%Y-%m-%d}"
    # Latitudes and longitudes
    nav_lat = ssh_file.createVariable("nav_lat", "float32", ("yb", "xbT"))
    nav_lat.long_name = "Latitude"
    nav_lat.units = "degrees_north"
    nav_lon = ssh_file.createVariable("nav_lon", "float32", ("yb", "xbT"))
    nav_lon.long_name = "Longitude"
    nav_lon.units = "degrees_east"
    # Sea surface height
    sossheig = ssh_file.createVariable(
        "sossheig", "float32", ("time_counter", "yb", "xbT"), zlib=True
    )
    sossheig.units = "m"
    sossheig.long_name = "Sea surface height"
    sossheig.grid = "SalishSea2"
    # Baroclinic u and v velocity components
    vobtcrtx = ssh_file.createVariable(
        "vobtcrtx", "float32", ("time_counter", "yb", "xbT"), zlib=True
    )
    vobtcrtx.units = "m/s"
    vobtcrtx.long_name = "Barotropic U Velocity"
    vobtcrtx.grid = "SalishSea2"
    vobtcrty = ssh_file.createVariable(
        "vobtcrty", "float32", ("time_counter", "yb", "xbT"), zlib=True
    )
    vobtcrty.units = "m/s"
    vobtcrty.long_name = "Barotropic V Velocity"
    vobtcrty.grid = "SalishSea2"
    # Boundary description for NEMO
    nbidta = ssh_file.createVariable("nbidta", "int32", ("yb", "xbT"), zlib=True)
    nbidta.long_name = "i grid position"
    nbidta.units = 1
    nbjdta = ssh_file.createVariable("nbjdta", "int32", ("yb", "xbT"), zlib=True)
    nbjdta.long_name = "j grid position"
    nbjdta.units = 1
    nbrdta = ssh_file.createVariable("nbrdta", "int32", ("yb", "xbT"), zlib=True)
    nbrdta.long_name = "position from boundary"
    nbrdta.units = 1

    # Load values
    for ir in range(r):
        nav_lat[0, ir * lengthj : (ir + 1) * lengthj] = lats[startj:endj, ir]
        nav_lon[0, ir * lengthj : (ir + 1) * lengthj] = lons[startj:endj, ir]
        nbidta[0, ir * lengthj : (ir + 1) * lengthj] = ir
        nbjdta[0, ir * lengthj : (ir + 1) * lengthj] = range(startj, endj)
        nbrdta[0, ir * lengthj : (ir + 1) * lengthj] = ir
    for ib in range(lengthj * r):
        sossheig[:, 0, ib] = surges
        time_counter[:] = tc + 1
        vobtcrtx[:, 0, ib] = numpy.zeros(len(surges))
        vobtcrty[:, 0, ib] = numpy.zeros(len(surges))
    ssh_file.close()
    try:
        lib.fix_perms(filepath)
    except PermissionError:
        # Can't change permissions/group because we don't own the file
        # but that's okay because we were able to write it above
        pass
    logger.debug(f"saved western open boundary file {filepath}")
    return filepath


def _ensure_all_files_created(run_date, run_type, ssh_dir, checklist, config):
    """Confirm that obs files were created. If not, create them by symlinking to fcst file for date."""
    earliest_obs_date = (
        run_date.shift(days=-4) if run_type == "nowcast" else run_date.shift(days=-5)
    )
    obs_dates = arrow.Arrow.range("days", earliest_obs_date, run_date.shift(days=-1))
    for obs_date in obs_dates:
        obs_file = config["ssh"]["file template"].format(obs_date.datetime)
        obs_path = ssh_dir / "obs" / obs_file
        if not obs_path.exists():
            fcst_relative_path = Path("..", "fcst", obs_file)
            obs_path.symlink_to(fcst_relative_path)
            logger.critical(
                f"{obs_path} was not created; using {fcst_relative_path} instead via symlink"
            )
            checklist[run_type].update({"obs": os.fspath(fcst_relative_path)})


def _setup_plot():
    fig = matplotlib.figure.Figure(figsize=(10, 4))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_title("Neah Bay SSH")
    ax.set_ylim([-1, 1])
    ax.grid()
    ax.set_ylabel("Sea surface height (m)")
    return fig, ax


def _render_plot(fig, ax, config):
    ax.legend(loc=4)
    image_file = config["ssh"]["monitoring image"]
    canvas = matplotlib.backends.backend_agg.FigureCanvasAgg(fig)
    canvas.print_figure(image_file)
    lib.fix_perms(image_file, grp_name=config["file group"])
    logger.debug(
        f"rendered sea surface height processing monitoring image: {image_file}"
    )


if __name__ == "__main__":
    main()  # pragma: no cover
