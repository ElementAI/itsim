from itsim.it_objects import ITObject, ITTag


def test_empty_constructor():
    it = ITObject()
    assert it._tag_set == set()


def test_populated_constructor():
    tags = set([ITTag.MALWARE])
    it = ITObject(*tags)
    assert it._tag_set == tags
