import click

from itsim.datastore.datastore_server import DatastoreRestServer


@click.command()
@click.option('--sqlite_file', default='itsim/datastore/storage/sqlite_01.sqlite', help='SQLite database file to use.')
@click.option('--host', default='0.0.0.0', help='Server host.')
@click.option('--port', default=5000, help='Server port.')
@click.option('--storage_mode', default='sqlite', help='Datastorage to be used by the datastore.')
def launch_server(sqlite_file: str, host: str, port: int, storage_mode: str) -> None:
    server = DatastoreRestServer(type=storage_mode, sqlite_file=sqlite_file)
    server.run(host, port)


if __name__ == "__main__":
    launch_server()
