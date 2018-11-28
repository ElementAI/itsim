from abc import abstractmethod
import requests
import json
from collections import namedtuple
from typing import Any
from queue import Queue
from threading import Thread, Timer
from itsim.datastore.datastore_server import DatastoreRestServer
from uuid import uuid4, UUID

class DatastoreClient:
    """
        Base class for datastore client implementation
    """
    def __init__(self, **kwargs):
        pass

    @abstractmethod
    def load_item(self, item_type: str, uuid: str, from_time: str = None, to_time: str = None) -> Any:  # get
        pass

    @abstractmethod
    def store_item(self, data: Any, overwrite: bool = True) -> str: # post
        pass

    @abstractmethod
    def delete(self, item_type, uuid):
        pass


class DatastoreRestClient(DatastoreClient):

    def __init__(self, hostname: str='0.0.0.0', port: int=5000, sim_uuid: UUID=uuid4()) -> None:
        self._hostname = hostname
        self._port = port
        self._sim_uuid = sim_uuid
        self._headers = {'Accept': 'application/json'}
        self._thr = None

        if not self.server_is_alive():
            self.launch_server_thread()
            print(f"Couldn't find server, launching a local instance: http://{self._hostname}:{self._port}/")

    def __del__(self):
        """
            Shutsdown the datastore server if it was created by constructor
        :return:
        """
        if self._thr is not None:
            response = requests.post(f"http://{self._hostname}:{self._port}/stop")
            if response.status_code != 200:
                print("Error shutting down the Datastore Server.")
            self._thr.join(timeout=5.0)

    def server_is_alive(self):
        try:
            print(f'http://{self._hostname}:{self._port}/isrunning/{self._sim_uuid}')
            page = requests.get(f'http://{self._hostname}:{self._port}/isrunning/{self._sim_uuid}')
            if page.status_code == 200:
                return True
            else:
                return False
        except:
            return False

    def launch_server_thread(self):
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
        try:
            server = DatastoreRestServer(type="sqlite", sqlite_file=":memory:")
            queue_port = Queue()
            self._thr = Thread(target=start_and_run_server, args=(server, self._hostname, queue_port))
            self._thr.start()
            self._port = queue_port.get()
            if self._port == 0:
                raise Exception('Unable to start the datastore server')
        except:
            print('Unable to start the datastore server.')

    def load_item(self, item_type: str, uuid: str, from_time: str = None, to_time: str = None) -> Any:
        """
            Requests GET

        :param item_type:
        :param uuid:
        :return:
        """
        response = requests.get(f'http:://{self._hostname}:{self._port}/{item_type}/{uuid}',
                                headers=self._headers,
                                json={'from_time': from_time, 'to_time': to_time})

        if response.status_code == 404:
            return None, 404

        response_json = json.loads(json.loads(response.content),
                                   object_hook=lambda d: namedtuple('X', d.keys())(*d.values()))
        return response_json, response.status_code

    def store_item(self, data: Any, overwrite: bool = True) -> str:
        """
            Requests POST

        :param data:
        :param overwrite:
        :return:
        """
        response = requests.post(f'http://{self._hostname}:{self._port}/{data.type}/{data.uuid}',
                                 headers=self._headers,
                                 json=data)
        return response.text  # 201?

    def delete(self, item_type: str, uuid: str) -> None:
        pass
