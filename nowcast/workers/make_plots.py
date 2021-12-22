#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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
"""Salish Sea NEMO nowcast worker that produces visualization images for
the web site from run results.
"""
import datetime
import logging
import os
import shlex
import subprocess
from glob import glob
from pathlib import Path

# **IMPORTANT**: matplotlib must be imported before anything else that uses it
# because of the matplotlib.use() call below
import matplotlib

## TODO: Get rid of matplotlib.use() call; see issue #19
matplotlib.use("Agg")
import matplotlib.pyplot

import arrow
import cmocean
from nemo_nowcast import NowcastWorker
import netCDF4 as nc
import scipy.io as sio
import xarray

from nowcast import lib
from nowcast.figures.research import (
    baynes_sound_agrif,
    time_series_plots,
    tracer_thalweg_and_surface_hourly,
    velocity_section_and_surface,
)
from nowcast.figures.comparison import compare_venus_ctd, sandheads_winds
from nowcast.figures.publish import (
    pt_atkinson_tide,
    storm_surge_alerts,
    storm_surge_alerts_thumbnail,
    compare_tide_prediction_max_ssh,
)
from nowcast.figures.fvcom.research import thalweg_transect, surface_currents
from nowcast.figures.fvcom.publish import second_narrows_current, tide_stn_water_level
from nowcast.figures.wwatch3 import wave_height_period

# Legacy figures code
from nowcast.figures import research_VENUS

NAME = "make_plots"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_plots --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "model",
        choices={"nemo", "fvcom", "wwatch3"},
        help="""
        Model to produce plots for:
        'nemo' means the Salish Sea NEMO model,
        'fvcom' means the Vancouver Harbour/Fraser River FVCOM model,
        'wwatch3' means the Strait of Georgia WaveWatch3(TM) model,
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={
            "nowcast",
            "nowcast-green",
            "nowcast-agrif",
            "nowcast-x2",
            "nowcast-r12",
            "forecast",
            "forecast2",
            "forecast-x2",
        },
        help="""
        Type of run to produce plots for:
        'nowcast' means NEMO nowcast physics-only run, or wwatch3 nowcast run,
        'nowcast-green' means NEMO nowcast-green physics/biology run,
        'nowcast-agrif' means NEMO nowcast-green physics/biology runs with AGRIF sub-grid(s),
        'nowcast-x2' means VHFR FVCOM x2 configuration nowcast run,
        'nowcast-r12' means VHFR FVCOM r12 configuration nowcast run,
        'forecast' means NEMO forecast physics-only runs, or wwatch3 forecast run,
        'forecast2' means NEMO preliminary forecast physics-only runs, or wwatch3 preliminary
        forecast run,
        'forecast-x2' means VHFR FVCOM x2 configuration forecast run,
        """,
    )
    worker.cli.add_argument(
        "plot_type",
        choices={"publish", "research", "comparison"},
        help="""
        Which type of plots to produce:
        "publish" means storm surge and other approved plots for publishing
        (forecast and forecast2 runs only),
        "research" means tracers, currents and other research plots
        (nowcast and nowcast-green runs only)
        "comparison" means model vs. observation plots (nowcast runs only)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to make plots for.",
    )
    worker.cli.add_argument(
        "--test-figure",
        help="""Identifier for a single figure to do a test on.
        The identifier may be the svg_name of the figure used in make_plots
        (e.g. SH_wind is the svg_name of figures stored as SH_wind_{ddmmmyy}.svg),
        the name of the website figure module
        (e.g. storm_surge_alerts is the module name of
        nowcast.figures.publish.storm_surge_alerts).
        The figure will be rendered in
        /results/nowcast-sys/figures/test/{run_type}/{ddmmmyy}/ so that it is
        accessible in a browser at
        https://salishsea.eos.ubc.ca/{run_type}/{ddmmmyy}/{svg_name}_{ddmmyy}.svg
        """,
    )
    worker.run(make_plots, success, failure)


def success(parsed_args):
    logger.info(
        f"{parsed_args.model} {parsed_args.plot_type} plots for "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} completed"
    )
    msg_type = (
        f"success {parsed_args.model} {parsed_args.run_type} "
        f"{parsed_args.plot_type}"
    )
    return msg_type


def failure(parsed_args):
    logger.critical(
        f"{parsed_args.model} {parsed_args.plot_type} plots failed for "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} {parsed_args.run_type} '
        f"failed"
    )
    msg_type = (
        f"failure {parsed_args.model} {parsed_args.run_type} "
        f"{parsed_args.plot_type}"
    )
    return msg_type


