from dataclasses import is_dataclass


class PostInitCaller(type):
    def __call__(cls, *args, **kwargs):
        obj = type.__call__(cls, *args, **kwargs)
        if not is_dataclass(obj):
            obj.__post_init__()
        return obj


class FrozenPostInitCaller(object, metaclass=PostInitCaller):

    __isfrozen = False
    __isfrozendataclass = None

    def __setattr__(self, key, value):
        if self.__isfrozen and not hasattr(self, key):
            raise AttributeError('%r is not an attribute of class %s. Call '
                                 '"unfreeze()" to allow addition of new '
                                 'attributes' % (key, self))
        object.__setattr__(self, key, value)

    def freeze(self):
        """Freeze the object so that only existing properties can be set"""
        if self.__isfrozen is True:
            raise AttributeError('%r is already frozen' % self)
        self.__isfrozen = True

    def unfreeze(self):
        """Unfreeze the object so that additional properties can be added"""
        if self.__isfrozen is False:
            raise AttributeError('%r is already unfrozen' % self)
        self.__isfrozen = False

    def __post_init__(self):
        # noinspection PyUnresolvedReferences
        object.__setattr__(
            self, f"_{FrozenPostInitCaller.__name__}__isfrozendataclass",
            is_dataclass(self) and (self.__dataclass_params__.frozen is True)
        )
        if self.__isfrozendataclass is False:
            self.freeze()

    @classmethod
    def _isfrozen_attr_key(cls):
        return f"_{FrozenPostInitCaller.__name__}__isfrozen"


def is_in_enum(value, enum_class):
    try:
        get_intenum_member(value, enum_class)
        return True
    except (ValueError, KeyError):
        return False


def get_intenum_member(value, enum_class,
                       b_allow_upper: bool = False):
    if isinstance(value, enum_class):
        return value
    elif isinstance(value, int):
        return enum_class(value)
    elif isinstance(value, str):
        if b_allow_upper is False:
            return enum_class[value]
        else:
            try:
                return enum_class[value]
            except KeyError:
                return enum_class[value.upper()]
    raise TypeError(f'Expected ({enum_class}, {int}, {str}), '
                    f'got {type(value).__name__}.')


def pop_enum_keys(dct, enum_class):
    res = {}
    if len(dct) < len(enum_class):
        pop_keys = []
        for k in dct:
            if is_in_enum(k, enum_class):
                # if k.name in model_dict:
                pop_keys.append(k)
        for k in pop_keys:
            res[k] = dct.pop(k)
    else:
        for x in enum_class:
            if x.name in dct:
                res[x.name] = dct.pop(x.name)
    return res
