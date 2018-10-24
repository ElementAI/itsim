from itsim.it_objects import ITObject

from typing import Any, Set


class UserAccount(ITObject):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def __eq__(self, o: Any) -> bool:
        if o is None:
            return False
        elif not isinstance(o, UserAccount):
            return False
        else:
            return self.name == o.name

    def __hash__(self) -> int:
        return self._name.__hash__()


class UserGroup(ITObject):
    def __init__(self, name: str) -> None:
        self._name: str = name
        self._members: Set[UserAccount] = set()

    @property
    def members(self) -> Set[UserAccount]:
        return self._members

    @property
    def name(self) -> str:
        return self._name

    def add_members(self, *members: UserAccount) -> None:
        self._members |= set(members)

    def remove_members(self, *members: UserAccount) -> None:
        self._members -= set(members)

    def __eq__(self, o: Any) -> bool:
        if o is None:
            return False
        elif not isinstance(o, UserGroup):
            return False
        else:
            return self.name == o.name \
                and self.members == o.members

    def __hash__(self) -> int:
        return self._name.__hash__() +\
            sum([mem.__hash__() for mem in self._members])
