from functools import total_ordering
from typing import List

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils.translation import ugettext_lazy as _

from checkout.user_manager import CheckoutUserManager


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
    storage_location = models.CharField(max_length=100, null=True, blank=True)

    # TODO: add constraints here to make sure the sum cannot exceed total_units
    units = models.IntegerField()

    def __str__(self):
        return "{} - {} ({} units)".format(self.site, self.sku.display_name, self.units)


class Classroom(models.Model):
    class Meta:
        unique_together = (('site', 'code'), ('site', 'name'))

    site = models.ForeignKey(Site)
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=3)

    def __str__(self):
        return "{} - {}".format(self.code, self.name, self.site)


class Team(models.Model):
    site = models.ForeignKey(Site)
    team = models.ManyToManyField(settings.AUTH_USER_MODEL)

    def __str__(self):
        return ", ".join([member.get_short_name() for member in self.team.all()])


@total_ordering
class Period(models.Model):
    number = models.IntegerField()
    name = models.CharField(max_length=12)
    site = models.ForeignKey(Site)

    def __eq__(self, other):
        return self.name == other.name and self.number == other.number

    def __lt__(self, other):
        if self.site == other.site:
            return self.number < other.number
        return self.site.id < other.site.id

    def __str__(self):
        return self.site.__str__() + " - " + self.name + " (" + str(self.number) + ")"


@total_ordering
class Reservation(models.Model):
    team = models.ForeignKey(Team)
    site_sku = models.ForeignKey(SiteSku)
    classroom = models.ForeignKey(Classroom)
    units = models.IntegerField()
    date = models.DateField()
    period = models.ForeignKey(Period)
    comment = models.CharField(max_length=1000, null=True, blank=True)

    def __eq__(self, other):
        return (
            self.team == other.team and self.site_sku == other.site_sku and self.classroom == other.classroom and
            self.units == other.units and self.date == other.date and self.period == other.period)

    def __lt__(self, other):
        if self.date != other.date:
            return self.date < other.date

        if self.period != other.period:
            return self.period < other.period

        if self.site_sku != other.site_sku:
            return self.units < other.units

    def __str__(self):
        return "{} Class {} {} - {} {}".format(
            self.period, self.classroom.name, self.team, self.units, self.site_sku.sku.display_name)


@total_ordering
class Day(models.Model):
    date = models.DateField(primary_key=True)

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
    days = models.ManyToManyField(Day, blank=True)

    def start_date(self):
        return list(self.days.all())[0].date

    def end_date(self):
        return list(self.days.all())[-1].date

    def __eq__(self, other):
        return self.site == other.site and \
               self.days.all()[0] == other.days.all()[0] and \
               self.days.all()[-1] == other.days.all()[-1]

    def __lt__(self, other):
        return list(self.days.all())[0] < list(other.days.all())[0]

    def __str__(self):
        days: List[Day] = list(self.days.all())
        return "{} - Week {} ({} days, {} - {})".format(
            self.site, self.week_number, len(days), days[0], days[-1])


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
    objects = user_manager

    def get_full_name(self):
        return self.display_name

    def get_short_name(self):
        return self.display_name

    def __str__(self):
        return "{} - {}".format(self.email, self.site)
