from typing import List

from itsim.network.route import Route
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
    :param routes:
        List of :py:class:`Route` objects indicating the possible packet routes from the owning :py:class:`Node`
        across the associated :py:class:`Link`.
    """

    def __init__(self, link: Link, address: Address, routes: List[Route]) -> None:
        super().__init__()
        self._link = link
        self.routes = routes
        self.address = address

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
        The new address is re-rooted so that the final address for this interface lies within the CIDR of the associated
        link.
        """
        self._address = as_address(ar, self.cidr)

    @property
    def routes(self):
        """
        List of :py:class:`Route`s for this interface. A :py:class:`Local` route to the CIDR of the associated
        :py:class:`Link` is always present, even though it has not been explicitly specified.
        """
        return self._routes

    @routes.setter
    def routes(self, fs: List[Route]):
        self._routes = fs
