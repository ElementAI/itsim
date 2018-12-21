import pytest
import os
import tempfile
import sqlite3
from uuid import UUID, uuid4
from itsim.datastore.database import DatabaseSQLite
from itsim.schemas.items import create_json_node, create_json_network_event, create_json_log
from itsim.time import now_iso8601
from contextlib import contextmanager


@contextmanager
def db_file():

    try:
        _, sqlite_file_name = tempfile.mkstemp(suffix=".sqlite")
        yield(sqlite_file_name)
    finally:
        if os.path.isfile(sqlite_file_name):
            os.remove(sqlite_file_name)


def test_create_tables():

    with db_file() as (sqlite_file):
        sim_uuid = uuid4()
        node_uuid = uuid4()
        timestamp = now_iso8601()

        node = create_json_node(sim_uuid=sim_uuid,
                                timestamp=timestamp,
                                uuid=node_uuid,
                                node_label='1')

        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=False)

        # Expected to fail as tables are not created in DB
        with pytest.raises(sqlite3.OperationalError):
            database.insert_items(node)

        if os.path.isfile(sqlite_file):
            os.remove(sqlite_file)

        # Expected to pass as tables are created in DB
        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(node)


def test_insert_node():
    """
        Insert node item in the database table.
    :return:
    """
    with db_file() as (sqlite_file):
        sim_uuid = uuid4()
        node_uuid = uuid4()
        timestamp = now_iso8601()

        node = create_json_node(sim_uuid=sim_uuid,
                                timestamp=timestamp,
                                uuid=node_uuid,
                                node_label='1')
        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(node)


def test_insert_network_event():
    """
        Insert a network event into the database table.
    :return:
    """
    with db_file() as (sqlite_file):
        sim_uuid = uuid4()

        network_event = create_json_network_event(sim_uuid=sim_uuid,
                                                  timestamp=now_iso8601(),
                                                  uuid=uuid4(),
                                                  tags=[],
                                                  uuid_node=uuid4(),
                                                  network_event_type='open',
                                                  protocol='UDP',
                                                  pid=32145,
                                                  src=['192.168.1.1', 64],
                                                  dst=['192.168.11.200', 72])

        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(network_event)


def test_insert_log():
    """
        Insert a log into the database table.
    :return:
    """
    with db_file() as (sqlite_file):
        sim_uuid = uuid4()

        log = create_json_log(sim_uuid=sim_uuid,
                              timestamp=now_iso8601(),
                              uuid=uuid4(),
                              content='log msg',
                              level='DEBUG')

        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(log)


def test_select_node():
    """
        Load/store a node item from the database table.
    :return:
    """
    with db_file() as (sqlite_file):
        sim_uuid = uuid4()
        node_uuid = uuid4()
        timestamp = now_iso8601()

        node = create_json_node(sim_uuid=sim_uuid,
                                timestamp=timestamp,
                                uuid=node_uuid,
                                node_label='1')

        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(node)
        result = database.select_items('node', node.uuid)
        assert len(result) == 1
        assert result[0].uuid == node.uuid

        result = database.select_items('node', str(uuid4()))
        assert len(result) == 0


def test_select_network_event():
    """
        Load/store a network event item from the database table.
    :return:
    """
    with db_file() as (sqlite_file):
        sim_uuid = uuid4()
        network_uuid = uuid4()

        network_event = create_json_network_event(sim_uuid=sim_uuid,
                                                  timestamp=now_iso8601(),
                                                  uuid=network_uuid,
                                                  tags=[],
                                                  uuid_node=uuid4(),
                                                  network_event_type='open',
                                                  protocol='UDP',
                                                  pid=32145,
                                                  src=['192.168.1.1', 64],
                                                  dst=['192.168.11.200', 72])

        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(network_event)
        result = database.select_items('network_event', network_event.uuid)
        assert len(result) == 1
        assert result[0].uuid == network_event.uuid
        result = database.select_items('node', str(uuid4()))
        assert len(result) == 0


def test_select_log():
    """
        Load/store a log item from the database table.
    :return:
    """
    with db_file() as (sqlite_file):
        sim_uuid = uuid4()
        log_uuid = uuid4()
        log = create_json_log(sim_uuid=sim_uuid,
                              timestamp=now_iso8601(),
                              uuid=log_uuid,
                              content='log msg',
                              level='DEBUG')

        database = DatabaseSQLite(sqlite_file=sqlite_file, create_tables_if_absent=True)
        database.insert_items(log)
        result = database.select_items('log', log.uuid)
        assert len(result) == 1
        assert result[0].uuid == log.uuid

        result = database.select_items('log', str(uuid4()))
        assert len(result) == 0


def test_select_items_timerange():

    def create_dummy_network_event(sim_uuid: UUID, timestamp: str, network_uuid: UUID):
        return create_json_network_event(sim_uuid=sim_uuid,
                                         timestamp=timestamp,
                                         uuid=network_uuid,
                                         tags=[],
                                         uuid_node=uuid4(),
                                         network_event_type='open',
                                         protocol='UDP',
                                         pid=32145,
                                         src=['192.168.1.1', 64],
                                         dst=['192.168.11.200', 72])

    with db_file() as (sqlite_file):
        sim_uuid = uuid4()
        nb_events = 5
        network_uuid = []
        timestamps = []
        database = DatabaseSQLite(sqlite_file=sqlite_file)

        for i in range(nb_events):
            timestamps.append(now_iso8601())
            network_uuid.append(uuid4())
            database.insert_items(create_dummy_network_event(sim_uuid, now_iso8601(), network_uuid[i]))
        timestamps.append(now_iso8601())

        for ts_index_start, ts_index_stop in [(0, 1), (0, 2), (1, nb_events - 1)]:
            results = database.select_items('network_event',
                                            from_time=timestamps[ts_index_start],
                                            to_time=timestamps[ts_index_stop])
            expected_result_len = ts_index_stop - ts_index_start
            assert len(results) == expected_result_len
            assert [str(network_uuid[i]) for i in range(ts_index_start, ts_index_stop)] == [r.uuid for r in results]
