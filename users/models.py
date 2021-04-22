from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.validators import UnicodeUsernameValidator

# to remove the username field and use email instead
from django.contrib.auth.models import BaseUserManager


class CustomUser(AbstractUser):
    age = models.PositiveIntegerField(null=True, blank=True)


class SearchResultHistoryModel(models.Model):
    searchtext = models.CharField(max_length=500)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now=True)


class HandleModel(models.Model):
    handle = models.CharField(max_length=500)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,)
    date = models.DateTimeField(auto_now=True)


class ClaimModel(models.Model):

    handle = models.CharField(max_length=500)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,)
    date = models.DateTimeField(auto_now=True)

    # claim_num = models.IntegerField(null=True)

    claim_field = models.CharField(
        max_length=500)

    Can_you_reproduce_this_claim = models.CharField(max_length=20)

    source_Code = models.CharField(
        max_length=100, help_text="Enter the URL of your sourcecode")

    datasets = models.CharField(
        max_length=100, help_text="Enter the URL of your dataset")

    experiments_and_results = models.CharField(max_length=1000)


class ClaimLikeModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,)
    handle = models.CharField(max_length=500)
    claim_id = models.IntegerField(null=False, default=0)
    star = models.IntegerField(null=False, default=0)


class SaveItemModel(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    handle = models.CharField(max_length=500, blank=False, unique=True)
    date = models.DateTimeField(auto_now=True)
  
