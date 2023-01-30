"""
    Module for calculating daily river flows
"""

from pathlib import Path

import arrow
import datetime as dt
import numpy as np
import pandas as pd
import xarray as xr
import yaml

from salishsea_tools import rivertools
from salishsea_tools import river_202108 as rivers

prop_dict_name = "river_202108"

bathy_type = "b202108"


names = [
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
    "bute": {"primary": "Homathko_Mouth", "secondary": "False"},
    "evi_n": {"primary": "Salmon_Sayward", "secondary": "False"},
    "jervis": {"primary": "Clowhom_ClowhomLake", "secondary": "RobertsCreek"},
    "evi_s": {"primary": "Englishman", "secondary": "False"},
    "howe": {"primary": "Squamish_Brackendale", "secondary": "False"},
    "jdf": {"primary": "SanJuan_PortRenfrew", "secondary": "False"},
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
    "Englishman": ["fit", "persist"],
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
    "Englishman": 0,
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


def get_area(config):
    # directory = Path(config["run"]["enabled hosts"]["salish-nowcast"]["grid dir"])
    directory = Path("/home/sallen/MEOPAR/grid/")
    coords_file = directory / config["run types"]["nowcast-green"]["coordinates"]
    with xr.open_dataset(coords_file, decode_times=False) as fB:
        area = fB["e1t"][0, :] * fB["e2t"][0, :]
    return area


def read_river(river_name, ps, config):
    """Read daily average discharge data for river_name from river flow file."""
    filename = Path(config["rivers"]["SOG river files"][river_name.replace("_", "")])
    river_flow = pd.read_csv(
        filename,
        header=None,
        sep="\s+",
        index_col=False,
        names=["year", "month", "day", "flow"],
    )
    river_flow["date"] = pd.to_datetime(river_flow.drop(columns="flow"))
    river_flow.set_index("date", inplace=True)
    river_flow = river_flow.drop(columns=["year", "month", "day"])
    if ps == "primary":
        river_flow = river_flow.rename(columns={"flow": "Primary River Flow"})
    elif ps == "secondary":
        river_flow = river_flow.rename(columns={"flow": "Secondary River Flow"})
    return river_flow


def read_river_Theodosia(config):
    part1 = pd.read_csv(
        config["rivers"]["SOG river files"]["TheodosiaScotty"],
        header=None,
        sep="\s+",
        index_col=False,
        names=["year", "month", "day", "flow"],
    )
    part2 = pd.read_csv(
        config["rivers"]["SOG river files"]["TheodosiaBypass"],
        header=None,
        sep="\s+",
        index_col=False,
        names=["year", "month", "day", "flow"],
    )
    part3 = pd.read_csv(
        config["rivers"]["SOG river files"]["TheodosiaDiversion"],
        header=None,
        sep="\s+",
        index_col=False,
        names=["year", "month", "day", "flow"],
    )
    for part in [part1, part2, part3]:
        part["date"] = pd.to_datetime(part.drop(columns="flow"))
        part.set_index("date", inplace=True)
        part.drop(columns=["year", "month", "day"], inplace=True)
    part1 = part1.rename(columns={"flow": "Scotty"})
    part2 = part2.rename(columns={"flow": "Bypass"})
    part3 = part3.rename(columns={"flow": "Diversion"})
    theodosia = (part3.merge(part2, how="inner", on="date")).merge(
        part1, how="inner", on="date"
    )
    theodosia["Secondary River Flow"] = (
        theodosia["Scotty"] + theodosia["Diversion"] - theodosia["Bypass"]
    )
    part3["FlowFromDiversion"] = part3.Diversion * theodosia_from_diversion_only
    theodosia = theodosia.merge(part3, how="outer", on="date", sort=True)
    theodosia["Secondary River Flow"] = theodosia["Secondary River Flow"].fillna(
        theodosia["FlowFromDiversion"]
    )
    theodosia = theodosia.drop(
        ["Diversion_x", "Bypass", "Scotty", "Diversion_y", "FlowFromDiversion"], axis=1
    )
    return theodosia


def patch_fitting(primary_river, useriver, dateneeded, gap_length, config):
    bad = False
    firstchoice = read_river(useriver, "primary", config)
    length = 7  # number of days we use to fit against
    ratio = 0
    for day in arrow.Arrow.range(
        "day",
        dateneeded.shift(days=-length - gap_length),
        dateneeded.shift(days=-1 - gap_length),
    ):
        numer = primary_river[primary_river.index == str(day.date())].values
        denom = firstchoice[firstchoice.index == str(day.date())].values
        if (len(denom) == 1) and (len(numer) == 1):
            ratio = ratio + numer / denom
        else:
            bad = True

    if len(firstchoice[firstchoice.index == str(dateneeded.date())].values) != 1:
        bad = True

    if not bad:
        flux = (
            ratio
            / length
            * firstchoice[firstchoice.index == str(dateneeded.date())].values
        )
    else:
        flux = np.nan
    return bad, flux


def patch_gaps(name, primary_river, dateneeded, config):
    lastdata = primary_river.iloc[-1]

    # Find the length of gap assuming that the required day is beyond the time series available
    lastdata = primary_river.iloc[-1]
    if lastdata.name > dateneeded.naive:
        print("Not working at end of time series, use MakeDailyNCFiles notebook")
        stop
    else:
        day = dt.datetime(2020, 1, 2) - dt.datetime(2020, 1, 1)
        gap_length = int((dateneeded.naive - lastdata.name) / day)
        print(gap_length)

    notfitted = True
    method = 0
    while notfitted:
        if gap_length > persist_until[name]:
            fittype = patching_dictionary[name][method]
        else:
            fittype = "persist"
        print(fittype)
        if fittype == "persist":
            flux = lastdata.values
            notfitted = False
        else:
            if fittype == "fit":
                useriver = matching_dictionary[name]
            elif fittype == "backup":
                useriver = backup_dictionary[name]
            else:
                print("typo in fit list")
                stop
            bad, flux = patch_fitting(
                primary_river, useriver, dateneeded, gap_length, config
            )
            if bad:
                method = method + 1
            else:
                notfitted = False
    return flux


def do_a_pair(
    water_shed,
    watershed_from_river,
    dateneeded,
    primary_river_name,
    use_secondary,
    config,
    secondary_river_name="Null",
):
    primary_river = read_river(primary_river_name, "primary", config)

    if len(primary_river[primary_river.index == str(dateneeded.date())]) == 1:
        primary_flow = primary_river[
            primary_river.index == str(dateneeded.date())
        ].values
    else:
        print(primary_river_name, " need to patch")
        primary_flow = patch_gaps(primary_river_name, primary_river, dateneeded, config)

    if use_secondary:
        if secondary_river_name == "Theodosia":
            secondary_river = read_river_Theodosia(config)
        else:
            secondary_river = read_river(secondary_river_name, "secondary", config)

        if len(secondary_river[secondary_river.index == str(dateneeded.date())]) == 1:
            secondary_flow = secondary_river[
                secondary_river.index == str(dateneeded.date())
            ].values
        else:
            print(secondary_river_name, " need to patch")
            secondary_flow = patch_gaps(
                secondary_river_name, secondary_river, dateneeded, config
            )

        watershed_flux = (
            primary_flow * watershed_from_river[water_shed]["primary"]
            + secondary_flow * watershed_from_river[water_shed]["secondary"]
        )
    else:
        watershed_flux = primary_flow * watershed_from_river[water_shed]["primary"]

    return watershed_flux


def do_fraser(
    watershed_from_river, dateneeded, primary_river_name, secondary_river_name, config
):
    primary_river = read_river(primary_river_name, "primary", config)

    if len(primary_river[primary_river.index == str(dateneeded.date())]) == 1:
        good = True
        primary_flow = primary_river[
            primary_river.index == str(dateneeded.date())
        ].values
    else:
        good = False
        print(primary_river_name, " need to patch")
        lastdata = primary_river.iloc[-1]
        if lastdata.name > dateneeded.naive:
            print("Not working at end of time series, use MakeDailyNCFiles notebook")
            stop
        else:
            day = dt.datetime(2020, 1, 2) - dt.datetime(2020, 1, 1)
            gap_length = int((dateneeded.naive - lastdata.name) / day)
            print(gap_length)
            primary_flow = lastdata.values

    secondary_river = read_river(secondary_river_name, "secondary", config)

    if len(secondary_river[secondary_river.index == str(dateneeded.date())]) == 1:
        good = True
        secondary_flow = secondary_river[
            secondary_river.index == str(dateneeded.date())
        ].values
    else:
        good = False
        print(secondary_river_name, " need to patch")
        secondary_flow = patch_gaps(
            secondary_river_name, secondary_river, dateneeded, config
        )

    Fraser_flux = (
        primary_flow * watershed_from_river["fraser"]["primary"]
        + secondary_flow
        * watershed_from_river["fraser"]["secondary"]
        * watershed_from_river["fraser"]["nico_into_fraser"]
    )
    secondary_flux = (
        secondary_flow
        * watershed_from_river["fraser"]["secondary"]
        * (1 - watershed_from_river["fraser"]["nico_into_fraser"])
    )

    return Fraser_flux, secondary_flux


def calculate_watershed_flows(dateneeded, config):

    flows = {}
    for name in names:
        print(name)
        if rivers_for_watershed[name]["secondary"] == "False":
            print("no secondary")
            flows[name] = do_a_pair(
                name,
                watershed_from_river,
                dateneeded,
                rivers_for_watershed[name]["primary"],
                False,
                config,
            )
        elif name == "fraser":
            flows["Fraser"], flows["nonFraser"] = do_fraser(
                watershed_from_river,
                dateneeded,
                rivers_for_watershed[name]["primary"],
                rivers_for_watershed[name]["secondary"],
                config,
            )
        else:
            flows[name] = do_a_pair(
                name,
                watershed_from_river,
                dateneeded,
                rivers_for_watershed[name]["primary"],
                True,
                config,
                rivers_for_watershed[name]["secondary"],
            )
        if name == "fraser":
            print(flows["Fraser"])
        else:
            print(flows[name])

    print("files read")

    return flows


def create_runoff_array(flows, horz_area):

    fraserratio = rivers.prop_dict["fraser"]["Fraser"]["prop"]

    runoff = np.zeros((horz_area.shape[0], horz_area.shape[1]))
    run_depth = np.ones_like(runoff)
    run_temp = np.empty_like(runoff)

    for name in names:
        if name == "fraser":
            for key in rivers.prop_dict[name]:
                if "Fraser" in key:
                    flux = flows["Fraser"].flatten()[0]
                    subarea = fraserratio
                else:
                    flux = flows["nonFraser"].flatten()[0]
                    subarea = 1 - fraserratio

                river = rivers.prop_dict["fraser"][key]
                runoff = rivertools.fill_runoff_array(
                    flux * river["prop"] / subarea,
                    river["i"],
                    river["di"],
                    river["j"],
                    river["dj"],
                    river["depth"],
                    runoff,
                    run_depth,
                    horz_area,
                )[0]
        else:
            flowtoday = flows[name].flatten()[0]
            runoff, run_depth, run_temp = rivertools.put_watershed_into_runoff(
                "constant",
                horz_area,
                flowtoday,
                runoff,
                run_depth,
                run_temp,
                rivers.prop_dict[name],
            )
    return runoff


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
    filename_tmpls = config["rivers"]["file templates"][bathy_type]

    filename = directory / filename_tmpls.format(day.date())
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
        "rivers_base": prop_dict_name,
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
    flows = calculate_watershed_flows(dateneeded, config)
    horz_area = get_area(config)
    runoff = create_runoff_array(flows, horz_area)
    write_file(dateneeded, runoff, config)
