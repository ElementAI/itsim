import uuid
import logging
from itsim.datastore.itsim_logging import create_logger
from itsim.datastore.datastore import DatastoreRestClient
from itsim.time import now_iso8601

"""
    TODO: REVIEW create_tables()... for now, tables must be created by local datastore.
"""


def example_datastore_log_store():
    """
        Requires a datastore server to be running
            From main directory:
            $ python datastore/datastore.py

    :return:
    """
    from_time = now_iso8601()

    datastore_server_url = 'http://localhost:5000'
    sim_uuid = str(uuid.uuid4())

    # Creating the logger for console and datastore output
    logger = create_logger(__name__,
                           sim_uuid=sim_uuid,
                           datastore_server=datastore_server_url,
                           console_level=logging.DEBUG,
                           datastore_level=logging.DEBUG)

    # Logging to console and datastore log table
    logger.error('This is an error')

    # Retrieving the log from the datastore
    datastore = DatastoreRestClient(sim_uuid=sim_uuid, base_url=datastore_server_url)

    to_time = now_iso8601()
    log, code = datastore.load_item('log', uuid=None, from_time=from_time, to_time=to_time)

    assert log.content == 'This is an error'
    print("Log example completed successfully!")


if __name__ == '__main__':
    example_datastore_log_store()
