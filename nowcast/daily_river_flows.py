"""
    Module for calculating daily river flows
"""
import functools
import warnings
from pathlib import Path

import arrow
import numpy as np
import pandas as pd
import xarray as xr

from salishsea_tools import rivertools
from salishsea_tools import river_202108 as rivers


watershed_names = [
    "bute",
    "evi_n",
    "jervis",
    "evi_s",
    "howe",
    "jdf",
    "skagit",
    "puget",
    "toba",
    "fraser",
]
watershed_from_river = {
    "bute": {"primary": 2.015},
    "jervis": {"primary": 8.810, "secondary": 140.3},
    "howe": {"primary": 2.276},
    "jdf": {"primary": 8.501},
    "evi_n": {"primary": 10.334},
    "evi_s": {"primary": 24.60},
    "toba": {"primary": 0.4563, "secondary": 14.58},
    "skagit": {"primary": 1.267, "secondary": 1.236},
    "puget": {"primary": 8.790, "secondary": 29.09},
    "fraser": {"primary": 1.161, "secondary": 162, "nico_into_fraser": 0.83565},
}
rivers_for_watershed = {
    "bute": {"primary": "Homathko_Mouth", "secondary": None},
    "evi_n": {"primary": "Salmon_Sayward", "secondary": None},
    "jervis": {"primary": "Clowhom_ClowhomLake", "secondary": "RobertsCreek"},
    "evi_s": {"primary": "Englishman", "secondary": None},
    "howe": {"primary": "Squamish_Brackendale", "secondary": None},
    "jdf": {"primary": "SanJuan_PortRenfrew", "secondary": None},
    "skagit": {"primary": "Skagit_MountVernon", "secondary": "Snohomish_Monroe"},
    "puget": {"primary": "Nisqually_McKenna", "secondary": "Greenwater_Greenwater"},
    "toba": {"primary": "Homathko_Mouth", "secondary": "Theodosia"},
    "fraser": {"primary": "Fraser", "secondary": "Nicomekl_Langley"},
}
theodosia_from_diversion_only = 1.429  # see TheodosiaWOScotty
matching_dictionary = {
    "Englishman": "Salmon_Sayward",
    "Theodosia": "Clowhom_ClowhomLake",
    "RobertsCreek": "Englishman",
    "Salmon_Sayward": "Englishman",
    "Squamish_Brackendale": "Homathko_Mouth",
    "SanJuan_PortRenfrew": "Englishman",
    "Nisqually_McKenna": "Snohomish_Monroe",
    "Snohomish_Monroe": "Skagit_MountVernon",
    "Skagit_MountVernon": "Snohomish_Monroe",
    "Homathko_Mouth": "Squamish_Brackendale",
    "Nicomekl_Langley": "RobertsCreek",
    "Greenwater_Greenwater": "Snohomish_Monroe",
    "Clowhom_ClowhomLake": "Theodosia_Diversion",
}
backup_dictionary = {"SanJuan_PortRenfrew": "RobertsCreek", "Theodosia": "Englishman"}
patching_dictionary = {
    # TODO: add config tests to ensure that all lists end with "persist"
    "Englishman": ["fit", "persist"],
    "Fraser": ["persist"],
    "Theodosia": ["fit", "backup", "persist"],
    "RobertsCreek": ["fit", "persist"],
    "Salmon_Sayward": ["fit", "persist"],
    "Squamish_Brackendale": ["fit", "persist"],
    "SanJuan_PortRenfrew": ["fit", "backup", "persist"],
    "Nisqually_McKenna": ["fit", "persist"],
    "Snohomish_Monroe": ["fit", "persist"],
    "Skagit_MountVernon": ["fit", "persist"],
    "Homathko_Mouth": ["fit", "persist"],
    "Nicomekl_Langley": ["fit", "persist"],
    "Greenwater_Greenwater": ["fit", "persist"],
    "Clowhom_ClowhomLake": ["fit", "persist"],
}
persist_until = {
    # number of days to persist last observation for before switching to fitting strategies
    "Englishman": 0,
    "Fraser": 10_000,  # always persist
    "Theodosia": 0,
    "RobertsCreek": 0,
    "Salmon_Sayward": 0,
    "Squamish_Brackendale": 0,
    "SanJuan_PortRenfrew": 0,
    "Nisqually_McKenna": 4,
    "Snohomish_Monroe": 0,
    "Skagit_MountVernon": 3,
    "Homathko_Mouth": 1,
    "Nicomekl_Langley": 0,
    "Greenwater_Greenwater": 1,
    "Clowhom_ClowhomLake": 2,
}


