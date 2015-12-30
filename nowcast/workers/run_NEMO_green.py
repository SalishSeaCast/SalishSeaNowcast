"""Salish Sea NEMO temporary worker that prepares the YAML run description
file and bash run script for a nowcast-green run on Salish and
launches the run.
"""

import datetime
import os
import yaml

import salishsea_cmd.api

TIMESTEPS_PER_DAY = 2160


def main():
    #  Do the work
    run_NEMO_green(run_type='nowcast-green')


def run_NEMO_green(run_type):
    run_prep_dir = '/data/sallen/MEOPAR/nowcast-green/'

    run_date = datetime.date.today()
    dmy = run_date.strftime('%d%b%y').lower()
    run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
    run_days = {'nowcast-green': run_date}

    results_dir = os.path.join('/results/SalishSea/nowcast-green/', dmy)

    print (run_prep_dir, run_date, dmy, run_id, run_days, results_dir)

    os.chdir(run_prep_dir)
    restart_timestep = update_time_namelist(run_prep_dir, run_date)
    config = update_yaml_file(run_prep_dir, run_date, restart_timestep)
    salishsea_cmd.api.run_in_subprocess(
          run_id, config, 'iodef.xml', results_dir)


def update_time_namelist(run_prep_dir, run_day):
    namelist = os.path.join(run_prep_dir, 'namelist.time')
    with open(namelist, 'rt') as f:
        lines = f.readlines()
    new_lines, restart_timestep = calc_new_namelist_lines(
        lines, 'nowcast-green', run_day)
    with open(namelist, 'wt') as f:
        f.writelines(new_lines)
    return restart_timestep


def update_yaml_file(run_prep_dir, run_date, restart_timestep):
    yesterday = run_date + datetime.timedelta(days=-1)
    dmy = yesterday.strftime('%d%b%y').lower()
    yamlfile = os.path.join(run_prep_dir,
                            'SalishSea_nowcast_green_template.yaml')
    with open(yamlfile, 'rt') as f:
        config = yaml.load(f)
    restartfile = (config['forcing']['restart.nc']['link to'])
    trcrestartfile = (config['forcing']['restart_trc.nc']['link to'])
    for f, s in zip((restartfile, trcrestartfile),
                    ('restart.nc', 'restart_trc.nc')):
        parts = restartfile.split('/')
        parts[4] = dmy
        fparts = parts[5].split('_')
        fparts[1] = '{:08d}'.format(restart_timestep)
        parts[5] = '_'.join(fparts)
        parts[0] = '/'
        config['forcing'][s]['link to'] = os.path.join(*parts)
    yamlfile = os.path.join(run_prep_dir, 'SalishSea_nowcast_green.yaml')
    with open(yamlfile, 'wt') as f:
        yaml.dump(config, f)
    return config


def calc_new_namelist_lines(
    lines, run_type, run_day,
    timesteps_per_day=TIMESTEPS_PER_DAY,
):
    # Read indices & values of it000 and itend from namelist;
    it000_line, it000 = get_namelist_value('nn_it000', lines)
    print (it000)
    itend_line, itend = get_namelist_value('nn_itend', lines)
    # Read the date that the previous run was done for
    date0_line, date0 = get_namelist_value('nn_date0', lines)
    print (date0)
    date0do = datetime.date(*map(int, [date0[:4], date0[4:6], date0[-2:]]))
    new_values = {
        'nowcast-green': (
            int(it000) + timesteps_per_day,
            int(itend) + timesteps_per_day,
            date0do + datetime.timedelta(days=1),
        ),
    }
    new_it000, new_itend, new_date0 = new_values['nowcast-green']
    print (new_date0)
    print (new_date0.strftime('%Y%m%d'))
    # Increment 1st and last time steps to values for the run
    lines[it000_line] = lines[it000_line].replace(it000, str(new_it000))
    lines[itend_line] = lines[itend_line].replace(itend, str(new_itend))
    print (new_date0.strftime('%Y%m%d'))
    lines[date0_line] = lines[date0_line].replace(date0, new_date0.strftime('%Y%m%d'))
    # Calculate the restart file time step
    restart_timestep = new_it000 - 1
    return lines, restart_timestep


def get_namelist_value(key, lines):
    line_index = [
        i for i, line in enumerate(lines)
        if line.strip() and line.split()[0] == key][-1]
    value = lines[line_index].split()[2]
    return line_index, value

if __name__ == '__main__':
    main()  # pragma: no cover
