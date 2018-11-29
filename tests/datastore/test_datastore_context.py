from contextlib import contextmanager
import os.path
from queue import Queue
from threading import Thread, Timer
from uuid import uuid4
import flask
import pytest
import requests
from itsim.datastore.datastore import DatastoreRestClient
from itsim.datastore.datastore_server import DatastoreRestServer


def stop_server():
    do_stop = flask.request.environ.get('werkzeug.server.shutdown')
    if do_stop is None:
        raise RuntimeError("Testing server supposed to be werkzeug!")
    do_stop()
    return "OK"


def start_and_run_server(server, queue_port):
    for port in range(5000, 2 ** 16 - 1):
        timer = None
        try:
            timer = Timer(0.05, lambda: queue_port.put(port))
            timer.start()
            server.run(host="localhost", port=port, debug=False)
            return
        except OSError as err:
            if err.errno == 97:  # Port already in use.
                if timer is not None:
                    timer.cancel()
    # At this point, we were unable to find a suitable port -- fail.
    queue_port.put(0)


@contextmanager
def server():
    thr = None
    port = 0
    try:
        server = DatastoreRestServer(type="sqlite", sqlite_file="test.sqlite")
        queue_port = Queue()
        thr = Thread(target=start_and_run_server, args=(server, queue_port))
        thr.start()
        port = queue_port.get()
        if port == 0:
            pytest.fail("Unable to start the datastore server.")
        yield (server, port)

    finally:
        try:
            if thr is not None:
                # Best effort to take down the server without waiting forever. Should the server fail to shut down, we
                # will merely run next instances on alternative ports.
                if port > 0:
                    response = requests.post(f"http://localhost:{port}/stop")
                    if response.status_code != 200:
                        pytest.fail("Failed to shut down the datastore server.")
                thr.join(timeout=5.0)
        finally:
            if os.path.isfile("test.sqlite"):
                os.remove("test.sqlite")


def client(port):
    return DatastoreRestClient(base_url=f"http://localhost:{port}", sim_uuid=str(uuid4()))


def test_context():
    with server() as (ss, port):
        assert port == 5000
        with server() as (ss, port):
            assert port == 5001
            with server() as (ss, port):
                assert port == 5002
