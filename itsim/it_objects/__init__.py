import greensim
from greensim.tags import Tags, TaggedObject


class Simulator(greensim.Simulator):
    pass


class ITTag(Tags):
    MALWARE = 0
    VULNERABLE = 1


class ITObject(TaggedObject):
    pass
