from __future__ import annotations

from typing import ClassVar, Literal

import numpy as np
from pydantic import Field, NonNegativeInt

from snngine_v4.utils.data_utils.validation.array_annotation import (
    ArrayInterfaces,
)
from snngine_v4.geometry.spatial_pars import (
    Pos3DVBO,
)

from snngine_v4.visualization.config_models.visuals.parameters import \
    BufferColorType
from snngine_v4.visualization.config_models.visuals.visual_config import \
    VisualConfig

type LineConnectType = Literal['strip', 'segments'] | None


class LineVisualConfig(VisualConfig):

    # --- Ownership policy (Phase 3) ---
    # Shared-runtime resource (in-place mutation only, no reassignment):
    #   pos         — VBO-backed float32 array; canonical owner is the
    #                 source model or simulation backend.
    # Visual-canonical (locally owned, writable via param tree):
    #   color, width, antialias
    # Source-canonical / build-time only:
    #   connect, method  (frozen)

    SHARED_RUNTIME_FIELDS: ClassVar[frozenset[str]] = frozenset({'pos'})

    pos: Pos3DVBO = Field(default=None, repr=False)
    color: BufferColorType = Field(repr=False)
    width: NonNegativeInt = Field(default=1, le=15)
    connect: LineConnectType = Field(default='strip', frozen=True,
                                     repr=False)
    method: Literal['gl', 'agg'] = Field(default='gl', frozen=True)
    antialias: bool = False


class XYZAxisVisualConfig(LineVisualConfig):
    pos: Pos3DVBO = Field(
        default_factory=lambda: np.array([
            [0, 0, 0],
            [1, 0, 0],
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 0],
            [0, 0, 1]],
            dtype=np.float32),
        repr=False,
    )
    connect: LineConnectType = Field(
        default='segments',
        # readonly=False,
        repr=False,)
    color: BufferColorType = Field(
        default_factory=lambda: np.array([
            [1, 0, 0, 1],
            [1, 0, 0, 1],
            [0, 1, 0, 1],
            [0, 1, 0, 1],
            [0, 0, 1, 1],
            [0, 0, 1, 1]],
            dtype=np.float32),
        repr=False,)


class MultiBoxLinesVisualConfig(LineVisualConfig):
    # --- Ownership policy (Phase 3) ---
    # Inherits SHARED_RUNTIME_FIELDS from LineVisualConfig (pos).
    # Visual-canonical (locally owned, writable via param tree):
    #   color, width, antialias
    # Build-time only (drives geometry at construction):
    #   connect  — index array defining box edge topology

    connect: ArrayInterfaces().make_type(
        '* x', 2, dtype=np.uint32) = Field(repr=False)
    subvisuals: None = None
