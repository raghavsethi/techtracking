from django.db import models
from django.conf import settings
from checkout.user_manager import CheckoutUserManager
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin


class SKU(models.Model):
    model_identifier = models.CharField(max_length=200)
    shortname = models.CharField(max_length=200)
    total_units = models.IntegerField()

    def __str__(self):
        return "{} ({}) - {} units" .format(self.shortname, self.model_identifier, self.total_units)


class Site(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class SiteAssignment(models.Model):
    site = models.ForeignKey(Site)
    sku = models.ForeignKey(SKU)

    # need constraints here to make sure the sum cannot exceed total_units
    units = models.IntegerField()

    def __str__(self):
        return "{} - {} ({} units)".format(self.site, self.sku.shortname, self.units)


class Classroom(models.Model):
    site = models.ForeignKey(Site)
    name = models.CharField(max_length=200)

    def __str__(self):
        return "{} - {}".format(self.name, self.site)


class TeachingTeam(models.Model):
    site = models.ForeignKey(Site)
    team = models.ManyToManyField(settings.AUTH_USER_MODEL)

    def __str__(self):
        return ", ".join([member.username for member in self.team.all()])


class TechnologyAssignment(models.Model):
    teachers = models.ForeignKey(TeachingTeam)
    technology = models.ForeignKey(SiteAssignment)
    classroom = models.ForeignKey(Classroom)
    units = models.IntegerField()
    date = models.DateField()

    PERIOD_CHOICES = (
        (1, 'Period 1'),
        (2, 'Period 2'),
        (3, 'Period 3'),
        (4, 'Period 4'),
        (5, 'Activity 1h'),
        (6, 'Activity 2h'),
    )

    period = models.IntegerField(choices=PERIOD_CHOICES)

    def __str__(self):
        return "{} {} - {} {}".format(
            self.classroom, self.teachers, self.units, self.technology.sku.shortname)


class User(AbstractBaseUser, PermissionsMixin):
    site = models.ForeignKey(Site, null=True)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=30)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this site.'),
    )

    user_manager = CheckoutUserManager()

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.short_name

    def __str__(self):
        if self.full_name :
            return self.full_name + " (" + self.email + ")"
        else:
            return self.email
