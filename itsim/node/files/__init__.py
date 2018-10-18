from inspect import getfullargspec

from itsim.it_objects import ITObject
from itsim.node.accounts import UserAccount, UserGroup

from typing import Dict, Generic, TypeVar, Union


class InvalidExecutable(Exception):
    pass


class PermissionDenied(Exception):
    pass


class InvalidPermission(Exception):
    pass


class TargetedPolicy(ITObject):

    def __init__(self, read: bool, write: bool, exc: bool):
        self._read: bool = read
        self._write: bool = write
        self._exec: bool = exc

    @property
    def has_read_access(self) -> bool:
        return self._read

    @property
    def has_write_access(self) -> bool:
        return self._write

    @property
    def has_exec_access(self) -> bool:
        return self._exec


class Policy(ITObject):

    def __init__(self,
                 default: TargetedPolicy,
                 rules: Dict[Union[UserAccount, UserGroup], TargetedPolicy] = {}) -> None:
        self._default = default
        self._rules = rules

    def has_read_access(self, user: UserAccount) -> bool:
        return self._has_access("has_read_access", user)

    def has_write_access(self, user: UserAccount) -> bool:
        return self._has_access("has_write_access", user)

    def has_exec_access(self, user: UserAccount) -> bool:
        return self._has_access("has_exec_access", user)

    def _has_access(self, access_type: str, user: UserAccount) -> bool:
        user_policies = [policy[1] for policy in self._rules.items() if policy[0] == user]
        user_access = [getattr(p, access_type) for p in user_policies]

        # If we find any False return False
        if sum(user_access) < len(user_access):
            return False
        # If we find no False and at least one True, return True
        elif len(user_access) > 0:
            return True

        groups = [policy_item for policy_item in self._rules.items() if isinstance(policy_item[0], UserGroup)]
        group_policies = [policy[1] for policy in groups if user in policy[0].members]
        group_access = [getattr(p, access_type) for p in group_policies]

        # If we find any False return False
        if sum(group_access) < len(group_access):
            return False
        # If we find no False and at least one True, return True
        elif len(group_access) > 0:
            return True

        return getattr(self._default, access_type)


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

    def read(self, user: UserAccount):
        if not self._policy.has_read_access(user):
            raise PermissionDenied()
        else:
            return self._content

    def write(self, user: UserAccount, new_content: T):
        if not self._policy.has_write_access(user):
            raise PermissionDenied()
        else:
            self._content = new_content

    def get_executable(self, user: UserAccount) -> T:
        # Needs to be a function with exactly one argument for the thread
        if not (hasattr(self._content, "__call__") and len(getfullargspec(self._content).args) == 1):
            print(hasattr(self._content, "__call__"))
            print(len(getfullargspec(self._content).args))
            raise InvalidExecutable()
        if not self._policy.has_exec_access(user):
            raise PermissionDenied()
        else:
            return self._content
