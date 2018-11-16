from typing import List

from itsim.network.forwarding import Forwarding, Local
from itsim.network.link import Link
from itsim.types import AddressRepr, Address, as_address, Cidr


class Interface:
    """
    Network interface between a :py:class:`Node` and a :py:class:`Link`. Indicates the node's address on this link, as
    well as known routes for packets across this link.

    :param link:
        Link interfaced to.
    :param address:
        Address (IP) of the owning :py:class:`Node` on the associated :py:class:`Link`.
    :param forwardings:
        List of :py:class:`Forwarding` objects indicating the possible packet routes from the owning :py:class:`Node`
        across the associated :py:class:`Link`.
    """

    def __init__(self, link: Link, address: Address, forwardings: List[Forwarding]) -> None:
        super().__init__()
        self._link = link
        self.forwardings = forwardings
        # Normally, only valid addresses with respect to the associated link's CIDR are acceptable for an interface.
        # However, the initial address can alternatively be 0.0.0.0 (or any value really), especially if the address
        # is meant to be set by some later process, such as a DHCP client running on the owning host. Thus, the setter
        # of this property is bypassed here in particular.
        self._address = address

    @property
    def link(self) -> Link:
        """
        :py:class:`Link` associated to the interface.
        """
        return self._link

    @property
    def cidr(self) -> Cidr:
        """
        Shortcut to the associated :py:class:`Link`'s CIDR.
        """
        return self.link.cidr

    @property
    def address(self) -> Address:
        """
        Address of the owning :py:class:`Node` on the associated :py:class:`Link`. Can be set, but then the new address
        must be inside the :py:class:`Link`'s CIDR.
        """
        return self._address

    @address.setter
    def address(self, ar: AddressRepr) -> None:
        """
        The new address must be inside the :py:class:`Link`'s CIDR.
        """
        address = as_address(ar)
        if address not in self.link.cidr:
            raise ValueError("Address not usable on this link.")
        self._address = address

    @property
    def forwardings(self):
        """
        List of :py:class:`Forwarding`s for this interface. A :py:class:`Local` forwarding to the CIDR of the associated
        :py:class:`Link` is always present, even though it has not been explicitly specified.
        """
        return [Local(self.cidr)] + self._forwardings

    @forwardings.setter
    def forwardings(self, fs: List[Forwarding]):
        self._forwardings = fs
