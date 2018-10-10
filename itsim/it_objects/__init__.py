from greensim import Simulator
from greensim.tags import Tags, TaggedObject


class ITSimulator(Simulator):
    pass


class ITTag(Tags):
    MALWARE = 0
    VULNERABLE = 1


class ITObject(TaggedObject):
    pass
