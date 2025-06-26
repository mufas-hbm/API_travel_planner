from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.settings import api_settings
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.authentication import TokenAuthentication

from .models import CustomUser, Destination, TravelPlan, TravelPlanDestination, Activity, Comment
from .serializers import (
    CustomUserSerializer, DestinationSerializer, TravelPlanSerializer,
    TravelPlanDestinationSerializer, ActivitySerializer, CommentSerializer
)
from .permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly, IsTravelPlanOwnerOrReadOnly, IsOwnerOrAdmin, IsOwnerOrAdminOrReadOnly

# --- Authentication Views ---

class UserLoginView(ObtainAuthToken):
    """
    API View for user login.
    Inherits from DRF's `ObtainAuthToken` to handle username/password authentication
    and issue/retrieve authentication tokens.

    Endpoint: POST /api/login/
    Request Body: {"username": "your_username", "password": "your_password"}
    Response: {"token": "your_auth_token", "user_id": 1, "email": "...", "username": "..."}
    """

    def post(self, request, *args, **kwargs):
        """
        Handles the POST request for user login.
        Validates credentials and returns an authentication token.
        """
        # Use the serializer provided by ObtainAuthToken (which expects username and password)
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        # If validation fails (e.g., wrong credentials), raise an exception
        serializer.is_valid(raise_exception=True)
        
        # Get the authenticated user object from the serializer's validated data
        user = serializer.validated_data['user']
        
        # Get or create an authentication token for the user.
        # 'created' will be True if a new token was generated, False if existing.
        token, created = Token.objects.get_or_create(user=user)
        
        # Return the token and some basic user info
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username
        })

class UserLogoutView(APIView):
    """
    API View for user logout.
    Deletes the user's current authentication token, invalidating their session.

    Endpoint: POST /api/logout/
    Authentication: Token (requires `Authorization: Token <your_token>` header)
    Permissions: Requires the user to be authenticated.
    """
    # Use TokenAuthentication to identify the user making the request
    authentication_classes = [TokenAuthentication]
    # Only authenticated users can log out
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles the POST request for user logout.
        Deletes the authentication token associated with the requesting user.
        """
        try:
            # Access the authenticated user's token and delete it
            request.user.auth_token.delete()
            # Return a 204 No Content status for successful deletion
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            # Handle cases where the token might already be gone or other errors
            return Response({"detail": f"Error logging out: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- CustomUser Views ---

class CustomUserListCreateView(generics.ListCreateAPIView):
    """
    API View for managing CustomUser resources.
    Allows:
    - GET (list): Retrieve a list of all users. (Admin only)
    - POST (create): Register a new user. (Any user)

    Endpoint: GET/POST /api/users/
    """
    queryset = CustomUser.objects.all() # Base queryset for all users
    serializer_class = CustomUserSerializer # Serializer for user data
    authentication_classes = [TokenAuthentication] # Requires token for listing (admins)

    def get_permissions(self):
        """
        Custom permission logic based on the request method.
        """
        # If the request is a POST (user registration), allow anyone to access.
        if self.request.method == 'POST':
            return [AllowAny()]
        # For any other method (like GET for listing), only allow admin users.
        return [IsAuthenticated(),IsAdminUser()]

class CustomUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View for retrieving, updating, or deleting a specific CustomUser.
    - Retrieve: A user can retrieve their own profile. Admin can retrieve any profile.
    - Update/Delete: A user can update/delete their own profile. Admin can update/delete any profile.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    authentication_classes = [TokenAuthentication]
    # *** IMPORTANT CHANGE HERE ***
    # Use the new IsOwnerOrAdmin permission.
    # We still keep IsAuthenticated as a baseline for all operations on this view.
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin] # Now it's IsAuthenticated AND (IsOwner OR IsAdmin)

    def get_object(self):
        """
        Retrieves the object instance for the current request.
        Handles the special case for '/api/users/me/'.
        """
        if self.kwargs.get('pk') == 'me':
            # ensure the user is authenticated before returning request.user
            if not self.request.user.is_authenticated:
                raise permissions.NotAuthenticated("Authentication credentials were not provided.")
            return self.request.user
        return super().get_object()

    def perform_update(self, serializer):
        """
        Custom logic executed before saving updates to a CustomUser instance.
        Prevents non-admin users from elevating their privileges.
        """
        if not self.request.user.is_staff and ('is_staff' in serializer.validated_data or 'is_superuser' in serializer.validated_data):
            serializer.validated_data.pop('is_staff', None)
            serializer.validated_data.pop('is_superuser', None)
        serializer.save()


# --- Destination Views ---

class DestinationListCreateView(generics.ListCreateAPIView):
    """
    API View for managing Destination resources.
    Allows:
    - GET (list): Retrieve a list of all destinations. (Any user)
    - POST (create): Create a new destination. (Admin only)

    Endpoint: GET/POST /api/destinations/
    Authentication: Token (required for POST, optional for GET in terms of DRF processing)
    Permissions: `IsAdminOrReadOnly` ensures read-only for non-admins, write for admins.
    """
    queryset = Destination.objects.all() # All destinations
    serializer_class = DestinationSerializer # Serializer for destination data
    authentication_classes = [TokenAuthentication] # Requires token for all operations for consistency
    permission_classes = [IsAuthenticatedOrReadOnly] # Defined in permissions.py: Read for all, Write for Admins

    def perform_create(self, serializer):
        """
        Automatically assigns the current authenticated user as the owner of the destination.
        """
        serializer.save(user=self.request.user)

class DestinationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View for managing a single Destination resource.
    Allows:
    - GET (retrieve): Get details of a specific destination. (Any user)
    - PUT/PATCH (update): Modify details of a specific destination. (Admin only)
    - DELETE (delete): Delete a specific destination. (Admin only)

    Endpoint: GET/PUT/PATCH/DELETE /api/destinations/<int:pk>/
    Authentication: Token
    Permissions: `IsAdminOrReadOnly` ensures read-only for non-admins, write for admins.
    """
    queryset = Destination.objects.all() # All destinations
    serializer_class = DestinationSerializer # Serializer for destination data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    permission_classes = [IsOwnerOrAdminOrReadOnly] # Defined in permissions.py: Read for all, Write for Admins


