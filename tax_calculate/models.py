from django.db import models
from users.models import UserAccount
from django.core.validators import MinValueValidator




class TaxCalculation(models.Model):
    TAXPAYER_CHOICES = [
        ("resident", "Resident"),
        ("senior", "Senior Citizen"),
        ("nri", "Non-Resident Indian"),
        ("huf", "HUF"),
    ]

    REGIME_CHOICES = [
        ("old", "Old Regime"),
        ("new", "New Regime"),
    ]

    user = models.CharField(max_length=200,null=True,blank=True)
    taxpayer_type = models.CharField(max_length=20, choices=TAXPAYER_CHOICES, default="resident")
    regime = models.CharField(max_length=10, choices=REGIME_CHOICES, default="old")
    gross_income = models.FloatField(validators=[MinValueValidator(0)])
    age = models.IntegerField(validators=[MinValueValidator(0)])
    tds = models.FloatField(default=0)
    deductions = models.JSONField(default=dict)
    has_business = models.BooleanField(default=False)
    presumptive = models.BooleanField(default=False)
    special_income = models.BooleanField(default=False)
    total_tax = models.FloatField(null=True, blank=True)
    taxable_income = models.FloatField(null=True, blank=True)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TaxCalculation({self.user}, {self.taxpayer_type}, {self.gross_income})"
from django.db import models

class ChatSession(models.Model):
    session_id = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ChatLog(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="logs")
    user_message = models.TextField()
    bot_response = models.TextField()
    intent = models.CharField(max_length=64, null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

from django.db import models
import uuid
class FAQ(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)  # will be filled later
    category = models.CharField(max_length=100, blank=True, null=True)
    email = models.TextField(blank=True, null=True)  # now fully safe as plain text
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.question[:50]
