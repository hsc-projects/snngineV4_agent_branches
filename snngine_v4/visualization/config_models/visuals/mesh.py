from pydantic import Field

from snngine_v4.visualization.config_models.visuals.parameters import \
    RGBAColorType
from snngine_v4.visualization.config_models.visuals.visual_config import \
    VisualConfig


class MeshVisualConfig(VisualConfig):
    # --- Ownership policy (Phase 3) ---
    # Visual-canonical (locally owned, writable via param tree):
    #   color
    # Source-canonical / build-time only:
    #   pos_origin — canonical owner is the parent source model;
    #                this copy exists for VispyLinks.connect_transform()
    # Shared-runtime resource (in-place mutation only):
    #   (none on this model; vertices/faces are managed by VisPy MeshVisual)

    color: RGBAColorType = Field(repr=True)