# --- TravelPlan Views ---

class TravelPlanListCreateView(generics.ListCreateAPIView):
    """
    API View for managing TravelPlan resources.
    Allows:
    - GET (list): Retrieve a list of travel plans. (Authenticated users see their own + public plans)
    - POST (create): Create a new travel plan. (Authenticated users only)

    Endpoint: GET/POST /api/travelplans/
    Authentication: Token
    Permissions: `IsAuthenticatedOrReadOnly` allows authenticated users to create/read,
                 unauthenticated users to only read (if plan is public).
    """
    queryset = TravelPlan.objects.all() # All travel plans (will be filtered by get_queryset)
    serializer_class = TravelPlanSerializer # Serializer for travel plan data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    permission_classes = [IsAuthenticatedOrReadOnly] # Authenticated can do anything (within scope), unauth can only read

    def get_queryset(self):
        """
        Custom queryset to filter travel plans based on user access.
        - If authenticated: See their own travel plans AND public plans by others.
        - If unauthenticated: Only see public travel plans.
        """
        # Start with a base queryset (e.g., all TravelPlans)
        queryset = TravelPlan.objects.all()

        # Check if the requesting user is authenticated
        if self.request.user.is_authenticated:
            # If authenticated, combine their own plans and public plans by others
            user_plans = queryset.filter(user=self.request.user)
            public_plans_not_owned = queryset.filter(is_public=True).exclude(user=self.request.user)
            return (user_plans | public_plans_not_owned).distinct().order_by('-created_at')
        else:
            # If unauthenticated (AnonymousUser), only return public plans
            return queryset.filter(is_public=True).order_by('-created_at')

    def perform_create(self, serializer):
        """
        Custom logic executed before saving a new TravelPlan instance.
        Automatically assigns the authenticated user as the owner.
        """
        # The user making the request is automatically set as the owner of the new travel plan
        serializer.save(user=self.request.user)

class TravelPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View for managing a single TravelPlan resource.
    Allows:
    - GET (retrieve): Get details of a specific travel plan. (Owner or if plan is public)
    - PUT/PATCH (update): Modify details of a specific travel plan. (Owner only)
    - DELETE (delete): Delete a specific travel plan. (Owner only)

    Endpoint: GET/PUT/PATCH/DELETE /api/travelplans/<int:pk>/
    Authentication: Token
    Permissions: `IsOwnerOrReadOnly` allows owner to modify, and read for authenticated users (handled by get_object).
                 `IsAuthenticatedOrReadOnly` ensures basic authentication for writes and read access.
    """
    queryset = TravelPlan.objects.all() # All travel plans
    serializer_class = TravelPlanSerializer # Serializer for travel plan data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    # Permissions for this view:
    # - IsOwnerOrReadOnly: The primary permission to ensure only owners can write (update/delete).
    # - IsAuthenticatedOrReadOnly: Ensures authenticated users can read.
    # The 'public' aspect for reads by non-owners is handled in get_object.
    permission_classes = [IsOwnerOrAdminOrReadOnly]

    def get_object(self):
        """
        Custom logic to retrieve a TravelPlan object based on permissions.
        - If the user is the owner, they can access it.
        - If it's a GET request and the plan is public, any authenticated user can access it.
        """
        obj = super().get_object() # Get the object normally using the PK from the URL
        
        # If the request is a safe method (GET, HEAD, OPTIONS) and the user is NOT the owner
        # AND the plan is NOT public, then deny permission.
        if (self.request.method in permissions.SAFE_METHODS and
            obj.user != self.request.user and
            not obj.is_public):
            raise PermissionDenied("You do not have permission to view this private travel plan.")
        # Otherwise, the user has permission to access the object
        return obj


# --- TravelPlanDestination Views ---
# These views manage the *individual entries* within a travel plan (e.g., Paris in 'My Europe Trip').
# They are tied to the ownership of the parent TravelPlan.

class TravelPlanDestinationListCreateView(generics.ListCreateAPIView):
    """
    API View for managing TravelPlanDestination entries.
    Allows:
    - GET (list): Retrieve a list of destination entries. (Only for travel plans owned by the current user)
    - POST (create): Create a new destination entry. (Only for travel plans owned by the current user)

    Endpoint: GET/POST /api/travelplandestinations/
    Authentication: Token
    Permissions: `IsTravelPlanOwnerOrReadOnly` ensures only the owner of the *parent TravelPlan*
                 can create/list these entries.
    """
    queryset = TravelPlanDestination.objects.all() # All TPD entries (will be filtered by get_queryset)
    serializer_class = TravelPlanDestinationSerializer # Serializer for TPD data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    # Custom permission: only owner of the related TravelPlan can interact
    permission_classes = [IsOwnerOrAdminOrReadOnly]

    def get_queryset(self):
        """
        Custom queryset to filter TravelPlanDestination entries.
        Only shows entries for travel plans that belong to the current authenticated user.
        Unauthenticated users will not see any entries here.
        """
        # Check if the requesting user is authenticated
        if self.request.user.is_authenticated:
            # If authenticated, filter TPD entries where the associated travel_plan's user
            # is the current requesting user.
            return self.queryset.filter(travel_plan__user=self.request.user).order_by('order')
        else:
            # If unauthenticated (AnonymousUser), return an empty queryset,
            # as TPDs are not public independent of a user's plan.
            return TravelPlanDestination.objects.none() # <--- THIS IS THE KEY FIX

    def perform_create(self, serializer):
        """
        Custom logic executed before saving a new TravelPlanDestination instance.
        The `travel_plan` field must be provided in the request body as an ID.
        The serializer's `create` method (if overridden) will handle converting this ID to an object.
        """
        # The permission `IsTravelPlanOwnerOrReadOnly` ensures the user has access
        # to the parent travel plan, so we just save the valid data.
        serializer.save()

class TravelPlanDestinationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View for managing a single TravelPlanDestination entry.
    Allows:
    - GET (retrieve): Get details of a specific entry. (Only if parent TravelPlan is owned by current user)
    - PUT/PATCH (update): Modify details of a specific entry. (Only if parent TravelPlan is owned by current user)
    - DELETE (delete): Delete a specific entry. (Only if parent TravelPlan is owned by current user)

    Endpoint: GET/PUT/PATCH/DELETE /api/travelplandestinations/<int:pk>/
    Authentication: Token
    Permissions: `IsTravelPlanOwnerOrReadOnly` ensures only the owner of the *parent TravelPlan*
                 can interact with this specific entry.
    """
    queryset = TravelPlanDestination.objects.all() # All TPD entries
    serializer_class = TravelPlanDestinationSerializer # Serializer for TPD data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    # Custom permission: only owner of the related TravelPlan can interact
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def perform_create(self, serializer):
        serializer.save()
# --- Activity Views ---

