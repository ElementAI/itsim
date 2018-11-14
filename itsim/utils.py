def assert_list(bools, throw=False):
    try:
        for i in range(len(bools)):
            assert bools[i]
    except AssertionError:
        if throw:
            raise AssertionError("False value at index %i" % i)
        else:
            return False
    else:
        return True
