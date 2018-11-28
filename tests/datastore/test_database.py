from itsim.datastore.database import DatabaseSQLite
from itsim.schemas.itsim_items import create_json_item
import uuid
from itsim.time import now_iso8601
import pytest
import os

sqlite_file = 'test.sqlite'

def test_create_tables():
    if os.path.isfile(sqlite_file):
        os.remove(sqlite_file)

    sim_uuid = str(uuid.uuid4())
    node_uuid = str(uuid.uuid4())
    timestamp = now_iso8601()

    node = create_json_item(sim_uuid=sim_uuid,
                            timestamp=timestamp,
                            item_type='node',
                            uuid=node_uuid,
                            node_label='1')

    database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=False)

    # Expected to fail as tables are not created in DB
    with pytest.raises(Exception):
        database.insert_items(node.timestamp, node.sim_uuid, node)

    if os.path.isfile(sqlite_file):
        os.remove(sqlite_file)

    # Expected to pass as tables are created in DB
    database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
    database.insert_items(node.timestamp, node.sim_uuid, node)

    if os.path.isfile(sqlite_file):
        os.remove(sqlite_file)


def test_insert_items():
    """
        Insert an item into each of the supported database tables.
    :return:
    """

    sim_uuid = str(uuid.uuid4())
    node_uuid = str(uuid.uuid4())
    timestamp = now_iso8601()

    node = create_json_item(sim_uuid=sim_uuid,
                            timestamp=timestamp,
                            item_type='node',
                            uuid=node_uuid,
                            node_label='1')

    network_event = create_json_item(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            item_type="network_event",
                            uuid=str(uuid.uuid4()),
                            uuid_node=str(uuid.uuid4()),
                            network_event_type='open',
                            protocol='UDP',
                            pid=32145,
                            src=['192.168.1.1', 64],
                            dst=['192.168.11.200', 72])

    log = create_json_item(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            item_type="log",
                            uuid=str(uuid.uuid4()),
                            content='log msg',
                            level='DEBUG')


    database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)

    database.insert_items(node.timestamp, node.sim_uuid, node)
    database.insert_items(network_event.timestamp, network_event.sim_uuid, network_event)
    database.insert_items(log.timestamp, log.sim_uuid, log)

    if os.path.isfile(sqlite_file):
        os.remove(sqlite_file)


def test_select_items():
    """
        Load an item from each of the supported database tables.
    :return:
    """

    sim_uuid = str(uuid.uuid4())
    node_uuid = str(uuid.uuid4())
    log_uuid = str(uuid.uuid4())
    network_uuid = str(uuid.uuid4())
    timestamp = now_iso8601()

    node = create_json_item(sim_uuid=sim_uuid,
                            timestamp=timestamp,
                            item_type='node',
                            uuid=node_uuid,
                            node_label='1')

    network_event = create_json_item(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            item_type="network_event",
                            uuid=network_uuid,
                            uuid_node=str(uuid.uuid4()),
                            network_event_type='open',
                            protocol='UDP',
                            pid=32145,
                            src=['192.168.1.1', 64],
                            dst=['192.168.11.200', 72])

    log = create_json_item(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            item_type="log",
                            uuid=log_uuid,
                            content='log msg',
                            level='DEBUG')


    database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)

    database.insert_items(node.timestamp, node.sim_uuid, node)
    database.insert_items(network_event.timestamp, network_event.sim_uuid, network_event)
    database.insert_items(log.timestamp, log.sim_uuid, log)

    result = database.select_items('node', node.uuid)
    assert len(result) == 1
    assert result[0].uuid == node.uuid

    result = database.select_items('log', log.uuid)
    assert len(result) == 1
    assert result[0].uuid == log.uuid

    result = database.select_items('network_event', network_event.uuid)
    assert len(result) == 1
    assert result[0].uuid == network_event.uuid

    result = database.select_items('node', str(uuid.uuid4()))
    assert len(result) == 0

    database.select_items('network_event', str(uuid.uuid4()))
    assert len(result) == 0

    database.select_items('log', str(uuid.uuid4()))
    assert len(result) == 0

    if os.path.isfile(sqlite_file):
        os.remove(sqlite_file)


# TODO: ADD TO-FROM

