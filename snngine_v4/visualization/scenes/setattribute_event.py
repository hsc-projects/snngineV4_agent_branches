from __future__ import annotations

from vispy.util.event import Event


class SetAttributeEvent(Event):

    def __init__(self, *arg, **kwargs):
        key = kwargs.pop('key', None)
        value = kwargs.pop('value', None)
        kwargs.setdefault('type', 'set_attribute')
        super().__init__(*arg, **kwargs)
        self.key = key
        self.value = value


class Set3DAttributeEvent(SetAttributeEvent):
    pass


class MeshDataChangedEvent(Event):
    def __init__(self, *arg, **kwargs):
        instance = kwargs.pop('instance', None)
        data = kwargs.pop('data', None)
        kwargs.setdefault('type', 'mesh_data_changed')
        super().__init__(*arg, **kwargs)
        self.instance = instance
        self.data = data
