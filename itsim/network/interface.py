from itsim.network.link import Link
from itsim.types import AddressRepr, Address, as_address, Cidr


class Interface:

    def __init__(self, link: Link, ar: AddressRepr = None, has_gateway: bool = False) -> None:
        super().__init__()
        self._link = link
        self._address = as_address(ar)  # Bypass the usual logic for initially null or invalid address.
        self.has_gateway = has_gateway

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
    def has_gateway(self) -> bool:
        return self._has_gateway

    @has_gateway.setter
    def has_gateway(self, hg: bool) -> None:
        self._has_gateway = hg
