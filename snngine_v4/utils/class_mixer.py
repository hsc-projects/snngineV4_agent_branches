from __future__ import annotations

from typing import ClassVar, Type

from snngine_v4.utils.containers.mappings import SingletonMap


class ClassMixer(SingletonMap):

    ContainerConfigClass: ClassVar = ((Type, ), (Type, ))
    Mixins: ClassVar[tuple] = ()
    Naming: ClassVar[str] = 'Mixed'

    def __getitem__(self, class_item):
        try:
            super().__getitem__(class_item)
        except KeyError:
            new = self.mix(class_item)
            self.obj_map[class_item] = new
            return new

    @classmethod
    def mix(cls, class_item: Type, name=None, **kwargs):
        name = name or class_item.__name__ + cls.Naming
        mixins = cls.Mixins
        if not isinstance(mixins, tuple):
            mixins = mixins,
        new_class = type(name, (class_item, *mixins), kwargs)
        return new_class