def make_plots(parsed_args, config, *args):
    model = parsed_args.model
    run_date = parsed_args.run_date
    dmy = run_date.format("DDMMMYY").lower()
    timezone = config["figures"]["timezone"]
    run_type = parsed_args.run_type
    plot_type = parsed_args.plot_type
    test_figure_id = parsed_args.test_figure

    fig_functions = {}
    if model == "nemo":
        dev_results_home = Path(config["results archive"]["nowcast-dev"])
        weather_path = Path(config["weather"]["ops dir"])
        if run_type in ["forecast", "forecast2"]:
            weather_path = weather_path / "fcst"
        results_dir = Path(config["results archive"][run_type], dmy)
        grid_dir = Path(config["figures"]["grid dir"])
        bathy = nc.Dataset(grid_dir / config["run types"][run_type]["bathymetry"])
        mesh_mask = nc.Dataset(grid_dir / config["run types"][run_type]["mesh mask"])
        dev_mesh_mask = nc.Dataset(
            grid_dir / config["run types"]["nowcast-dev"]["mesh mask"]
        )
        coastline = sio.loadmat(config["figures"]["coastline"])

        if run_type == "nowcast" and plot_type == "research":
            fig_functions = _prep_nowcast_research_fig_functions(
                bathy, mesh_mask, results_dir, run_date
            )
        if run_type == "nowcast-green" and plot_type == "research":
            fig_functions = _prep_nowcast_green_research_fig_functions(
                config, bathy, mesh_mask, results_dir, run_date
            )
        if run_type == "nowcast-agrif" and plot_type == "research":
            fig_functions = _prep_nowcast_agrif_research_fig_functions(
                config, results_dir, run_date
            )
        if run_type == "nowcast" and plot_type == "comparison":
            fig_functions = _prep_comparison_fig_functions(
                config,
                bathy,
                coastline,
                mesh_mask,
                dev_mesh_mask,
                results_dir,
                run_type,
                run_date,
                dev_results_home,
                dmy,
                timezone,
            )
        if run_type.startswith("forecast") and plot_type == "publish":
            fig_functions = _prep_publish_fig_functions(
                config,
                bathy,
                coastline,
                weather_path,
                results_dir,
                run_type,
                run_date,
                timezone,
            )

    if model == "fvcom":
        _, model_config = run_type.split("-")
        fvcom_results_dataset_filename = f"vh_{model_config}_0001.nc"
        fvcom_stns_datasets = {}
        if run_type.startswith("nowcast"):
            model_configs = ("x2", "r12") if model_config == "r12" else ("x2",)
            for mdl_cfg in model_configs:
                fvcom_stns_dataset_filename = config["vhfr fvcom runs"][
                    "stations dataset filename"
                ][mdl_cfg]
                results_dir = Path(
                    config["vhfr fvcom runs"]["results archive"][f"nowcast {mdl_cfg}"],
                    dmy,
                )
                if plot_type == "publish":
                    fvcom_stns_dataset_path = results_dir / fvcom_stns_dataset_filename
                    _rename_fvcom_vars(fvcom_stns_dataset_path)
                    fvcom_stns_datasets[mdl_cfg] = xarray.open_dataset(
                        f"/tmp/{fvcom_stns_dataset_path.name}"
                    )
            if plot_type == "research":
                fvcom_results_dataset = nc.Dataset(
                    results_dir / fvcom_results_dataset_filename
                )
        else:
            fvcom_stns_dataset_filename = config["vhfr fvcom runs"][
                "stations dataset filename"
            ][model_config]
            nowcast_results_dir = Path(
                config["vhfr fvcom runs"]["results archive"][f"nowcast {model_config}"],
                dmy,
            )
            forecast_results_dir = Path(
                config["vhfr fvcom runs"]["results archive"][
                    f"forecast {model_config}"
                ],
                dmy,
            )
            if plot_type == "publish":
                nowcast_dataset_path = nowcast_results_dir / fvcom_stns_dataset_filename
                forecast_dataset_path = (
                    forecast_results_dir / fvcom_stns_dataset_filename
                )
                fvcom_stns_dataset_path = Path("/tmp", fvcom_stns_dataset_filename)
                cmd = (
                    f"ncrcat -O {nowcast_dataset_path} {forecast_dataset_path} "
                    f"-o {fvcom_stns_dataset_path}"
                )
                subprocess.check_output(shlex.split(cmd))
                _rename_fvcom_vars(fvcom_stns_dataset_path)
                fvcom_stns_datasets[model_config] = xarray.open_dataset(
                    f"/tmp/{fvcom_stns_dataset_path.name}"
                )
            if plot_type == "research":
                cmd = (
                    f"ncrcat -O {nowcast_results_dir / fvcom_results_dataset_filename} "
                    f"{forecast_results_dir / fvcom_results_dataset_filename} "
                    f"-o /tmp/{fvcom_results_dataset_filename}"
                )
                subprocess.check_output(shlex.split(cmd))
                fvcom_results_dataset = nc.Dataset(
                    f"/tmp/{fvcom_results_dataset_filename}"
                )
        if plot_type == "publish":
            nemo_ssh_dataset_url_tmpl = config["figures"]["dataset URLs"][
                "tide stn ssh time series"
            ]
            obs_hadcp_dataset = xarray.open_dataset(
                config["figures"]["dataset URLs"]["2nd narrows hadcp time series"]
            )
            fig_functions = _prep_fvcom_publish_fig_functions(
                fvcom_stns_datasets,
                nemo_ssh_dataset_url_tmpl,
                obs_hadcp_dataset,
                run_type,
                run_date,
            )
        if plot_type == "research":
            fig_functions = _prep_fvcom_research_fig_functions(
                fvcom_results_dataset,
                run_type,
                run_date,
                run_duration=24 if run_type.startswith("nowcast") else 60,
            )
    if model == "wwatch3":
        wwatch3_dataset_url = config["figures"]["dataset URLs"]["wwatch3 fields"]
        fig_functions = _prep_wwatch3_publish_fig_functions(
            wwatch3_dataset_url, run_type, run_date
        )

    checklist = _render_figures(
        config, model, run_type, plot_type, dmy, fig_functions, test_figure_id
    )
    return checklist