def _parse_long_csv_line(line):
    """pandas .csv parser helper to handle lines with extra columns.

    Returns the first 4 columns from the line.

    :param list line:

    :rtype: list
    """
    return line[:4]


_read_river_csv = functools.partial(
    # Customize pandas.read_csv() with the args we always want to use for reading river discharge
    # .csv files
    pd.read_csv,
    header=None,
    delim_whitespace=True,
    index_col=False,
    names=["year", "month", "day", "flow"],
    engine="python",
    on_bad_lines=_parse_long_csv_line,
)


def _set_date_as_index(river_flow):
    """Set date as dataframe index and drop year, month & day columns used to construct date.

    :param :py:class:`pandas.Dataframe` river_flow:
    """
    river_flow["date"] = pd.to_datetime(river_flow.drop(columns="flow"))
    river_flow.set_index("date", inplace=True)
    river_flow.drop(columns=["year", "month", "day"], inplace=True)


def _read_river(river_name, ps, config):
    """Read daily average discharge data for river_name from river flow file.

    :param str river_name:
    :param str ps: "primary" or "secondary"
    :param dict config:

    :rtype: :py:class:`pandas.Dataframe`
    """
    filename = Path(config["rivers"]["SOG river files"][river_name.replace("_", "")])
    with warnings.catch_warnings():
        # ignore ParserWarning until https://github.com/pandas-dev/pandas/issues/49279 is fixed
        warnings.simplefilter("ignore")
        river_flow = _read_river_csv(filename)
    _set_date_as_index(river_flow)
    if ps == "primary":
        river_flow = river_flow.rename(columns={"flow": "Primary River Flow"})
    elif ps == "secondary":
        river_flow = river_flow.rename(columns={"flow": "Secondary River Flow"})
    return river_flow


def _read_river_Theodosia(config):
    """Read daily average discharge observations for 3 parts of Theodosia River
    from river flow files, and combine them to get total.

    :param dict config:

    :rtype: :py:class:`pandas.Dataframe`
    """
    part_names = ("TheodosiaScotty", "TheodosiaBypass", "TheodosiaDiversion")
    with warnings.catch_warnings():
        # ignore ParserWarning until https://github.com/pandas-dev/pandas/issues/49279 is fixed
        warnings.simplefilter("ignore")
        parts = [
            _read_river_csv(Path(config["rivers"]["SOG river files"][part_name]))
            for part_name in part_names
        ]
    for part, part_name in zip(parts, part_names):
        _set_date_as_index(part)
        part.rename(columns={"flow": part_name.replace("Theodosia", "")}, inplace=True)

    # Calculate discharge from 3 gauged parts of river above control infrastructure
    theodosia = (parts[2].merge(parts[1], how="outer", on="date")).merge(
        parts[0], how="outer", on="date"
    )
    theodosia["Secondary River Flow"] = (
        theodosia["Scotty"] + theodosia["Diversion"] - theodosia["Bypass"]
    )

    # Alternative discharge calculation from gauged diversion part
    # Used for dates before Scotty part was gauged, or in the event of missing obs
    parts[2]["FlowFromDiversion"] = parts[2].Diversion * theodosia_from_diversion_only
    theodosia = theodosia.merge(parts[2], how="outer", on="date", sort=True)
    theodosia["Secondary River Flow"].fillna(
        theodosia["FlowFromDiversion"], inplace=True
    )

    theodosia.drop(
        ["Diversion_x", "Bypass", "Scotty", "Diversion_y", "FlowFromDiversion"],
        axis=1,
        inplace=True,
    )
    return theodosia


