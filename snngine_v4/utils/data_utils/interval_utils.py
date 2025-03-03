from enum import IntEnum

import numpy as np
import pandas as pd


class IntervalClosingType(IntEnum):
    right = 0
    left = 1
    both = 2
    neither = 3


def make_interval(ge=None, gt=None, lt=None, le=None):

    b_left_closed = False
    b_right_closed = False

    if ge is not None:
        if gt is not None:
            raise ValueError('Cannot have both gt and ge')
        b_left_closed = True

    if le is not None:
        if lt is not None:
            raise ValueError('Cannot have both lt and le')
        b_right_closed = True

    left = (ge if ge is not None else gt)
    right = (le if le is not None else lt)

    if left is None:
        left = -np.inf
    if right is None:
        right = np.inf

    if (b_left_closed is True) and (b_right_closed is True):
        interval_type = IntervalClosingType.both
    elif (b_left_closed is True) and (b_right_closed is False):
        interval_type = IntervalClosingType.left
    elif (b_left_closed is False) and (b_right_closed is True):
        interval_type = IntervalClosingType.right
    elif (b_left_closed is False) and (b_right_closed is False):
        interval_type = IntervalClosingType.neither
    else:
        raise ValueError('Invalid interval type')
    # noinspection PyTypeChecker,PydanticTypeChecker
    return pd.Interval(left=left, right=right, closed=interval_type.name)


def limits_from_interval(interval: pd.Interval, step_size):
    start = interval.left
    stop = interval.right
    if interval.closed != 'both':
        if interval.closed in ['left', 'neither']:
            stop -= step_size
        if interval.closed in ['right', 'neither']:
            start += step_size
    return start, stop


def restricted_linspace_interval(
        interval: pd.Interval,
        step_size,
        max_n_steps,
        value=None):

    if value is None:
        if interval.closed in ['neither', 'right']:
            value = interval.left + step_size
        else:
            value = interval.left

    min_value = value - ((max_n_steps - 1) // 2 * step_size)
    max_value = value + ((max_n_steps - 1) // 2 * step_size)

    new_interval = pd.Interval(
        max(interval.left, min_value),
        min(interval.right, max_value),
        closed=interval.closed)

    bounds = list(limits_from_interval(new_interval, step_size=step_size))

    n_steps = int(((bounds[1] - bounds[0]) / step_size) + .5)

    span_diff = max_n_steps - n_steps

    available_diff0 = 0
    available_diff1 = 0

    if span_diff > 0:

        init_bounds = limits_from_interval(interval, step_size=step_size)

        if bounds[0] > init_bounds[0]:
            available_diff0 = (bounds[0] - init_bounds[0]) / step_size
            if available_diff0 > span_diff:
                bounds[0] -= span_diff * step_size
            else:
                bounds[0] -= available_diff0 * step_size
                span_diff -= available_diff0
                if (span_diff > 0) and bounds[1] < init_bounds[1]:
                    available_diff1 = (init_bounds[1] - bounds[1]) / step_size
                    if available_diff1 > span_diff:
                        bounds[1] += span_diff * step_size
                    else:
                        bounds[1] += available_diff1
    if (bounds[0] not in interval) or (bounds[1] not in interval):
        raise ValueError()
    new_n_steps = int((bounds[1] - bounds[0]) / step_size + .5)
    if span_diff > 0:
        if (((available_diff0 > span_diff) or (available_diff1 > span_diff))
                and (new_n_steps != max_n_steps)):
            raise ValueError()
    return pd.Interval(bounds[0], bounds[1], closed='both'), new_n_steps


def linspace_from_interval(interval: pd.Interval,
                           n_steps_if_closed=101,
                           b_change_n_steps_if_open=True,
                           **kwargs):

    endpoint = True
    n_steps = n_steps_if_closed

    step_size = interval.length / (n_steps - 1)

    start = interval.left

    if interval.closed != 'both':
        if interval.closed in ['left', 'neither']:
            endpoint = False
            if b_change_n_steps_if_open is True:
                n_steps -= 1
        if interval.closed in ['right', 'neither']:
            if b_change_n_steps_if_open is True:
                start += step_size
                n_steps -= 1

    # noinspection PyTypeChecker
    return np.linspace(start, interval.right, n_steps,
                       endpoint=endpoint, **kwargs)


def coerce_value_into_interval(value, intv: pd.Interval, step_size=1):
    if value <= intv.left:
        value = intv.left
        if intv.closed in ['right', 'neither']:
            value += step_size
    elif value >= intv.right:
        value = intv.right
        if intv.closed in ['left', 'neither']:
            value -= step_size
    return value
