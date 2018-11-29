import logging
import requests
import uuid

from logging import Handler, Formatter, Logger
from itsim.schemas.itsim_items import create_json_item
from itsim.time import now_iso8601
from typing import Any


"""
    ITSIM logging provides console and rest datastore handlers for outputting logs (an additional handler for a local
    datastore could be added if required).
"""


class DatastoreRestHandler(Handler):

    def __init__(self, server: str) -> None:
        """
        Logging handler to dispatch logs to a datastore rest server

        :param server: Server's url (ex: 'http://localhost:5000/')
        """
        self._server_url = server
        super(DatastoreRestHandler, self).__init__()

    def emit(self, record: Any) -> Any:
        """
        Method for posting data to the datastore server.

        :param record: Log data
        :return: post's response
        """
        log_uuid, log_entry = self.format(record)
        url = self._server_url + 'log/' + log_uuid
        headers = {'Accept': 'application/json'}
        return requests.post(url, headers=headers, json=log_entry)


class DatastoreFormatter(Formatter):

    def __init__(self, sim_uuid: str) -> None:
        """
        Formatter allowing a log entry to be converted to a JSON object (for sending it to a datastore server)
        :param sim_uuid: Simulation's uuid
        """

        self._sim_uuid = sim_uuid
        super(DatastoreFormatter, self).__init__()

    def format(self, record: Any) -> Any:
        """
        Create a JSON object from the log data.

        :param record: log data
        :return: tuple: log's uuid, JSON log object
        """

        log_uuid = str(uuid.uuid4())
        log = create_json_item(sim_uuid=self._sim_uuid,
                               timestamp=now_iso8601(),
                               item_type='log',
                               uuid=log_uuid,
                               content=record.message,
                               level=record.levelname)
        return log_uuid, log


def create_logger(name: str,
                  sim_uuid: str,
                  datastore_server: str,
                  console_level: Any = None,
                  datastore_level: Any = None) -> Logger:
    """
    Function for setting up the itsim logger (avoids subclassing the Python logging class)

    :param name: Python logger name
    :param sim_uuid: simulation's uuid
    :param console_level: log level for the console output
    :param datastore_level: log level for the datastore output
    :param datastore_server: datastore's url (ex: 'http://localhost:5000/')
    :return: logger
    """

    logger = logging.getLogger(name)

    if console_level is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if datastore_level is not None:
        datastore_formatter = DatastoreFormatter(sim_uuid)
        datastore_handler = DatastoreRestHandler(datastore_server)
        datastore_handler.setLevel(datastore_level)
        datastore_handler.setFormatter(datastore_formatter)
        logger.addHandler(datastore_handler)

    return logger
