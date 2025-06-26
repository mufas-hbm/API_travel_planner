from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit or delete it.
    Read permissions are allowed for any authenticated user.
    Assumes the object instance has an 'user' attribute.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated request.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.user == request.user

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow access if the user is either the owner of the object
    OR if the user is an administrator (is_staff).

    This permission now covers direct 'user'/'owner' fields, related 'travel_plan.user' fields,
    and the user object itself.
    """
    def has_object_permission(self, request, view, obj):
        # Admins always have permission
        if request.user and request.user.is_staff:
            return True

        # Check direct ownership via 'user' attribute (e.g., TravelPlan, CustomUser)
        if hasattr(obj, 'user') and obj.user:
            return obj.user == request.user
            
        # Check chained ownership via 'travel_plan' attribute (e.g., TravelPlanDestination, Activity)
        if hasattr(obj, 'travel_plan') and obj.travel_plan:
            return obj.travel_plan.user == request.user

        # If the object itself is a user (e.g., in CustomUserDetailView for /users/me/)
        if isinstance(obj, type(request.user)):
            return obj == request.user

        # If none of the above conditions are met, deny.
        return False

    def has_permission(self, request, view):
        # For this permission, we generally require authentication for any interaction beyond basic
        # (potentially public) reads which are handled by IsOwnerOrAdminOrReadOnly's 'read' part.
        # This means, for any method where IsOwnerOrAdmin is used, we expect the user to be authenticated.
        return request.user and request.user.is_authenticated

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow admin users to edit or delete objects.
    Read permissions are allowed for any request (authenticated or not).
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to admin users.
        return request.user and request.user.is_staff

class IsTravelPlanOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission for TravelPlanDestination and Activity models.
    Allows read access to anyone authenticated.
    Allows write access (create, update, delete) only if the related
    TravelPlan's owner is the requesting user.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated request.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if hasattr(obj, 'travel_plan') and obj.travel_plan:
            return obj.travel_plan.user == request.user
        
        return False # Deny if no travel_plan or not owner

    def has_permission(self, request, view):
        if request.method == 'POST':
            return request.user and request.user.is_authenticated
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user and request.user.is_authenticated
    

class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    Custom permission that allows:
    - Read (GET, HEAD, OPTIONS) for any user (authenticated or unauthenticated).
    - Write (POST, PUT, PATCH, DELETE) only for:
        - The owner of the object (if the object has an 'owner' attribute).
        - An admin user (is_staff=True).
    Assumes the object either has an 'owner' ForeignKey to a User,
    or the object itself IS a User instance (e.g., for user profile views).
    """

    def has_permission(self, request, view):
        # Allow read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # For write permissions (POST, PUT, PATCH, DELETE), require authentication first.
        # The object-level permission check (has_object_permission) will then refine this.
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Allow read permissions for any request (already handled by has_permission if it's SAFE_METHODS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # For write methods:
        # 1. Admin users always have permission.
        if request.user and request.user.is_staff:
            return True
        
        # 2. Check for ownership via 'user' attribute (common for many models like TravelPlan)
        if hasattr(obj, 'user') and obj.user:
            return obj.user == request.user
        
        # 3. If the object itself is a user (e.g., in CustomUserDetailView for /users/me/)
        # and the requesting user is that user.
        if isinstance(obj, type(request.user)):
            return obj == request.user

        # If none of the above conditions are met, deny permission for write methods.
        return False