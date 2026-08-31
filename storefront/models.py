from django.db import models

from core.models import TimeStampedModel


class ContactMessage(TimeStampedModel):
    """
    A message submitted through the public Contact page.
    """

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.full_name} — {self.created_at:%Y-%m-%d}"


class Review(TimeStampedModel):
    """
    Customer review submitted through the public website.

    Reviews remain hidden until approved by staff in Django Admin.
    """

    RATING_CHOICES = [
        (1, "1 Star"),
        (2, "2 Stars"),
        (3, "3 Stars"),
        (4, "4 Stars"),
        (5, "5 Stars"),
    ]

    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
    )
    review = models.TextField()

    is_approved = models.BooleanField(
        default=False,
        help_text="Only approved reviews appear on the public website.",
    )

    is_featured = models.BooleanField(
        default=False,
        help_text="Featured reviews appear on the homepage.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Customer Review"
        verbose_name_plural = "Customer Reviews"

    def __str__(self):
        return f"{self.full_name} — {self.rating}/5"