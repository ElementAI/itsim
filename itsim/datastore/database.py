from abc import abstractmethod
import sqlite3
import json
from collections import namedtuple
from typing import Any, List, Dict


class Database:
    """
     Base class for datastore database implementations
    """
    def __init(self) -> None:
        pass

    @abstractmethod
    def open_connection(self, **kwargs) -> None:
        pass

    @abstractmethod
    def close_connection(self, **kwargs) -> None:
        pass

    @abstractmethod
    def create_table(self, table_name, column_list) -> None:
        pass

    @abstractmethod
    def delete_table(self, table_name) -> None:
        pass

    @abstractmethod
    def select_items(self, table_name, query_conditions, str_output=False, from_time=None, to_time=None) -> Any:
        pass

    @abstractmethod
    def insert_items(self, time, sim_uuid, item_list) -> None:
        pass

    @abstractmethod
    def run_query(self, **kwargs) -> Any:
        pass


class DatabaseSQLite(Database):
    """
        Database implementation for SQLite

        Notes:      Timestamp TEXT as ISO8601 strings (“YYYY-MM-DD HH:MM:SS.SSS”).
                    https://sqlitebrowser.org/

    :param sqlite_file:
    :param create_tables_if_absent:
    """

    def __init__(self, sqlite_file: str = '', create_tables_if_absent: bool = True) -> None:
        self._sqlite_file = sqlite_file

        # For initial implementation, all tables use the same columns as follows:
        self._table_columns = [{'name': 'timestamp', 'type': 'TEXT'},
                               {'name': 'sim_uuid', 'type': 'TEXT'},
                               {'name': 'json', 'type': 'TEXT'}]
        self._itsim_object_types = [
            "node",
            "link",
            "log"
        ]
        if create_tables_if_absent:
            self.open_connection()

            for itsim_object_type in self._itsim_object_types:
                self.create_table(itsim_object_type, self._table_columns)

            self.close_connection()

    def open_connection(self, **kwargs) -> None:
        """
        Opens the database connection and gets a cursor.

        :param kwargs:
        :return:
        """
        del kwargs
        self._conn = sqlite3.connect(self._sqlite_file)
        self._c = self._conn.cursor()

    def close_connection(self, **kwargs) -> None:
        """
        Closes the database connection.

        :param kwargs:
        :return:
        """
        self._conn.close()

    def create_table(self, table_name: str, column_list: List[Any]) -> None:
        """

        :param table_name:
        :param column_list:
        :return:
        """
        table_count = self.check_if_table_exists(table_name)

        if table_count == 0:
            self._c.execute("CREATE TABLE {tn} ({nf} {ft} PRIMARY KEY)".format(tn=table_name, nf='uuid', ft='TEXT'))
            for col in column_list:
                self._c.execute("ALTER TABLE {tn} ADD COLUMN '{cn}' {ct}"
                                .format(tn=table_name, cn=col['name'], ct=col['type']))
            self._conn.commit()

    def delete_table(self, table_name: str) -> None:
        """

        :param table_name: Name of table to delete
        :return:
        """
        self._c.execute("DROP TABLE [IF EXISTS] {tn}".format(tn=table_name))
        self._conn.commit()

    def check_if_table_exists(self, table_name: str) -> Any:
        """

        :param table_name:
        :return:
        """
        self._c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{tn}'".format(tn=table_name))
        table_count = self._c.fetchall()
        table_count = table_count[0][0]
        return table_count

    def select_items(self,
                     table_name: str,
                     conditions: List[Dict[str, str]] = None,
                     str_output: bool = False,
                     from_time: str = None,
                     to_time: str = None) -> Any:

        """
        # conditions: List of query conditions (ex: query_list = [{'column':'timestamp', 'operator'= '=',
        #         'value':'xyz'}, {'column_name':'simulation_uuid', 'value':'1234'}])

        :param table_name:
        :param conditions:
        :param str_output:
        :param from_time:
        :param to_time:
        :return:
        """
        q = ''

        if conditions is not None:
            q = q + 'WHERE'
            for c in conditions:
                q = q + (' ' + c['column'] + ' ' + c['operator'] + " '" + c['value'] + "' " + 'AND')
                q = ' '.join(q.split(' ')[:-1])
        elif from_time is not None and to_time is not None:
            q = q + "WHERE timestamp BETWEEN '{0}' AND '{1}'".format(from_time, to_time)
        else:
            return None

        execute_str = 'SELECT * FROM {tn} {qs}'.format(tn=table_name, qs=q)
        self._c.execute(execute_str)
        all_rows = self._c.fetchall()

        json_results = []
        for row in all_rows:
            if str_output:
                json_results.append(row[3])
            else:
                json_results.append(json.loads(row[3], object_hook=lambda d: namedtuple('X', d.keys())(*d.values())))
        return json_results

    def insert_items(self, timestamp: str, sim_uuid: str, items: Any) -> None:
        """
            Assumes for now that all tables have "uuid", "timestamp", "sim_uuid" and "json" columns

        :param timestamp:
        :param sim_uuid:
        :param items:
        :return:
        """
        def insert_item(table_name, uuid, timestamp, sim_uuid, item):
            try:
                self._c.execute(
                    "INSERT INTO {tn} (uuid, timestamp, sim_uuid, json) VALUES ('{id}', '{ts}', '{sm}', '{js}')".
                    format(tn=table_name, id=uuid, ts=timestamp, sm=sim_uuid, js=item))
                self._conn.commit()

            except sqlite3.IntegrityError:
                print('ERROR: ID already exists in PRIMARY KEY column {}'.format(uuid))

        # TODO: REFORMAT THIS
        # items are str
        if isinstance(items, list):
            for item in items:
                table_name = item.type
                uuid = item.uuid
                item = json.dumps(item)

                insert_item(table_name, uuid, timestamp, sim_uuid, item)
        else:
            item = items
            table_name = item['type']
            uuid = item['uuid']
            item = json.dumps(item)
            insert_item(table_name, uuid, timestamp, sim_uuid, item)

    def run_query(self, **kwargs) -> Any:
        result = None
        try:
            self._c.execute(kwargs['query'])
            result = self._c.fetchall()
        except sqlite3.IntegrityError:
            print('ERROR: Bad query')
        return result

    def commit(self) -> None:
        self._conn.commit()
        self._conn.close()
