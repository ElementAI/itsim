import weakref

from collections import OrderedDict
from typing import Any, MutableMapping

from greensim import advance
from greensim.random import VarRandom

from itsim import _Node
from itsim.it_objects import ITSimulator
from itsim.it_objects.networking import _Link
from itsim.it_objects.packet import Packet
from itsim.types import Address, AddressRepr, as_address


class AddressError(Exception):
    """
    Generic superclass for Exception objects that refer to an issue with a specific address 
    """

    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value_for_address = value


class AddressInUse(AddressError):
    """
    Indicates that the address requested is already in use by the class that threw the Exception
    This is a non-fatal event and can be safely handled at runtime, occasionally with a retry
    """
    pass


class InvalidAddress(AddressError):
    """
    Indicates that the address requested is not a valid IP address
    This is non-fatal in general, but also should not be retried with the same address
    """
    pass


class Link(_Link):
    """
    A simple generic class representing a physical connection between a set of machines.
    Notez bien, the transmit method will always send a message to every connected Node. This is a fixed property of physical connections.
    Since a Link could be a wire or a region in physical space where a wireless transmission is detectable, all messages must be
    received by all parties. Trust and security must be handled outside of the Link class
    
    In addition, this class uses the Address class, but does not perform any logic with it aside from simple matching.
    The use of Address is only a convenience here, and it is meant to be an arbitrary label for a Node on the Link.
    It serves no purpose other than allowing the Node to be uniquely identified for addition and removal. Any address management
    for allocating unique and meaningful Address objects to Nodes should be handled outside of this class.
    """

    def __init__(self, sim: ITSimulator, bandwidth: VarRandom[float], latency: VarRandom[float]) -> None:
        super().__init__()
        self._bandwidth: VarRandom[float] = bandwidth
        self._latency: VarRandom[float] = latency
        self._nodes: MutableMapping[Address, weakref.ReferenceType[_Node]] = OrderedDict()
        self._sim: ITSimulator = sim

    @property
    def sim(self) -> ITSimulator:
        """
        An ITSimulator object referring to the simulator in which this Link exists.
        It will be called on with transmission events triggered by Node objects on the Link
        """
        return self._sim

    def add_node(self, node: _Node, ar: AddressRepr) -> None:
        """
        Converts the AddressRepr passed to an Address using the as_address function from itsim.types
        If the Address is already used to label a Node, throw AddressInUse
        Otherwise, create a weak reference to the Node and store it at the Address.
        As described in the class-level description, the Link class treats all addresses as arbitrary.
        There is no concept of address management in this physical connection
        """

        address = as_address(ar)

        if address in self._nodes:
            raise AddressInUse(address)

        self._nodes[address] = weakref.ref(node)

    def drop_node(self, ar: AddressRepr) -> bool:
        """
        Converts the AddressRepr passed to an Address using the as_address function from itsim.types
        If the Address is already used to label a Node, remove it from the dictionary and return True
        Otherwise, return False
        
        This method returns a boolean value to indicate whether action was taken or not, rather than throwing
        """

        address = as_address(ar)

        if address in self._nodes:
            del self._nodes[address]
            return True

        return False

    def transmit(self, packet: Packet, sender: _Node) -> None:
        """
        Sends the Packet from the arguments to all Node objects on the Link. This is accomplished by adding
        a single event to the ITSimulator which delays based on the Link's latency and bandwidth, then
        delivers the Packet to every Node on the Link (including the sender)
        """

        receivers = self._nodes.values()

        def transmission():
            advance(next(self._latency) + len(packet) / next(self._bandwidth))
            for node in receivers:
                self.sim.add(node._receive, packet)

        self.sim.add(transmission)