def _rename_fvcom_vars(fvcom_dataset_path):
    cmd = (
        f"ncrename -O -v siglay,sigma_layer -v siglev,sigma_level "
        f"{fvcom_dataset_path} /tmp/{fvcom_dataset_path.name}"
    )
    subprocess.check_output(shlex.split(cmd))


def _results_dataset(period, grid, results_dir):
    """Return the results dataset for period (e.g. 1h or 1d)
    and grid (e.g. grid_T, grid_U) from results_dir.
    """
    filename_pattern = "SalishSea_{period}_*_{grid}.nc"
    filepaths = glob(
        os.path.join(results_dir, filename_pattern.format(period=period, grid=grid))
    )
    return nc.Dataset(filepaths[0])


def _results_dataset_gridded(station, results_dir):
    """Return the results dataset for station (e.g. central or east)
    for the quarter hourly data from results_dir.
    """
    filename_pattern = "VENUS_{station}_gridded.nc"
    filepaths = glob(
        os.path.join(results_dir, filename_pattern.format(station=station))
    )
    return nc.Dataset(filepaths[0])


def _prep_nowcast_research_fig_functions(bathy, mesh_mask, results_dir, run_date):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} NEMO nowcast-blue research figures"
    )
    yyyymmdd = run_date.format("YYYYMMDD")
    grid_T_hr = _results_dataset("1h", "grid_T", results_dir)
    grid_U_hr = _results_dataset("1h", "grid_U", results_dir)
    grid_V_hr = _results_dataset("1h", "grid_V", results_dir)
    grid_central = _results_dataset_gridded("central", results_dir)
    grid_east = _results_dataset_gridded("east", results_dir)
    image_loops = {
        "salinity": {"nemo var": "vosaline", "cmap": cmocean.cm.haline},
        "temperature": {"nemo var": "votemper", "cmap": cmocean.cm.thermal},
    }
    fig_functions = {}
    for tracer, params in image_loops.items():
        clevels_thalweg, clevels_surface = tracer_thalweg_and_surface_hourly.clevels(
            grid_T_hr.variables[params["nemo var"]], mesh_mask, depth_integrated=False
        )
        fig_functions.update(
            {
                f"{tracer}_thalweg_and_surface_{yyyymmdd}_{hr:02d}3000_UTC": {
                    "function": tracer_thalweg_and_surface_hourly.make_figure,
                    "args": (
                        hr,
                        grid_T_hr.variables[params["nemo var"]],
                        bathy,
                        mesh_mask,
                        clevels_thalweg,
                        clevels_surface,
                    ),
                    "kwargs": {"cmap": params["cmap"], "depth_integrated": False},
                    "format": "png",
                    "image loop": True,
                }
                for hr in range(24)
            }
        )
        logger.info(
            f"added {tracer}_thalweg_and_surface figures to {run_date.format('YYYY-MM-DD')} "
            f"NEMO nowcast-blue research render list"
        )
    fig_functions.update(
        {
            "Currents_sections_and_surface": {
                "function": velocity_section_and_surface.make_figure,
                "args": (
                    grid_U_hr.variables["vozocrtx"],
                    grid_V_hr.variables["vomecrty"],
                    bathy,
                    mesh_mask,
                ),
                "kwargs": {
                    "sections": (450, 520, 680),
                    "pos": ((0.1, 0.35), (0.4, 0.65), (0.7, 0.95)),
                    "section_lims": (
                        (235, 318, 0, 445),
                        (192, 277, 0, 445),
                        (127, 197, 0, 445),
                    ),
                },
            },
            "Currents_at_VENUS_Central": {
                "function": research_VENUS.plot_vel_NE_gridded,
                "args": ("Central", grid_central),
            },
            "Currents_at_VENUS_East": {
                "function": research_VENUS.plot_vel_NE_gridded,
                "args": ("East", grid_east),
            },
        }
    )
    for fig_func in fig_functions:
        if fig_func.startswith("Currents"):
            logger.info(
                f"added {fig_func} figure to {run_date.format('YYYY-MM-DD')} NEMO nowcast-blue "
                f"research render list"
            )
    return fig_functions


