"""
To run those examples (from main itsim folder):
    $ python itsim/datastore/datastore_server.py
"""
import uuid
from itsim.schemas.itsim_items import create_json_item
from itsim.datastore.datastore import DatastoreRestClient
from itsim.time import now_iso8601
from time import sleep
import random
import string


def example_datastore_populate_plotly():

    sim_uuid = str(uuid.uuid4())
    node_uuids = [
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4()),
        str(uuid.uuid4())]

    # Connect to a datastore
    datastore = DatastoreRestClient(sim_uuid=sim_uuid, base_url='http://localhost:5000')

    for _ in range(0, 25):

        start = now_iso8601()
        sleep(random.uniform(0, 5))
        finish = now_iso8601()

        event = create_json_item(
            sim_uuid=sim_uuid,
            uuid=node_uuids[random.randint(0, 4)],
            timestamp=now_iso8601(),
            start=start,
            finish=finish,
            item_type='node_event_dbg',
            event_name=''.join(random.choices(string.ascii_uppercase + string.digits, k=8)))

        datastore.store_item(event)


if __name__ == '__main__':
    example_datastore_populate_plotly()
