import datetime
from django.urls import reverse
from rest_framework import status

# Import the existing API test classes to inherit their setUp and data
from travel_planner.tests.test_API import (
    APIBaseTest, CustomUserAPIViewTest, DestinationAPIViewTest
)
from travel_planner.models import Destination

class CustomUserFilterAPIViewTest(CustomUserAPIViewTest):
    """
    API Tests specifically for filtering CustomUser resources.
    Inherits setUp from CustomUserAPIViewTest to use its pre-created data.
    """

    def setUp(self):
        super().setUp()
        self.regular_user.city = 'London'
        self.regular_user.preferred_travel_style = 'Adventure'
        self.regular_user.save()

        self.other_user.city = 'Paris'
        self.other_user.preferred_travel_style = 'Relaxation'
        self.other_user.save()

        self.admin_user.city = 'New York'
        self.admin_user.preferred_travel_style = 'Luxury'
        self.admin_user.save()


    # --- FILTERING TESTS FOR CUSTOM USERS ---

    def test_filter_users_by_username_icontains(self):
        """
        Tests filtering users by username using 'icontains'.
        Only admin can list all users.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get(reverse('user-list-create') + '?username=user')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data) 
        self.assertEqual(len(response.data['results']), 2) # 'user' and 'otheruser'
        usernames = {u['username'] for u in response.data['results']}
        self.assertIn('user', usernames)
        self.assertIn('otheruser', usernames)
        self.assertNotIn('admin', usernames)

    def test_filter_users_by_email_icontains(self):
        """
        Tests filtering users by email using 'icontains'.
        Only admin can list all users.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get(reverse('user-list-create') + '?email=test.com')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 3) # All users have @test.com
        emails = {u['email'] for u in response.data['results']}
        self.assertIn('admin@test.com', emails)
        self.assertIn('user@test.com', emails)
        self.assertIn('other@test.com', emails)

    def test_filter_users_by_city(self):
        """
        Tests filtering users by city.
        Only admin can list all users.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get(reverse('user-list-create') + '?city=london')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'user')

    def test_filter_users_by_preferred_travel_style(self):
        """
        Tests filtering users by preferred_travel_style.
        Only admin can list all users.
        """
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.admin_token.key)
        response = self.client.get(reverse('user-list-create') + '?preferred_travel_style=adventure')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['username'], 'user')


class DestinationFilterAPIViewTest(DestinationAPIViewTest):
    """
    API Tests specifically for filtering Destination resources.
    Inherits setUp from DestinationAPIViewTest to use its pre-created data.
    """

    def test_filter_destinations_by_name(self):
        """
        Tests filtering destinations by name (case-insensitive contains).
        """
        self.user_destination = Destination.objects.create(
            name='Admin Place Paris',
            country='Germany',
            city='Berlin',
            latitude=52.52,
            longitude=13.40,
            is_popular=False,
            user=self.regular_user
        )

        response = self.client.get(reverse('destination-list-create') + '?name=Admin') # we filter if the word 'User is in the destinations queryset'
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        names = {d['name'] for d in response.data['results']}
        self.assertNotIn('User Created Place', names)
        self.assertNotIn('Other User Place', names)
        self.assertIn('Admin Place Paris', names)

    def test_filter_destinations_by_country(self):
        """
        Tests filtering destinations by country (case-insensitive contains).
        """
        response = self.client.get(reverse('destination-list-create') + '?country=germany')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'User Created Place')

        response = self.client.get(reverse('destination-list-create') + '?country=italy')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['results'], []) # there is no Destination entry with country 'italy, so it returns an empty list'

    def test_filter_destinations_by_city(self):
        """
        Tests filtering destinations by city (case-insensitive contains).
        """
        response = self.client.get(reverse('destination-list-create') + '?city=madrid')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Other User Place')

        response = self.client.get(reverse('destination-list-create') + '?city=potsdam')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(response.data['results'], [])

    def test_filter_destinations_by_is_popular(self):
        """
        Tests filtering destinations by is_popular boolean field.
        """
        response = self.client.get(reverse('destination-list-create') + '?is_popular=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        names = {d['name'] for d in response.data['results']}
        self.assertIn('Other User Place', names)
        self.assertNotIn('Admin Place', names)
    
    def test_multiple_filters(self):
        """
        Tests if country, city, and is_popular filters work together correctly.
        Creates specific test data for this scenario.
        Expected: Only 'germany_destination_1' should match.
        """
        self.germany_destination_1= Destination.objects.create(
            name='germany_destination_1',
            country='Germany',
            city='Berlin',
            latitude=52.52,
            longitude=13.40,
            is_popular=True,
            user=self.regular_user
        )
        self.germany_destination_2 = Destination.objects.create(
            name='germany_destination_2',
            country='Germany',
            city='Potsdam',
            latitude=52.52,
            longitude=13.40,
            is_popular=True,
            user=self.regular_user 
        )
        self.germany_destination_3 = Destination.objects.create(
            name='germany_destination_3',
            country='Deutschland',
            city='Berlin',
            latitude=52.52,
            longitude=13.40,
            is_popular=True,
            user=self.regular_user
            )
        filter_params = "country=Germany&city=Berlin&is_popular=true"
        response = self.client.get(reverse('destination-list-create') + '?' + filter_params)        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('germany_destination_1', response.data['results'][0]['name'])
        self.assertNotIn('germany_destination_3', response.data['results'][0]['name'])