def _prep_nowcast_green_research_fig_functions(
    config, bathy, mesh_mask, results_dir, run_date
):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} NEMO nowcast-green research figures"
    )
    yyyymmdd = run_date.format("YYYYMMDD")
    grid_T_hr = _results_dataset("1h", "grid_T", results_dir)
    ptrc_T_hr = _results_dataset("1h", "ptrc_T", results_dir)
    turb_T_hr = _results_dataset("1h", "carp_T", results_dir)
    fig_functions = {}
    image_loops = {
        "salinity": {"nemo var": "vosaline", "cmap": cmocean.cm.haline},
        "temperature": {"nemo var": "votemper", "cmap": cmocean.cm.thermal},
    }
    for tracer, params in image_loops.items():
        clevels_thalweg, clevels_surface = tracer_thalweg_and_surface_hourly.clevels(
            grid_T_hr.variables[params["nemo var"]], mesh_mask, depth_integrated=False
        )
        fig_functions.update(
            {
                f"{tracer}_thalweg_and_surface_{yyyymmdd}_{hr:02d}3000_UTC": {
                    "function": tracer_thalweg_and_surface_hourly.make_figure,
                    "args": (
                        hr,
                        grid_T_hr.variables[params["nemo var"]],
                        bathy,
                        mesh_mask,
                        clevels_thalweg,
                        clevels_surface,
                    ),
                    "kwargs": {"cmap": params["cmap"], "depth_integrated": False},
                    "format": "png",
                    "image loop": True,
                }
                for hr in range(24)
            }
        )
    logger.info(
        f"added {tracer}_thalweg_and_surface figures to {run_date.format('YYYY-MM-DD')} NEMO "
        f"nowcast-green research render list"
    )
    image_loops = {
        "nitrate": {
            "nemo var": "nitrate",
            "cmap": cmocean.cm.tempo,
            "depth integrated": False,
        },
        "ammonium": {
            "nemo var": "ammonium",
            "cmap": cmocean.cm.matter,
            "depth integrated": False,
        },
        "silicon": {
            "nemo var": "silicon",
            "cmap": cmocean.cm.turbid,
            "depth integrated": False,
        },
        "dissolved_organic_nitrogen": {
            "nemo var": "dissolved_organic_nitrogen",
            "cmap": cmocean.cm.amp,
            "depth integrated": False,
        },
        "particulate_organic_nitrogen": {
            "nemo var": "particulate_organic_nitrogen",
            "cmap": cmocean.cm.amp,
            "depth integrated": False,
        },
        "biogenic_silicon": {
            "nemo var": "biogenic_silicon",
            "cmap": cmocean.cm.turbid,
            "depth integrated": False,
        },
        "diatoms": {
            "nemo var": "diatoms",
            "cmap": cmocean.cm.algae,
            "depth integrated": True,
        },
        "ciliates": {
            "nemo var": "ciliates",
            "cmap": cmocean.cm.algae,
            "depth integrated": True,
        },
        "flagellates": {
            "nemo var": "flagellates",
            "cmap": cmocean.cm.algae,
            "depth integrated": True,
        },
        "microzooplankton": {
            "nemo var": "microzooplankton",
            "cmap": cmocean.cm.algae,
            "depth integrated": True,
        },
        "mesozooplankton": {
            "nemo var": "mesozooplankton",
            "cmap": cmocean.cm.algae,
            "depth integrated": True,
        },
    }
    for tracer, params in image_loops.items():
        clevels_thalweg, clevels_surface = tracer_thalweg_and_surface_hourly.clevels(
            ptrc_T_hr.variables[params["nemo var"]],
            mesh_mask,
            depth_integrated=params["depth integrated"],
        )
        fig_functions.update(
            {
                f"{tracer}_thalweg_and_surface_{yyyymmdd}_{hr:02d}3000_UTC": {
                    "function": tracer_thalweg_and_surface_hourly.make_figure,
                    "args": (
                        hr,
                        ptrc_T_hr.variables[params["nemo var"]],
                        bathy,
                        mesh_mask,
                        clevels_thalweg,
                        clevels_surface,
                    ),
                    "kwargs": {
                        "cmap": params["cmap"],
                        "depth_integrated": params["depth integrated"],
                    },
                    "format": "png",
                    "image loop": True,
                }
                for hr in range(24)
            }
        )
        logger.info(
            f"added {tracer}_thalweg_and_surface figures to {run_date.format('YYYY-MM-DD')} NEMO "
            f"nowcast-green research render list"
        )
    image_loops = {
        "Fraser_tracer": {
            "nemo var": "Fraser_tracer",
            "cmap": cmocean.cm.turbid,
            "depth integrated": False,
        }
    }
    for tracer, params in image_loops.items():
        clevels_thalweg, clevels_surface = tracer_thalweg_and_surface_hourly.clevels(
            turb_T_hr.variables[params["nemo var"]],
            mesh_mask,
            depth_integrated=params["depth integrated"],
        )
        fig_functions.update(
            {
                f"{tracer}_thalweg_and_surface_{yyyymmdd}_{hr:02d}3000_UTC": {
                    "function": tracer_thalweg_and_surface_hourly.make_figure,
                    "args": (
                        hr,
                        turb_T_hr.variables[params["nemo var"]],
                        bathy,
                        mesh_mask,
                        clevels_thalweg,
                        clevels_surface,
                    ),
                    "kwargs": {
                        "cmap": params["cmap"],
                        "depth_integrated": params["depth integrated"],
                    },
                    "format": "png",
                    "image loop": True,
                }
                for hr in range(24)
            }
        )
        logger.info(
            f"added {tracer}_thalweg_and_surface figures to {run_date.format('YYYY-MM-DD')} NEMO "
            f"nowcast-green research render list"
        )
    place = "S3"
    phys_dataset = xarray.open_dataset(
        config["figures"]["dataset URLs"]["3d tracer fields"]
    )
    bio_dataset = xarray.open_dataset(
        config["figures"]["dataset URLs"]["3d biology fields"]
    )
    fig_functions.update(
        {
            "temperature_salinity_timeseries": {
                "function": time_series_plots.make_figure,
                "args": (phys_dataset, "temperature", "salinity", place),
            },
            "nitrate_diatoms_timeseries": {
                "function": time_series_plots.make_figure,
                "args": (bio_dataset, "nitrate", "diatoms", place),
            },
            "mesodinium_flagellates_timeseries": {
                "function": time_series_plots.make_figure,
                "args": (bio_dataset, "ciliates", "flagellates", place),
            },
            "mesozoo_microzoo_timeseries": {
                "function": time_series_plots.make_figure,
                "args": (bio_dataset, "mesozooplankton", "microzooplankton", place),
            },
        }
    )
    for fig_func in fig_functions:
        if fig_func.endswith("timeseries"):
            logger.info(
                f"added {fig_func} figure to {run_date.format('YYYY-MM-DD')} NEMO "
                f"nowcast-green research render list"
            )
    return fig_functions


