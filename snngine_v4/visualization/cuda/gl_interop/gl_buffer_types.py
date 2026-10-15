from enum import IntEnum, auto


class GLBufferTypes(IntEnum):
    VBO = 0
    IBO = auto()
    POS_VBO = auto()
    CONNECT_IBO = auto()
    TEXTURE_3D = auto()
