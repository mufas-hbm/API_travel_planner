import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from travel_planner.models import Destination, TravelPlan, TravelPlanDestination, Activity, Comment


# Get the CustomUser model defined in settings.AUTH_USER_MODEL
CustomUser = get_user_model()

# --- Model Tests ---
# Test basic model creation, __str__ methods, and model-level constraints

class CustomUserModelTest(TestCase):
    """
    Tests for the CustomUser model.
    """
    def test_create_user(self):
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpassword'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin_user = CustomUser.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpassword'
        )
        self.assertEqual(admin_user.username, 'admin')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_custom_fields(self):
        user = CustomUser.objects.create_user(
            username='john_doe',
            email='john@example.com',
            password='password',
            date_birth=datetime.date(1990, 5, 10),
            city='New York',
            zip_code='10001',
            preferred_travel_style='ADVENTURE'
        )
        self.assertEqual(user.date_birth, datetime.date(1990, 5, 10))
        self.assertEqual(user.city, 'New York')
        self.assertEqual(user.zip_code, '10001')
        self.assertEqual(user.preferred_travel_style, 'ADVENTURE')
        self.assertEqual(str(user), 'john_doe') 

class DestinationModelTest(TestCase):
    """
    Tests for the Destination model.
    """
    def test_destination_creation(self):
        destination = Destination.objects.create(
            name='Paris',
            country='France',
            city='Paris',
            latitude=48.8566,
            longitude=2.3522,
            is_popular=True
        )
        self.assertEqual(destination.name, 'Paris')
        self.assertEqual(destination.country, 'France')
        self.assertEqual(str(destination), 'Paris, France') # Test __str__

    def test_unique_together_constraint(self):
        # Create the first destination
        Destination.objects.create(
            name='Springfield', country='USA', city='Springfield', latitude=0, longitude=0
        )
        # Attempt to create another with the exact same name, city, country
        with self.assertRaises(Exception): # Will raise IntegrityError
            Destination.objects.create(
                name='Springfield', country='USA', city='Springfield', latitude=1, longitude=1
            )

class TravelPlanModelTest(TestCase):
    """
    Tests for the TravelPlan model.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='planner', password='password')
        self.destination = Destination.objects.create(name='Rome', country='Italy', city='Rome')

    def test_travel_plan_creation(self):
        plan = TravelPlan.objects.create(
            name='Italian Holiday',
            user=self.user,
            start_date='2025-09-01',
            end_date='2025-09-10',
            description='A trip to Italy',
            budget=1500.00,
            is_public=True
        )
        self.assertEqual(plan.name, 'Italian Holiday')
        self.assertEqual(plan.user, self.user)
        self.assertEqual(str(plan), 'Italian Holiday, from 2025-09-01 until 2025-09-10') # Test __str__

    def test_m2m_through_relationship(self):
        plan = TravelPlan.objects.create(
            name='Italian Holiday',
            user=self.user,
            start_date='2025-09-01',
            end_date='2025-09-10',
            description='A trip to Italy',
            budget=1500.00,
            is_public=True
        )
        TravelPlanDestination.objects.create(
            travel_plan=plan,
            destination=self.destination,
            order=1,
            arrival_date='2025-09-01',
            departure_date='2025-09-05'
        )
        self.assertEqual(plan.destinations.count(), 1)
        self.assertEqual(plan.destinations.first().name, 'Rome')

class ActivityModelTest(TestCase):
    """
    Tests for the Activity model.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='activity_user', password='password')
        self.destination = Destination.objects.create(name='Berlin', country='Germany')
        self.travel_plan = TravelPlan.objects.create(
            name='German Trip', user=self.user, start_date='2025-08-01',
            end_date='2025-08-05', description='Test', budget=100.00,
            is_public = True
        )

    def test_activity_creation(self):
        activity = Activity.objects.create(
            name='Museum Visit',
            travel_plan=self.travel_plan,
            destination=self.destination,
            date='2025-08-02 10:00:00Z',
            cost=25.00
        )
        self.assertEqual(activity.name, 'Museum Visit')
        self.assertEqual(activity.travel_plan, self.travel_plan)
        self.assertEqual(str(activity), 'Museum Visit, cost: 25.00') # Test __str__

class CommentModelTest(TestCase):
    """
    Tests for the Comment model and GenericForeignKey.
    """
    def setUp(self):
        self.user = CustomUser.objects.create_user(username='comment_user', password='password')
        self.destination = Destination.objects.create(name='Kyoto', country='Japan')
        self.travel_plan = TravelPlan.objects.create(
            name='Japan Trip', user=self.user, start_date='2025-10-01',
            end_date='2025-10-10', description='Test', budget=1000.00,
            is_public=False
        )

    def test_comment_on_destination(self):
        comment = Comment.objects.create(
            user=self.user,
            text='Lovely place!',
            content_object=self.destination
        )
        self.assertEqual(comment.content_object, self.destination)
        self.assertEqual(comment.content_type, ContentType.objects.get_for_model(self.destination))
        self.assertEqual(comment.object_id, self.destination.id)
        self.assertIn('Kyoto, Japan', str(comment)) # Test __str__ includes destination info

    def test_comment_on_travel_plan(self):
        comment = Comment.objects.create(
            user=self.user,
            text='Great plan!',
            content_object=self.travel_plan
         )
        self.assertEqual(comment.content_object, self.travel_plan)
        self.assertEqual(comment.content_type, ContentType.objects.get_for_model(self.travel_plan))
        self.assertEqual(comment.object_id, self.travel_plan.id)
        self.assertIn('Japan Trip', str(comment)) # Test __str__ includes travel plan info
