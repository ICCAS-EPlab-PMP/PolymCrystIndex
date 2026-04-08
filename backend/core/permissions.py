"""Permission constants and role-based access control.

This module centralizes all permission definitions for the system.
Do not scatter permission strings across other files.
"""

ROLE_ADMIN = "admin"
ROLE_USER = "user"

PERM_USER_READ = "user:read"
PERM_USER_CREATE = "user:create"
PERM_USER_UPDATE = "user:update"
PERM_USER_DISABLE = "user:disable"

PERM_TASK_READ_ALL = "task:read_all"
PERM_TASK_CANCEL_ALL = "task:cancel_all"

PERM_SYSTEM_READ = "system:read"
PERM_SYSTEM_WRITE = "system:write"

ROLE_PERMISSIONS = {
    ROLE_ADMIN: {
        PERM_USER_READ,
        PERM_USER_CREATE,
        PERM_USER_UPDATE,
        PERM_USER_DISABLE,
        PERM_TASK_READ_ALL,
        PERM_TASK_CANCEL_ALL,
        PERM_SYSTEM_READ,
        PERM_SYSTEM_WRITE,
    },
    ROLE_USER: set(),
}

VALID_ROLES = {ROLE_ADMIN, ROLE_USER}


def get_permissions_for_role(role: str) -> set:
    """Get the permission set for a given role.

    Args:
        role: Role name (e.g., "admin", "user")

    Returns:
        Set of permission strings for the role.
        Returns empty set for unknown roles.
    """
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission.

    Args:
        role: Role name
        permission: Permission string (e.g., "user:read")

    Returns:
        True if the role has the permission, False otherwise.
    """
    return permission in get_permissions_for_role(role)
