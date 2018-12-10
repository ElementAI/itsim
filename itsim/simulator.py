import greensim
from uuid import UUID


class Simulator(greensim.Simulator):

    # Todo: validate this in unit tests.
    @property
    def uuid(self) -> UUID:
        return UUID(self._name)

    def uuid_str(self) -> str:
        return str(self.uuid)


add = greensim.add
add_in = greensim.add_in
advance = greensim.advance
now = greensim.now
