from typing import ClassVar

from pydantic_settings import BaseSettings


class JSESlots:
    ENUM: ClassVar[str] = 'enum'
    LIST: ClassVar[str] = 'list'
    SUFFIX: ClassVar[str] = 'suffix'


class ParameterUIOpts(BaseSettings):

    UI_OPTIONS_KEYWORD: ClassVar[str] = 'ui_opts'

    title: str | None = None
    expanded: bool = True