def _patch_fitting(river_flow, fit_from_river_name, obs_date, gap_length, config):
    """
    :param :py:class:`pandas.Dataframe` river_flow:
    :param str fit_from_river_name:
    :param :py:class:`arrow.Arrow` obs_date:
    :param int gap_length:
    :param dict config:

    :rtype: float
    """
    fit_from_river_flow = _read_river(fit_from_river_name, "primary", config)
    obs_yyyymmdd = obs_date.format("YYYY-MM-DD")
    try:
        fit_from_river_flow.loc[obs_yyyymmdd]
    except KeyError:
        # If river to fit from is missing obs date, the fit is a failure
        flux = np.nan
        return flux

    fit_duration = 7  # number of days we use to fit against
    fit_dates = arrow.Arrow.range(
        "day",
        obs_date.shift(days=-fit_duration - gap_length),
        obs_date.shift(days=-1 - gap_length),
    )
    try:
        ratio = sum(
            river_flow.loc[yyyymmdd := day.format("YYYY-MM-DD"), river_flow.columns[0]]
            / fit_from_river_flow.loc[yyyymmdd, river_flow.columns[0]]
            for day in fit_dates
        )
    except KeyError:
        # If either river is missing a value during the fitting period, the fit is a failure
        flux = np.nan
        return flux

    flux = (ratio / fit_duration) * fit_from_river_flow.loc[
        obs_yyyymmdd, river_flow.columns[0]
    ]
    return flux


def _patch_missing_obs(river_name, river_flow, obs_date, config):
    """
    :param str river_name:
    :param :py:class:`pandas.Dataframe` river_flow:
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: float

    :raises: :py:exc:`ValueError`
    """
    last_obs_date = arrow.get(river_flow.iloc[-1].name)
    if last_obs_date > obs_date:
        # We can only handle patching discharge values for dates beyond the end of the observations
        # time series.
        # Use Susan's MakeDailyNCFiles notebook if you need to patch discharges
        # within the time series.
        raise ValueError(
            f"obs_date={obs_date.format('YYYY-MM-DD')} is not beyond end of time series at "
            f"{last_obs_date.format('YYYY-MM-DD')}"
        )

    gap_length = (obs_date - last_obs_date).days
    print(gap_length)
    if gap_length <= persist_until[river_name]:
        # Handle rivers for which Susan's statistical investigation showed that persistence
        # is better than fitting for short periods of missing observations.
        print("persist")
        flux = river_flow.iloc[-1, -1]
        return flux

    for fit_type in patching_dictionary[river_name]:
        print(fit_type)
        match fit_type:
            case "persist":
                flux = river_flow.iloc[-1, -1]
                return flux
            case "fit":
                fit_from_river_name = matching_dictionary[river_name]
            case "backup":
                fit_from_river_name = backup_dictionary[river_name]
            case _:
                # TODO: add config tests to ensure that patching_dictionary has only valid keys
                #       making this case unnecessary
                raise ValueError("typo in fit list")
        flux = _patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )
        if not np.isnan(flux):
            return flux


def _get_river_flow(river_name, river_df, obs_date, config):
    """
    :param str river_name:
    :param :py:class:`pandas.Dataframe` river_df:
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: float
    """
    try:
        river_flow = river_df.loc[obs_date.format("YYYY-MM-DD"), river_df.columns[0]]
    except KeyError:
        # No discharge obs for date, so patch
        print(river_name, " need to patch")
        river_flow = _patch_missing_obs(river_name, river_df, obs_date, config)
    return river_flow


def _do_a_pair(
    watershed_name,
    obs_date,
    primary_river_name,
    config,
    secondary_river_name=None,
):
    """
    :param str watershed_name:
    :param :py:class:`arrow.Arrow` obs_date:
    :param str primary_river_name:
    :param dict config:
    :param str or :py:class:`NoneType` secondary_river_name:

    :rtype: float
    """
    primary_river = _read_river(primary_river_name, "primary", config)
    primary_flow = _get_river_flow(primary_river_name, primary_river, obs_date, config)
    watershed_flow = primary_flow * watershed_from_river[watershed_name]["primary"]
    if secondary_river_name is None:
        return watershed_flow

    secondary_river = (
        _read_river_Theodosia(config)
        if secondary_river_name == "Theodosia"
        else _read_river(secondary_river_name, "secondary", config)
    )
    secondary_flow = _get_river_flow(
        secondary_river_name, secondary_river, obs_date, config
    )
    watershed_flow += secondary_flow * watershed_from_river[watershed_name]["secondary"]
    return watershed_flow


