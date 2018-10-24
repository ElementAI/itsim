from abc import abstractmethod

from itsim import AbstractITObject


class _Thread(AbstractITObject):
    pass


class _Process(AbstractITObject):
    @abstractmethod
    def thread_complete(self, t) -> None:
        pass
