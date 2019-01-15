import random
from itsim.schemas.items import create_json_node, create_json_network_event
from itsim.datastore.datastore import DatastoreRestClient
from itsim.time import now_iso8601
from time import sleep
from uuid import uuid4
from pytest import fixture


# Explicitly close the client at the end of each test to isolate and prevent hanging
@fixture(autouse=True)
def close_db():
    yield
    DatastoreRestClient().close()


def test_datastore_logger():
    from_time = now_iso8601()
    sim_uuid = uuid4()

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
    sim_uuid = uuid4()
    node_uuid = uuid4()

    node = create_json_node(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            uuid=node_uuid,
                            node_label="pc_001")

    # Connect to a datastore
    datastore = DatastoreRestClient(sim_uuid=sim_uuid)
    # Posting a node to the datastore
    datastore.store_item(node)
    # Retrieving the node from the datastore
    item_type = 'node'
    node = datastore.load_item(item_type, node_uuid)
    assert node.uuid == str(node_uuid)


def test_datastore_store_load_network_event():
    sim_uuid = uuid4()
    network_events = []
    nb_events = 2
    event_uuids = [uuid4() for _ in range(nb_events)]
    node_uuids = [uuid4() for _ in range(nb_events)]

    for uuid, uuid_node, network_event_type, src, dst in [
        (event_uuids[0], node_uuids[0], 'open', ['192.168.1.1', 64], ['192.168.11.200', 72]),
        (event_uuids[1], node_uuids[1], 'open', ['192.168.1.111', 64], ['192.168.11.20', 72]),
        (event_uuids[0], node_uuids[0], 'close', ['192.168.1.1', 64], ['192.168.11.200', 72]),
        (event_uuids[1], node_uuids[1], 'close', ['192.168.1.111', 64], ['192.168.11.20', 72])
    ]:
        network_events.append(
            create_json_network_event(
                sim_uuid=sim_uuid,
                timestamp=now_iso8601(),
                uuid=uuid,
                uuid_node=uuid_node,
                network_event_type=network_event_type,
                protocol='UDP',
                pid=32145,
                src=src,
                dst=dst))
        sleep(random.uniform(0, 1))

    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    for event in network_events:
        datastore.store_item(event)

    item_type = 'network_event'

    for i in range(nb_events):
        event = datastore.load_item(item_type, event_uuids[i])
        assert event.uuid_node == str(node_uuids[i])
