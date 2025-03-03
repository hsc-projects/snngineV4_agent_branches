class CudaKeywords:

    DEVICE = 'device'


def compare_devices(d0, d1):
    if (not isinstance(d0, int)) and (d0 != 'cpu'):
        d0 = d0.index
    if (not isinstance(d1, int)) and (d1 != 'cpu'):
        d1 = d1.index
    return d0 == d1


def assert_device_equivalency(d0, d1):
    if not compare_devices(d0, d1):
        raise AssertionError(
            f"d0 ({d0}) != d1 ({d1}) ")
