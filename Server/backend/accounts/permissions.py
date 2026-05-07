"""
Production-hardened permission classes for Roe's POS backend.

Permission hierarchy:
- IsAdmin: Only administrators
- IsAdminOrReadOnly: Admin write, all authenticated read
- IsAdminOrSelf: Admin write all, staff write own
- CanChangePin: Admins change any PIN, staff change own
- HasRole: Factory for role-based access
- IsAdminOrInventoryManager: Admin or inventory manager operations
- IsAuthenticatedAndInventoryManagerOrReadOnly: Inventory manager write, all authenticated read

Usage:
- Sensitive financial operations: IsAdmin
- Data modification: IsAdmin or role-specific permissions
- Data access: IsAuthenticated or role-based
- Self-service operations: IsAdminOrSelf or CanChangePin
"""
from rest_framework import permissions
from .models import Staff


class IsAdmin(permissions.BasePermission):
    """Only admin staff can access"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == Staff.Roles.ADMIN)


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin can do everything, others can only read"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.role == Staff.Roles.ADMIN)


class IsAdminOrSelf(permissions.BasePermission):
    """Admin can access all, staff can only access their own"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Admin → always allowed
        if request.user.role == Staff.Roles.ADMIN:
            return True

        # Staff → only own object
        if getattr(obj, 'staffId', None) == getattr(request.user, 'staffId', None):
            return True

        return False
    
class CanChangePin(permissions.BasePermission):
    """Staff can change their own PIN, admin can change any PIN"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Admin → can change any
        if request.user.role == Staff.Roles.ADMIN:
            return True

        # Staff → only own
        return obj.staffId == request.user.staffId
    
class IsAdminOrManagerOrOwner(permissions.BasePermission):
    """Admin, Inventory Manager, or the user themselves"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.role in [Staff.Roles.ADMIN, Staff.Roles.INVENTORY_MANAGER]:
            return True
        return getattr(obj, 'staffId', None) == getattr(request.user, 'staffId', None)


class IsAdminOrInventoryManager(permissions.BasePermission):
    """Admin or inventory manager can perform sensitive inventory actions"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in [
            Staff.Roles.ADMIN, Staff.Roles.INVENTORY_MANAGER
        ])


class IsAuthenticatedAndInventoryManagerOrReadOnly(permissions.BasePermission):
    """Inventory manager write access, authenticated read-only access."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.role in [
            Staff.Roles.ADMIN,
            Staff.Roles.INVENTORY_MANAGER
        ])
