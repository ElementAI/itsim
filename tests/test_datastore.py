import uuid
from itsim.datastore.datastore import DatastoreLocalClient, DatastoreRestClient
from itsim.schemas.itsim_items import create_json_item
from itsim.time import now_iso8601


"""
    Need a datastore server to be running (ex: $python itsim/datastore/datastore_server.py)


    TODO: look at using xprocess to start the server from the test
        from xprocess import ProcessStarter
        import pytest
        import os

        @pytest.fixture
        def datastore_server(xprocess):
            class Starter(ProcessStarter):
                pattern = "* Debugger PIN: 264-453-431"
                args = ['itsim/datastore/datastore.py']
            logfile = xprocess.ensure("myserver", Starter)
            # conn = # create a connection or url/port info to the server
            return
"""


def test_datastore_local_store_load_node():
    """
        This is testing a local datastore, i.e. without any datastore server running.
        The datastore uses a SQLite database to archive its data.

    :return:
    """
    # Connect to a datastore
    datastore = DatastoreLocalClient(type='sqlite', sqlite_file='itsim/datastore/storage/sqlite_01.sqlite')

    # This json node content must be handled by the node class
    sim_uuid = str(uuid.uuid4())   # to be taken from simulation object
    node_uuid = str(uuid.uuid4())
    node = create_json_item(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            item_type='node',
                            uuid=node_uuid,
                            node_label="pc_001")

    # Posting a node to the datastore
    response_code = datastore.store_item(sim_uuid, node)
    assert response_code == 201

    # Retrieving the node from the datastore
    item_type = 'node'
    node, response_code = datastore.load_item(item_type, node_uuid)
    assert response_code == 201
    assert node.uuid == node_uuid


def test_datastore_rest_store_load_node():
    """
        This is testing a remote datastore over a rest api.
        The datastore uses a SQLite database to archive its data.

        To launch the datastore:

    :return:
    """

    # This json node content must be handled by the node class
    sim_uuid = str(uuid.uuid4())   # should be in simulation object
    node_uuid = str(uuid.uuid4())
    node = create_json_item(sim_uuid=sim_uuid,
                            timestamp=now_iso8601(),
                            item_type='node',
                            uuid=node_uuid,
                            node_label="pc_001")

    # Connect to a datastore
    datastore = DatastoreRestClient(sim_uuid=sim_uuid, base_url='http://localhost:5000')

    # Posting a node to the datastore
    datastore.store_item(node)

    # Retrieving the node from the datastore
    item_type = 'node'
    node, response_code = datastore.load_item(item_type, node_uuid)
    assert response_code == 201
    assert node.uuid == node_uuid

