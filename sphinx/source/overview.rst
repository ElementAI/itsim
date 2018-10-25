*********************
ITSim Design Document
*********************

Welcome to ITSim!

This is a reformatting of a document title "DSL for malware behaviour fingerprinting and reconstruction of cyberattacks" by Benoit Hamelin and Matt Craddock

Context
=======
This research work aims at supporting and improving the processes of security operations. As things stand, SOC analysts are overwhelmed with alert investigation workload. We propose to automate the detection of common attack patterns, so as to help reconstruct the causal chain leading up to an alert event. Analysts would thereby be imbued with clearer visibility on the status of an incident, better ability to connect the dots with other previous and incipient investigations, and stronger evidence on the provenance, intentions and identity of the attacker.
The first step towards malware fingerprinting is to develop a tool for describing the artifacts deployed throughout the attack and the behaviours exhibited thereby, in context of the IT infrastructure being penetrated.
This document proposes a design for that language, composed of a series of principles that its construction should follow, a list of categories into which components should fall, and descriptions of the objects in those categories along with their importance in malware simulation.
This design is informed by the authors’ experience and intentions, as well as domain knowledge gathered in a broad review of the state of the art

Language Components
===================

Network Creation Component
--------------------------

In comparison to existing simulators that generate faster-than-real-time network data, the topology of the network is a secondary consideration for us. The malware and the telemetry it produces are paramount. However, any characteristics of the network that a malicious actor will leverage need to be explicitly modeled. For example, if the network of the organization is comprised of physically separated subnets (or some other topological feature), and if overcoming this segmentation yields observable malware behaviour.

It should not be necessary for every program to specify its network configuration (e.g., enumerate hosts, define their properties, define connections), so networks should be dispensed in some form that can be imported to an arbitrary malware program. Further, since it will almost certainly be useful to generate a large network programmatically, a developer should have the option to write a program that will generate a static network configuration (similar to the way ./configure typically generates a Makefile), which can in turn be imported into a malware program. This will separate the definition of networks from the definition of malware and prevent complex networks from having to be defined in multiple places or generated on the fly in a malware simulation.
The network configuration is likely to be best represented by a static configuration or simple program which can be read in using simple DSL commands similar to import statements. This will allow the underlying network to be interchangeable across simulations and enforce a policy where the network and malware are defined independently. Even if the network is highly dynamic (i.e., almost all of its attributes are prone to change), it will still be useful to have a static representation on the disk to use as a starting point. That way, any complexities inherent in generating the network (e.g., gathering data about machine attributes or creating complex topologies) are separated from the simulation flow. In other words, the network representation should be a compiled state that can be loaded and used at runtime, optionally using parameters. This will support the Modular and Simple qualities of a good DSL.
The act of generating these files may not lend itself to static configuration, however. It may be useful to have an API for generating the network configurations that can leverage useful imperative programming constructs like loops and conditional logic. This will support the Useful quality of a good DSL
The organizational network is itself embedded in a larger Internet environment. The DSL will allow ad hoc Internet access, excepting outbound access restrictions modeled for a certain network, and enable modeling salient endpoint behaviours as they enact IP communications.

Simulator
---------

The API for controlling the simulation should be kept separate from the API for outlining the behavior of the network and the malware. This should be a relatively simple set of classes, similar to the Simulator class from Greensim, which handle event scheduling, network loading, process initiation, and other aspects (e.g., logging) that are not meant to emulate any real entity. To paraphrase, the behaviour model should not be aware that it is to be reproduced through simulation, nor that this simulation is to be subject to recording or logging. These components will inevitably have the closest ties to the underlying simulator, but should still represent an independant layer which calls on concrete backend-specific implementations in order to access simulator functions, for Modularity.
This may be a good place to manage a notion of discovery in the network. Since a typical attacker is not likely to have a deep knowledge of the network architecture when an attack begins, and not all nodes are aware of all other nodes, the simulation should control the elements of the network state that are accessible to any given entity.

IT Objects
----------

This category should include machines, software, networks, data, and anything else meant to emulate a real entity that lacks self-determination of any kind. In the SLEUTH attack representation, each IT object would represent a node, and operations performed on them by actors or other objects would represent edges. Each of these should have an API for the set of actions which can be performed on them (for use by malware and other simulation objects) and performed by them (for use by the simulator). These calls should be carefully chosen in the context of the Useful, Simple, Expressive, and Abstractive traits of a good DSL.
These objects should also carry tags representing their status within the network. Certainly data should have tags representing their level of confidentiality. Other objects may have more flexible sets indicating that they are compromised, vulnerable, or have some other important trait.
The functions of these objects should be deterministic (though they may be triggered by stochastic processes) to reflect the behavior of a network under normal conditions. For example, if a network object is instructed to transfer a packet, it should always start a transmission process using the same logic. The resultant process may have a random result in terms of time and packet drops, triggering the receiving events at random, but the network creating it should only react to the realized events in a deterministic way, as machines do. This will allow us to simply and reliably test the behavior of these classes. This is supported by the assumptions that the realization of a random variable should always happen as part of an event rather than a static object, and the Modularity principle of the good DSL.
Also for Modularity, these components should consist of no more than a well-defined set of classes and API’s with no functionality in the DSL aside from calling concrete implementations and returning internal types. Whatever actions they must take to affect the internal state of the simulation, generate output, or any other activity should be handled by concrete implementations which are specific to our chosen backend. As a result, this will be a very “broad” (covering very many components in the simulation) but “thin” (covering very few simulation activities) layer.

Actor Objects
-------------