def _prep_nowcast_agrif_research_fig_functions(config, agrif_results_dir, run_date):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} NEMO nowcast-agrif research figures"
    )
    yyyymmdd = run_date.format("YYYYMMDD")
    ss_tracers_path = agrif_results_dir / "BaynesSoundSurface_grid_T.nc"
    bs_phys_path = agrif_results_dir / f"1_SalishSea_1h_{yyyymmdd}_{yyyymmdd}_grid_T.nc"
    bs_bio_path = agrif_results_dir / f"1_SalishSea_1h_{yyyymmdd}_{yyyymmdd}_ptrc_T.nc"
    ss_grid_url = config["figures"]["dataset URLs"]["bathymetry"]
    bs_grid_path = Path(config["run types"]["nowcast-agrif"]["sub-grid bathymetry"])
    fig_functions = {
        "baynes_sound_surface": {
            "function": baynes_sound_agrif.make_figure,
            "args": (
                ss_tracers_path,
                bs_phys_path,
                bs_bio_path,
                run_date,
                ss_grid_url,
                bs_grid_path,
            ),
        }
    }
    logger.info(
        f"added baynes_sound_surface figure to {run_date.format('YYYY-MM-DD')} NEMO "
        f"nowcast-agrif research render list"
    )
    return fig_functions


def _prep_comparison_fig_functions(
    config,
    bathy,
    coastline,
    mesh_mask,
    dev_mesh_mask,
    results_dir,
    run_type,
    run_date,
    dev_results_home,
    dmy,
    timezone,
):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} NEMO nowcast-blue comparison figures"
    )
    hrdps_dataset_url = config["figures"]["dataset URLs"]["HRDPS fields"]
    ferry_data_dir = config["observations"]["ferry data"]
    dev_results_dir = os.path.join(dev_results_home, dmy)
    grid_T_hr = _results_dataset("1h", "grid_T", results_dir)
    dev_grid_T_hr = _results_dataset("1h", "grid_T", dev_results_dir)
    grid_central = _results_dataset_gridded("central", results_dir)
    grid_obs_central = sio.loadmat("/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPcentral.mat")
    grid_east = _results_dataset_gridded("east", results_dir)
    grid_obs_east = sio.loadmat("/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPeast.mat")
    grid_ddl = _results_dataset_gridded("delta", results_dir)
    grid_obs_ddl = sio.loadmat("/ocean/dlatorne/MEOPAR/ONC_ADCP/ADCPddl.mat")
    adcp_datetime = datetime.datetime.strptime(dmy, "%d%b%y").replace(minute=45)
    fig_functions = {
        "SH_wind": {
            "function": sandheads_winds.make_figure,
            "args": (hrdps_dataset_url, run_type, run_date, coastline),
        },
        "Compare_VENUS_East": {
            "function": compare_venus_ctd.make_figure,
            "args": (
                "East node",
                grid_T_hr,
                dev_grid_T_hr,
                timezone,
                mesh_mask,
                dev_mesh_mask,
            ),
        },
        "Compare_VENUS_Central": {
            "function": compare_venus_ctd.make_figure,
            "args": (
                "Central node",
                grid_T_hr,
                dev_grid_T_hr,
                timezone,
                mesh_mask,
                dev_mesh_mask,
            ),
        },
        "Compare_VENUS_Delta_DDL": {
            "function": compare_venus_ctd.make_figure,
            "args": (
                "Delta DDL node",
                grid_T_hr,
                dev_grid_T_hr,
                timezone,
                mesh_mask,
                dev_mesh_mask,
            ),
        },
        "Central_ADCP": {
            "function": research_VENUS.plotADCP,
            "args": (
                grid_central,
                grid_obs_central,
                adcp_datetime,
                "Central",
                [0, 285],
            ),
        },
        "Central_depavADCP": {
            "function": research_VENUS.plotdepavADCP,
            "args": (grid_central, grid_obs_central, adcp_datetime, "Central"),
        },
        "Central_timeavADCP": {
            "function": research_VENUS.plottimeavADCP,
            "args": (grid_central, grid_obs_central, adcp_datetime, "Central"),
        },
        "East_ADCP": {
            "function": research_VENUS.plotADCP,
            "args": (grid_east, grid_obs_east, adcp_datetime, "East", [0, 150]),
        },
        "East_depavADCP": {
            "function": research_VENUS.plotdepavADCP,
            "args": (grid_east, grid_obs_east, adcp_datetime, "East"),
        },
        "East_timeavADCP": {
            "function": research_VENUS.plottimeavADCP,
            "args": (grid_east, grid_obs_east, adcp_datetime, "East"),
        },
        "ddl_ADCP": {
            "function": research_VENUS.plotADCP,
            "args": (grid_ddl, grid_obs_ddl, adcp_datetime, "ddl", [0, 148]),
        },
        "ddl_depavADCP": {
            "function": research_VENUS.plotdepavADCP,
            "args": (grid_ddl, grid_obs_ddl, adcp_datetime, "ddl"),
        },
        "ddl_timeavADCP": {
            "function": research_VENUS.plottimeavADCP,
            "args": (grid_ddl, grid_obs_ddl, adcp_datetime, "ddl"),
        },
    }
    for fig_func in fig_functions:
        logger.info(
            f"added {fig_func} figure to {run_date.format('YYYY-MM-DD')} NEMO nowcast-blue "
            f"comparison render list"
        )
    return fig_functions


