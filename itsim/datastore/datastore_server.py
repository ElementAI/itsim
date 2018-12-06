import flask
from flask import Flask
from flask_restful import Api, Resource, request
from typing import Any
from itsim.datastore.database import DatabaseSQLite


class _Item(Resource):

    def __init__(self, db_file):
        self._db_file = db_file

    def get(self, item_type: str, uuid: str) -> Any:

        if item_type == 'isrunning':
            return 'ok', 200

        if not request.is_json:
            return "Invalid format", 400

        request_time_range = request.get_json()

        items = DatabaseSQLite(sqlite_file=self._db_file).select_items(item_type,
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

        DatabaseSQLite(sqlite_file=self._db_file).insert_items(timestamp, sim_uuid, content)
        return "ok", 201

    def delete(self, item_type: str, uuid: str) -> Any:
        if not request.is_json:
            return "Invalid format", 400
        # content = request.get_json()
        # TODO: Use id to delete from DB
        # id = 0 # to be uuid

        return "{} is deleted.".format(0), 200


class DatastoreRestServer:

    def __init__(self, type: str = 'sqlite', sqlite_file: str = ':memory:') -> None:
        assert type == 'sqlite', 'Datastore server only support sqlite databases.'
        self._db_file = sqlite_file

        DatabaseSQLite(sqlite_file=self._db_file).create_tables()

        # Init. the server (Http Rest API)
        self._app = Flask(__name__)
        self._api = Api(self._app)

        self._api.add_resource(_Item, "/<string:item_type>/<string:uuid>", resource_class_args=(self._db_file,))
        self._app.add_url_rule("/stop", "stop", self.stop_server, methods=["POST"])

    def stop_server(self):
        do_stop = flask.request.environ.get('werkzeug.server.shutdown')
        if do_stop is None:
            raise RuntimeError("Testing server supposed to be werkzeug!")
        do_stop()
        return "OK"

    def run(self, host: str = '0.0.0.0', port: int = 5000, **options: Any) -> None:
        self._app.run(host=host, port=port, **options)

    @property
    def app(self) -> Flask:
        return self._app
