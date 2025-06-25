import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from travel_planner.models import Destination, TravelPlan, TravelPlanDestination, Activity, Comment
from travel_planner.serializers import (
    CustomUserSerializer, DestinationSerializer, TravelPlanSerializer,
    TravelPlanDestinationSerializer, ActivitySerializer, CommentSerializer
)
from django.contrib.auth.models import AnonymousUser

# Get the CustomUser model defined in settings.AUTH_USER_MODEL
CustomUser = get_user_model()
# --- Serializer Tests ---
# Test serializer validation rules and custom create/update methods

class CustomUserSerializerTest(TestCase):
    """
    Tests for CustomUserSerializer.
    """
    def test_create_user_serializer(self):
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepassword',
            'date_birth': '1995-01-01',
            'preferred_travel_style': 'CULTURAL'
        }
        serializer = CustomUserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertIsInstance(user, CustomUser)
        self.assertEqual(user.username, 'newuser')
        self.assertTrue(user.check_password('securepassword')) # Check if password is hashed

    def test_update_user_password_serializer(self):
        user = CustomUser.objects.create_user(username='updater', password='oldpassword')
        data = {'password': 'newstrongpassword'}
        serializer = CustomUserSerializer(instance=user, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_user = serializer.save()
        self.assertTrue(updated_user.check_password('newstrongpassword'))
        self.assertFalse(updated_user.check_password('oldpassword'))

    def test_validate_date_birth_future(self):
        data = {
            'username': 'futureuser',
            'email': 'future@example.com',
            'password': 'password',
            'date_birth': str(datetime.date.today() + datetime.timedelta(days=1))
        }
        serializer = CustomUserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('date_birth', serializer.errors)
        self.assertIn("Date of birth cannot be in the future.", str(serializer.errors['date_birth']))

class DestinationSerializerTest(TestCase):
    """
    Tests for DestinationSerializer.
    """
    def test_create_destination_serializer(self):
        """
        Test that the DestinationSerializer can successfully create a new Destination object.
        """
        initial_destination_count = Destination.objects.count()
        data = {
            'name': 'New City',
            'description': 'A beautiful new city.',
            'country': 'Imaginaryland',
            'city': 'Metropolis',
            'latitude': 10.0,
            'longitude': 20.0,
            'image_url': 'http://example.com/newcity.jpg',
            'is_popular': False
        }
        serializer = DestinationSerializer(data=data)
        # Assert that the serializer is valid.
        self.assertTrue(serializer.is_valid(),serializer.errors)
        
        # Save the serializer to create the object in the database
        destination = serializer.save()
        
        # Assert that an instance of Destination was returned
        self.assertIsInstance(destination, Destination)
        
        # Assert that the object was actually created in the database
        self.assertEqual(Destination.objects.count(), initial_destination_count + 1)
        
        # Verify some attributes of the created object
        self.assertEqual(destination.name, 'New City')
        self.assertEqual(destination.country, 'Imaginaryland')
        self.assertEqual(destination.city, 'Metropolis')
        self.assertEqual(float(destination.latitude), 10.0) #Convert Decimal to float for direct comparison
        self.assertEqual(float(destination.longitude), 20.0)
        self.assertFalse(destination.is_popular)

    def test_validate_latitude_out_of_range(self):
        data = {
            'name': 'Test Dest', 'country': 'Test', 'latitude': 91.0, 'longitude': 0.0
        }
        serializer = DestinationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('latitude', serializer.errors)
        self.assertIn("Latitude must be between -90 and 90.", str(serializer.errors['latitude']))

    def test_validate_longitude_out_of_range(self):
        data = {
            'name': 'Test Dest', 'country': 'Test', 'latitude': 0.0, 'longitude': 181.0
        }
        serializer = DestinationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('longitude', serializer.errors)
        self.assertIn("Longitude must be between -180 and 180.", str(serializer.errors['longitude']))

class TravelPlanSerializerTest(TestCase):
    """
    Tests for TravelPlanSerializer.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='plan_creator', password='password')

    def test_validate_budget_negative(self):
        data = {
            'name': 'Bad Plan', 'user': self.user.id,
            'start_date': '2025-01-01', 'end_date': '2025-01-05',
            'description': 'Test', 'budget': -100.00, 'is_public': True
        }
        serializer = TravelPlanSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('budget', serializer.errors)
        self.assertIn("Budget must be a positive value.", str(serializer.errors['budget']))

    def test_validate_dates_inverted(self):
        data = {
            'name': 'Bad Plan 2', 'user': self.user.id,
            'start_date': '2025-01-05', 'end_date': '2025-01-01',
            'description': 'Test', 'budget': 100.00, 'is_public': True
        }
        serializer = TravelPlanSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("Start date cannot be after end date.", str(serializer.errors['non_field_errors']))

class TravelPlanDestinationSerializerTest(TestCase):

    """
    Tests for TravelPlanDestinationSerializer.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='tpd_user', password='password')
        self.destination = Destination.objects.create(name='London', country='UK')
        self.travel_plan = TravelPlan.objects.create(
            name='UK Trip', user=self.user, start_date='2025-06-01',
            end_date='2025-06-10', description='Test', budget=500.00, is_public=True
        )

        # Create a mock request object for serializer context, needed for ownership validation
        self.mock_request = type('MockRequest', (object,), {
            'user': self.user,
            'method': 'POST' # Specify method if context matters for permission checks
        })()


    def test_validate_dates_outside_travel_plan(self):
        """
        Tests if the serializer correctly rejects TPD dates outside the parent travel plan's range.
        """
        # Test arrival date before plan start
        data_before_arrival = {
            'travel_plan_id': self.travel_plan.id,
            'destination_id': self.destination.id,
            'order': 1,
            'arrival_date': '2025-05-30', # Before plan start
            'departure_date': '2025-06-05'
        }
        serializer_before_arrival = TravelPlanDestinationSerializer(data=data_before_arrival, context={'request': self.mock_request})
        self.assertFalse(serializer_before_arrival.is_valid())
        self.assertIn('arrival_date', serializer_before_arrival.errors)
        self.assertIn("Arrival date cannot be before the travel plan's start date.", str(serializer_before_arrival.errors['arrival_date']))

        # Test departure date after plan end
        data_after_departure = {
            'travel_plan_id': self.travel_plan.id,
            'destination_id': self.destination.id,
            'order': 1,
            'arrival_date': '2025-06-05',
            'departure_date': '2025-06-15' # After plan end
        }
        serializer_after_departure = TravelPlanDestinationSerializer(data=data_after_departure, context={'request': self.mock_request})
        self.assertFalse(serializer_after_departure.is_valid())
        self.assertIn('departure_date', serializer_after_departure.errors)
        self.assertIn("Departure date cannot be after the travel plan's end date.", str(serializer_after_departure.errors['departure_date']))

        # Test destination dates not fully within the plan (both arrival before and departure after)
        # This will result in both 'arrival_date' and 'departure_date' errors being present.
        data_not_fully_contained = {
            'travel_plan_id': self.travel_plan.id,
            'destination_id': self.destination.id,
            'order': 1,
            'arrival_date': '2025-05-28', # Before plan start
            'departure_date': '2025-06-12'  # After plan end
        }
        serializer_not_fully_contained = TravelPlanDestinationSerializer(data=data_not_fully_contained, context={'request': self.mock_request})
        self.assertFalse(serializer_not_fully_contained.is_valid())
        
        self.assertIn('arrival_date', serializer_not_fully_contained.errors)
        self.assertIn("Arrival date cannot be before the travel plan's start date.", str(serializer_not_fully_contained.errors['arrival_date']))
        self.assertIn('departure_date', serializer_not_fully_contained.errors)
        self.assertIn("Departure date cannot be after the travel plan's end date.", str(serializer_not_fully_contained.errors['departure_date']))


    def test_validate_arrival_after_departure(self):
        """
        Tests if the serializer correctly rejects an arrival date after departure date.
        """
        data = {
            'travel_plan_id': self.travel_plan.id,
            'destination_id': self.destination.id,
            'order': 1,
            'arrival_date': '2025-06-05',
            'departure_date': '2025-06-03' # Arrival after departure
        }
        serializer = TravelPlanDestinationSerializer(data=data, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertIn("Arrival date cannot be after departure date.", str(serializer.errors['non_field_errors']))

    def test_create_tpd_serializer_valid(self):
        """
        Tests if a valid TPD can be created via the serializer.
        """
        data = {
            'travel_plan_id': self.travel_plan.id,
            'destination_id': self.destination.id,
            'order': 1,
            'arrival_date': '2025-06-03',
            'departure_date': '2025-06-07'
        }
        serializer = TravelPlanDestinationSerializer(data=data, context={'request': self.mock_request})
        
        self.assertTrue(serializer.is_valid(raise_exception=True), serializer.errors)
        tpd = serializer.save()
        self.assertIsInstance(tpd, TravelPlanDestination)
        self.assertEqual(tpd.travel_plan, self.travel_plan)
        self.assertEqual(tpd.destination, self.destination)

class ActivitySerializerTest(TestCase):
    """
    Tests for ActivitySerializer.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='activity_user', password='password')
        self.destination = Destination.objects.create(name='Tokyo', country='Japan')
        self.travel_plan = TravelPlan.objects.create(
            name='Japan Trip', user=self.user, start_date='2025-07-01',
            end_date='2025-07-10', description='Test', budget=100.00, is_public=False
        )

        # Create a mock request object for serializer context, needed for ownership validation
        self.mock_request = type('MockRequest', (object,), {
            'user': self.user,
            'method': 'POST' # For create, method is POST
        })()

    def test_validate_cost_negative(self):
        """
        Tests if the serializer correctly rejects a negative cost.
        """
        data = {
            'name': 'Negative Cost Activity',
            'travel_plan_id': self.travel_plan.id, 
            'destination_id': self.destination.id, 
            'date': '2025-07-05T10:00:00Z',
            'cost': -5.00, # Negative cost
            'notes': 'Should fail validation'
        }
        serializer = ActivitySerializer(data=data, context={'request': self.mock_request}) # Pass context
        self.assertFalse(serializer.is_valid())
        self.assertIn('cost', serializer.errors)
        self.assertIn("Cost cannot be negative.", str(serializer.errors['cost']))

    def test_validate_activity_date_outside_plan(self):
        """
        Tests if the serializer correctly rejects an activity date outside the travel plan's range.
        """
        # Test date before plan start
        data_before = {
            'name': 'Activity Before Plan',
            'travel_plan_id': self.travel_plan.id, 
            'destination_id': self.destination.id, 
            'date': '2025-06-25T10:00:00Z', # Before 2025-07-01
            'cost': 10.00,
            'notes': ''
        }
        serializer_before = ActivitySerializer(data=data_before, context={'request': self.mock_request}) # Pass context
        self.assertFalse(serializer_before.is_valid())
        self.assertIn('date', serializer_before.errors)
        self.assertIn("Activity date must fall within the associated travel plan's start and end dates.", str(serializer_before.errors['date']))

        # Test date after plan end
        data_after = {
            'name': 'Activity After Plan',
            'travel_plan_id': self.travel_plan.id, # <-- Use _id here
            'destination_id': self.destination.id, # <-- Use _id here
            'date': '2025-07-15T10:00:00Z', # After 2025-07-10
            'cost': 10.00,
            'notes': ''
        }
        serializer_after = ActivitySerializer(data=data_after, context={'request': self.mock_request}) # Pass context
        self.assertFalse(serializer_after.is_valid())
        self.assertIn('date', serializer_after.errors)
        self.assertIn("Activity date must fall within the associated travel plan's start and end dates.", str(serializer_after.errors['date']))

    def test_create_activity_serializer_valid(self): # Renamed for clarity, was test_create_activity_serializer
        """
        Tests if a valid activity can be created via the serializer.
        """
        data = {
            'name': 'New Activity',
            'travel_plan_id': self.travel_plan.id, # <-- Use _id here
            'destination_id': self.destination.id, # <-- Use _id here
            'date': '2025-07-05T10:00:00Z',
            'cost': 50.00,
            'notes': 'Some notes'
        }
        serializer = ActivitySerializer(data=data, context={'request': self.mock_request}) # Pass context

        # Adding debug if this fails (it should pass after fixes)
        if not serializer.is_valid():
            print(f"\n--- DEBUG INFO for test_create_activity_serializer_valid ---")
            print(f"Serializer Errors: {serializer.errors}")
            print(f"--- END DEBUG INFO ---")

        self.assertTrue(serializer.is_valid(raise_exception=True), serializer.errors)
        activity = serializer.save()
        self.assertIsInstance(activity, Activity)
        self.assertEqual(activity.name, 'New Activity')
        self.assertEqual(activity.travel_plan, self.travel_plan)
        self.assertEqual(activity.destination, self.destination)

class CommentSerializerTest(TestCase):
    """
    Tests for the CommentSerializer.
    Focuses on field-level and object-level validations within the serializer.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='comment_test_user', password='password')
        self.admin_user = CustomUser.objects.create_superuser(username='comment_admin', password='password')

        self.destination = Destination.objects.create(
            name='Test Destination for Comment', country='Testland', city='TestCity', user=self.user
        )
        self.travel_plan = TravelPlan.objects.create(
            name='Test Plan for Comment', user=self.user,
            start_date='2025-08-01', end_date='2025-08-10',
            description='A plan for comments', budget=100.00, is_public=True
        )

        self.user_content_type_id = ContentType.objects.get_for_model(CustomUser).id
        self.destination_content_type_id = ContentType.objects.get_for_model(Destination).id
        self.travel_plan_content_type_id = ContentType.objects.get_for_model(TravelPlan).id

        # Create a mock request object for serializer context
        self.mock_request = type('MockRequest', (object,), {
            'user': self.user,
            'method': 'POST' # Method might be relevant for some context checks
        })()
        # Mock request for admin
        self.mock_admin_request = type('MockRequest', (object,), {
            'user': self.admin_user,
            'method': 'POST'
        })()


    #--- Test validate_text ---

    def test_validate_text_empty(self):
        data = {
            'text': '    ', # Whitespace only
            'content_type_id': self.destination_content_type_id, # Use _id suffix
            'object_id': self.destination.id # Use _id suffix
        }
        serializer = CommentSerializer(data=data, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('text', serializer.errors)
        self.assertIn("Comment text cannot be empty.", str(serializer.errors['text']))

    def test_validate_text_too_long(self):
        long_text = 'a' * 1001
        data = {
            'text': long_text,
            'content_type_id': self.destination_content_type_id,
            'object_id': self.destination.id
        }
        serializer = CommentSerializer(data=data, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('text', serializer.errors)
        self.assertIn("Comment text is too long (max 1000 characters).", str(serializer.errors['text']))

    # --- Test create method's generic foreign key and user assignment logic ---

    def test_create_comment_valid(self):
        data = {
            'text': 'This is a valid comment.',
            'content_type_id': self.destination_content_type_id,
            'object_id': self.destination.id
        }
        serializer = CommentSerializer(data=data, context={'request': self.mock_request})
        self.assertTrue(serializer.is_valid(raise_exception=True), serializer.errors)
        comment = serializer.save()

        self.assertIsInstance(comment, Comment)
        self.assertEqual(comment.text, 'This is a valid comment.')
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.content_object, self.destination)
        self.assertEqual(comment.content_type, ContentType.objects.get_for_model(self.destination))
        self.assertEqual(comment.object_id, self.destination.id)

    def test_create_comment_missing_content_type_or_object_id(self):
        """
        Tests that comment creation fails if content_type_id or object_id are missing.
        """
        # Missing content_type_id
        data_missing_type = {
            'text': 'Missing type',
            'object_id': self.destination.id # Still need to provide object_id to test content_type_id specifically
        }
        serializer = CommentSerializer(data=data_missing_type, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('content_type_id', serializer.errors) # Error on specific field
        self.assertIn("This field is required.", str(serializer.errors['content_type_id']))

        # Missing object_id
        data_missing_id = {
            'text': 'Missing ID',
            'content_type_id': self.destination_content_type_id # Still need to provide content_type_id
        }
        serializer = CommentSerializer(data=data_missing_id, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('object_id', serializer.errors) # Error on specific field
        self.assertIn("This field is required.", str(serializer.errors['object_id']))

        # Both missing - will show both errors
        data_both_missing = {
            'text': 'Both Missing'
        }
        serializer = CommentSerializer(data=data_both_missing, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('content_type_id', serializer.errors)
        self.assertIn('object_id', serializer.errors)

    def test_create_comment_invalid_content_type_id(self):
        """
        Tests that comment creation fails with a non-existent content_type ID
        when serializer.save() is called.
        """
        data = {
            'text': 'Invalid content type',
            'content_type_id': 99999, # Non-existent ID
            'object_id': self.destination.id
        }
        serializer = CommentSerializer(data=data, context={'request': self.mock_request})
        
        # is_valid() will return True here because the raw data is valid,
        # but the error occurs during the object creation in .save()
        self.assertTrue(serializer.is_valid(), serializer.errors) # Assert data is structurally valid
        
        # Now, assert that calling save() raises the expected validation error
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        # Check the specific error message on the correct field
        self.assertIn('content_type_id', cm.exception.detail)
        self.assertIn("Content type not found.", str(cm.exception.detail['content_type_id']))

    def test_create_comment_non_existent_object_id(self):
        """
        Tests that comment creation fails with a valid content_type but non-existent object_id
        when serializer.save() is called.
        """
        data = {
            'text': 'Non-existent object',
            'content_type_id': self.destination_content_type_id,
            'object_id': 999999 # Non-existent ID
        }
        serializer = CommentSerializer(data=data, context={'request': self.mock_request})
        
        # is_valid() will return True here
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Now, assert that calling save() raises the expected validation error
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        # Check the specific error message on the correct field
        self.assertIn('object_id', cm.exception.detail)
        self.assertIn(f"The 'destination' object with ID '999999' was not found.", str(cm.exception.detail['object_id']))


    def test_create_comment_disallowed_content_type(self):
        """
        Tests that comment creation fails if the content type is not in allowed_models
        when serializer.save() is called.
        """
        data = {
            'text': 'Disallowed type',
            'content_type_id': self.user_content_type_id, # Trying to comment on a User object (not allowed)
            'object_id': self.user.id
        }
        serializer = CommentSerializer(data=data, context={'request': self.mock_request})
        
        # is_valid() will return True here
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Now, assert that calling save() raises the expected validation error
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        # Check the specific error message on the correct field
        self.assertIn('content_type_id', cm.exception.detail)
        self.assertIn("Comments are not allowed on 'customuser' objects. Allowed types are: destination, travelplan.", str(cm.exception.detail['content_type_id']))


    def test_create_comment_unauthenticated_user_in_serializer(self):
        """
        Tests that the serializer explicitly rejects unauthenticated users attempting to create
        when serializer.save() is called.
        """
        mock_unauth_request = type('MockRequest', (object,), {'user': AnonymousUser()})()
        data = {
            'text': 'Anon comment',
            'content_type_id': self.destination_content_type_id,
            'object_id': self.destination.id
        }
        serializer = CommentSerializer(data=data, context={'request': mock_unauth_request})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        # Now, assert that calling save() raises the expected validation error
        with self.assertRaises(serializers.ValidationError) as cm:
            serializer.save()
        
        # Check the specific error message on the correct field
        self.assertIn('user', cm.exception.detail)
        self.assertIn("Authentication is required to create a comment.", str(cm.exception.detail['user']))


    # --- Test update method restrictions ---

    def test_update_comment_content_type_forbidden(self):
        comment = Comment.objects.create(user=self.user, text='Original', content_object=self.destination)
        data = {'content_type_id': self.travel_plan_content_type_id} # Use _id suffix
        serializer = CommentSerializer(instance=comment, data=data, partial=True, context={'request': self.mock_request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('content_type_id', serializer.errors) # Error on specific field
        self.assertIn("Content type cannot be changed for an existing comment.", str(serializer.errors['content_type_id']))

    def test_update_comment_object_id_forbidden(self):
        """
        Tests that updating object_id for an existing comment is forbidden.
        Ensures the new object_id is genuinely different from the original.
        """
        comment = Comment.objects.create(user=self.user, text='Original', content_object=self.destination)
        
        another_destination = Destination.objects.create(
            name='Another Destination', country='Farland', city='FarCity', user=self.user
        )
        data = {'object_id': another_destination.id}
        
        serializer = CommentSerializer(instance=comment, data=data, partial=True, context={'request': self.mock_request})
        
        is_valid = serializer.is_valid() # Store the result of is_valid()

        self.assertFalse(is_valid) # Assert on the stored result
        self.assertIn('object_id', serializer.errors)
        self.assertIn("Object ID cannot be changed for an existing comment.", str(serializer.errors['object_id']))

    def test_update_comment_valid(self):
        comment = Comment.objects.create(user=self.user, text='Original text', content_object=self.destination)
        data = {'text': 'Updated text by owner.'}
        serializer = CommentSerializer(instance=comment, data=data, partial=True, context={'request': self.mock_request})
        self.assertTrue(serializer.is_valid(raise_exception=True), serializer.errors)
        updated_comment = serializer.save()
        self.assertEqual(updated_comment.text, 'Updated text by owner.')
        self.assertEqual(updated_comment.content_object, self.destination)
        self.assertEqual(updated_comment.user, self.user)

    def test_update_comment_as_admin_valid(self):
        comment = Comment.objects.create(user=self.user, text='Original text for admin', content_object=self.destination)
        data = {'text': 'Updated by admin.'}
        serializer = CommentSerializer(instance=comment, data=data, partial=True, context={'request': self.mock_admin_request})
        self.assertTrue(serializer.is_valid(raise_exception=True), serializer.errors)
        updated_comment = serializer.save()
        self.assertEqual(updated_comment.text, 'Updated by admin.')
        self.assertEqual(updated_comment.user, self.user)