def _prep_publish_fig_functions(
    config, bathy, coastline, weather_path, results_dir, run_type, run_date, timezone
):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} NEMO {run_type} publish figures"
    )
    ssh_fcst_dataset_url_tmpl = config["figures"]["dataset URLs"][
        "tide stn ssh time series"
    ]
    tidal_predictions = Path(config["ssh"]["tidal predictions"])
    forecast_hrs = int(config["run types"][run_type]["duration"] * 24)
    grid_T_hr = _results_dataset("1h", "grid_T", results_dir)
    start_day = {
        "forecast": run_date.shift(days=+1).format("YYYYMMDD"),
        "forecast2": run_date.shift(days=+2).format("YYYYMMDD"),
    }
    end_day = {
        "forecast": run_date.shift(days=+2).format("YYYYMMDD"),
        "forecast2": run_date.shift(days=+3).format("YYYYMMDD"),
    }
    grid_T_hr_path = (
        results_dir
        / f"SalishSea_1h_{start_day[run_type]}_{end_day[run_type]}_grid_T.nc"
    )
    names = {
        "Boundary Bay": "BB_maxSSH",
        "Campbell River": "CR_maxSSH",
        "Cherry Point": "CP_maxSSH",
        "Friday Harbor": "FH_maxSSH",
        "Halfmoon Bay": "HB_maxSSH",
        "Nanaimo": "Nan_maxSSH",
        "Neah Bay": "NB_maxSSH",
        "New Westminster": "NW_maxSSH",
        "Patricia Bay": "PB_maxSSH",
        "Point Atkinson": "PA_maxSSH",
        "Port Renfrew": "PR_maxSSH",
        "Sand Heads": "SH_maxSSH",
        "Sandy Cove": "SC_maxSSH",
        "Squamish": "Sqam_maxSSH",
        "Victoria": "Vic_maxSSH",
        "Woodwards Landing": "WL_maxSSH",
    }
    grids_10m = {
        name: nc.Dataset(results_dir / "{}.nc".format(name.replace(" ", "")))
        for name in names
    }
    fig_functions = {
        "Website_thumbnail": {
            "function": storm_surge_alerts_thumbnail.make_figure,
            "args": (grids_10m, weather_path, coastline, tidal_predictions),
            "format": "png",
        },
        "Threshold_website": {
            "function": storm_surge_alerts.make_figure,
            "args": (grids_10m, weather_path, coastline, tidal_predictions),
        },
        "PA_tidal_predictions": {
            "function": pt_atkinson_tide.make_figure,
            "args": (grid_T_hr, tidal_predictions, timezone),
        },
    }
    for fig_func in fig_functions:
        logger.info(
            f"added {fig_func} figure to {run_date.format('YYYY-MM-DD')} NEMO {run_type} publish render list"
        )
    for place, svg_root in names.items():
        fig_functions.update(
            {
                svg_root: {
                    "function": compare_tide_prediction_max_ssh.make_figure,
                    "args": (
                        place,
                        ssh_fcst_dataset_url_tmpl,
                        tidal_predictions,
                        forecast_hrs,
                        weather_path,
                        bathy,
                        grid_T_hr_path,
                    ),
                }
            }
        )
        logger.info(
            f"added {place} figure to {run_date.format('YYYY-MM-DD')} NEMO {run_type} publish render list"
        )
    return fig_functions


