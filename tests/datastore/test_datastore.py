from uuid import uuid4
from itsim.datastore.datastore import DatastoreRestClient
from itsim.schemas.items import create_json_node, create_json_network_event, create_json_log
from itsim.time import now_iso8601


def test_store_load_node():
    """
        Stores/loads a node into each of the supported database tables.
    :return:
    """
    sim_uuid = uuid4()
    node_uuid = uuid4()
    timestamp = now_iso8601()

    node = create_json_node(sim_uuid=sim_uuid,
                            timestamp=timestamp,
                            uuid=node_uuid,
                            node_label='1')

    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    datastore.store_item(node)
    result = datastore.load_item('node', node_uuid)
    assert result.uuid == str(node_uuid)


def test_store_load_network_event():
    """
        Stores/loads a network event into each of the supported database tables.
    :return:
    """
    sim_uuid = uuid4()
    network_uuid = uuid4()

    network_event = create_json_network_event(sim_uuid=sim_uuid,
                                              timestamp=now_iso8601(),
                                              uuid=network_uuid,
                                              uuid_node=uuid4(),
                                              network_event_type='open',
                                              protocol='UDP',
                                              pid=32145,
                                              src=['192.168.1.1', 64],
                                              dst=['192.168.11.200', 72])

    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    datastore.store_item(network_event)
    result = datastore.load_item('network_event', network_uuid)
    assert result.uuid == str(network_uuid)


def test_store_load_log():
    """
        Stores/loads a log into each of the supported database tables.
    :return:
    """
    sim_uuid = uuid4()
    log_uuid = uuid4()

    log = create_json_log(sim_uuid=sim_uuid,
                          timestamp=now_iso8601(),
                          uuid=log_uuid,
                          content='log msg',
                          level='DEBUG')

    datastore = DatastoreRestClient(sim_uuid=sim_uuid)

    datastore.store_item(log)
    result = datastore.load_item('log', log_uuid)
    assert result.uuid == str(log_uuid)
