from datetime import datetime, timedelta
from typing import Optional, Any
from uuid import uuid4

import greensim
from requests.exceptions import ConnectionError

from itsim.datastore.datastore import DatastoreRestClient
from itsim.schemas.itsim_items import create_json_item


class DatastoreRestClientStub(DatastoreRestClient):

    def __init__(self, sim_uuid):
        # Drop any actual initialization -- this is a do-nothing stub.
        self._sim_uuid = sim_uuid

    def url(self, type: str, uuid: str) -> str:
        return ""

    def load_item(self, item_type: str, uuid: str, from_time: str = None, to_time: str = None) -> Any:
        return None

    def store_item(self, data: Any, overwrite: bool = True) -> str:
        return ""


class Simulator(greensim.Simulator):
    pass


add = greensim.add
add_in = greensim.add_in
advance = greensim.advance
now = greensim.now


_the_datastore: Optional[DatastoreRestClient] = None
_base_timestamp: Optional[datetime] = None


class SimulationNotYetRunning(Exception):
    pass


def record(**fields: Any) -> None:
    # This only makes sense during the execution of a simulation. Simply skip outside of simulation.
    try:
        sim = greensim.Process.current().rsim()
    except TypeError:
        return

    global _the_datastore
    global _base_timestamp
    if _the_datastore is None:
        _base_timestamp = datetime.now()
        try:
            _the_datastore = DatastoreRestClient(base_url="http://localhost:5000", sim_uuid=sim.name)
            _the_datastore.store_item(
                create_json_item(
                    item_type="log",
                    sim_uuid=_the_datastore._sim_uuid,
                    timestamp=_base_timestamp.isoformat(),
                    uuid=str(uuid4()),
                    content="Checking datastore connectivity",
                    level="DEBUG"
                )
            )
        except ConnectionError:
            # Datastore unavailable -- use stub.
            _the_datastore = DatastoreRestClientStub(sim.name)

    record_fields = dict(
        sim_uuid=_the_datastore._sim_uuid,
        timestamp=(_base_timestamp + timedelta(0, sim.now())).isoformat(),
        uuid=str(uuid4())
    )
    record_fields.update(fields)
    _the_datastore.store_item(create_json_item(**record_fields))
