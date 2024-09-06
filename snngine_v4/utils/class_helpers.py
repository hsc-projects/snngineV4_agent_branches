from dataclasses import is_dataclass


class PostInitCaller(type):
    def __call__(cls, *args, **kwargs):
        obj = type.__call__(cls, *args, **kwargs)
        if not is_dataclass(obj):
            obj.__post_init__()
        return obj
