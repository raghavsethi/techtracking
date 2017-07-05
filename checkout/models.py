from django.db import models
from django.conf import settings
from checkout.user_manager import CheckoutUserManager
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from functools import total_ordering


class SKU(models.Model):
    model_identifier = models.CharField(max_length=200)
    display_name = models.CharField(max_length=50)
    units = models.IntegerField()

    def __str__(self):
        return "{} ({}) - {} units" .format(self.display_name, self.model_identifier, self.units)


class Site(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SiteSku(models.Model):
    class Meta:
        unique_together = (('site', 'sku'),)

    site = models.ForeignKey(Site)
    sku = models.ForeignKey(SKU)

    # TODO: add constraints here to make sure the sum cannot exceed total_units
    units = models.IntegerField()

    def __str__(self):
        return "{} - {} ({} units)".format(self.site, self.sku.display_name, self.units)


class Classroom(models.Model):
    class Meta:
        unique_together = (('site', 'name'),)

    site = models.ForeignKey(Site)
    name = models.CharField(max_length=50)

    def __str__(self):
        return "{} - {}".format(self.name, self.site)


class Team(models.Model):
    site = models.ForeignKey(Site)
    team = models.ManyToManyField(settings.AUTH_USER_MODEL)

    def __str__(self):
        return ([member for member in self.team.all()])[0].get_short_name()
        # return ", ".join([member.display_name for member in self.team.all()])


class Reservation(models.Model):
    team = models.ForeignKey(Team)
    site_sku = models.ForeignKey(SiteSku)
    classroom = models.ForeignKey(Classroom)
    units = models.IntegerField()
    date = models.DateField()

    PERIODS = (
        (1, 'Period 1'),
        (2, 'Period 2'),
        (3, 'Period 3'),
        (4, 'Period 4'),
        (5, 'Activity 1'),
        (6, 'Activity 2'),
    )

    period = models.IntegerField(choices=PERIODS)

    def __str__(self):
        return "{} Class {} {} - {} {}".format(
            self.get_period_display(), self.classroom.name, self.team, self.units, self.site_sku.sku.shortname)


# Need to figure out how to autogenerate these
@total_ordering
class Day(models.Model):
    date = models.DateField(unique=True)

    def __str__(self):
        return self.date.isoformat()

    def __eq__(self, other):
        return self.date == other.date

    def __lt__(self, other):
        return self.date < other.date


# Will not be visible in the admin UI by default
@total_ordering
class Week(models.Model):
    class Meta:
        unique_together = (('site', 'week_number'),)

    NUM_WEEKS = 5

    site = models.ForeignKey(Site)
    week_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.ManyToManyField(Day)

    def __eq__(self, other):
        return self.site == other.site and self.start_date == other.start_date and self.end_date == other.end_date

    def __lt__(self, other):
        return self.start_date < other.start_date

    def __str__(self):
        return "{} - Week {} ({} - {})".format(self.site, self.week_number, self.start_date, self.end_date)


class User(AbstractBaseUser, PermissionsMixin):
    class Meta:
        unique_together = (('site', 'display_name'),)

    site = models.ForeignKey(Site, null=True)
    email = models.EmailField(unique=True, primary_key=True)
    display_name = models.CharField(max_length=50)

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
        help_text=_('Designates whether the user can log into the admin site.'),
    )

    user_manager = CheckoutUserManager()

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    def __str__(self):
        return "{} - {}".format(self.email, self.site)
