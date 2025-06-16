from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import CustomUser, Destination, TravelPlan, TravelPlanDestination, Activity, Comment

# --- User Serializer ---
class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the CustomUser model.
    Exposes essential user details and their custom profile fields.
    """
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'date_birth', 'city', 'zip_code', 'preferred_travel_style'
        ]
        read_only_fields = ['username', 'email']


# --- Destination Serializer ---
class DestinationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Destination model.
    Includes all fields for displaying and creating destinations.
    """
    class Meta:
        model = Destination
        fields = '__all__' 
        read_only_fields = ['created_at', 'updated_at']


# --- TravelPlanDestination (Through Model) Serializer ---
# This serializer is used to represent the relationship between TravelPlan and Destination
# It includes details of the destination and the specific attributes of its inclusion in a plan.
class TravelPlanDestinationSerializer(serializers.ModelSerializer):
    # Nested serializer to display full destination details
    destination = DestinationSerializer(read_only=True)

    class Meta:
        model = TravelPlanDestination
        fields = [
            'id', 'destination', 'order', 'arrival_date', 'departure_date'
        ]


# --- TravelPlan Serializer ---
class TravelPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for the TravelPlan model.
    Includes nested serializers for related CustomUser and TravelPlanDestination instances.
    """
    # Use CustomUserSerializer for read-only display of the user who created the plan
    user = CustomUserSerializer(read_only=True)

    # Use TravelPlanDestinationSerializer to represent the destinations in the plan.
    # many=True because a TravelPlan can have many TravelPlanDestinations.
    # source='travelplandestination_set' refers to the reverse relationship name from TravelPlanDestination to TravelPlan.
    # Default reverse name is <related_model_name>_set
    destinations_in_plan = TravelPlanDestinationSerializer(
        source='travelplandestination_set', many=True, read_only=True
    )

    class Meta:
        model = TravelPlan
        fields = [
            'id', 'name', 'user', 'start_date', 'end_date', 'description',
            'budget', 'is_public', 'created_at', 'updated_at', 'destinations_in_plan'
        ]
        read_only_fields = ['created_at', 'updated_at'] 


# --- Activity Serializer ---
class ActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for the Activity model.
    Includes IDs for related TravelPlan and Destination.
    """
    # Display the related TravelPlan and Destination names for readability
    travel_plan_name = serializers.CharField(source='travel_plan.name', read_only=True)
    destination_name = serializers.CharField(source='destination.name', read_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'name', 'description', 'travel_plan', 'travel_plan_name',
            'destination', 'destination_name', 'date', 'cost', 'notes'
        ]

# --- Comment Serializer ---
class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Comment model using GenericForeignKey.
    Handles the generic relationship for comments on various objects.
    """
    # Read-only field to display the username of the commenter
    user_username = serializers.CharField(source='user.username', read_only=True)

    # For displaying the related object's name/representation on read operations
    # This field is for output only.
    content_object_display = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'user_username', 'text', 'created_at', 'updated_at',
            'content_type', 'object_id', 'content_object_display'
        ]
        read_only_fields = ['created_at', 'updated_at', 'user'] # User is set automatically on creation