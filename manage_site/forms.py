from django import forms
from providers.models import Provider
from content.models import MediaItem


class ProviderForm(forms.ModelForm):
    class Meta:
        model = Provider
        fields = ["name", "logo", "description", "url"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "nhsuk-input"}),
            "description": forms.Textarea(attrs={"class": "nhsuk-textarea", "rows": 4}),
            "url": forms.URLInput(attrs={"class": "nhsuk-input"}),
        }


class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = ["title", "file", "provider"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "nhsuk-input"}),
            "provider": forms.Select(attrs={"class": "nhsuk-select"}),
        }


class PlaylistForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "nhsuk-input"}),
    )
