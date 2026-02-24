from rest_framework import permissions

class IsOwner(permissions.BasePermission):
    """
    Custom permission: only allow owners of a league to edit/delete it.
    """

    def has_object_permission(self, request, view, obj):
        return obj.creator == request.user.userprofile