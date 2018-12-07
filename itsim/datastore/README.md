#Itsim Datastore

The datastore provides a way for itsim to archive and query simulation telemetry and logs.

The datastore is meant to be a generic interface for accessing data regardless of its storage location. The datastore 
is currently used through a REST API (support could be added for local API) and it is currently using a local SQLite 
database  for storage (could eventually support PostgreSQL as well for native JSON and UUIDs support). 


## Implementation
The Datastore has been implemented following a client/server architecture. The server exposes its functionality to the 
client(s) through a REST API and stores its data into a SQLite database. This design allows simulations to be 
running on multiple machines to archive their telemetry into a single endpoint, making it convenient for post 
processing the data. 

The DatastoreRestClient will attempt to connect to a default local server (http://0.0.0.0:5000/) and will launch a 
temporary server if it can't connect to it (in which case the database file will be deleted after running the 
simulation). Of course, the DatastoreRestClient can also be instantiated to connect to a different host and port.

## Running the datastore server standalone

From the main itsim folder (inside a pipenv shell), launch the datastore with proper database file and server host and 
port. 

```
itsim$ pipenv shell
(itsim)$ python bin/itsim_serve_datastore.py --sqlite_file sqlite_01.sqlite --host localhost --port 5000
```

