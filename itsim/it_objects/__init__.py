import greensim
from greensim.tags import Tags, TaggedObject


class Simulator(greensim.Simulator):
    pass


class Tag(Tags):
    MALWARE = 0
    VULNERABLE = 1


class ITObject(TaggedObject):
    def _bind_and_call_constructor(self, t: type, *args) -> None:
        """
        For a detailed description of why this is necessary and what it does see get_binding.md
        """
        t.__init__.__get__(self)(*args)  # type: ignore
    pass
