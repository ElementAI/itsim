import logging
import requests
from uuid import UUID, uuid4
from logging import Handler, Formatter, Logger
from itsim.schemas.items import create_json_log
from itsim.time import now_iso8601
from typing import Any


"""
    ITSIM logging provides console and rest datastore handlers for outputting logs (an additional handler for a local
    datastore could be added if required).
"""
global logger_name

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
        url = f'{self._server_url}log/{str(log_uuid)}'
        headers = {'Accept': 'application/json'}
        return requests.post(url, headers=headers, json=log_entry)


class DatastoreFormatter(Formatter):

    def __init__(self, sim_uuid: UUID) -> None:
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

        log_uuid = uuid4()
        log = create_json_log(sim_uuid=self._sim_uuid,
                              timestamp=now_iso8601(),
                              uuid=log_uuid,
                              content=record.message,
                              level=record.levelname)
        return log_uuid, log


def create_logger(name: str,
                  sim_uuid: UUID,
                  datastore_server: str,
                  logger_level: int = logging.DEBUG,
                  enable_console: bool = True,
                  enable_datastore: bool = True) -> None:
    """
    Function for setting up the itsim logger (avoids subclassing the Python logging class)
    """

    global logger_name
    logger_name = name
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if enable_console is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logger_level)
        console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    if enable_datastore is not None:
        datastore_formatter = DatastoreFormatter(sim_uuid)
        datastore_handler = DatastoreRestHandler(datastore_server)
        datastore_handler.setLevel(logger_level)
        datastore_handler.setFormatter(datastore_formatter)
        logger.addHandler(datastore_handler)


def get_logger() -> Logger:
    global logger_name

    try:
        return logging.getLogger(logger_name)
    except NameError:
        raise RuntimeError("A simulator needs to be created before getting the itsim logger using get_logger().")
