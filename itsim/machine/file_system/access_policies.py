"""
These classes embody the rules that govern access to files.
:py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` is only a named
3-tuple of bools indicating read, write, and exec access. The
:py:class:`~itsim.machine.file_system.access_policies.Policy` object collects
:py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` objects into
three groups. One group is the default policy, containing exactly one
:py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy`. The default is
a catch-all rule for entities that do not meet a more specific grouping. The second and third are
dictionaries mapping from :py:class:`~itsim.machine.accounts.UserAccount` and
:py:class:`~itsim.machine.accounts.UserGroup` objects to
:py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` objects.
"""
from itsim import ITObject
from itsim.machine.user_management.__init__ import UserAccount, UserGroup

from typing import Dict


class InvalidPermission(Exception):
    pass


class TargetedPolicy(ITObject):
    """
    This class only is a named 3-tuple of bools indicating read, write, and exec access. The
    :py:class:`~itsim.machine.file_system.access_policies.Policy` object collects these into
    groups to determine access. A TargetedPolicy should not be used to control access on its own
    (except as the default of a :py:class:`~itsim.machine.file_system.access_policies.Policy`)

    :param read: Whether or not this grants read access
    :param write: Whether or not this grants write access
    :param exec: Whether or not this grants exec access
    """

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
    """
    This object collects
    :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` objects into
    three groups. One group is the default policy, containing exactly one
    :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy`. The default
    is a catch-all rule for entities that do not meet a more specific grouping. The second and third
    are dictionaries mapping from :py:class:`~itsim.machine.accounts.UserAccount` and
    :py:class:`~itsim.machine.accounts.UserGroup` objects to
    :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` objects.

    Precedence is given to rules matching the :py:class:`~itsim.machine.accounts.UserAccount`, then
    the :py:class:`~itsim.machine.accounts.UserGroup`, before falling back to the default.

    In the case of a collision at the same level of precedence, a denial of permission will always override the granting
    of permission.

    :param default:
        A :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` that
        will serve as the fallback if a more specific role is not met
    :param user_rules:
        A dictionary mapping from :py:class:`~itsim.machine.accounts.UserAccount` to
        :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy`,
        indicating a rule for a specific user
    :param group_rules:
        A dictionary mapping from :py:class:`~itsim.machine.accounts.UserGroup` to
        :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy`,
        indicating a rule for a specific group
    """

    def __init__(self,
                 default: TargetedPolicy,
                 user_rules: Dict[UserAccount, TargetedPolicy] = {},
                 group_rules: Dict[UserGroup, TargetedPolicy] = {}) -> None:
        self._default = default
        self._user_rules = user_rules
        self._group_rules = group_rules

    def has_read_access(self, user: UserAccount) -> bool:
        """
        :param user:
            The :py:class:`~itsim.machine.accounts.UserAccount` attempting to
            get permission for the action
        """
        return self._has_access("has_read_access", user)

    def has_write_access(self, user: UserAccount) -> bool:
        """
        :param user:
            The :py:class:`~itsim.machine.accounts.UserAccount` attempting to
            get permission for the action
        """
        return self._has_access("has_write_access", user)

    def has_exec_access(self, user: UserAccount) -> bool:
        """
        :param user:
            The :py:class:`~itsim.machine.accounts.UserAccount` attempting to
            get permission for the action
        """
        return self._has_access("has_exec_access", user)

    def set_user_rule(self, user: UserAccount, rule: TargetedPolicy) -> None:
        """
        Set a new :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy`
        for a specific :py:class:`~itsim.machine.accounts.UserAccount`

        :param user:
            The :py:class:`~itsim.machine.accounts.UserAccount` that is the
            subject of the rule

        :param rule:
            :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` to be
            applied for the given entity
        """
        self._user_rules[user] = rule

    def set_group_rule(self, group: UserGroup, rule: TargetedPolicy) -> None:
        """
        Set a new :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy`
        for a specific :py:class:`~itsim.machine.accounts.UserGroup`

        :param user:
            The :py:class:`~itsim.machine.accounts.UserGroup` that is the
            subject of the rule

        :param rule:
            :py:class:`~itsim.machine.file_system.access_policies.TargetedPolicy` to be
            applied for the given entity
        """
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
