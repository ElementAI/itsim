import uuid
from itsim.schemas.itsim_items import create_json_item
from itsim.datastore.datastore import DatastoreRestClient
from itsim.time import now_iso8601

"""
    To run those examples (from main itsim folder):
        $ python itsim/datastore/datastore_server.py
"""


def example_datastore_rest_store_load_node():
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
    print("Rest example completed successfully")


if __name__ == '__main__':
    example_datastore_rest_store_load_node()