def _prep_fvcom_publish_fig_functions(
    fvcom_stns_datasets,
    nemo_ssh_dataset_url_tmpl,
    obs_hadcp_dataset,
    run_type,
    run_date,
):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} VHFR FVCOM {run_type} publish figures"
    )
    fig_functions = {}
    names = {
        "Calamity Point": "CP_waterlevel",
        "Indian Arm Head": "IAH_waterlevel",
        "New Westminster": "NW_waterlevel",
        "Port Moody": "PM_waterlevel",
        "Sand Heads": "SH_waterlevel",
        "Sandy Cove": "SC_waterlevel",
        "Vancouver Harbour": "VH_waterlevel",
        "Woodwards Landing": "WL_waterlevel",
    }
    for place, svg_root in names.items():
        fig_functions.update(
            {
                svg_root: {
                    "function": tide_stn_water_level.make_figure,
                    "args": (place, fvcom_stns_datasets, nemo_ssh_dataset_url_tmpl),
                }
            }
        )
        logger.info(
            f"added {place} figure to {run_date.format('YYYY-MM-DD')} VHFR FVCOM {run_type} publish render list"
        )
    fig_functions.update(
        {
            "2ndNarrows_current": {
                "function": second_narrows_current.make_figure,
                "args": ("2nd Narrows", fvcom_stns_datasets, obs_hadcp_dataset),
            }
        }
    )
    logger.info(
        f"added 2ndNarrows_current figure to {run_date.format('YYYY-MM-DD')} VHFR FVCOM {run_type} "
        f"publish render list"
    )
    return fig_functions


def _prep_fvcom_research_fig_functions(
    fvcom_results_dataset, run_type, run_date, run_duration
):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} VHFR FVCOM {run_type} research figures"
    )
    fig_functions = {}
    names = {
        "English Bay": "EnglishBay_surface_currents",
        "Vancouver Harbour": "VancouverHarbour_surface_currents",
        "Indian Arm": "IndianArm_surface_currents",
    }
    for place, svg_root in names.items():
        for time_index in range(run_duration):
            hr = time_index + 1
            yyyymmdd = run_date.shift(hours=hr).format("YYYYMMDD")
            hhmmss = run_date.shift(hours=hr).format("HHmmss")
            fig_functions.update(
                {
                    f"{svg_root}_{yyyymmdd}_{hhmmss}_UTC": {
                        "function": surface_currents.make_figure,
                        "args": (place, time_index, fvcom_results_dataset),
                        "format": "png",
                        "image loop": True,
                    }
                }
            )
        logger.info(
            f"added {svg_root} figures to {run_date.format('YYYY-MM-DD')} VHFR FVCOM {run_type} "
            f"research render list"
        )
    names = {
        "Vancouver Harbour": "VancouverHarbour_thalweg",
        "Port Moody": "PortMoody_thalweg",
        "Indian Arm": "IndianArm_thalweg",
    }
    for place, svg_root in names.items():
        for time_index in range(run_duration):
            hr = time_index + 1
            yyyymmdd = run_date.shift(hours=hr).format("YYYYMMDD")
            hhmmss = run_date.shift(hours=hr).format("HHmmss")
            for varname in ["salinity", "temp", "tangential velocity"]:
                fvarname = varname.replace(" ", "_")
                fig_functions.update(
                    {
                        f"{svg_root}_{fvarname}_{yyyymmdd}_{hhmmss}_UTC": {
                            "function": thalweg_transect.make_figure,
                            "args": (place, time_index, fvcom_results_dataset, varname),
                            "format": "png",
                            "image loop": True,
                        }
                    }
                )
        logger.info(
            f"added {svg_root} figures to {run_date.format('YYYY-MM-DD')} VHFR FVCOM {run_type} "
            f"research render list"
        )
    return fig_functions


def _prep_wwatch3_publish_fig_functions(wwatch3_dataset_url, run_type, run_date):
    logger.info(
        f"preparing render list for {run_date.format('YYYY-MM-DD')} WaveWatch3 {run_type} publish figures"
    )
    buoys = {"Halibut Bank": "HB_waves", "Sentry Shoal": "SS_waves"}
    fig_functions = {}
    for buoy, svg_root in buoys.items():
        fig_functions.update(
            {
                svg_root: {
                    "function": wave_height_period.make_figure,
                    "args": (buoy, wwatch3_dataset_url),
                }
            }
        )
        logger.info(
            f"added {buoy} figure to {run_date.format('YYYY-MM-DD')} WaveWatch3 {run_type} "
            f"publish render list"
        )
    return fig_functions


