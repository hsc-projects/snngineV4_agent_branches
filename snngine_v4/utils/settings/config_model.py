from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict


from snngine_v4.utils.settings.config_model_base import (
    ConfigModelMixin,
    default_config_dict,
)
from snngine_v4.utils.settings.ui_parameter_options import FrozenParamOpts


class ConfigModel(BaseModel, ConfigModelMixin):

    model_config: ClassVar[ConfigDict] = default_config_dict()

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self.post_init_process_extra_classes()

    @classmethod
    def validate_model_item(cls, data, key, field_info=None) -> Any:
        b_iterable = super().validate_model_iterable_item(
            data, key, field_info=field_info)
        if not b_iterable:
            super().validate_model_item(
                data=data, key=key, field_info=field_info)
        else:
            pass


class ConfigContainerModel(ConfigModel):

    model_config: ClassVar[ConfigDict] = (
        default_config_dict(extra='allow'))

    parameter_ui_opts: ClassVar[FrozenParamOpts] = FrozenParamOpts(
        expanded=True,
        c_auto_collapse=True,
        c_collapsed_children=True,
    )

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)