def _do_fraser(obs_date, config):
    """
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: tuple
    """
    primary_river = _read_river("Fraser", "primary", config)
    primary_flow = _get_river_flow("Fraser", primary_river, obs_date, config)

    secondary_river = _read_river("Nicomekl_Langley", "secondary", config)
    secondary_flow = _get_river_flow(
        "Nicomekl_Langley", secondary_river, obs_date, config
    )

    Fraser_flux = (
        # Fraser at Hope plus its portion that is proxy for glacial runoff dominated rivers
        # (e.g. Harrison) that flow into Fraser below Hope
        primary_flow * watershed_from_river["fraser"]["primary"]
        # Proxy for rainfall runoff dominated rivers that flow into Fraser below Hope
        + secondary_flow
        * watershed_from_river["fraser"]["secondary"]
        * watershed_from_river["fraser"]["nico_into_fraser"]
    )
    secondary_flux = (
        # Proxy for rainfall runoff dominated rivers in the Fraser Basin that flow into SoG
        secondary_flow
        * watershed_from_river["fraser"]["secondary"]
        * (1 - watershed_from_river["fraser"]["nico_into_fraser"])
    )

    return Fraser_flux, secondary_flux


def _calc_watershed_flows(obs_date, config):
    """
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: dict
    """

    flows = {}
    for watershed_name in watershed_names:
        print(watershed_name)
        if watershed_name == "fraser":
            flows["fraser"], flows["non_fraser"] = _do_fraser(obs_date, config)
            print(flows["fraser"])
        else:
            if rivers_for_watershed[watershed_name]["secondary"] is None:
                print("no secondary")
            flows[watershed_name] = _do_a_pair(
                watershed_name,
                obs_date,
                rivers_for_watershed[watershed_name]["primary"],
                config,
                rivers_for_watershed[watershed_name]["secondary"],
            )
            print(flows[watershed_name])

    print("files read")

    return flows


def _get_area(config):
    """
    :param dict config:

    :rtype: :py:class:`numpy.ndarray`
    """
    # TODO: Make getting the coordinates less convoluted
    grid_dir = Path(config["run"]["enabled hosts"]["salish-nowcast"]["grid dir"])
    if not grid_dir.exists():
        # TODO: This should be unnecessary in worker code
        grid_dir = Path("../../grid/")
    coords_file = grid_dir / config["run types"]["nowcast-green"]["coordinates"]
    with xr.open_dataset(coords_file, decode_times=False) as ds:
        area = ds.e1t[0] * ds.e2t[0]
    return area


def _create_runoff_array(flows, horz_area):
    """
    :param dict flows:
    :param :py:class:`numpy.ndarray` horz_area:

    :rtype: :py:class:`numpy.ndarray`
    """
    runoff_array = np.zeros((horz_area.shape[0], horz_area.shape[1]))
    # rivertools.fill_runoff_array() needs depth and temperature arrays,
    # but we don't return them
    runoff_depth = np.ones_like(runoff_array)
    runoff_temperature = np.empty_like(runoff_array)

    for watershed_name in watershed_names:
        if watershed_name == "fraser":
            fraser_ratio = rivers.prop_dict["fraser"]["Fraser"]["prop"]
            for key in rivers.prop_dict[watershed_name]:
                flux, subarea = (
                    (flows["fraser"], fraser_ratio)
                    if key == "Fraser"
                    else (flows["non_fraser"], 1 - fraser_ratio)
                )
                river = rivers.prop_dict["fraser"][key]
                runoff_array, _ = rivertools.fill_runoff_array(
                    flux * river["prop"] / subarea,
                    river["i"],
                    river["di"],
                    river["j"],
                    river["dj"],
                    river["depth"],
                    runoff_array,
                    runoff_depth,
                    horz_area,
                )
        else:
            flow = flows[watershed_name]
            runoff_array, _, _ = rivertools.put_watershed_into_runoff(
                "constant",
                horz_area,
                flow,
                runoff_array,
                runoff_depth,
                runoff_temperature,
                rivers.prop_dict[watershed_name],
            )
    return runoff_array


