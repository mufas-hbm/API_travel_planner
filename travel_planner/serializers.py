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
    # Define password as a write-only field, so it's accepted on input but not returned on output.
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'date_birth', 'city', 'zip_code', 'preferred_travel_style', 'password'
        ]
        #read_only_fields = ['username', 'email']

    def validate_date_birth(self, value):
        """
        Validate that the date of birth is not in the future.
        """
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value
    
    def create(self, validated_data):
        """
        Custom create method to handle user registration.
        Uses `CustomUser.objects.create_user` for secure password hashing.
        """
        # Pop the password from validated_data because create_user expects it separately
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(password=password, **validated_data)
        return user

    def update(self, instance, validated_data):
        """
        Custom update method to handle password changes.
        If a new password is provided, set it securely.
        """
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password) # set_password hash the new password

        # Now, handle updates for other fields
        return super().update(instance, validated_data)

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

# --- TravelPlanDestination (Through Model) Serializer - FORWARD DECLARATION ---
# Declare this class first so TravelPlanSerializer can refer to it.
# Let's define it here with the assumption that TravelPlan will use StringRelatedField for it
class TravelPlanDestinationSerializer(serializers.ModelSerializer):
    # This will be defined in full below, after TravelPlanSerializer
    pass

# --- TravelPlan Serializer ---
class TravelPlanSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)

    '''
    serializers.StringRelatedField is a simple and effective solution for displaying related
    objects in a serializer's output without creating complex nested structures or circular 
    dependencies, especially when you only need a concise representation of the related item.
    '''
    destinations_in_plan = serializers.StringRelatedField(
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


# --- TravelPlanDestination ---
class TravelPlanDestinationSerializer(serializers.ModelSerializer):
    # Field for OUTPUT (nested representation of Destination)
    destination_detail = DestinationSerializer(source='destination', read_only=True)
    
    travel_plan_display = serializers.StringRelatedField(source='travel_plan', read_only=True)


    # Fields for INPUT (ID representation)
    destination_id = serializers.PrimaryKeyRelatedField(
        queryset=Destination.objects.all(), write_only=True
    )
    travel_plan_id = serializers.PrimaryKeyRelatedField(
        queryset=TravelPlan.objects.all(), write_only=True
    )

    class Meta:
        model = TravelPlanDestination
        fields = [
            'id', 'order', 'arrival_date', 'departure_date', 
            'destination_detail', 'travel_plan_display', 
            'destination_id', 'travel_plan_id' 
        ]

    def validate(self, data):
        travel_plan_obj = data.get('travel_plan_id') 
        arrival_date = data.get('arrival_date')
        departure_date = data.get('departure_date')
        
        errors = {} 

        # Ownership check
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if not request.user.is_staff:
                if travel_plan_obj and travel_plan_obj.user != request.user:
                    errors['travel_plan_id'] = ["You do not have permission to add destinations to this travel plan."]
        else:
            errors['non_field_errors'] = ["Authentication is required to create a Travel Plan Destination."]
        
        # Date order check
        if arrival_date and departure_date and arrival_date > departure_date:
            errors['non_field_errors'] = errors.get('non_field_errors', []) + ["Arrival date cannot be after departure date."]

        # Check if we have a travel plan and dates before proceeding with range checks
        if travel_plan_obj and arrival_date and departure_date:
            if arrival_date < travel_plan_obj.start_date:
                errors['arrival_date'] = errors.get('arrival_date', []) + ["Arrival date cannot be before the travel plan's start date."]
            
            if departure_date > travel_plan_obj.end_date:
                errors['departure_date'] = errors.get('departure_date', []) + ["Departure date cannot be after the travel plan's end date."]
            
            
            if not (travel_plan_obj.start_date <= arrival_date and departure_date <= travel_plan_obj.end_date):
                 if 'arrival_date' not in errors and 'departure_date' not in errors:
                    errors['non_field_errors'] = errors.get('non_field_errors', []) + ["Destination dates must be fully within the associated travel plan's dates."]
            
        if errors:
            raise serializers.ValidationError(errors) # Raise all collected errors
            
        return data
    
    def create(self, validated_data):
        travel_plan = validated_data.pop('travel_plan_id')
        destination = validated_data.pop('destination_id')
        
        return TravelPlanDestination.objects.create(
            travel_plan=travel_plan,
            destination=destination,
            **validated_data
        )

    def update(self, instance, validated_data):
        if 'travel_plan_id' in validated_data:
            instance.travel_plan = validated_data.pop('travel_plan_id')
        if 'destination_id' in validated_data:
            instance.destination = validated_data.pop('destination_id')

        return super().update(instance, validated_data)

# --- Activity Serializer ---
class ActivitySerializer(serializers.ModelSerializer):
    # Fields for OUTPUT
    travel_plan_name = serializers.CharField(source='travel_plan.name', read_only=True)
    destination_name = serializers.CharField(source='destination.name', read_only=True)
    destination_detail = DestinationSerializer(source='destination', read_only=True) # Nested destination output
    
    # Use StringRelatedField for travel_plan to break circular dependency
    travel_plan_display = serializers.StringRelatedField(source='travel_plan', read_only=True)


    # Fields for INPUT
    destination_id = serializers.PrimaryKeyRelatedField(queryset=Destination.objects.all(), write_only=True)
    travel_plan_id = serializers.PrimaryKeyRelatedField(queryset=TravelPlan.objects.all(), write_only=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'name', 'description', 'date', 'cost', 'notes', # Direct fields
            'travel_plan_name', 'destination_name', # Read-only char fields
            'destination_detail', 'travel_plan_display', # Output-only nested/string fields
            'destination_id', 'travel_plan_id' # Input-only ID fields
        ]


    def validate_cost(self, value):
        if value < 0:
            raise serializers.ValidationError("Cost cannot be negative.")
        return value

    def validate(self, data):
        travel_plan_obj = data.get('travel_plan_id')
        activity_date = data.get('date')

        # Check if the requesting user owns the linked travel plan ---
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Admins can bypass this check
            if not request.user.is_staff:
                # If the travel_plan_obj exists and its user is not the requesting user, deny.
                if travel_plan_obj and travel_plan_obj.user != request.user:
                    raise serializers.ValidationError(
                        {"travel_plan_id": "You do not have permission to add activities to this travel plan."}
                    )
        else:
            # If unauthenticated, they shouldn't even reach here for POST due to permission_classes,
            raise serializers.ValidationError("Authentication is required to create an Activity.")
        

        if travel_plan_obj and activity_date:
            formatted_activity_date = activity_date.date()

            if not (travel_plan_obj.start_date <= formatted_activity_date <= travel_plan_obj.end_date):
                raise serializers.ValidationError(
                    {"date": "Activity date must fall within the associated travel plan's start and end dates."}
                )
        return data

    def create(self, validated_data):
        travel_plan = validated_data.pop('travel_plan_id')
        destination = validated_data.pop('destination_id')

        return Activity.objects.create(
            travel_plan=travel_plan,
            destination=destination,
            **validated_data
        )

    def update(self, instance, validated_data):
        if 'travel_plan_id' in validated_data:
            instance.travel_plan = validated_data.pop('travel_plan_id')
        if 'destination_id' in validated_data:
            instance.destination = validated_data.pop('destination_id')

        return super().update(instance, validated_data)


# --- Comment Serializer ---
class CommentSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    content_object_display = serializers.SerializerMethodField()

    content_type_id = serializers.IntegerField(write_only=True)
    object_id = serializers.IntegerField(write_only=True)


    class Meta:
        model = Comment
        fields = [
            'id', 'user_username', 'text', 'created_at', 'updated_at',
            'content_object_display',
            'content_type_id', 'object_id'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_content_object_display(self, obj):
        if obj.content_object:
            return str(obj.content_object)
        return None

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment text cannot be empty.")
        if len(value) > 1000:
            raise serializers.ValidationError("Comment text is too long (max 1000 characters).")
        return value
    
    def validate_content_type_id(self, value):
        # This validation only applies during updates (when an instance exists)
        if self.instance and value is not None and self.instance.content_type_id != value:
            raise serializers.ValidationError("Content type cannot be changed for an existing comment.")
        return value

    def validate_object_id(self, value):
        # This validation only applies during updates (when an instance exists)
        if self.instance and value is not None and self.instance.object_id != value:
            raise serializers.ValidationError("Object ID cannot be changed for an existing comment.")
        return value

    def create(self, validated_data):
        content_type_id = validated_data.pop('content_type_id')
        object_id = validated_data.pop('object_id')

        request_user = self.context.get('request').user
        if not request_user or not request_user.is_authenticated:
            raise serializers.ValidationError({"user": "Authentication is required to create a comment."})

        try:
            content_type = ContentType.objects.get(id=content_type_id)
            ModelClass = content_type.model_class()

            if ModelClass is None:
                raise serializers.ValidationError({"content_type_id": f"No model found for content type ID {content_type_id}."})

            allowed_models = ['destination', 'travelplan']
            if content_type.model not in allowed_models:
                raise serializers.ValidationError(
                    {"content_type_id": f"Comments are not allowed on '{content_type.model}' objects. "
                                     f"Allowed types are: {', '.join(allowed_models)}."}
                )

            related_object = ModelClass.objects.get(id=object_id)
            
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({"content_type_id": "Content type not found."})
        except ModelClass.DoesNotExist:
            raise serializers.ValidationError(
                {"object_id": f"The '{content_type.model}' object with ID '{object_id}' was not found."}
            )
        
        comment = Comment.objects.create(
            user=request_user,
            content_type=content_type,
            object_id=object_id,
            content_object=related_object,
            **validated_data
        )
        return comment

    def update(self, instance, validated_data):
        validated_data.pop('content_type_id', None)
        validated_data.pop('object_id', None)
        
        validated_data.pop('user', None) 

        return super().update(instance, validated_data)