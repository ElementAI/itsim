from greensim.tags import Tags, TaggedObject


class ITTag(Tags):
    MALWARE = 0
    VULNERABLE = 1


class ITObject(TaggedObject):
    pass
