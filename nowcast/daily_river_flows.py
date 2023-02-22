"""
    Module for calculating daily river flows
"""
import functools
import warnings
from pathlib import Path

import arrow
import datetime as dt
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
        grid_dir = Path("../grid/")
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


def write_file(day, runoff, config):
    "keep it small and simple, runoff only"
    notebook = "ProductionDailyRiverNCfile.ipynb"
    coords = {
        "x": range(398),
        "y": range(898),
        "time_counter": [0],
    }
    var_attrs = {"units": "kg m-2 s-1", "long_name": "runoff_flux"}

    # set up filename
    directory = Path(config["rivers"]["rivers dir"])
    filename_tmpl = config["rivers"]["file template"]

    filename = directory / filename_tmpl.format(day.date())
    print(filename)

    netcdf_title = f"Rivers for {day.date()}"
    ds_attrs = {
        "acknowledgements": "Based on river fit",
        "creator_email": "sallen@eoas.ubc.ca",
        "creator_name": "Salish Sea MEOPAR Project Contributors",
        "creator_url": "https://salishsea-meopar-docs.readthedocs.org/",
        "institution": "UBC EOAS",
        "institution_fullname": (
            "Earth, Ocean & Atmospheric Sciences," " University of British Columbia"
        ),
        "title": netcdf_title,
        "notebook": notebook,
        "rivers_base": config["rivers"]["prop_dict module"],
        "summary": f"Daily Runoff for Bathymetry 202108",
        "history": (
            "[{}] File creation.".format(dt.datetime.today().strftime("%Y-%m-%d"))
        ),
    }
    runoffs = np.empty((1, runoff.shape[0], runoff.shape[1]))
    runoffs[0] = runoff

    da = xr.DataArray(
        data=runoffs,
        name="rorunoff",
        dims=("time_counter", "y", "x"),
        coords=coords,
        attrs=var_attrs,
    )

    ds = xr.Dataset(data_vars={"rorunoff": da}, coords=coords, attrs=ds_attrs)

    encoding = {var: {"zlib": True} for var in ds.data_vars}

    ds.to_netcdf(
        filename,
        unlimited_dims=("time_counter"),
        encoding=encoding,
    )


def make_runoff_files(dateneeded, config):
    flows = _calc_watershed_flows(dateneeded, config)
    horz_area = _get_area(config)
    runoff = _create_runoff_array(flows, horz_area)
    write_file(dateneeded, runoff, config)
