# Network Events Demo

1- Generate Data (into SQLite):
-
The following steps will start a datastore server (creating an empty SQLite DB) and store a few network events into it.

- Launch the datastore:
```
$ python bin/itsim_serve_datastore.py --sqlite_file demos/network_events/network_events_demo.sqlite
```
- Simulate simple data:
```
$ python demos/network_events/create_network_events.py
```
2- Visualizing with jupyter notebook: 
-
- Start Jupyter
```
$ cd demos/network_events
$ jupyter notebook
```
- Open and run the network_events.ipynb notebook


#####Note: Using virtual environment within the notebook:
- Install ipykernel package and create a new kernel:
```
$ pip install ipykernel
$ ipython kernel install --user --name=itsim
```
- Then create a notebook from jupyter based on the newly created kernel.
