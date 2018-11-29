from abc import abstractmethod
import sqlite3
import json
from collections import namedtuple
from typing import Any


class Database:
    """
     Base class for datastore database implementations
    """
    def __init(self) -> None:
        pass

    @abstractmethod
    def create_tables(self) -> None:
        pass

    @abstractmethod
    def select_items(self, table_name, query_conditions, str_output=False, from_time=None, to_time=None) -> Any:
        pass

    @abstractmethod
    def insert_items(self, time, sim_uuid, item_list) -> None:
        pass


class DatabaseSQLite(Database):
    """
        Database implementation for SQLite

        Notes:      Timestamp TEXT as ISO8601 strings (“YYYY-MM-DD HH:MM:SS.SSS”).
                    https://sqlitebrowser.org/

    :param sqlite_file:
    :param create_tables_if_absent:
    """
    def __init__(self, sqlite_file: str, create_tables_if_absent: bool = True) -> None:
        self._sqlite_file = sqlite_file
        self._conn = sqlite3.connect(self._sqlite_file)
        if create_tables_if_absent:
            self.create_tables()

    def create_tables(self) -> Any:
        """

        :param table_name:
        :return:
        """
        try:
            with self._conn:
                cursor = self._conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS network_event(uuid TEXT, timestamp TEXT, sim_uuid TEXT, "
                               "json TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS node(uuid TEXT, timestamp TEXT, sim_uuid TEXT, json TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS log(uuid TEXT, timestamp TEXT, sim_uuid TEXT, json TEXT)")
                # TODO add all other tables here!
        except sqlite3.IntegrityError:
            print("SQLite create tables failedfailed.")

    def select_items(self,
                     table_name: str,
                     uuid: str = None,
                     str_output: bool = False,
                     from_time: str = None,
                     to_time: str = None) -> Any:
        """
            Note: add simulation uuid to queries (for supporting logging from multiple sims running at once)

        :param table_name:
        :param conditions:
        :param str_output:
        :param from_time:
        :param to_time:
        :return:
        """
        try:
            with self._conn:
                cursor = self._conn.cursor()

                from_time = None if from_time == 'None' else from_time
                to_time = None if to_time == 'None' else to_time

                # TODO: support all tables here
                if table_name == "network_event":
                    if uuid is not None:
                        if from_time is not None and to_time is not None:
                            cursor.execute('SELECT * FROM network_event WHERE uuid=? AND timestamp BETWEEN ? AND ?',
                                           (uuid, from_time, to_time))
                        else:
                            cursor.execute('SELECT * FROM network_event WHERE uuid=?', (uuid,))
                    else:
                        if from_time is not None and to_time is not None:
                            cursor.execute('SELECT * FROM network_event WHERE timestamp BETWEEN ? AND ?',
                                           (from_time, to_time))
                        else:
                            cursor.execute('SELECT * FROM network_event')
                elif table_name == "node":
                    if uuid is not None:
                        if from_time is not None and to_time is not None:
                            cursor.execute('SELECT * FROM node WHERE uuid=? AND timestamp BETWEEN ? AND ?',
                                           (uuid, from_time, to_time))
                        else:
                            cursor.execute('SELECT * FROM node WHERE uuid=?', (uuid,))
                    else:
                        if from_time is not None and to_time is not None:
                            cursor.execute('SELECT * FROM node WHERE timestamp BETWEEN ? AND ?', (from_time, to_time))
                        else:
                            cursor.execute('SELECT * FROM node')

                elif table_name == "log":
                    if uuid is not None and uuid != 'None':
                        if from_time is not None and to_time is not None:
                            cursor.execute('SELECT * FROM log WHERE uuid=? AND timestamp BETWEEN ? AND ?',
                                           (uuid, from_time, to_time))
                        else:
                            cursor.execute('SELECT * FROM log WHERE uuid=?', (uuid,))
                    else:
                        if from_time is not None and to_time is not None:
                            cursor.execute('SELECT * FROM log WHERE timestamp BETWEEN ? AND ?', (from_time, to_time))
                        else:
                            cursor.execute('SELECT * FROM log')

                all_rows = cursor.fetchall()

                json_results = []
                for row in all_rows:
                    if str_output:
                        json_results.append(row[3])
                    else:
                        json_results.append(
                            json.loads(row[3], object_hook=lambda d: namedtuple('X', d.keys())(*d.values())))
                return json_results
        except sqlite3.IntegrityError:
            print("SQLite select failed.")

    def insert_items(self, timestamp: str, sim_uuid: str, items: Any) -> None:
        try:
            with self._conn:
                cursor = self._conn.cursor()

                if isinstance(items, list):
                    data = []
                    for item in items:
                        table_name = item.type
                        uuid = item.uuid
                        entry = (uuid, timestamp, sim_uuid, json.dumps(item))
                        data.append(entry)
                    if table_name == "network_event":
                        cursor.executemany("INSERT INTO network_event VALUES (?, ?, ?, ?)", data)
                    elif table_name == "node":
                        cursor.executemany("INSERT INTO node VALUES (?, ?, ?, ?)", data)
                    elif table_name == "log":
                        cursor.executemany("INSERT INTO log VALUES (?, ?, ?, ?)", data)
                    # TODO: add cases for all tables explicitely here
                else:
                    item = items
                    table_name = item['type']
                    uuid = item['uuid']
                    if table_name == "network_event":
                        cursor.execute(
                            "INSERT INTO network_event (uuid, timestamp, sim_uuid, json) VALUES (?, ?, ?, ?)",
                            (uuid, timestamp, sim_uuid, json.dumps(item)))
                    elif table_name == "node":
                        cursor.execute("INSERT INTO node (uuid, timestamp, sim_uuid, json) VALUES (?, ?, ?, ?)",
                                       (uuid, timestamp, sim_uuid, json.dumps(item)))
                    elif table_name == "log":
                        cursor.execute("INSERT INTO log (uuid, timestamp, sim_uuid, json) VALUES (?, ?, ?, ?)",
                                       (uuid, timestamp, sim_uuid, json.dumps(item)))
                    # TODO: add cases for all tables explicitely here

        except sqlite3.IntegrityError:
            print("SQLite insert_items failed.")
