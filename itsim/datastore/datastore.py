from abc import abstractmethod
import requests
import json
import os
import logging
from logging import Logger
from collections import namedtuple
from typing import Any
from queue import Queue
from threading import Thread, Timer
from itsim.datastore.datastore_server import DatastoreRestServer
from itsim.logging import create_logger
from uuid import uuid4, UUID


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
        self._db_file = '.sqlite'
        self._url = f'http://{hostname}:{port}/'
        self._started_server = 'no'

        if not self.server_is_alive():
            port = self.launch_server_thread(hostname)
            self._started_server = 'yes'
            self._url = f'http://{hostname}:{port}/'
            print(f"Couldn't find server, launching a local instance: {self._url}")

    def __del__(self) -> None:
        """
            Shuts down the datastore server if it was created by constructor
        """
        if self._started_server == 'yes':
            response = requests.post(f'{self._url}stop')
            if response.status_code != 200:
                print("Error shutting down the Datastore Server.")
            self._thr.join(timeout=5.0)
            if os.path.isfile(self._db_file):
                os.remove(self._db_file)

    def server_is_alive(self) -> bool:
        try:
            print(f'{self._url}isrunning/{self._sim_uuid}')
            page = requests.get(f'{self._url}isrunning/{self._sim_uuid}')
            if page.status_code == 200:
                return True
            else:
                return False
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

    def load_item(self, item_type: str, uuid: UUID, from_time: str = None, to_time: str = None) -> str:
        """
            Requests GET
        """
        response = requests.get(f'{self._url}{item_type}/{str(uuid)}',
                                headers=self._headers,
                                json={'from_time': from_time, 'to_time': to_time})

        if response.status_code == 404:
            raise RuntimeError("Unable to load data from server (Get returned status code 404)")
            return ''
        else:
            return json.loads(json.loads(response.content),
                              object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))

    def store_item(self, data: Any, overwrite: bool = True) -> None:
        """
            Requests POST
        """
        response = requests.post(f'{self._url}{data.type}/{data.uuid}',
                                 headers=self._headers,
                                 json=data)
        if response.text != '"ok"\n':
            raise RuntimeError("Unable to store data on server (Post didn't return 'OK')")

    def delete(self, item_type: str, uuid: UUID) -> None:
        pass
