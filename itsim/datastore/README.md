#Itsim Datastore

The datastore provides a way for itsim to archive and query simulation data and logs.

The datastore is meant to be a generic interface for accessing data regardless of its storage location. The datastore 
can either be used through its local api or remotely using a rest api. Data can be stored on a remote PostgreSQL 
database or a local SQLite database (eventually support local folders?). 


```
Simulator       Datastore                       Database
Instance
                                            ___ remote PostgreSQL
itsim   -----> datastore local api         /
           \                         -----
            --> datastore rest api         \___ local SQLite (support remote as well?)        
            
```

### PostgreSQL vs SQLite

- PostgreSQL: requires a database server to be running (setup inside a docker?). Supports JSON, UUIDs natively.
- SQLite: Easier to setup and work with, datastore needs a single db file (no server). JSON, UUIDs aren't natively 
supported.
