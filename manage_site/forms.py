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
        fields = ["title", "media_type", "file", "provider", "duration"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "nhsuk-input"}),
            "media_type": forms.Select(attrs={"class": "nhsuk-select"}),
            "provider": forms.Select(attrs={"class": "nhsuk-select"}),
            "duration": forms.NumberInput(attrs={"class": "nhsuk-input nhsuk-input--width-5"}),
        }

    def clean(self):
        cleaned = super().clean()
        media_type = cleaned.get("media_type")
        duration = cleaned.get("duration")
        if media_type == MediaItem.MediaType.IMAGE and not duration:
            self.add_error("duration", "Duration is required for images.")
        return cleaned


class PlaylistForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={"class": "nhsuk-input"}),
    )
