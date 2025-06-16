from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from datetime import date
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

    def validate_date_birth(self, value):
        """
        Validate that the date of birth is not in the future.
        """
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value
    
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

    def validate_latitude(self, value):
        """
        Validate that latitude is within the valid range (-90 to +90).
        """
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        """
        Validate that longitude is within the valid range (-180 to +180).
        """
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value

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

    def validate(self, data):
        """
        Ensures logical date order and that destination dates fit within the parent travel plan's dates.
        """
        arrival_date = data.get('arrival_date')
        departure_date = data.get('departure_date')
        travel_plan = data.get('travel_plan') 

        # 1. Check if arrival date & departure_date are not None 
        # Check if arrival date is before departure date
        if arrival_date and departure_date and arrival_date > departure_date:
            raise serializers.ValidationError("Arrival date cannot be after departure date.")

        # 2. Check if destination dates are within the main travel plan's dates
        # This part applies when creating/updating a TravelPlanDestination entry directly,
        # where the 'travel_plan' ForeignKey is part of the submitted data.
        if travel_plan and arrival_date and departure_date:
            if arrival_date < travel_plan.start_date:
                raise serializers.ValidationError(
                    {"arrival_date": "Arrival date cannot be before the travel plan's start date."}
                )
            if departure_date > travel_plan.end_date:
                raise serializers.ValidationError(
                    {"departure_date": "Departure date cannot be after the travel plan's end date."}
                )
            # ensure the destination's stay is fully contained within the plan
            if departure_date < travel_plan.start_date or arrival_date > travel_plan.end_date:
                 raise serializers.ValidationError(
                    "Destination dates must be fully within the associated travel plan's dates."
                 )
            
        return data
    
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

    def validate_budget(self, value):
        """
        Validate that the budget is a positive value.
        """
        if value <= 0:
            raise serializers.ValidationError("Budget must be a positive value.")
        return value
    
    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("Start date cannot be after end date.")
        return data
    
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

    def validate_cost(self, value):
        """
        Validate that the activity cost is a non-negative value.
        """
        if value < 0:
            raise serializers.ValidationError("Cost cannot be negative.")
        return value
    
    def validate(self, data):
        travel_plan = data.get('travel_plan') or (self.instance.travel_plan if self.instance else None)
        activity_date = data.get('date') # is datetime format because includes at what time the activity beginns

        if travel_plan and activity_date:
            formatted_activity_date = activity_date.date() # Convert datetime to date for comparison

            if not (travel_plan.start_date <= formatted_activity_date <= travel_plan.end_date):
                raise serializers.ValidationError(
                    {"date": "Activity date must fall within the associated travel plan's start and end dates."}
                )
        return data

    def create(self, validated_data):
        """
        Overrides the default ModelSerializer create method to handle
        Foreign Key assignments for `travel_plan` and `destination`.

        Clients typically send IDs for foreign key fields. This method
        converts those IDs into actual model instances before saving.

        Args:
            validated_data (dict): A dictionary of validated data, where
                                   'travel_plan' and 'destination' might
                                   initially be IDs from the request.

        Returns:
            Activity: The newly created Activity instance with associated
                      TravelPlan and Destination objects.

        Raises:
            serializers.ValidationError: If the provided `travel_plan` or
                                         `destination` ID does not exist.
        """
        # Extract the raw IDs for foreign key relationships from the client's request data.
        travel_plan_id = self.context['request'].data.get('travel_plan')
        destination_id = self.context['request'].data.get('destination')

        if travel_plan_id:
            try:
                validated_data['travel_plan'] = TravelPlan.objects.get(id=travel_plan_id)
            except TravelPlan.DoesNotExist:
                raise serializers.ValidationError({"travel_plan": "TravelPlan not found."})
        
        if destination_id:
            try:
                validated_data['destination'] = Destination.objects.get(id=destination_id)
            except Destination.DoesNotExist:
                raise serializers.ValidationError({"destination": "Destination not found."})

        return super().create(validated_data)
    
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
    
    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        if len(value) > 1000:
            raise serializers.ValidationError("Comment text is too long (max 1000 characters).")
        return value