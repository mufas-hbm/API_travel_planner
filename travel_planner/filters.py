
import django_filters
from .models import CustomUser, Destination, TravelPlan, TravelPlanDestination, Activity, Comment

class CustomUserFilter(django_filters.FilterSet):
    username = django_filters.CharFilter(lookup_expr='icontains') #case insensitive
    email = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    preferred_travel_style = django_filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'city', 'preferred_travel_style']

class DestinationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    country = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    is_popular = django_filters.BooleanFilter()

    class Meta:
        model = Destination
        fields = ['name', 'country', 'city', 'is_popular']

class TravelPlanFilter(django_filters.FilterSet):
    # Filter by user ID
    user = django_filters.NumberFilter(field_name='user__id')

    is_public = django_filters.BooleanFilter()
    
    # Date range filters for start_date and end_date
    start_date_gte = django_filters.DateFilter(field_name='start_date', lookup_expr='gte') 
    start_date_lte = django_filters.DateFilter(field_name='start_date', lookup_expr='lte') 
    end_date_gte = django_filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_lte = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')

    # Budget range filters
    budget_gte = django_filters.NumberFilter(field_name='budget', lookup_expr='gte')
    budget_lte = django_filters.NumberFilter(field_name='budget', lookup_expr='lte')

    class Meta:
        model = TravelPlan
        fields = ['user', 'is_public','start_date', 'end_date','budget']

class TravelPlanDestinationFilter(django_filters.FilterSet):
    # Filter by IDs of related models
    travel_plan = django_filters.NumberFilter(field_name='travel_plan__id')
    destination = django_filters.NumberFilter(field_name='destination__id')

    # Date range filters for arrival_date and departure_date
    arrival_date_gte = django_filters.DateFilter(field_name='arrival_date', lookup_expr='gte')
    arrival_date_lte = django_filters.DateFilter(field_name='arrival_date', lookup_expr='lte')
    departure_date_gte = django_filters.DateFilter(field_name='departure_date', lookup_expr='gte')
    departure_date_lte = django_filters.DateFilter(field_name='departure_date', lookup_expr='lte')

    class Meta:
        model = TravelPlanDestination
        fields = ['travel_plan', 'destination','order','arrival_date', 'departure_date' ]

class ActivityFilter(django_filters.FilterSet):
    # Filter by IDs of related models
    travel_plan = django_filters.NumberFilter(field_name='travel_plan__id')
    destination = django_filters.NumberFilter(field_name='destination__id')

    # Date range filters
    date_gte = django_filters.DateTimeFilter(field_name='date', lookup_expr='gte') 
    date_lte = django_filters.DateTimeFilter(field_name='date', lookup_expr='lte')
    
    # Cost range filters
    cost_gte = django_filters.NumberFilter(field_name='cost', lookup_expr='gte')
    cost_lte = django_filters.NumberFilter(field_name='cost', lookup_expr='lte')

    class Meta:
        model = Activity
        fields = ['travel_plan', 'destination', 'date', 'cost','name' ]

class CommentFilter(django_filters.FilterSet):
    # Filter by user ID
    user = django_filters.NumberFilter(field_name='user__id')
    # Filter by text
    text = django_filters.CharFilter(lookup_expr='icontains')
    
    # Date range for creation time
    created_at_gte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_at_lte = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')

    # Filtering for Generic Foreign Key (by content_type and object_id)
    content_type_id = django_filters.NumberFilter() 
    object_id = django_filters.NumberFilter() 

    class Meta:
        model = Comment
        fields = ['user', 'text', 'created_at','content_type_id', 'object_id']