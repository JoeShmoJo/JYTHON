"""Expand the supplied annual table onto forecast dates; write mapped rule curves."""
import csv
from datetime import datetime, timedelta
from pathlib import Path

from extraction_context import load_context

RESERVOIRS = ('DETROIT', 'FOSTER', 'GREEN PETER', 'FERN RIDGE', 'BLUE RIVER',
              'COUGAR', 'COTTAGE GROVE', 'DORENA', 'FALL CREEK', 'LOOKOUT POINT', 'HILLS CREEK')


def annual_table(path):
    schedule = {}
    with open(path, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if not set(RESERVOIRS).issubset(reader.fieldnames or []):
            raise ValueError('Rule-curve CSV is missing mapped reservoir columns')
        for row in reader:
            day = datetime.strptime(row['date'], '%d%b%Y')
            key = (day.month, day.day)
            values = {name: float(row[name]) for name in RESERVOIRS}
            if key in schedule and schedule[key] != values:
                raise ValueError('Conflicting annual boundary values for {}'.format(key))
            schedule[key] = values
    return schedule


def expand(schedule, begin, end, leap_day="error"):
    if leap_day not in ('error','linear','feb28'):
        raise ValueError('Unknown rule-curve leap-day policy: '+str(leap_day))
    # Include an extra daily point at each boundary for model interpolation.
    day = begin.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    last = end.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    dates, values = [], {name: [] for name in RESERVOIRS}
    while day <= last:
        key = (day.month, day.day)
        row = schedule.get(key)
        if row is None and key==(2,29) and leap_day!='error':
            if (2,28) not in schedule or (3,1) not in schedule:
                raise ValueError('Leap-day policy requires supplied February 28 and March 1 rows')
            row = {name:(schedule[(2,28)][name]+schedule[(3,1)][name])/2.0
                   if leap_day=='linear' else schedule[(2,28)][name] for name in RESERVOIRS}
        if row is None:
            raise ValueError('No supplied rule-curve value for {}; choose a February 29 policy in the archive dialog or supply an explicit row'.format(day.date()))
        dates.append(day)
        for name in RESERVOIRS:
            values[name].append(row[name])
        day += timedelta(days=1)
    return dates, values


def main():
    context = load_context()
    if context is None:
        raise ValueError('This loader requires explicit forecast context; standalone files are unchanged')
    schedule = annual_table(Path(__file__).with_name('CON_SEASON_RULE_CURVES.csv'))
    settings=context.data.get('archive_settings',context.data.get('menu_settings',{}))
    policy=settings.get('rule_curve_leap_day','linear')
    dates, values = expand(schedule, context.lookback, context.end, leap_day=policy)
    print('Rule-curve February 29 policy:',policy,flush=True)
    import numpy as np
    from pydsstools.heclib.dss import HecDss
    from pydsstools.core import TimeSeriesContainer
    if not context.dss_path.is_file():
        raise FileNotFoundError(context.dss_path)
    with HecDss.Open(str(context.dss_path), version=7) as dss:
        for name in RESERVOIRS:
            array = np.asarray(values[name], dtype=float)
            if not np.isfinite(array).all():
                raise ValueError('Nonfinite rule curve for ' + name)
            record = TimeSeriesContainer()
            record.pathname = '//{}/ELEV//1DAY/RULE CURVE/'.format(name)
            record.startDateTime = dates[0].strftime('%d%b%Y %H%M')
            record.numberValues = len(dates)
            record.interval = 1440
            record.units = 'FT'
            record.type = 'INST-VAL'
            record.values = array
            dss.put_ts(record)
            print('Rule curve:', record.pathname, dates[0], 'through', dates[-1])
    print('Mapped rule curves written:', len(RESERVOIRS))


if __name__ == '__main__':
    main()
