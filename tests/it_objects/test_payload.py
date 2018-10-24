from itsim.network import Payload, PayloadDictionaryType


entries = {PayloadDictionaryType.CONTENT: "48 65 6c 6c 6f 2c 20 77 6f 72 6c 64 21"}


def test_init():
    Payload(entries)
    Payload()


def test_entries():
    assert Payload(entries).entries == {PayloadDictionaryType.CONTENT: "48 65 6c 6c 6f 2c 20 77 6f 72 6c 64 21"}
    assert Payload().entries == {}


def test_eq():
    candidate = Payload({PayloadDictionaryType.CONTENT: "Red Sox"})
    # None (PEP-8 complains == should be "is", so call __eq__ directly)
    assert not candidate.__eq__(None)
    # Compare type
    assert not candidate == "Red Sox"
    # Compare entries
    assert not candidate == Payload({PayloadDictionaryType.CONTENT: "Yankees"})
    assert not candidate == Payload({PayloadDictionaryType.CONTENT: "Red Sox",
                                     PayloadDictionaryType.CONTENT_TYPE: "Baseball"})
    assert not candidate == Payload({PayloadDictionaryType.CONTENT_TYPE: "Red Sox"})
    assert candidate == Payload({PayloadDictionaryType.CONTENT: "Red Sox"})
