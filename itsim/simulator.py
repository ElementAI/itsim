import greensim
from uuid import UUID
from itsim.datastore.datastore import DatastoreRestClient


class Simulator(greensim.Simulator):

    def __init__(self,
                 ds_hostname: str = '0.0.0.0',
                 ds_port: int = 5000):
        greensim.Simulator.__init__(self)
        self._datastore = DatastoreRestClient(hostname=ds_hostname, port=ds_port, sim_uuid=self.uuid)

    @property
    def datastore(self):
        return self._datastore

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
