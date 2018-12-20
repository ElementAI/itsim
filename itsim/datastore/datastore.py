from abc import abstractmethod
import requests
import json
import os
import logging
from logging import Logger
from collections import namedtuple
from typing import Any, Dict, Optional
from queue import Queue
from threading import Thread, Timer
from itsim.datastore.datastore_server import DatastoreRestServer
from itsim.logging import create_logger
from uuid import uuid4, UUID
import tempfile


class DatastoreClient:
    """
        Base class for datastore client implementation
    """
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def load_item(self, item_type: str, uuid: UUID, from_time: str = None, to_time: str = None) -> str:
        pass

    @abstractmethod
    def store_item(self, data: Any, overwrite: bool = True) -> None:
        pass

    @abstractmethod
    def delete(self, item_type: str, uuid: UUID):
        pass


class DatastoreRestClient(DatastoreClient):

    def __init__(self, hostname: str = '0.0.0.0', port: int = 5000, sim_uuid: UUID = uuid4()) -> None:
        self._sim_uuid = sim_uuid
        self._headers = {'Accept': 'application/json'}
        self._url = f'http://{hostname}:{port}/'
        self._started_server = False

        if not self.server_is_alive():
            _, self._db_file = tempfile.mkstemp(suffix=".sqlite")
            port = self.launch_server_thread(hostname)
            self._started_server = True
            self._url = f'http://{hostname}:{port}/'
            print(f"Couldn't find server, launching a local instance: {self._url}")

    def __del__(self) -> None:
        """
            Shuts down the datastore server if it was created by constructor
        """
        timeout_thr_join = 5.0

        if self._started_server:
            response = requests.post(f'{self._url}stop')
            if response.status_code != 200:
                raise RuntimeError("Error shutting down the Datastore Server.")
            self._thr.join(timeout=timeout_thr_join)
            if os.path.isfile(self._db_file):
                os.remove(self._db_file)

    def server_is_alive(self) -> bool:
        try:
            is_alive_url = f'{self._url}isrunning/{self._sim_uuid}'
            print(is_alive_url)
            page = requests.get(is_alive_url)
            return page.status_code == 200
        except Exception:
            return False

    def launch_server_thread(self, hostname) -> int:
        def start_and_run_server(server, hostname, queue_port):
            for port in range(5000, 2 ** 16 - 1):
                timer = None
                try:
                    timer = Timer(0.05, lambda: queue_port.put(port))
                    timer.start()
                    server.run(host=hostname, port=port, debug=False)
                    return
                except OSError as err:
                    if err.errno == 97:  # Port already in use.
                        if timer is not None:
                            timer.cancel()
            # At this point, we were unable to find a suitable port -- fail.
            queue_port.put(0)
        server = DatastoreRestServer(type="sqlite", sqlite_file=self._db_file)
        queue_port: Queue = Queue()
        self._thr = Thread(target=start_and_run_server, args=(server, hostname, queue_port))
        self._thr.start()
        port = queue_port.get()
        if port == 0:
            raise RuntimeError('Unable to start the datastore server')
        return port

    # Creating the logger for console and datastore output
    def create_logger(self,
                      logger_name: str = __name__,
                      console_level=logging.DEBUG,
                      datastore_level=logging.DEBUG) -> Logger:

        return create_logger(logger_name,
                             self._sim_uuid,
                             self._url,
                             console_level,
                             datastore_level)

    def load_item(self, item_type: str, uuid: UUID, from_time: Optional[str] = None,
                  to_time: Optional[str] = None) -> str:
        """
            Requests GET
        """
        response = requests.get(f'{self._url}{item_type}/{str(uuid)}',
                                headers=self._headers,
                                json={'from_time': from_time, 'to_time': to_time})

        if response.status_code not in range(200, 299):
            raise RuntimeError("Error raised while loading data from server")
            return ''
        else:
            return json.loads(json.loads(response.content),
                              object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

    def store_item(self, data: Any, overwrite: Optional[bool] = True) -> None:
        """
            Requests POST
        """
        response = requests.post(f'{self._url}{data.type}/{data.uuid}',
                                 headers=self._headers,
                                 json=data)
        if response.status_code not in range(200, 299):
            raise RuntimeError("Error raised while storing data on server")

    def delete(self, item_type: str, uuid: UUID) -> None:
        pass


class DatastoreClientFactory:

    _shared: Dict[str, Any] = {}

    def __init__(self):
        self.__dict__ = DatastoreClientFactory._shared
        if len(DatastoreClientFactory._shared) == 0:
            self._hostname: str = "localhost"
            self._port: int = 5000
            self._sim_uuid: UUID = uuid4()

    @property
    def hostname(self) -> str:
        return self._hostname

    @hostname.setter
    def hostname(self, hostname: str) -> None:
        if len(hostname) == 0:
            raise ValueError("Empty string forbidden")
        self._hostname = hostname

    @property
    def port(self) -> int:
        return self._port

    @port.setter
    def port(self, port: int) -> None:
        if port <= 0 or port >= 2 ** 16:
            raise ValueError("Port out of useful range")
        self._port = port

    @property
    def sim_uuid(self) -> UUID:
        return self._sim_uuid

    @sim_uuid.setter
    def sim_uuid(self, uuid: UUID) -> None:
        self._sim_uuid = uuid

    def get_client(self, sim_uuid: Optional[UUID] = None):
        return DatastoreRestClient(self.hostname, self.port, sim_uuid or self.sim_uuid)
