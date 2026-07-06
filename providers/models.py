from django.db import models


class Provider(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to="providers/logos/", blank=True)
    description = models.TextField(blank=True)
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