The DSL should include a library of actor objects which trigger various events on the network and may act in a probabilistic way. This category should explicitly include the malware activities that are the main target of the project. The methods on these objects will be of the most interest in our DSL, since these represent entities (good and bad) that have initiative and goals for their activity on the network. These should have tags as well, at a minimum along two dimensions: benign - malicious and human - automated.
Since these objects have initiative they should create events in either a probabilistic or deterministic manner. These events will be of paramount importance in the output, and should inflict the will of the actor onto the IT objects.
Since modelling the behaviors and resultant effects of actors is the primary goal of the project, the traces of an actor’s lifetime in the system should be labeled and easily collected in simulation logs for analysis, validation, and training data. The labels should be removed for testing data

Events
------

This category should contain many small classes representing actions taken by entities on the network (e.g., I/O operations, user input). These should be triggered by actors and IT objects. These events should also encapsulate the randomness of the network, calling the relevant functions on their targets with random delays or modifications as appropriate based on the action (that is, they may include no randomness at all). Events should publish logs about themselves with full detail, i.e. the initiator and target of the action, and any parameters included.
In the SLEUTH graph representation, these are the edges on the graph. They will allow traversal of the graph when doing analysis of an attack.
These should also be labeled in a similar way or actors and IT objects, and should contain the rules for transferring tags between them (e.g., a process forked by a malicious process is implicitly malicious, but an authorized benign process reading confidential data does not become “confidential”).
It will be useful to base the design of these events on the “subject, operation, object” model, where a subject (e.g., a process) applies an operation (e.g., a system call) to an object (e.g., a file). The rigorous definition varies in the literature, but a strong definition in the context of this DSL will help keep it Simple, Expressive, and Abtractive.

Engine Internals
================

Underlying Simulator Interface
------------------------------

We should aim to keep strong modularity and interchangeability by implementing all of the aspects of our DSL without (unnecessary) regard to the underlying simulator. All of those methods that require some aspect of network simulation should have overrides in a simulator-specific subclass which handles all of the calls to the underlying simulator and returns a value whose type is controlled by our DSL. This will keep a clean separation between our objects and the objects of a third party simulator, which in turn will give us the ability to change out the simulator without affecting the APIs exposed to our DSL, enforcing Modularity.

Output Events and Formatting
----------------------------

Output from the simulator should come in two distinct, but related forms.
Internal types should be the fully internal representation of data, eligible to change in any way at any release. This pattern will give the developers control over the content and format of the output of internal classes. The documentation should not communicate any information about these types to users (or, more practically, not promise anything). These represent the output generated by all of the objects and events in the simulation and should contain at least as much information as the union of the external types we expect to produce, even if the format and naming are different
External types should be accountable to externally defined and communicated standards (e.g, SYSMON), so they must be rigid. They should be well documented and any changes aside from expansion should be rare and backwards-compatible. They should also only be referred to by a translation layer for converting the internal types into final output.
In the same manner as the translation from IT objects to internal simulation as defined above, the translation from internal types to external types should be performed by concrete implementations of the translation classes specific to the output format specified. A developer should be able to choose one or more output types for an arbitrary simulation and expect that they will be populated as fully as the documentation guarantees. Developers should be able to define a new output type by simply documenting it and writing a translation layer from the input types, with no modification of simulation internals necessary (unless extra information is required).

Internal State Representation
-----------------------------
One promising method from the literature is to model the network as a simple graph and to endow the nodes and paths with special traits as necessary to simulate the desired traits of the network (e.g., capabilities and vulnerabilities. connections). For a wireframe backend this will be inexpensive, flexible, and ultimately useful for the final product. In other words, translating a program in the DSL a series of operations on a graph will form a useful backend prototype and will give us an interface that can be readily applied to whatever full simulation backend is eventually chosen. This also makes it possible to represent the network as a POMDP to the simulated malware (as in this talk and this paper), which reflects many of the real properties (i.e., partial information) that are present from the perspective of real malware.

Syntax and Semantics
--------------------

Two approaches have been discussed at a high-level. These will create very different paradigms and have a strong impact on usability, so they will require careful consideration

Old-school (derived from P-BEST / Prolog)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The DSL can be used to generate a causal chain of signals, which can be parsed by a logic engine to deduce (in a non-deterministic way) probable root causes from a known malware event.
This approach will generate models that are highly explainable, easy to test, and have minimal data requirements. However, it does not leverage modern machine learning technology and has been used many times in the past with varying success.

Nouvelle Mode (derived from Python)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The DSL can be used to power a simulation which will generate representative data that can be used to train a GAN, and thereby a discriminator with the ability to deduce information about malware.
A language built in this format should leverage the Python interpreter directly so that an entirely new parser does not need to be built.
If our attempts to apply GANs to the data are successful this is likely to result in a more powerful model that can analyze a much broader array of features. However, it is much more difficult to explain and test and may be more likely to find spurious correlations than an experienced analyst.

Known Unknowns
==============

#. What is the range of objects that will be necessary to generate the Telemetry table?
#. What qualities are we optimizing for?
    * Flexibility?
    * Explainability?
    * Future-proofing?
#. What are the fidelity requirements for the output? That is, given that we will only be using a wireframe backend for the simulation, what tests of the output will be sufficient to claim that it is representative enough? It will be too rigorous to expect the output to match customer telemetry exactly, but it will not be rigorous enough the accept arbitrary output, so we must find some other appropriate conditions.
#. Which language format will we attempt first? Logic or imperative?
#. What ability will we have to conduct user studies and interviews?
#. What will the timelines and format be for feedback? What are the expected response times from EAI?
#. At what point in the timeline will our customers be able to render an informed opinion of whether or not this project will create a useful tool for their analysts? If the answer is negative, will there be time available to realign?