class ActivityListCreateView(generics.ListCreateAPIView):
    """
    API View for managing Activity resources.
    Allows:
    - GET (list): Retrieve a list of activities. (Only for travel plans owned by the current user)
    - POST (create): Create a new activity. (Only for travel plans owned by the current user)

    Endpoint: GET/POST /api/activities/
    Authentication: Token
    Permissions: `IsTravelPlanOwnerOrReadOnly` ensures only the owner of the *parent TravelPlan*
                 can create/list activities.
    """
    queryset = Activity.objects.all() # All activities (will be filtered by get_queryset)
    serializer_class = ActivitySerializer # Serializer for activity data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    # Custom permission: only owner of the related TravelPlan can interact
    permission_classes = [IsOwnerOrAdminOrReadOnly]

    def get_queryset(self):
        """
        Custom queryset to filter Activity entries.
        Only shows activities that belong to travel plans owned by the current authenticated user.
        Unauthenticated users will not see any activities here, as activities are
        always linked to a user's travel plan.
        """
        # Check if the requesting user is authenticated
        if self.request.user.is_authenticated:
            # Filter activities where the associated travel_plan's user is the current requesting user
            return self.queryset.filter(travel_plan__user=self.request.user).order_by('date')
        else:
            # If unauthenticated (AnonymousUser), return an empty queryset,
            # as activities are not public independent of a user's plan.
            return Activity.objects.none()

    def perform_create(self, serializer):
        """
        Custom logic executed before saving a new Activity instance.
        The `travel_plan` and `destination` fields must be provided as IDs in the request.
        The serializer's custom `create` method handles converting these IDs to objects.
        """
        # The permission `IsTravelPlanOwnerOrReadOnly` ensures the user has access
        # to the parent travel plan, so we just save the valid data.
        serializer.save()

class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View for managing a single Activity resource.
    Allows:
    - GET (retrieve): Get details of a specific activity. (Only if parent TravelPlan is owned by current user)
    - PUT/PATCH (update): Modify details of a specific activity. (Only if parent TravelPlan is owned by current user)
    - DELETE (delete): Delete a specific activity. (Only if parent TravelPlan is owned by current user)

    Endpoint: GET/PUT/PATCH/DELETE /api/activities/<int:pk>/
    Authentication: Token
    Permissions: `IsTravelPlanOwnerOrReadOnly` ensures only the owner of the *parent TravelPlan*
                 can interact with this specific activity.
    """
    queryset = Activity.objects.all() 
    serializer_class = ActivitySerializer 
    authentication_classes = [TokenAuthentication] 
    permission_classes = [IsAuthenticated,IsOwnerOrAdmin]


# --- Comment Views ---

class CommentListCreateView(generics.ListCreateAPIView):
    """
    API View for managing Comment resources.
    Allows:
    - GET (list): Retrieve a list of all comments. (Any authenticated user)
    - POST (create): Create a new comment. (Any authenticated user)

    Endpoint: GET/POST /api/comments/
    Authentication: Token
    Permissions: `IsAuthenticatedOrReadOnly` allows authenticated users to create/read,
                 unauthenticated users to only read.
    """
    queryset = Comment.objects.all() # All comments
    serializer_class = CommentSerializer # Serializer for comment data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    permission_classes = [IsAuthenticatedOrReadOnly] # Authenticated can create/read, unauth can only read

    def perform_create(self, serializer):
        """
        Custom logic executed before saving a new Comment instance.
        The user is automatically set within the serializer's `create` method,
        so this `perform_create` just triggers the save.
        """
        # The serializer's create method handles assigning the user and generic object.
        serializer.save()

class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API View for managing a single Comment resource.
    Allows:
    - GET (retrieve): Get details of a specific comment. (Any authenticated user)
    - PUT/PATCH (update): Modify details of a specific comment. (Only the owner of the comment)
    - DELETE (delete): Delete a specific comment. (Only the owner of the comment)

    Endpoint: GET/PUT/PATCH/DELETE /api/comments/<int:pk>/
    Authentication: Token
    Permissions: `IsOwnerOrReadOnly` ensures owners can modify/delete their own comments,
                 and authenticated users can read.
    """
    queryset = Comment.objects.all() # All comments
    serializer_class = CommentSerializer # Serializer for comment data
    authentication_classes = [TokenAuthentication] # Requires token for all operations
    permission_classes = [IsOwnerOrAdminOrReadOnly] # Defined in permissions.py: Owner can write, authenticated can read

