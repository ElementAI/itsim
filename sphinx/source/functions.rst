Functions and Their Many Uses in ITSim
======================================

Functions and wrappers around them are used to represent any active component of the simulation. That is, anything with a goal or intention is represented using a function. Since ITSim is a discrete event simulator, this makes it possible to schedule the actions of these components in order to produce the desired effects on the network.

In practice, there are four concepts which are independently represented by functions:

.. contents::
   :local:

Threads
-------
Threads are presented by the :py:class:`Thread <itsim.node.process_management.thread.Thread>` class, which interfaces directly with the simulator. The :py:meth:`clone <itsim.node.process_management.thread.Thread.clone>` and :py:meth:`clone_in <itsim.node.process_management.thread.Thread.clone_in>` methods take a Callable as an argument and schedule it to be executed at the specified time. The function must take a :py:class:`Thread <itsim.node.process_management.thread.Thread>` as its first argument, which allows it to interrogate its environment and schedule further events at later times in the same flow of execution.

Software
--------
Since the actions of software processes are represented using :py:class:`Process <itsim.node.process_management.process.Process>` and :py:class:`Thread <itsim.node.process_management.thread.Thread>`, a full representation of a piece of software must, in the end, be composed of these objects. For a function in memory, this is as simple as calling :py:meth:`fork_exec <itsim.node.Node.fork_exec>` or :py:meth:`fork_exec_in <itsim.node.Node.fork_exec_in>` on the :py:class:`Node <itsim.node.Node>` that should execute the code. This will allow the :py:class:`Node <itsim.node.Node>` to create a tree of :py:class:`Process <itsim.node.process_management.process.Process>` and :py:class:`Thread <itsim.node.process_management.thread.Thread>` objects to represent the state of the machine and translate the function into a series of discrete simulation events. If the goal is to simulate the running of an executable file on the disk, it is possible to instatntiate a :py:class:`File <itsim.node.file_system.File>` object which contains a callable, for example with::

    default_policy = TargetedPolicy(False, False, False)
    user_policy = TargetedPolicy(False, False, True)
    user_allowed: Policy = Policy(default_policy, user_rules={UserAccount("demo"): user_policy})
    runnable: File[Callable[[Thread], None]] = File(ping, user_allowed)

Once the :py:class:`File <itsim.node.file_system.File>` object is instantiated, it can be passed to :py:meth:`run_file <itsim.node.Node.run_file>` on :py:class:`Node <itsim.node.Node>` to execute in exactly the same manner as :py:meth:`fork_exec <itsim.node.Node.fork_exec>` or :py:meth:`fork_exec_in <itsim.node.Node.fork_exec_in>`, while also checking the relevant :py:meth:`Policy <itsim.node.file_system.access_policies.Policy>` objects to ensure that the execution is allowed by the predefined rules.


Users
-----
Since the actions of users are taken at (usually many) fixed points in time and often have non-zero durations, they are also represented in the simulation as a series of discrete events. The API for these events is not formally defined at this time, but the actions of a user with arbitrary privelege may be simulated by writing a series of functions and adding them to the simulation directly.


Daemons and Services
--------------------
:py:class:`Daemons <itsim.network.internet.Daemon>` and :py:class:`Services <itsim.network.service.Service>` are similar to :py:class:`Threads <itsim.node.process_management.thread.Thread>` in form and function. Their precise specifications are still being defined, but in general they serve as an abstraction for long-running processes which do not require or expect direct user intervention.
