import click

from itsim.datastore.datastore_server import DatastoreRestServer


@click.command()
@click.option('--storage_mode', default='sqlite', help='Datastorage to be used by the datastore.')
@click.option('--sqlite_file', default='itsim/datastore/storage/sqlite_01.sqlite', help='SQLite database file to use.')
def launch_server(storage_mode: str, sqlite_file: str) -> None:
    server = DatastoreRestServer(type=storage_mode, sqlite_file=sqlite_file)
    server.run()


if __name__ == "__main__":
    launch_server()
