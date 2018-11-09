from typing import List

from itsim.network.forwarding import Forwarding, Local
from itsim.network.link import Link
from itsim.types import AddressRepr, Address, as_address, Cidr


class Interface:

    def __init__(self, link: Link, address: Address, forwardings: List[Forwarding]) -> None:
        super().__init__()
        self._link = link
        self._address = address  # Bypass the usual logic for initially null or invalid address.
        self.forwardings = forwardings

    @property
    def link(self) -> Link:
        return self._link

    @property
    def cidr(self) -> Cidr:
        return self.link.cidr

    @property
    def address(self) -> Address:
        return self._address

    @address.setter
    def address(self, ar: AddressRepr) -> None:
        address = as_address(ar)
        if address not in self.link.cidr:
            raise ValueError("Address not usable on this link.")
        self._address = address

    @property
    def forwardings(self):
        return [Local(self.cidr)] + self._forwardings

    @forwardings.setter
    def forwardings(self, fs: List[Forwarding]):
        self._forwardings = fs
