import click
from flask import Flask
from flask_restful import Api, Resource, request
from typing import Any


class _Item(Resource):

    def __init__(self, db_file):
        self._db_file = db_file

    def get(self, item_type: str, uuid: str) -> Any:
        if not request.is_json:
            return "Invalid format", 400

        request_time_range = request.get_json()

        items = DatabaseSQLite(self._db_file).select_items(item_type,
                                                           uuid,
                                                           str_output=True,
                                                           from_time=request_time_range['from_time'],
                                                           to_time=request_time_range['to_time'])
        if items is None:
            return "Node not found", 404
        elif len(items) == 0:
            return "Node not found", 404
        else:
            return items[0], 201

    def post(self, item_type: str, uuid: str) -> Any:
        if not request.is_json:
            return "Invalid format", 400

        content = request.get_json()
        sim_uuid = content['sim_uuid']
        timestamp = content['timestamp']

        DatabaseSQLite(self._db_file).insert_items(timestamp, sim_uuid, content)
        return "ok", 201

    def delete(self, item_type: str, uuid: str) -> Any:
        if not request.is_json:
            return "Invalid format", 400
        # content = request.get_json()
        # TODO: Use id to delete from DB
        # id = 0 # to be uuid

        return "{} is deleted.".format(0), 200


class DatastoreRestServer:

    def __init__(self, **kwargs) -> None:
        assert kwargs['type'] == 'sqlite', 'Datastore server only support sqlite databases.'

        self._db_file = kwargs['sqlite_file']

        DatabaseSQLite(self._db_file).create_tables()

        # Init. the server (Http Rest API)
        self._app = Flask(__name__)
        self._api = Api(self._app)

        """
            Note: all itsim_objects use the same rest functions (from _Item class).
            This could eventually be split for object specific implementation
        """
        self._api.add_resource(_Item, "/<string:item_type>/<string:uuid>", resource_class_args=(self._db_file,))

    def run(self) -> None:
        self._app.run(debug=True)


@click.command()
@click.option('--storage_mode', default='sqlite', help='Datastorage to be used by the datastore.')
@click.option('--sqlite_file', default='itsim/datastore/storage/sqlite_01.sqlite', help='SQLite database file to use.')
def launch_server(storage_mode: str, sqlite_file: str) -> None:
    server = DatastoreRestServer(type=storage_mode, sqlite_file=sqlite_file)
    server.run()


if __name__ == "__main__":
    # This import is here to allow running the server from the command line without itsim
    # Documentation generation fails if at the top of the file.
    from database import DatabaseSQLite
    launch_server()
