from __future__ import annotations

from enum import IntEnum
from typing import Iterable

import numpy as np


class GridDirections(IntEnum):
    XP = 0
    XM = 1
    YP = 2
    YM = 3
    ZP = 4
    ZM = 5


class GridDirectionsObject:

    coord = np.array([
        [-1, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [0, -1, 0],
        [0, 0, -1],
        [0, 0, 1],
    ])

    def __init__(self, obj):
        self._index = 0
        self._obj = obj

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._obj[item]
        else:
            return self._obj[GridDirections[item]]

    def __iter__(self):
        return iter(self._obj)


class GridStep(GridDirectionsObject):
    """
    A class that represents the possible steps in a grid
    with respect to the lattice.
    """
    def __init__(self, lattice: tuple | Iterable):

        if len(lattice) != 3:
            raise ValueError('lattice must be a 3-element iterable.')

        obj = np.zeros((6, 3))
        obj[0] = np.array([lattice[0], 0., 0.])
        obj[1] = np.array([-lattice[0], 0., 0.])
        obj[2] = np.array([0., lattice[1], 0.])
        obj[3] = np.array([0., -lattice[1], 0.])
        obj[4] = np.array([0., 0., lattice[2]])
        obj[5] = np.array([0., 0., -lattice[2]])

        super().__init__(obj)
