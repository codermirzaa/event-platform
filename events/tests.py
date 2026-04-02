from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Event, Booking, Review, Category
from datetime import timedelta

User = get_user_model()

class ReviewEligibilityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user(username='organizer', password='password', role='organizer')
        self.attendee = User.objects.create_user(username='attendee', password='password', role='attendee')
        self.category = Category.objects.create(name='Test Category', slug='test-category')

        # Past Event
        self.past_event = Event.objects.create(
            title='Past Event',
            organizer=self.organizer,
            category=self.category,
            date=timezone.now() - timedelta(days=1),
            location='Test Location',
            capacity=100,
            status=Event.Status.PUBLISHED
        )

        # Upcoming Event
        self.upcoming_event = Event.objects.create(
            title='Upcoming Event',
            organizer=self.organizer,
            category=self.category,
            date=timezone.now() + timedelta(days=1),
            location='Test Location',
            capacity=100,
            status=Event.Status.PUBLISHED
        )

    def test_unauthenticated_user_cannot_review(self):
        response = self.client.get(reverse('events:add_review', args=[self.past_event.pk]))
        self.assertEqual(response.status_code, 302) # Redirect to login

    def test_user_without_booking_cannot_review_past_event(self):
        self.client.login(username='attendee', password='password')
        response = self.client.get(reverse('events:add_review', args=[self.past_event.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('events:detail', args=[self.past_event.pk]))

    def test_user_with_cancelled_booking_cannot_review_past_event(self):
        self.client.login(username='attendee', password='password')
        Booking.objects.create(event=self.past_event, attendee=self.attendee, status=Booking.Status.CANCELLED)
        response = self.client.get(reverse('events:add_review', args=[self.past_event.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('events:detail', args=[self.past_event.pk]))

    def test_user_with_confirmed_booking_cannot_review_upcoming_event(self):
        self.client.login(username='attendee', password='password')
        Booking.objects.create(event=self.upcoming_event, attendee=self.attendee, status=Booking.Status.CONFIRMED)
        response = self.client.get(reverse('events:add_review', args=[self.upcoming_event.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('events:detail', args=[self.upcoming_event.pk]))

    def test_user_with_confirmed_booking_can_access_review_page_for_past_event(self):
        self.client.login(username='attendee', password='password')
        Booking.objects.create(event=self.past_event, attendee=self.attendee, status=Booking.Status.CONFIRMED)
        response = self.client.get(reverse('events:add_review', args=[self.past_event.pk]))
        self.assertEqual(response.status_code, 200)

    def test_user_can_submit_review_for_past_event_with_confirmed_booking(self):
        self.client.login(username='attendee', password='password')
        Booking.objects.create(event=self.past_event, attendee=self.attendee, status=Booking.Status.CONFIRMED)
        response = self.client.post(reverse('events:add_review', args=[self.past_event.pk]), {
            'rating': 5,
            'comment': 'Great event!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(event=self.past_event, author=self.attendee).exists())