def _calc_runoff_dataset(obs_date, runoff_array, config):
    """
    :param :py:class:`arrow.Arrow` obs_date:
    :param :py:class:`numpy.ndarray` runoff_array:
    :param dict config:

    :rtype: :py:class:`xarray.Dataset`
    """
    coords = {
        "time_counter": pd.to_datetime([obs_date.format("YYYY-MM-DD")]),
        "y": np.arange(runoff_array.shape[0]),
        "x": np.arange(runoff_array.shape[1]),
    }
    runoff_da = xr.DataArray(
        # expand runoff array to include time coordinate
        data=np.expand_dims(runoff_array, axis=0),
        coords=coords,
        attrs={
            "standard_name": "runoff_flux",
            "long_name": "River Runoff Flux",
            "units": "kg m-2 s-1",
        },
    )
    runoff_ds = xr.Dataset(
        data_vars={"rorunoff": runoff_da},
        coords=coords,
        attrs={
            "creator_email": "sallen@eoas.ubc.ca",
            "creator_name": "SalishSeaCast Project contributors",
            "creator_url": "https://github.com/SalishSeaCast/SalishSeaNowcast/blob/main/nowcast/workers/make_runoff_file.py",
            "institution": "UBC EOAS",
            "institution_fullname": (
                "Earth, Ocean & Atmospheric Sciences, University of British Columbia"
            ),
            "title": f"River Runoff Fluxes for {obs_date.format('YYYY-MM-DD')}",
            "summary": (
                f"Day-average river runoff fluxes calculated for {obs_date.format('YYYY-MM-DD')} "
                f"on v202108 bathymetry. "
                f"The runoff fluxes are calculated from day-averaged discharge (1 day lagged) "
                f"observations from gauged rivers across the SalishSeaCast model domain using "
                f"fits developed by Susan Allen."
            ),
            "development_notebook": "https://github.com/SalishSeaCast/tools/blob/main/I_ForcingFiles/Rivers/ProductionDailyRiverNCfile.ipynb",
            "rivers_watersheds_proportions": config["rivers"]["prop_dict module"],
            "history": (
                f"[{arrow.now('local').format('ddd YYYY-MM-DD HH:mm:ss ZZ')}] "
                f"python3 -m nowcast.workers.make_runoff_file $NOWCAST_YAML "
                f"--run-date {obs_date.format('YYYY-MM-DD')}"
            ),
        },
    )
    return runoff_ds


def _write_netcdf(runoff_ds, obs_date, config):
    """
    :param :py:class:`xarray.Dataset` runoff_ds:
    :param :py:class:`arrow.Arrow` obs_date:
    :param dict config:

    :rtype: :py:class:`pathlib.Path`
    """
    encoding = {
        "time_counter": {
            "calendar": "gregorian",
            "units": "days since 2007-01-01",
        },
    }
    encoding.update(
        {var: {"zlib": True, "complevel": 4} for var in runoff_ds.data_vars}
    )
    rivers_dir = Path(config["rivers"]["rivers dir"])
    # TODO: Change from hard-coded to config item in worker;
    #       hard-coded here to avoid disrupting automation
    # filename_tmpl = config["rivers"]["file template"]
    filename_tmpl = "R202108Dailies_{:y%Ym%md%d}.nc"
    nc_filename = filename_tmpl.format(obs_date.date())
    to_netcdf(runoff_ds, encoding, rivers_dir / nc_filename)
    print(f"created {rivers_dir / nc_filename}")
    return rivers_dir / nc_filename


def to_netcdf(runoff_ds, encoding, nc_file_path):
    """This function is separate to facilitate testing of the calling function.

    :param :py:class:`xarray.Dataset` runoff_ds:
    :param dict encoding:
    :param :py:class:`pathlib.Path` nc_file_path:
    """
    runoff_ds.to_netcdf(
        nc_file_path, encoding=encoding, unlimited_dims=("time_counter",)
    )


def make_runoff_files(dateneeded, config):
    flows = _calc_watershed_flows(dateneeded, config)
    horz_area = _get_area(config)
    runoff_array = _create_runoff_array(flows, horz_area)
    runoff_ds = _calc_runoff_dataset(dateneeded, runoff_array, config)
    nc_file_path = _write_netcdf(runoff_ds, dateneeded, config)
