from abc import abstractmethod

from itsim.it_objects import AbstractITObject

class _Thread(AbstractITObject):
    pass


class _Process(AbstractITObject):
    @abstractmethod
    def thread_complete(self, t) -> None:
        pass
