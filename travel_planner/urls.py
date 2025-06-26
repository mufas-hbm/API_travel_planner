from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token # DRF's default token obtainer
from . import views

urlpatterns = [
    # --- Authentication URLs ---
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),

    # --- User URLs ---
    path('users/', views.CustomUserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', views.CustomUserDetailView.as_view(), name='user-detail'),
    path('users/me/', views.CustomUserDetailView.as_view(), {'pk': 'me'}, name='user-detail-me'), # Allows /users/me/ to get current user

    # --- Destination URLs ---
    path('destinations/', views.DestinationListCreateView.as_view(), name='destination-list-create'),
    path('destinations/<int:pk>/', views.DestinationDetailView.as_view(), name='destination-detail'),

    # --- Travel Plan URLs ---
    path('travelplans/', views.TravelPlanListCreateView.as_view(), name='travelplan-list-create'),
    path('travelplans/<int:pk>/', views.TravelPlanDetailView.as_view(), name='travelplan-detail'),

    # --- Travel Plan Destination URLs (for managing itinerary items) ---
    path('travelplandestinations/', views.TravelPlanDestinationListCreateView.as_view(), name='travelplandestination-list-create'),
    path('travelplandestinations/<int:pk>/', views.TravelPlanDestinationDetailView.as_view(), name='travelplandestination-detail'),

    # --- Activity URLs ---
    path('activities/', views.ActivityListCreateView.as_view(), name='activity-list-create'),
    path('activities/<int:pk>/', views.ActivityDetailView.as_view(), name='activity-detail'),

    # --- Comment URLs ---
    path('comments/', views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', views.CommentDetailView.as_view(), name='comment-detail'),
]
