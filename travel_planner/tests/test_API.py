import datetime
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from travel_planner.models import Destination, TravelPlan, TravelPlanDestination, Activity, Comment

# Get the CustomUser model defined in settings.AUTH_USER_MODEL
CustomUser = get_user_model()

class APIBaseTest(APITestCase):
    """
    Base class for API tests.
    Sets up common test users (admin, regular, other_user) and their authentication tokens.
    It also sets a default client credential for easier testing.
    """
    def setUp(self):
        # Create different types of users for testing permissions
        self.admin_user = CustomUser.objects.create_superuser(username='admin', email='admin@test.com', password='adminpassword')
        self.regular_user = CustomUser.objects.create_user(username='user', email='user@test.com', password='userpassword')
        self.other_user = CustomUser.objects.create_user(username='otheruser', email='other@test.com', password='otherpassword')

        # Get or create authentication tokens for each user.
        # These tokens will be used to authenticate requests in tests.
        self.admin_token = Token.objects.create(user=self.admin_user)
        self.user_token = Token.objects.create(user=self.regular_user)
        self.other_user_token = Token.objects.create(user=self.other_user)

        # Set the default client credentials to the regular_user's token.
        # This means most tests will run as the regular user by default unless overridden.
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user_token.key)

class CustomUserAPIViewTest(APIBaseTest):
    """
    Tests for CustomUserListCreateView (user listing/registration)
    and CustomUserDetailView (single user profile access/update/delete).
    --- User URLs ---
    """
    def test_list_users_as_admin(self):
        """
        Tests if an admin user can successfully retrieve a list of all users.
        Expected: HTTP 200 OK, returns all user objects.
        """
        # Change client credentials to admin for this test
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get(reverse('user-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # We expect 3 users: admin, regular_user, other_user (created in APIBaseTest setUp)
        self.assertEqual(len(response.data), 3)

    def test_list_users_as_regular_user_fails(self):
        """
        Tests if a regular (non-admin) user is denied access to list all users.
        Expected: HTTP 403 Forbidden.
        """
        # Client is already set to regular_user by default in APIBaseTest
        response = self.client.get(reverse('user-list-create'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_users_unauthenticated_fails(self):
        """
        Tests if an unauthenticated user is denied access to list all users.
        Expected: HTTP 401 Unauthorized.
        """
        # Clear any existing client credentials to simulate an unauthenticated request
        self.client.credentials()
        response = self.client.get(reverse('user-list-create'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_user_public(self):
            """
            Tests if an unauthenticated user can register a new user (POST to user-list-create).
            Expected: HTTP 201 Created.
            """
            self.client.credentials() # No authentication needed for user creation (registration)
            data = {
                'username': 'newreguser',
                'email': 'newreg@test.com',
                'password': 'pass12345678', #ensure that password have at least 8 digits
                'first_name': 'New',
                'last_name': 'Register',
                'date_birth': '1990-01-01',
                'city': 'TestCity',
                'zip_code': '12345',
                'preferred_travel_style': 'ADVENTURE'
            }
            response = self.client.post(reverse('user-list-create'), data, format='json')

            # --- DEBUG ---
            if response.status_code != status.HTTP_201_CREATED:
                print("\n--- DEBUG INFO for test_create_user_public ---")
                print(f"Status Code: {response.status_code}")
                print(f"Response Data (Errors): {response.data}")
                print("--- END DEBUG INFO ---")
            # --- END DEBUG LINES ---

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(CustomUser.objects.count(), 4)

    def test_retrieve_own_user_profile(self):
        """
        Tests if an authenticated user can retrieve their own profile using '/users/me/'.
        Expected: HTTP 200 OK, returns the user's own data.
        """
        # Client is already set to regular_user by default
        response = self.client.get(reverse('user-detail-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.regular_user.username)

    def test_retrieve_other_user_profile_fails(self):
        """
        Tests if a regular user is denied access to retrieve another user's profile
        (since they are not the owner and not an admin).
        Expected: HTTP 403 Forbidden.
        """
        # Client is already set to regular_user by default
        response = self.client.get(reverse('user-detail', args=[self.other_user.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_any_user_profile_as_admin(self):
        """
        Tests if an admin user can retrieve any user's profile.
        Expected: HTTP 200 OK.
        """
        # Change client credentials to admin for this test
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get(reverse('user-detail', args=[self.regular_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.regular_user.username)

    def test_update_own_user_profile(self):
        """
        Tests if an authenticated user can update their own profile.
        Expected: HTTP 200 OK, profile data updated.
        """
        # Client is already set to regular_user by default
        data = {'city': 'New City', 'preferred_travel_style': 'LUXURY'}
        response = self.client.patch(reverse('user-detail-me'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db() # Refresh the instance from the database to get latest changes
        self.assertEqual(self.regular_user.city, 'New City')
        self.assertEqual(self.regular_user.preferred_travel_style, 'LUXURY')

    def test_update_other_user_profile_fails(self):
        """
        Tests if a regular user is denied permission to update another user's profile.
        Expected: HTTP 403 Forbidden.
        """
        # Client is already set to regular_user by default
        data = {'city': 'Should Not Change'}
        response = self.client.patch(reverse('user-detail', args=[self.other_user.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own_user_profile(self):
        """
        Tests if an authenticated user can delete their own profile.
        Expected: HTTP 204 No Content.
        """
        # Client is already set to regular_user by default
        response = self.client.delete(reverse('user-detail-me'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify the user is actually deleted from the database
        self.assertEqual(CustomUser.objects.count(), 2) # admin, otheruser remain

class AuthViewsTest(APIBaseTest):
    """
    Tests for UserLoginView (POST /api/login/) and UserLogoutView (POST /api/logout/).
    These views handle user authentication and token management.
    """
    def test_user_login_success(self):
        """
        Tests successful user login with valid credentials.
        Expected: HTTP 200 OK, returns an authentication token and user info.
        """
        # Clear any existing credentials to ensure we're testing a fresh login
        self.client.credentials()
        
        # Make a POST request to the login endpoint with the regular_user's credentials
        response = self.client.post(
            reverse('user-login'), # 'user-login' is the name given in urls.py
            {'username': self.regular_user.username, 'password': 'userpassword'}, # cannot use self.regular_user.password because is hashed
            format='json' # Ensure data is sent as JSON
        )
        
        # Assert the response status code is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assert that the response data contains a 'token' key
        self.assertIn('token', response.data)
        # Assert that the user_id in the response matches the regular user's ID
        self.assertEqual(response.data['user_id'], self.regular_user.id)

    def test_user_login_invalid_credentials(self):
        """
        Tests user login with incorrect password.
        Expected: HTTP 400 Bad Request, with non-field errors.
        """
        self.client.credentials() # Clear any existing credentials
        
        # Attempt to log in with correct username but wrong password
        response = self.client.post(
            reverse('user-login'),
            {'username': self.regular_user.username, 'password': 'wrongpassword'},
            format='json'
        )
        
        # Assert the response status code is 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Assert that the response contains non-field errors (e.g., "Unable to log in with provided credentials.")
        self.assertIn('non_field_errors', response.data)

    def test_user_logout_success(self):
        """
        Tests successful user logout (token deletion).
        Expected: HTTP 204 No Content, and the token should no longer exist in the database.
        """
        # First, ensure the user is logged in and has a token for this test.
        # We perform a login operation directly within the test setup.
        login_response = self.client.post(
            reverse('user-login'),
            {'username': self.regular_user.username, 'password': 'userpassword'},
            format='json'
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        # Extract the token key from the login response
        token_key = login_response.data['token']
        
        # Set the client's credentials with the obtained token for the logout request
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token_key)

        # Make a POST request to the logout endpoint
        response = self.client.post(reverse('user-logout'))
        
        # Assert the response status code is 204 No Content (successful deletion)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Assert that the token no longer exists in the database
        self.assertFalse(Token.objects.filter(key=token_key).exists())

    def test_user_logout_unauthenticated_fails(self):
        """
        Tests if an unauthenticated user is denied access to logout (as they have no token to delete).
        Expected: HTTP 401 Unauthorized.
        """
        # Clear any client credentials to simulate an unauthenticated request
        self.client.credentials()
        
        # Attempt to logout without providing authentication
        response = self.client.post(reverse('user-logout'))
        
        # Assert the response status code is 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class DestinationAPIViewTest(APIBaseTest):
    """
    Tests for DestinationListCreateView and DestinationDetailView.
    Permissions:
    - List/Retrieve: Any user (authenticated or unauthenticated)
    - Create: Any Authenticated user (owner automatically assigned)
    - Update/Delete: Owner OR Admin only
    """
    def setUp(self):
        super().setUp()
        # Create destinations, explicitly assigning owners
        self.user_destination = Destination.objects.create(
            name='User Created Place',
            country='Germany',
            city='Berlin',
            latitude=52.52,
            longitude=13.40,
            is_popular=False,
            user=self.regular_user # This destination is owned by regular_user
        )
        self.other_user_destination = Destination.objects.create(
            name='Other User Place',
            country='Spain',
            city='Madrid',
            latitude=40.41,
            longitude=-3.70,
            is_popular=True,
            user=self.other_user # This destination is owned by other_user
        )
        # Set default client credentials to a regular user for most tests
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.user_token.key)

    def test_list_destinations_unauthenticated(self):
        """
        Tests if an unauthenticated user can list destinations (all should be visible).
        Expected: HTTP 200 OK.
        """
        self.client.credentials() # Clear credentials
        response = self.client.get(reverse('destination-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2) # Both user_destination and other_user_destination
        names = [d['name'] for d in response.data]
        self.assertIn('User Created Place', names)
        self.assertIn('Other User Place', names)

    def test_list_destinations_authenticated(self):
        """
        Tests if an authenticated (regular) user can list destinations.
        Expected: HTTP 200 OK.
        """
        # Client is already authenticated as regular_user in setUp
        response = self.client.get(reverse('destination-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_destination_as_authenticated_user(self):
        """
        Tests if an authenticated user can create a new destination, and they become the owner.
        Expected: HTTP 201 Created.
        """
        # Client is authenticated as regular_user by default
        data = {
            'name': 'New User Place',
            'country': 'USA',
            'city': 'New York',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'is_popular': False,
        }

        response = self.client.post(reverse('destination-list-create'), data, format='json')        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Destination.objects.count(), 3) # Original 2 + new one
        new_destination = Destination.objects.get(name='New User Place')
        self.assertEqual(new_destination.user, self.regular_user) # Verify user is set

    def test_create_destination_unauthenticated_fails(self):
        """
        Tests if an unauthenticated user is denied access to create a destination.
        Expected: HTTP 401 Unauthorized.
        """
        self.client.credentials() # Clear credentials
        data = {
            'name': 'Anon Place', 'country': 'Canada', 'city': 'Toronto',
            'latitude': 43.6532, 'longitude': -79.3832, 'is_popular': False
        }
        response = self.client.post(reverse('destination-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_retrieve_destination_detail_unauthenticated(self):
        """
        Tests if an unauthenticated user can retrieve a single destination's details (any).
        Expected: HTTP 200 OK.
        """
        self.client.credentials() # Clear auth
        response = self.client.get(reverse('destination-detail', args=[self.user_destination.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'User Created Place')

    def test_retrieve_destination_detail_authenticated(self):
        """
        Tests if an authenticated (regular) user can retrieve any single destination's details.
        Expected: HTTP 200 OK.
        """
        # Client is authenticated as regular_user by default
        response = self.client.get(reverse('destination-detail', args=[self.other_user_destination.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Other User Place')


    def test_update_own_destination(self):
        """
        Tests if the owner of a destination can update it.
        Expected: HTTP 200 OK.
        """
        # Client is regular_user, who owns user_destination
        data = {'description': 'An updated description for my place.'}
        response = self.client.patch(reverse('destination-detail', args=[self.user_destination.id]), data, format='json')        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_destination.refresh_from_db()
        self.assertEqual(self.user_destination.description, 'An updated description for my place.')

    def test_update_other_user_destination_fails(self):
        """
        Tests if a non-owner (regular user) is denied access to update another user's destination.
        Expected: HTTP 403 Forbidden.
        """
        # Client is regular_user, trying to update other_user_destination
        data = {'description': 'Should not change.'}
        response = self.client.patch(reverse('destination-detail', args=[self.other_user_destination.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_destination_as_admin(self):
        """
        Tests if an admin user can update any destination (including one they don't own).
        Expected: HTTP 200 OK.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key) # Authenticate as admin
        data = {'name': 'Other User Place Updated by Admin'}
        response = self.client.patch(reverse('destination-detail', args=[self.other_user_destination.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.other_user_destination.refresh_from_db()
        self.assertEqual(self.other_user_destination.name, 'Other User Place Updated by Admin')


    def test_delete_own_destination(self):
        """
        Tests if the owner of a destination can delete it.
        Expected: HTTP 204 No Content.
        """
        # Client is regular_user, who owns user_destination
        response = self.client.delete(reverse('destination-detail', args=[self.user_destination.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Destination.objects.filter(id=self.user_destination.id).exists())

    def test_delete_other_user_destination_fails(self):
        """
        Tests if a non-owner (regular user) is denied access to delete another user's destination.
        Expected: HTTP 403 Forbidden.
        """
        # Client is regular_user, trying to delete other_user_destination
        response = self.client.delete(reverse('destination-detail', args=[self.other_user_destination.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_destination_as_admin(self):
        """
        Tests if an admin user can delete any destination (including one they don't own).
        Expected: HTTP 204 No Content.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key) # Authenticate as admin
        response = self.client.delete(reverse('destination-detail', args=[self.other_user_destination.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Destination.objects.filter(id=self.other_user_destination.id).exists())

class TravelPlanAPIViewTest(APIBaseTest):
    """
    Tests for TravelPlanListCreateView (list/create travel plans)
    and TravelPlanDetailView (retrieve/update/delete single travel plan).
    """
    def setUp(self):
        # Call parent's setUp to get admin_user, regular_user, other_user, and their tokens
        super().setUp()
        
        # Create some sample Travel Plans for testing
        # A private plan owned by the regular_user (default client)
        self.private_plan_user = TravelPlan.objects.create(
            name='My Private European Trip',
            user=self.regular_user,
            start_date='2025-01-01',
            end_date='2025-01-05',
            description='A personal, secret journey.',
            budget=1000.00,
            is_public=False
        )
        # A public plan owned by the regular_user
        self.public_plan_user = TravelPlan.objects.create(
            name='My Public US Roadtrip',
            user=self.regular_user,
            start_date='2025-03-01',
            end_date='2025-03-10',
            description='Open for anyone to see.',
            budget=1500.00,
            is_public=True
        )
        # A public plan owned by another user (other_user)
        self.public_plan_other = TravelPlan.objects.create(
            name='Other User\'s Public Asian Adventure',
            user=self.other_user,
            start_date='2025-02-01',
            end_date='2025-02-15',
            description='A public trip by another user.',
            budget=2000.00,
            is_public=True
        )
        # A private plan owned by another user (other_user)
        self.private_plan_other = TravelPlan.objects.create(
            name='Other User\'s Private Getaway',
            user=self.other_user,
            start_date='2025-04-01',
            end_date='2025-04-05',
            description='This should be hidden.',
            budget=500.00,
            is_public=False
        )

        # Default client is set to regular_user's token in APIBaseTest

    # --- Tests for TravelPlanListCreateView ---

    def test_list_travel_plans_authenticated_user(self):
        """
        Tests if an authenticated user can list travel plans.
        Expected: HTTP 200 OK. Should see their own plans (private+public)
        and public plans by other users. Should NOT see other users' private plans.
        """
        # Client is regular_user by default (authenticated)
        response = self.client.get(reverse('travelplan-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Expect to see: private_plan_user, public_plan_user, public_plan_other (3 plans)
        self.assertEqual(len(response.data), 3)
        plan_names = {p['name'] for p in response.data}
        self.assertIn('My Private European Trip', plan_names)
        self.assertIn('My Public US Roadtrip', plan_names)
        self.assertIn('Other User\'s Public Asian Adventure', plan_names)
        self.assertNotIn('Other User\'s Private Getaway', plan_names)

    def test_list_travel_plans_unauthenticated_user(self):
        """
        Tests if an unauthenticated user can list travel plans.
        Expected: HTTP 200 OK. Should ONLY see public plans (by any user).
        """
        self.client.credentials() # Clear credentials to simulate unauthenticated request
        response = self.client.get(reverse('travelplan-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Expect to see: public_plan_user, public_plan_other (2 plans)
        self.assertEqual(len(response.data), 2)
        plan_names = {p['name'] for p in response.data}
        self.assertIn('My Public US Roadtrip', plan_names)
        self.assertIn('Other User\'s Public Asian Adventure', plan_names)
        self.assertNotIn('My Private European Trip', plan_names) # Should not see private plans
        self.assertNotIn('Other User\'s Private Getaway', plan_names) # Should not see private plans

    def test_create_travel_plan_authenticated(self):
        """
        Tests if an authenticated user can create a new travel plan.
        Expected: HTTP 201 Created, owner automatically assigned.
        """
        # Client is regular_user by default (authenticated)
        data = {
            'name': 'My New Authenticated Plan',
            'start_date': '2025-05-01',
            'end_date': '2025-05-10',
            'description': 'A plan created by an authenticated user.',
            'budget': 750.00,
            'is_public': True
        }
        response = self.client.post(reverse('travelplan-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TravelPlan.objects.count(), 5) # 4 from setUp + 1 new
        
        # Verify the owner was automatically set to the requesting user
        new_plan = TravelPlan.objects.get(name='My New Authenticated Plan')
        self.assertEqual(new_plan.user, self.regular_user)

    def test_create_travel_plan_unauthenticated_fails(self):

        """
        Tests if an unauthenticated user is denied access to create a travel plan.
        Expected: HTTP 401 Unauthorized.
        """
        self.client.credentials() # Clear credentials
        data = {
            'name': 'Anon Plan',
            'start_date': '2025-06-01',
            'end_date': '2025-06-05',
            'description': 'Should not be created.',
            'budget': 100.00,
            'is_public': False
        }
        response = self.client.post(reverse('travelplan-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_own_private_travel_plan(self):
        """
        Tests if an authenticated user can retrieve their own private travel plan.
        Expected: HTTP 200 OK.
        """
        # Client is regular_user (owner of private_plan_user)
        response = self.client.get(reverse('travelplan-detail', args=[self.private_plan_user.id]))
        
        # --- DEBUG INFO ---
        if response.status_code != status.HTTP_200_OK:
            print("\n--- DEBUG INFO for test_retrieve_own_private_travel_plan ---")
            print(f"Status Code: {response.status_code}")
            print(f"Response Data (Errors): {response.data}")
            print("--- END DEBUG INFO ---")
        # --- END DEBUG INFO ---
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.private_plan_user.name)

    def test_retrieve_other_user_public_travel_plan(self):
        """
        Tests if an authenticated user can retrieve another user's public travel plan.
        Expected: HTTP 200 OK.
        """
        # Client is regular_user (not owner of public_plan_other, but it's public)
        response = self.client.get(reverse('travelplan-detail', args=[self.public_plan_other.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.public_plan_other.name)

    def test_retrieve_other_user_private_travel_plan_authenticated_fails(self):
        """
        Tests if an authenticated user is denied access to another user's private travel plan.
        Expected: HTTP 403 Forbidden.
        """
        # Client is regular_user (not owner of private_plan_other, and it's private)
        response = self.client.get(reverse('travelplan-detail', args=[self.private_plan_other.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_other_user_private_travel_plan_unauthenticated_fails(self):
        """
        Tests if an unauthenticated user is denied access to another user's private travel plan.
        Expected: HTTP 401 Unauthorized (due to `IsOwnerOrAdminOrReadOnly` for safe methods, which requires authentication to check object perms).
        """
        self.client.credentials() # Clear credentials
        response = self.client.get(reverse('travelplan-detail', args=[self.private_plan_other.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_own_travel_plan(self):
        """
        Tests if the owner of a travel plan can update it.
        Expected: HTTP 200 OK.
        """
        # Client is regular_user (owner of private_plan_user)
        data = {'name': 'My Updated Private European Trip', 'budget': 1200.00}
        response = self.client.patch(reverse('travelplan-detail', args=[self.private_plan_user.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.private_plan_user.refresh_from_db()
        self.assertEqual(self.private_plan_user.name, 'My Updated Private European Trip')
        self.assertEqual(self.private_plan_user.budget, 1200.00)

    def test_update_other_user_travel_plan_fails(self):
        """
        Tests if an authenticated non-owner user is denied access to update another user's travel plan.
        Expected: HTTP 403 Forbidden.
        """
        # Client is regular_user (not owner of public_plan_other)
        data = {'name': 'Attempted Update by Non-Owner'}
        response = self.client.patch(reverse('travelplan-detail', args=[self.public_plan_other.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_travel_plan_as_admin(self):
        """
        Tests if an admin user can update any travel plan (including one they don't own).
        Expected: HTTP 200 OK.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key) # Authenticate as admin
        data = {'name': 'Admin Updated Public Trip'}
        response = self.client.patch(reverse('travelplan-detail', args=[self.public_plan_other.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.public_plan_other.refresh_from_db()
        self.assertEqual(self.public_plan_other.name, 'Admin Updated Public Trip')

    def test_delete_own_travel_plan(self):
        """
        Tests if the owner of a travel plan can delete it.
        Expected: HTTP 204 No Content.
        """
        # Client is regular_user (owner of private_plan_user)
        response = self.client.delete(reverse('travelplan-detail', args=[self.private_plan_user.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TravelPlan.objects.filter(id=self.private_plan_user.id).exists())

    def test_delete_other_user_travel_plan_fails(self):
        """
        Tests if an authenticated non-owner user is denied access to delete another user's travel plan.
        Expected: HTTP 403 Forbidden.
        """
        # Client is regular_user (not owner of public_plan_other)
        response = self.client.delete(reverse('travelplan-detail', args=[self.public_plan_other.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_travel_plan_as_admin(self):
        """
        Tests if an admin user can delete any travel plan.
        Expected: HTTP 204 No Content.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key) # Authenticate as admin
        response = self.client.delete(reverse('travelplan-detail', args=[self.private_plan_user.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TravelPlan.objects.filter(id=self.private_plan_user.id).exists())

class TravelPlanDestinationAPIViewTest(APIBaseTest):
    """
    Tests for TravelPlanDestinationListCreateView and TravelPlanDestinationDetailView.
    Permissions: Owner of parent TravelPlan OR Admin for write/list/retrieve. Read for all.
    """
    def setUp(self):
        super().setUp()
        
        self.user_plan = TravelPlan.objects.create(
            name='My User Plan', user=self.regular_user,
            start_date='2025-05-01', end_date='2025-05-10', budget=100.00, is_public=False
        )
        self.other_user_plan = TravelPlan.objects.create(
            name='Other User Plan', user=self.other_user,
            start_date='2025-06-01', end_date='2025-06-10', budget=100.00, is_public=False
        )

        # Create some destinations, ensuring they have a 'user' (owner) as per latest model
        self.destination_paris = Destination.objects.create(name='Paris', country='France', city='Paris', user=self.regular_user)
        self.destination_rome = Destination.objects.create(name='Rome', country='Italy', city='Rome', user=self.other_user)

        self.tpd_entry_user_plan = TravelPlanDestination.objects.create(
            travel_plan=self.user_plan,
            destination=self.destination_paris,
            order=1,
            arrival_date='2025-05-02',
            departure_date='2025-05-05'
        )
        self.tpd_entry_other_plan = TravelPlanDestination.objects.create(
            travel_plan=self.other_user_plan,
            destination=self.destination_rome,
            order=1,
            arrival_date='2025-06-02',
            departure_date='2025-06-05'
        )

        # Default client is regular_user's token

    # --- Tests for TravelPlanDestinationListCreateView ---

    def test_list_tpd_own_plan_authenticated_user(self):
        response = self.client.get(reverse('travelplandestination-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['destination_detail']['name'], 'Paris') 

    def test_list_tpd_other_plan_authenticated_user_empty(self):
        response = self.client.get(reverse('travelplandestination-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        # Verify the content of the single TPD:
        self.assertEqual(response.data[0]['destination_detail']['name'], 'Paris')
        self.assertEqual(response.data[0]['travel_plan_display'], str(self.user_plan)) # Check string representation

    def test_list_tpd_unauthenticated_user_empty(self):
        self.client.credentials()
        response = self.client.get(reverse('travelplandestination-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_tpd_other_plan_authenticated_user_fails(self):
        new_destination_nice = Destination.objects.create(name='Nice', country='France', city='Nice', user=self.regular_user)
        data = {
            'travel_plan_id': self.other_user_plan.id,
            'destination_id': new_destination_nice.id,
            'order': 1,
            'arrival_date': '2025-06-06',
            'departure_date': '2025-06-08'
        }
        response = self.client.post(reverse('travelplandestination-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_tpd_unauthenticated_user_fails(self):
        self.client.credentials()
        new_destination_berlin = Destination.objects.create(name='Berlin', country='Germany', city='Berlin', user=self.regular_user)
        data = {
            'travel_plan_id': self.user_plan.id,
            'destination_id': new_destination_berlin.id,
            'order': 1,
            'arrival_date': '2025-05-01',
            'departure_date': '2025-05-02'
        }
        response = self.client.post(reverse('travelplandestination-list-create'), data, format='json')         
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    # # --- Tests for TravelPlanDestinationDetailView ---

    def test_retrieve_tpd_own_plan_authenticated_user(self):
    
        response = self.client.get(reverse('travelplandestination-detail', args=[self.tpd_entry_user_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['destination_detail']['name'], 'Paris')
        self.assertEqual(response.data['travel_plan_display'], str(self.user_plan))

    def test_retrieve_tpd_other_plan_authenticated_user_fails(self):
        response = self.client.get(reverse('travelplandestination-detail', args=[self.tpd_entry_other_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_tpd_unauthenticated_user_fails(self):
        self.client.credentials()
        response = self.client.get(reverse('travelplandestination-detail', args=[self.tpd_entry_user_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_update_tpd_own_plan_authenticated_user(self):
        data = {'order': 5}
        response = self.client.patch(reverse('travelplandestination-detail', args=[self.tpd_entry_user_plan.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tpd_entry_user_plan.refresh_from_db()
        self.assertEqual(self.tpd_entry_user_plan.order, 5)

    def test_update_tpd_other_plan_authenticated_user_fails(self):
        data = {'order': 99}
        response = self.client.patch(reverse('travelplandestination-detail', args=[self.tpd_entry_other_plan.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_tpd_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        data = {'order': 100}
        response = self.client.patch(reverse('travelplandestination-detail', args=[self.tpd_entry_other_plan.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tpd_entry_other_plan.refresh_from_db()
        self.assertEqual(self.tpd_entry_other_plan.order, 100)

    def test_delete_tpd_own_plan_authenticated_user(self):
        response = self.client.delete(reverse('travelplandestination-detail', args=[self.tpd_entry_user_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TravelPlanDestination.objects.filter(id=self.tpd_entry_user_plan.id).exists())

    def test_delete_tpd_other_plan_authenticated_user_fails(self):
        response = self.client.delete(reverse('travelplandestination-detail', args=[self.tpd_entry_other_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_tpd_as_admin(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.delete(reverse('travelplandestination-detail', args=[self.tpd_entry_other_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TravelPlanDestination.objects.filter(id=self.tpd_entry_other_plan.id).exists())

class ActivityAPIViewTest(APIBaseTest):
    """
    Tests for ActivityListCreateView (list/create activities)
    and ActivityDetailView (retrieve/update/delete single activity).
    Permissions: Owner of parent TravelPlan OR Admin for write/list/retrieve.
    """
    def setUp(self):
        # Call parent's setUp to get admin_user, regular_user, other_user, and their tokens
        super().setUp()
        
        # Create a travel plan for the regular_user (default client)
        self.user_plan = TravelPlan.objects.create(
            name='My Activity Plan', user=self.regular_user,
            start_date='2025-07-01', end_date='2025-07-10', budget=500.00, is_public=False
        )
        # Create a travel plan for the other_user
        self.other_user_plan = TravelPlan.objects.create(
            name='Other User Activity Plan', user=self.other_user,
            start_date='2025-08-01', end_date='2025-08-10', budget=300.00, is_public=False
        )

        # Create some destinations (ensure they have an owner/user)
        self.destination_museum = Destination.objects.create(name='Museum', country='Germany', city='Berlin', user=self.admin_user)
        self.destination_restaurant = Destination.objects.create(name='Restaurant', country='France', city='Paris', user=self.admin_user)

        # Create an Activity entry for the user's plan
        self.activity_user_plan = Activity.objects.create(
            name='Visit Museum', travel_plan=self.user_plan, destination=self.destination_museum,
            date='2025-07-03T10:00:00Z', cost=25.00
        )
        # Create an Activity entry for the other user's plan
        self.activity_other_plan = Activity.objects.create(
            name='Eat Dinner', travel_plan=self.other_user_plan, destination=self.destination_restaurant,
            date='2025-08-05T19:00:00Z', cost=50.00
        )

        # Default client is set to regular_user's token in APIBaseTest

    # # --- Tests for ActivityListCreateView ---

    def test_list_activities_own_plan_authenticated_user(self):
        """
        Tests if an authenticated user can list Activity entries for their own plans.
        Expected: HTTP 200 OK, returns entries for user_plan.
        """
        response = self.client.get(reverse('activity-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only see the Activity entry belonging to self.user_plan
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Visit Museum')
        # Check nested destination detail
        self.assertEqual(response.data[0]['destination_detail']['name'], 'Museum')
        # Check travel plan display string
        self.assertEqual(response.data[0]['travel_plan_display'], str(self.user_plan))


    def test_list_activities_other_plan_authenticated_user_empty(self):
        """
        Tests if an authenticated user correctly does NOT see Activity entries from other users' plans.
        Expected: HTTP 200 OK, but an empty list.
        """
        # The list view for the regular_user should still only show their own.
        response = self.client.get(reverse('activity-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1) # Still 1, not 2, because other's Activity is filtered out

    def test_list_activities_unauthenticated_user_empty(self):
        """
        Tests if an unauthenticated user gets an empty list when trying to list Activity entries.
        Expected: HTTP 200 OK, empty list, as Activities are tied to private plans.
        """
        self.client.credentials() # Clear credentials
        response = self.client.get(reverse('activity-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_activity_own_plan_authenticated_user(self):
        """
        Tests if an authenticated user can create an Activity entry for their own travel plan.
        Expected: HTTP 201 Created.
        """
        data = {
            'name': 'Shopping',
            'travel_plan_id': self.user_plan.id, # Link to user's own plan
            'destination_id': self.destination_restaurant.id,
            'date': '2025-07-05T14:00:00Z',
            'cost': 100.00,
            'notes': 'Buy souvenirs'
        }
        response = self.client.post(reverse('activity-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Activity.objects.count(), 3) # 2 from setUp + 1 new
        # Verify related objects by name from response data
        self.assertEqual(response.data['destination_detail']['name'], 'Restaurant')
        self.assertEqual(response.data['travel_plan_display'], str(self.user_plan))


    def test_create_activity_other_plan_authenticated_user_fails(self):
        """
        Tests if an authenticated user is denied creating an Activity entry for another user's plan.
        Expected: HTTP 400 Bad Request (due to serializer validation).
        """
        data = {
            'name': 'Forbidden Activity',
            'travel_plan_id': self.other_user_plan.id, # Attempt to link to other user's plan
            'destination_id': self.destination_museum.id,
            'date': '2025-08-03T11:00:00Z',
            'cost': 15.00,
            'notes': 'Should not be created'
        }
        response = self.client.post(reverse('activity-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('travel_plan_id', response.data) # Check for specific error message on travel_plan_id

    def test_create_activity_unauthenticated_user_fails(self):
        """
        Tests if an unauthenticated user is denied creating any Activity entry.
        Expected: HTTP 401 Unauthorized.
        """
        self.client.credentials() # Clear credentials
        data = {
            'name': 'Anon Activity',
            'travel_plan_id': self.user_plan.id,
            'destination_id': self.destination_museum.id,
            'date': '2025-07-01T09:00:00Z',
            'cost': 5.00,
            'notes': ''
        }
        response = self.client.post(reverse('activity-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # # --- Tests for ActivityDetailView ---

    def test_retrieve_activity_own_plan_authenticated_user(self):
        """
        Tests if an authenticated user can retrieve an Activity entry for their own plan.
        Expected: HTTP 200 OK.
        """
        response = self.client.get(reverse('activity-detail', args=[self.activity_user_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Visit Museum')
        self.assertEqual(response.data['destination_detail']['name'], 'Museum')
        self.assertEqual(response.data['travel_plan_display'], str(self.user_plan))

    def test_retrieve_activity_other_plan_authenticated_user_fails(self):
        """
        Tests if an authenticated user is denied retrieving an Activity entry from another user's plan.
        Expected: HTTP 403 Forbidden.
        """
        response = self.client.get(reverse('activity-detail', args=[self.activity_other_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_activity_unauthenticated_user_fails(self):
        """
        Tests if an unauthenticated user is denied retrieving any Activity entry.
        Expected: HTTP 401 Unauthorized.
        """
        self.client.credentials() # Clear credentials
        response = self.client.get(reverse('activity-detail', args=[self.activity_user_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_update_activity_own_plan_authenticated_user(self):
        """
        Tests if the owner of a TravelPlan can update its Activity entry.
        Expected: HTTP 200 OK.
        """
        data = {'cost': 30.00, 'notes': 'Updated cost'}
        response = self.client.patch(reverse('activity-detail', args=[self.activity_user_plan.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.activity_user_plan.refresh_from_db()
        self.assertEqual(self.activity_user_plan.cost, 30.00)
        self.assertEqual(self.activity_user_plan.notes, 'Updated cost')

    def test_update_activity_other_plan_authenticated_user_fails(self):
        """
        Tests if an authenticated non-owner user is denied updating another user's Activity entry.
        Expected: HTTP 403 Forbidden.
        """
        data = {'cost': 999.00}
        response = self.client.patch(reverse('activity-detail', args=[self.activity_other_plan.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_activity_as_admin(self):
        """
        Tests if an admin user can update any Activity entry.
        Expected: HTTP 200 OK.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        data = {'cost': 75.00, 'name': 'Admin Updated Activity'}
        response = self.client.patch(reverse('activity-detail', args=[self.activity_other_plan.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.activity_other_plan.refresh_from_db()
        self.assertEqual(self.activity_other_plan.cost, 75.00)
        self.assertEqual(self.activity_other_plan.name, 'Admin Updated Activity')

    def test_delete_activity_own_plan_authenticated_user(self):
        """
        Tests if the owner of a TravelPlan can delete its Activity entry.
        Expected: HTTP 204 No Content.
        """
        response = self.client.delete(reverse('activity-detail', args=[self.activity_user_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.filter(id=self.activity_user_plan.id).exists())

    def test_delete_activity_other_plan_authenticated_user_fails(self):
        """
        Tests if an authenticated non-owner user is denied deleting another user's Activity entry.
        Expected: HTTP 403 Forbidden.
        """
        response = self.client.delete(reverse('activity-detail', args=[self.activity_other_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_activity_as_admin(self):
        """
        Tests if an admin user can delete any Activity entry.
        Expected: HTTP 204 No Content.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.delete(reverse('activity-detail', args=[self.activity_other_plan.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.filter(id=self.activity_other_plan.id).exists())

class CommentAPIViewTest(APIBaseTest):
    """
    Tests for CommentListCreateView (list/create comments)
    and CommentDetailView (retrieve/update/delete single comment).
    Permissions:
    - List/Retrieve (any comment): Any user (authenticated or unauthenticated).
    - Create: Authenticated users only.
    - Update/Delete: Only the owner of the comment OR an Admin.
    """
    def setUp(self):
        super().setUp()
        
        # Create objects to comment on
        self.destination_to_comment = Destination.objects.create(
            name='Eiffel Tower', country='France', city='Paris', user=self.admin_user
        )
        self.travel_plan_to_comment = TravelPlan.objects.create(
            name='Paris Honeymoon', user=self.admin_user,
            start_date='2025-07-01', end_date='2025-07-05', budget=5000.00, is_public=True
        )

        # Get ContentType IDs for generic foreign key
        self.destination_content_type_id = ContentType.objects.get_for_model(Destination).id
        self.travel_plan_content_type_id = ContentType.objects.get_for_model(TravelPlan).id

        # Create some comments for testing (order by created_at for consistent indexing)
        self.comment_by_regular_user = Comment.objects.create(
            user=self.regular_user, text='Loved this place!', content_object=self.destination_to_comment
        )
        self.comment_by_other_user = Comment.objects.create(
            user=self.other_user, text='Great plan!', content_object=self.travel_plan_to_comment
        )

        # Default client is regular_user's token (already set in APIBaseTest)

    # --- Tests for CommentListCreateView ---

    def test_list_comments_authenticated_user(self):
        """
        Tests if an authenticated user can list all comments.
        Expected: HTTP 200 OK, returns all comments.
        """
        response = self.client.get(reverse('comment-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Use assertion for existence and then content regardless of order if order is not strict
        comment_texts = {p['text'] for p in response.data}
        self.assertIn(self.comment_by_regular_user.text, comment_texts)
        self.assertIn(self.comment_by_other_user.text, comment_texts)

        # Check display fields (assuming any comment in list has them)
        if response.data:
            self.assertIn('user_username', response.data[0])
            self.assertIn('content_object_display', response.data[0])


    def test_list_comments_unauthenticated_user(self):
        """
        Tests if an unauthenticated user can list all comments (read-only allowed by IsAuthenticatedOrReadOnly).
        Expected: HTTP 200 OK, returns all comments.
        """
        self.client.credentials() # Clear credentials
        response = self.client.get(reverse('comment-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_comment_authenticated_user_on_destination(self):
        """
        Tests if an authenticated user can create a comment on a Destination.
        Expected: HTTP 201 Created, user automatically assigned.
        """
        data = {
            'text': 'So beautiful!',
            'content_type_id': self.destination_content_type_id, # *** FIX: Use _id suffix ***
            'object_id': self.destination_to_comment.id
        }
        response = self.client.post(reverse('comment-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 3) # 2 from setUp + 1 new
        new_comment = Comment.objects.get(text='So beautiful!')
        self.assertEqual(new_comment.user, self.regular_user) # Verify user is assigned
        self.assertEqual(new_comment.content_object, self.destination_to_comment)
        self.assertEqual(response.data['user_username'], self.regular_user.username)
        self.assertEqual(response.data['content_object_display'], str(self.destination_to_comment))


    def test_create_comment_authenticated_user_on_travel_plan(self):
        """
        Tests if an authenticated user can create a comment on a TravelPlan.
        Expected: HTTP 201 Created.
        """
        data = {
            'text': 'Planning to visit this next year!',
            'content_type_id': self.travel_plan_content_type_id, # *** FIX: Use _id suffix ***
            'object_id': self.travel_plan_to_comment.id
        }
        response = self.client.post(reverse('comment-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 3)
        new_comment = Comment.objects.get(text='Planning to visit this next year!')
        self.assertEqual(new_comment.user, self.regular_user)
        self.assertEqual(new_comment.content_object, self.travel_plan_to_comment)
        self.assertEqual(response.data['user_username'], self.regular_user.username)
        self.assertEqual(response.data['content_object_display'], str(self.travel_plan_to_comment))


    def test_create_comment_unauthenticated_user_fails(self):
        """
        Tests if an unauthenticated user is denied creating a comment.
        Expected: HTTP 401 Unauthorized (due to IsAuthenticatedOrReadOnly).
        """
        self.client.credentials() # Clear credentials
        data = {
            'text': 'Unauthorized comment',
            'content_type_id': self.destination_content_type_id, # *** FIX: Use _id suffix ***
            'object_id': self.destination_to_comment.id
        }
        response = self.client.post(reverse('comment-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_comment_with_invalid_content_type_fails(self):
        """
        Tests if creating a comment with an invalid content type fails.
        Expected: HTTP 400 Bad Request (serializer validation).
        """
        data = {
            'text': 'Invalid type comment',
            'content_type_id': 9999, # *** FIX: Use _id suffix, also this ID is what serializer looks for ***
            'object_id': self.destination_to_comment.id
        }
        response = self.client.post(reverse('comment-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # *** FIX: Assert error on content_type_id, not content_type ***
        self.assertIn('content_type_id', response.data)
        self.assertIn("Content type not found.", str(response.data['content_type_id']))


    def test_create_comment_with_invalid_object_id_fails(self):
        """
        Tests if creating a comment with a valid content type but non-existent object ID fails.
        Expected: HTTP 400 Bad Request (serializer validation).
        """
        data = {
            'text': 'Non-existent object comment',
            'content_type_id': self.destination_content_type_id, # *** FIX: Use _id suffix ***
            'object_id': 999999 # Non-existent object ID
        }
        response = self.client.post(reverse('comment-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # *** FIX: Assert error on object_id ***
        self.assertIn('object_id', response.data)
        self.assertIn(f"The 'destination' object with ID '999999' was not found.", str(response.data['object_id']))


    def test_create_comment_with_empty_text_fails(self):
        """
        Tests if creating a comment with empty text fails.
        Expected: HTTP 400 Bad Request (serializer validation).
        """
        data = {
            'text': '', # Empty text
            'content_type_id': self.destination_content_type_id, # *** FIX: Use _id suffix ***
            'object_id': self.destination_to_comment.id
        }
        response = self.client.post(reverse('comment-list-create'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('text', response.data)


    # # --- Tests for CommentDetailView ---

    def test_retrieve_comment_owner(self):
        response = self.client.get(reverse('comment-detail', args=[self.comment_by_regular_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], self.comment_by_regular_user.text)
        self.assertEqual(response.data['user_username'], self.regular_user.username)

    def test_retrieve_comment_non_owner_authenticated(self):
        response = self.client.get(reverse('comment-detail', args=[self.comment_by_other_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], self.comment_by_other_user.text)
        self.assertEqual(response.data['user_username'], self.other_user.username)

    def test_retrieve_comment_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(reverse('comment-detail', args=[self.comment_by_regular_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], self.comment_by_regular_user.text)

    def test_update_comment_owner(self):
        data = {'text': 'Updated comment by owner.'}
        response = self.client.patch(reverse('comment-detail', args=[self.comment_by_regular_user.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment_by_regular_user.refresh_from_db()
        self.assertEqual(self.comment_by_regular_user.text, 'Updated comment by owner.')

    def test_update_comment_non_owner_fails(self):
        data = {'text': 'Attempted update by non-owner.'}
        response = self.client.patch(reverse('comment-detail', args=[self.comment_by_other_user.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_comment_as_admin(self): 
        """
        Tests if an admin user can update any comment.
        Expected: HTTP 200 OK (because IsOwnerOrAdminOrReadOnly allows admin override).
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        data = {'text': 'Updated by admin.'}
        response = self.client.patch(reverse('comment-detail', args=[self.comment_by_regular_user.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.comment_by_regular_user.refresh_from_db()
        self.assertEqual(self.comment_by_regular_user.text, 'Updated by admin.')

    def test_delete_comment_owner(self):
        response = self.client.delete(reverse('comment-detail', args=[self.comment_by_regular_user.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment_by_regular_user.id).exists())

    def test_delete_comment_non_owner_fails(self):
        response = self.client.delete(reverse('comment-detail', args=[self.comment_by_other_user.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_comment_as_admin(self):
        """
        Tests if an admin user can delete any comment.
        Expected: HTTP 204 No Content (because IsOwnerOrAdminOrReadOnly allows admin override).
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.delete(reverse('comment-detail', args=[self.comment_by_other_user.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=self.comment_by_other_user.id).exists())
