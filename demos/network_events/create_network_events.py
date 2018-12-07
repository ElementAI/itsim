from itsim.schemas.items import create_json_network_event
from itsim.datastore.datastore import DatastoreRestClient
from itsim.time import now_iso8601
from time import sleep
import random
from uuid import uuid4

"""
    Datastore client starts a datastore server if it can't connect to an existing one.
"""


def create_network_events():
    sim_uuid = uuid4()   # should be in simulation object
    event_uuid1 = uuid4()
    node_uuid1 = uuid4()
    event_uuid2 = uuid4()
    node_uuid2 = uuid4()
    network_events = []

    # open1
    network_events.append(
        create_json_network_event(
            sim_uuid=sim_uuid,
            timestamp=now_iso8601(),
            uuid=event_uuid1,
            uuid_node=node_uuid1,
            network_event_type='open',
            protocol='UDP',
            pid=32145,
            src=['192.168.1.1', 64],
            dst=['192.168.11.200', 72]))
    sleep(random.uniform(0, 2))

    # open 2
    network_events.append(
        create_json_network_event(
            sim_uuid=sim_uuid,
            timestamp=now_iso8601(),
            uuid=event_uuid2,
            uuid_node=node_uuid2,
            network_event_type='open',
            protocol='UDP',
            pid=32145,
            src=['192.168.1.111', 64],
            dst=['192.168.1.20', 72]))
    sleep(random.uniform(0, 10))

    # close 1
    network_events.append(
        create_json_network_event(
            sim_uuid=sim_uuid,
            timestamp=now_iso8601(),
            uuid=event_uuid1,
            uuid_node=node_uuid1,
            network_event_type='close',
            protocol='UDP',
            pid=32145,
            src=['192.168.1.1', 64],
            dst=['192.168.11.200', 72]))
    sleep(random.uniform(0, 2))

    # close 2
    network_events.append(
        create_json_network_event(
            sim_uuid=sim_uuid,
            timestamp=now_iso8601(),
            uuid=event_uuid2,
            uuid_node=node_uuid2,
            network_event_type='close',
            protocol='UDP',
            pid=32145,
            src=['192.168.1.111', 64],
            dst=['192.168.1.20', 72]))

    # Connect to a datastore
    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    for event in network_events:
        datastore.store_item(event)

    node = datastore.load_item("network_event", event_uuid2)

    # Quick sanity check:
    assert node.uuid_node == str(event_uuid2)


if __name__ == '__main__':
    create_network_events()
    print("Done")