def _render_figures(
    config, model, run_type, plot_type, dmy, fig_functions, test_figure_id
):
    logger.info(f"starting to render {model} {run_type} {plot_type} {dmy} figures")
    checklist = {}
    fig_files = []
    for svg_name, func in fig_functions.items():
        fig_func = func["function"]
        args = func.get("args", [])
        kwargs = func.get("kwargs", {})
        fig_save_format = func.get("format", "svg")
        image_loop_figure = func.get("image loop", False)
        test_figure = False
        if test_figure_id:
            test_figure = any(
                (
                    svg_name == test_figure_id,
                    image_loop_figure and svg_name.startswith(test_figure_id),
                    fig_func.__module__.endswith(f"{plot_type}.{test_figure_id}"),
                )
            )
            if not test_figure:
                continue
        logger.debug(f"starting {fig_func.__module__}.{fig_func.__name__}")
        try:
            fig = _calc_figure(fig_func, args, kwargs)
        except (FileNotFoundError, IndexError, KeyError, TypeError):
            # **IMPORTANT**: the collection of exception above must match those
            # handled in the _calc_figure() function
            continue
        if test_figure:
            fig_files_dir = Path(config["figures"]["test path"], run_type, dmy)
            fig_files_dir.mkdir(parents=True, exist_ok=True)
        else:
            fig_files_dir = (
                Path(config["figures"]["storage path"], run_type, dmy)
                if model == "nemo"
                else Path(config["figures"]["storage path"], model, run_type, dmy)
            )
            lib.mkdir(fig_files_dir, logger, grp_name=config["file group"])
        filename = fig_files_dir / f"{svg_name}_{dmy}.{fig_save_format}"
        if image_loop_figure:
            filename = fig_files_dir / f"{svg_name}.{fig_save_format}"
        fig.savefig(
            os.fspath(filename), facecolor=fig.get_facecolor(), bbox_inches="tight"
        )
        logger.debug(f"{filename} saved")
        matplotlib.pyplot.close(fig)
        if fig_save_format == "svg":
            logger.debug(f"starting SVG scouring of {filename}")
            tmpfilename = filename.with_suffix(".scour")
            scour = Path(os.environ["NOWCAST_ENV"], "bin", "scour")
            cmd = f"{scour} {filename} {tmpfilename}"
            logger.debug(f"running subprocess: {cmd}")
            try:
                proc = subprocess.run(
                    shlex.split(cmd),
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                )
            except subprocess.CalledProcessError as e:
                logger.warning("SVG scouring failed, proceeding with unscoured figure")
                logger.debug(f"scour return code: {e.returncode}")
                if e.output:
                    logger.debug(e.output)
                continue
            logger.debug(proc.stdout)
            tmpfilename.rename(filename)
            logger.debug(f"{filename} scoured")
        lib.fix_perms(filename, grp_name=config["file group"])
        fig_files.append(os.fspath(filename))
        fig_path = _render_storm_surge_alerts_thumbnail(
            config,
            run_type,
            plot_type,
            dmy,
            fig,
            svg_name,
            fig_save_format,
            test_figure,
        )
        if checklist is not None:
            checklist["storm surge alerts thumbnail"] = fig_path
    checklist[f"{model} {run_type} {plot_type}"] = fig_files
    logger.info(f"finished rendering {model} {run_type} {plot_type} {dmy} figures")
    return checklist


def _calc_figure(fig_func, args, kwargs):
    try:
        fig = fig_func(*args, **kwargs)
    except FileNotFoundError as e:
        if fig_func.__name__.endswith("salinity_ferry_route"):
            logger.warning(
                f"{args[3]} ferry route salinity comparison figure failed: {e}"
            )
        else:
            logger.error(
                f"unexpected FileNotFoundError in {fig_func.__name__}:", exc_info=True
            )
        raise
    except IndexError:
        adcp_plot_funcs = ("plotADCP", "plotdepavADCP", "plottimeavADCP")
        if fig_func.__name__.endswith(adcp_plot_funcs):
            logger.warning(
                f"VENUS {args[3]} ADCP comparison figure failed: "
                f"No observations available"
            )
        else:
            logger.error(
                f"unexpected IndexError in {fig_func.__name__}:", exc_info=True
            )
        raise
    except KeyError:
        if fig_func.__name__.endswith("salinity_ferry_route"):
            logger.warning(
                f"{args[3]} ferry route salinity comparison figure "
                f"failed: No observations found in .mat file"
            )
        else:
            logger.error(f"unexpected KeyError in {fig_func.__name__}:", exc_info=True)
        raise
    except TypeError:
        if fig_func.__module__.endswith("compare_venus_ctd"):
            logger.warning(
                f"VENUS {args[0]} CTD comparison figure failed: "
                f"No observations available"
            )
        else:
            logger.error(f"unexpected TypeError in {fig_func.__name__}:", exc_info=True)
        raise
    return fig


def _render_storm_surge_alerts_thumbnail(
    config, run_type, plot_type, dmy, fig, svg_name, fig_save_format, test_figure
):
    """Undated storm surge alerts thumbnail for storm-surge/index.html page"""
    now = arrow.now()
    today_dmy = now.format("DDMMMYY").lower()
    yesterday_dmy = now.shift(days=-1).format("DDMMMYY").lower()
    thumbnail_root = config["figures"]["storm surge alerts thumbnail"]
    if not all(
        (
            plot_type == "publish",
            svg_name == thumbnail_root,
            any(
                (
                    run_type == "forecast" and dmy == today_dmy,
                    run_type == "forecast2" and dmy == yesterday_dmy,
                )
            ),
        )
    ):
        return
    if test_figure:
        dest_dir = Path(
            config["figures"]["test path"],
            config["figures"]["storm surge info portal path"],
        )
        dest_dir.mkdir(parents=True, exist_ok=True)
    else:
        dest_dir = Path(
            config["figures"]["storage path"],
            config["figures"]["storm surge info portal path"],
        )
    undated_thumbnail = dest_dir / f"{thumbnail_root}.{fig_save_format}"
    fig.savefig(
        os.fspath(undated_thumbnail), facecolor=fig.get_facecolor(), bbox_inches="tight"
    )
    lib.fix_perms(undated_thumbnail, grp_name=config["file group"])
    logger.debug(f"{undated_thumbnail} saved")
    return os.fspath(undated_thumbnail)


if __name__ == "__main__":
    main()
