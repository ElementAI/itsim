import uuid
import random

from itsim.schemas.items import create_json_node, create_json_network_event
from itsim.datastore.datastore import DatastoreRestClient
from itsim.time import now_iso8601
from time import sleep


def test_datastore_logger():
    from_time = now_iso8601()
    sim_uuid = str(uuid.uuid4())

    datastore = DatastoreRestClient(sim_uuid=sim_uuid)
    logger = datastore.create_logger()

    logger.error('This is an error')    # Logging to console and datastore log table

    to_time = now_iso8601()             # Retrieving the log from the datastore
    log = datastore.load_item('log', uuid=None, from_time=from_time, to_time=to_time)

    assert log.content == 'This is an error'


def test_datastore_store_load_node():
    """
        This is testing a remote datastore over a rest api.
        The datastore uses a SQLite database to archive its data.
    :return:
    """
    sim_uuid = str(uuid.uuid4())
    node_uuid = str(uuid.uuid4())

    node = create_json_node(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            uuid=node_uuid,
                            node_label="pc_001")

    # Connect to a datastore
    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    print(f'Storing node: {node.uuid}')
    datastore.store_item(node)                  # Posting a node to the datastore
    item_type = 'node'                          # Retrieving the node from the datastore
    node = datastore.load_item(item_type, node_uuid)
    print(f'Loaded: {node.uuid}')

    assert node.uuid == node_uuid


def test_datastore_store_load_network_event():
    sim_uuid = str(uuid.uuid4())
    event_uuid1 = str(uuid.uuid4())
    node_uuid1 = str(uuid.uuid4())
    event_uuid2 = str(uuid.uuid4())
    node_uuid2 = str(uuid.uuid4())

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
    sleep(random.uniform(0, 1))

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
    sleep(random.uniform(0, 1))

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
    sleep(random.uniform(0, 1))

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

    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    for event in network_events:
        datastore.store_item(event)

    item_type = 'network_event'
    node = datastore.load_item(item_type, event_uuid1)
    assert node.uuid_node == node_uuid1

    node = datastore.load_item(item_type, event_uuid2)
    assert node.uuid_node == node_uuid2
