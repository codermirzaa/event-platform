from django import forms
from django.utils import timezone
from .models import Event, Category


class EventForm(forms.ModelForm):
    """F-03: Event creation and editing form."""

    date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M'],
    )

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'category',
            'date', 'location',
            'capacity', 'price',
            'cover_image', 'cover_image_url',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Event title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Describe your event...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Venue name or address'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'placeholder': '0 = Free'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_image_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date <= timezone.now():
            raise forms.ValidationError("Event date must be in the future.")
        return date

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')
        # On edit: capacity cannot be reduced below existing bookings
        if self.instance and self.instance.pk:
            booked = self.instance.booked_count
            if capacity < booked:
                raise forms.ValidationError(
                    f"Cannot reduce capacity below current bookings ({booked} booked)."
                )
        return capacity


class EventSearchForm(forms.Form):
    """F-04: Event search and filter form."""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search events...',
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    price_type = forms.ChoiceField(
        choices=[('', 'Any Price'), ('free', 'Free'), ('paid', 'Paid')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    sort = forms.ChoiceField(
        choices=[('date', 'Soonest'), ('popular', 'Most Popular')],
        required=False,
        initial='date',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
