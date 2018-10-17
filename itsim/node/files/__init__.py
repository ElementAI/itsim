from inspect import getfullargspec

from itsim.it_objects import ITObject
from itsim.node.accounts import UserAccount, UserGroup

from typing import Generic, TypeVar


class InvalidExecutable(Exception):
    pass


class PermissionDenied(Exception):
    pass


class InvalidPermission(Exception):
    pass


class Policy(ITObject):

    def __init__(self,
                 owning_user: UserAccount,
                 owning_group: UserGroup,
                 # Uses chmod convention to be concise
                 user: int, group: int, other: int):
        self.owning_user: UserAccount = owning_user
        self.owning_group: UserGroup = owning_group

        if sum([0 > i or i > 7 for i in (user, group, other)]):
            raise InvalidPermission()

        self.user: int = user
        self.group: int = group
        self.other: int = other

    def has_read(self, user: UserAccount, group: UserGroup):
        return self._check_binary_digit(4, user, group)

    def has_write(self, user: UserAccount, group: UserGroup):
        return self._check_binary_digit(2, user, group)

    def has_exec(self, user: UserAccount, group: UserGroup):
        return self._check_binary_digit(1, user, group)

    def _check_binary_digit(self, dig: int, user: UserAccount, group: UserGroup):
        if user == self.owning_user:
            return self.user & dig == dig
        elif group == self.owning_group:
            return self.group & dig == dig
        return self.other & dig == dig


T = TypeVar('T')


class File(ITObject, Generic[T]):

    def __init__(self, content: T, policy: Policy) -> None:
        # Calls up to ITObject
        super().__init__()
        self._content: T = content
        self._policy = policy

    @property
    def policy(self) -> Policy:
        return self._policy

    @policy.setter
    def policy(self, new_policy: Policy):
        self._policy = new_policy

    def read(self, user: UserAccount, group: UserGroup):
        if not self._policy.has_read(user, group):
            raise PermissionDenied()
        else:
            return self._content

    def write(self, user: UserAccount, group: UserGroup, new_content: T):
        if not self._policy.has_read(user, group):
            raise PermissionDenied()
        else:
            self._content = new_content

    def get_executable(self, user: UserAccount, group: UserGroup) -> T:
        # Needs to be a function with exactly one argument for the thread
        if not (hasattr(self._content, "__call__") and len(getfullargspec(self._content).args) == 1):
            print(hasattr(self._content, "__call__"))
            print(len(getfullargspec(self._content).args))
            raise InvalidExecutable()
        if not self._policy.has_exec(user, group):
            raise PermissionDenied()
        else:
            return self._content
