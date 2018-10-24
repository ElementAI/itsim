from itsim.it_objects import ITObject
from itsim.node.accounts import UserAccount, UserGroup

from typing import Dict


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
                 user_rules: Dict[UserAccount, TargetedPolicy] = {},
                 group_rules: Dict[UserGroup, TargetedPolicy] = {}) -> None:
        self._default = default
        self._user_rules = user_rules
        self._group_rules = group_rules

    def has_read_access(self, user: UserAccount) -> bool:
        return self._has_access("has_read_access", user)

    def has_write_access(self, user: UserAccount) -> bool:
        return self._has_access("has_write_access", user)

    def has_exec_access(self, user: UserAccount) -> bool:
        return self._has_access("has_exec_access", user)

    def set_user_rule(self, user: UserAccount, rule: TargetedPolicy) -> None:
        self._user_rules[user] = rule

    def set_group_rule(self, group: UserGroup, rule: TargetedPolicy) -> None:
        self._group_rules[group] = rule

    def _has_access(self, access_type: str, user: UserAccount) -> bool:
        user_policies = [policy[1] for policy in self._user_rules.items() if policy[0] == user]
        user_access = [getattr(p, access_type) for p in user_policies]

        # If we find any False return False
        if sum(user_access) < len(user_access):
            return False
        # If we find no False and at least one True, return True
        elif len(user_access) > 0:
            return True

        group_policies = [policy[1] for policy in self._group_rules.items() if user in policy[0].members]
        group_access = [getattr(p, access_type) for p in group_policies]

        # If we find any False return False
        if sum(group_access) < len(group_access):
            return False
        # If we find no False and at least one True, return True
        elif len(group_access) > 0:
            return True

        return getattr(self._default, access_type)
