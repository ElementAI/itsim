import pytest
import os
import uuid
from itsim.datastore.database import DatabaseSQLite
from itsim.schemas.itsim_items import create_json_item
from itsim.time import now_iso8601
from contextlib import contextmanager


@contextmanager
def db_file():
    sqlite_file_name = '.sqlite'
    try:
        if os.path.isfile(sqlite_file_name):
            os.remove(sqlite_file_name)
        yield(sqlite_file_name)
    finally:
        if os.path.isfile(sqlite_file_name):
            os.remove(sqlite_file_name)


def test_create_tables():

    with db_file() as (sqlite_file):
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


def test_insert_items():
    """
        Insert an item into each of the supported database tables.
    :return:
    """
    with db_file() as (sqlite_file):
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


def test_select_items():
    """
        Load an item from each of the supported database tables.
    :return:
    """
    with db_file() as (sqlite_file):
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


def test_select_items_timerange():

    def create_dummy_network_event(timestamp, network_uuid):
        return create_json_item(sim_uuid=sim_uuid,
                                timestamp=timestamp,
                                item_type="network_event",
                                uuid=network_uuid,
                                uuid_node=str(uuid.uuid4()),
                                network_event_type='open',
                                protocol='UDP',
                                pid=32145,
                                src=['192.168.1.1', 64],
                                dst=['192.168.11.200', 72])

    with db_file() as (sqlite_file):
        sim_uuid = str(uuid.uuid4())
        network_uuid_1 = str(uuid.uuid4())
        network_uuid_2 = str(uuid.uuid4())
        network_uuid_3 = str(uuid.uuid4())
        network_uuid_4 = str(uuid.uuid4())
        network_uuid_5 = str(uuid.uuid4())

        timestamp1 = now_iso8601()
        database = DatabaseSQLite(sqlite_file=sqlite_file)

        network_event_1 = create_dummy_network_event(now_iso8601(), network_uuid_1)
        database.insert_items(network_event_1.timestamp,
                              network_event_1.sim_uuid,
                              network_event_1)

        timestamp2 = now_iso8601()
        network_event_2 = create_dummy_network_event(now_iso8601(), network_uuid_2)
        database.insert_items(network_event_2.timestamp,
                              network_event_2.sim_uuid,
                              network_event_2)

        timestamp3 = now_iso8601()
        network_event_3 = create_dummy_network_event(now_iso8601(), network_uuid_3)
        database.insert_items(network_event_3.timestamp,
                              network_event_3.sim_uuid,
                              network_event_3)

        network_event_4 = create_dummy_network_event(now_iso8601(), network_uuid_4)
        database.insert_items(network_event_4.timestamp,
                              network_event_4.sim_uuid,
                              network_event_4)

        network_event_5 = create_dummy_network_event(now_iso8601(), network_uuid_5)
        database.insert_items(network_event_5.timestamp,
                              network_event_5.sim_uuid,
                              network_event_5)

        timestamp6 = now_iso8601()

        result = database.select_items('network_event', from_time=timestamp1, to_time=timestamp2)
        assert len(result) == 1
        assert result[0].uuid == network_uuid_1

        result = database.select_items('network_event', from_time=timestamp1, to_time=timestamp3)
        assert len(result) == 2
        assert result[0].uuid == network_uuid_1
        assert result[1].uuid == network_uuid_2

        result = database.select_items('network_event', from_time=timestamp2, to_time=timestamp6)
        assert len(result) == 4
        assert result[0].uuid == network_uuid_2
        assert result[1].uuid == network_uuid_3
        assert result[2].uuid == network_uuid_4
        assert result[3].uuid == network_uuid_5
