from __future__ import annotations

from typing import ClassVar


from snngine_v4.utils.settings.xml_settings_base import XMLSettingsModelBase

from snngine_v4.utils.settings.xml_converter_options import XMLConverterOptions


class XMLSettingsModel(XMLSettingsModelBase):

    xml_model: ClassVar[XMLConverterOptions] = XMLConverterOptions()
