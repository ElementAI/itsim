from abc import abstractmethod
import requests
import json
from collections import namedtuple
from itsim.schemas.itsim_items import itsim_object_types
from itsim.time import now_iso8601
from typing import Any, List
from itsim.datastore.database import DatabaseSQLite

"""
    Local api instantiates a "local" datastore server, which handles the database interaction
    REST api requires a datastore server to be running...
"""


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
    def store_item(self, sim_uuid: str, data: Any, overwrite: bool = True) -> int:  # post
        pass

    @abstractmethod
    def create_table(self, table_name, column_list):
        pass

    @abstractmethod
    def delete(self, item_type, uuid):
        pass


class DatastoreLocalClient(DatastoreClient):

    def __init__(self, **kwargs) -> None:
        if kwargs['type'] == 'sqlite':
            self._database = DatabaseSQLite(kwargs['sqlite_file'])
            self._database.open_connection()

        elif kwargs['type'] == 'postgresql':
            # host = kwargs['host']
            # database = kwargs['database']
            # user = kwargs['user']
            # password = kwargs['password']
            # self._database = ...
            raise NotImplementedError
        self._table_names = itsim_object_types

    def load_item(self, item_type: str, uuid: str = None, from_time: str = None, to_time: str = None) -> Any:
        """
            Equivalent to REST server 'GET'

        :param item_type:
        :param uuid:
        :return:
        """
        assert item_type in self._table_names, "Invalid item_type: {0} not in self._table_names".format(item_type)

        if uuid is not None:
            query_conditions = [{'column': 'uuid', 'operator': '=', 'value': uuid}]
            items = self._database.select_items(item_type, query_conditions)
        elif from_time is not None and to_time is not None:
            items = self._database.select_items(item_type, conditions=None, from_time=from_time, to_time=to_time)
        else:
            return None, 404

        if len(items) == 0:
            return "Node not found", 404
        else:
            return items[0], 201

    def store_item(self, sim_uuid: str, data: Any, overwrite: bool = True) -> int:
        """
            Equivalent to REST server 'POST'

        :param sim_uuid:
        :param data: either a list of itsim objects (as json_data) or a single one.
        :param overwrite:
        :return:
        """
        time = now_iso8601()
        items: List[Any] = []
        if isinstance(data, list):
            items = data
        else:
            items.append(data)

        self._database.insert_items(time, sim_uuid, items)

        return 201

    def delete(self, item_type: str, uuid: str) -> None:
        pass

    def create_table(self, table_name: str, column_list: List[str]) -> None:
        self._database.create_table(table_name, column_list)


# TODO: fix store_item(): inconsistent with base class...
# class DatastoreRestClient(DatastoreClient):
class DatastoreRestClient():

    def __init__(self, **kwargs) -> None:
        self.base_url = kwargs['base_url']              # ex: 'http://localhost:5000'
        self._sim_uuid = kwargs['sim_uuid']
        self._headers = {'Accept': 'application/json'}

    def url(self, type: str, uuid: str) -> str:
        return '{0}/{1}/{2}'.format(self.base_url, type, uuid)

    def load_item(self, item_type: str, uuid: str, from_time: str = None, to_time: str = None) -> Any:
        """
            Requests GET

        :param item_type:
        :param uuid:
        :return:
        """

        request_time_range = {'from_time': from_time, 'to_time': to_time}
        response = requests.get(self.url(item_type, uuid), headers=self._headers, json=request_time_range)

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
        response = requests.post(self.url(data.type, data.uuid), headers=self._headers, json=data)
        return response.text  # 201?

    def delete(self, item_type: str, uuid: str) -> None:
        pass

    def create_table(self, table_name: str, column_list: List[str]) -> None:
        pass
