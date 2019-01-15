from itsim import Singleton


def test_singleton_instantiation():
    class Test1(metaclass=Singleton):
        pass

    assert Test1() is Test1()


def test_singleton_no_overlap():
    class Test1(metaclass=Singleton):
        pass

    class Test2(metaclass=Singleton):
        pass

    assert not Test1() is Test2()


def test_singleton_reset():
    class Test1(metaclass=Singleton):
        pass

    class Test2(metaclass=Singleton):
        pass

    a = Test1()
    b = Test2()

    Singleton.reset(Test1)

    assert not Test1() is a
    assert Test2() is b


def test_reset_graceful():
    # Show that no errors result from reseting something with no instance
    Singleton.reset(object)


def test_has():
    class Test1(metaclass=Singleton):
        pass

    class Test2(metaclass=Singleton):
        pass

    Test1()
    assert Singleton.has_instance(Test1)
    assert not Singleton.has_instance(Test2)


def test_singleton_shared():
    class Test1(metaclass=Singleton):
        pass

    class Test2(metaclass=Singleton):
        pass

    a = Test1()
    b = Test2()

    assert a is Singleton._instances[Test1]
    assert b is Singleton._instances[Test2]
