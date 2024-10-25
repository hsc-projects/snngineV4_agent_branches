from typing import Callable, ClassVar, Iterable

import numpy as np
import torch

from snngine_v4.utils.containers.configurable_dict import (
    ConfigurableDict,
    DictContainerConfig,
)
from snngine_v4.utils.containers.mappings import Object2ObjectMap


class ArrayToTensorMap(Object2ObjectMap):
    ContainerConfigClass: ClassVar = ((np.ndarray, ), (torch.Tensor, ))


class TensorDict(ConfigurableDict):
    values: Callable[[], Iterable[torch.Tensor]]
    ContainerConfigClass: ClassVar = (DictContainerConfig, torch.Tensor)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.array2tensor = ArrayToTensorMap()

    def __setitem__(self, key: str, value: torch.Tensor):
        super().__setitem__(key, value)
        self.array2tensor[value.cpu().numpy()] = value
