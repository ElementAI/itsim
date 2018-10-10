from greensim import Simulator
from greensim.tags import Tags, TaggedObject


class ITSimulator(Simulator):
    pass


class ITTag(Tags):
    MALWARE = 0
    VULNERABLE = 1


class ITObject(TaggedObject):
    def _bind_and_call_constructor(self, t: type, *args) -> None:
        """
        For a detailed description of why this is necessary and what it does see get_binding.md
        """
        t.__init__.__get__(self)(*args)  # type: ignore
    pass
