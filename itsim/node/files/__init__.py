from inspect import getfullargspec

from itsim.it_objects import ITObject
from itsim.node.accounts import UserAccount
from itsim.node.files.access_policies import Policy

from sys import getsizeof

from typing import Callable, cast, Generic, TypeVar


class InvalidExecutable(Exception):
    pass


class PermissionDenied(Exception):
    pass


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
    def policy(self, new_policy: Policy) -> None:
        self._policy = new_policy

    def read(self, user: UserAccount) -> T:
        if not self._policy.has_read_access(user):
            raise PermissionDenied()
        else:
            return self._content

    def write(self, user: UserAccount, new_content: T) -> int:
        if not self._policy.has_write_access(user):
            raise PermissionDenied()
        else:
            self._content = new_content
            if hasattr(new_content, "byte_size"):
                return getattr(new_content, "byte_size")
            else:
                return getsizeof(new_content)

    def get_executable(self, user: UserAccount) -> Callable:
        # Needs to be a function with exactly one argument for the thread
        if not (hasattr(self._content, "__call__") and len(getfullargspec(self._content).args) == 1):
            raise InvalidExecutable()
        if not self._policy.has_exec_access(user):
            raise PermissionDenied()
        else:
            return cast(Callable, self._content)
