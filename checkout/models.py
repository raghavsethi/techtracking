from functools import total_ordering
from typing import List

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext_lazy as _

from checkout.user_manager import CheckoutUserManager


class SKU(models.Model):
    model_identifier = models.CharField(max_length=200, help_text='e.g. Apple 13.3" MacBook Pro (Mid 2017, Space Gray)')
    display_name = models.CharField(max_length=50, help_text='Short name to show in schedule - e.g. MacbookPro13-2017')
    units = models.IntegerField(help_text='How many total functional units Aim High has available')

    def __str__(self):
        return "{} ({}) - {} units" .format(self.display_name, self.model_identifier, self.units)


class Site(models.Model):
    name = models.CharField(max_length=100, help_text='e.g. Francisco, Western Addition')

    def __str__(self):
        return self.name


class SiteSku(models.Model):
    class Meta:
        unique_together = (('site', 'sku'),)

    site = models.ForeignKey(Site, help_text='Which site these units are being assigned to')
    sku = models.ForeignKey(SKU)
    storage_location = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="e.g. Closet in site directors's office")

    # TODO: add constraints here to make sure the sum cannot exceed total_units
    units = models.IntegerField(help_text='Number of units being assigned to this site')

    def __str__(self):
        return "{} - {} ({} units)".format(self.site, self.sku.display_name, self.units)


class Classroom(models.Model):
    class Meta:
        unique_together = (('site', 'code'), ('site', 'name'))

    site = models.ForeignKey(Site)
    name = models.CharField(max_length=50, help_text='e.g. Classroom 101, Cafeteria')
    code = models.CharField(max_length=3, help_text='3 letter code to identify classroom in schedule - e.g. 101, CAF')

    def __str__(self):
        return "{} - {}".format(self.code, self.name, self.site)


class Subject(models.Model):
    name = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    site = models.ForeignKey(Site)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL)
    subject = models.ForeignKey(Subject, blank=True)

    def __str__(self):
        if self.id == None:
            return "In-progress teaching team"

        return ", ".join([member.get_short_name() for member in self.members.all()]) + " (" + self.subject.__str__() + ")"


@total_ordering
class Period(models.Model):
    site = models.ForeignKey(Site)
    number = models.IntegerField(help_text='Determines the ordering of periods in a day. For example, if Period 4 is '
                                           'given number 4, and Activity 1 is given number 5, then Period 4 occurs '
                                           'right before Activity 1')
    name = models.CharField(max_length=12, help_text='e.g. Period 3, Activity 2')

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

    site = models.ForeignKey(Site)
    week_number = models.IntegerField()
    days = models.ManyToManyField(Day, blank=True, help_text="Working days in this week")

    def start_date(self):
        return sorted(list(self.days.all()))[0].date

    def end_date(self):
        return sorted(list(self.days.all()))[-1].date

    def __eq__(self, other):
        return self.site == other.site and self.week_number == other.week_number

    def __lt__(self, other):
        return self.week_number < other.week_number

    def __str__(self):
        days: List[Day] = list(self.days.all())
        return "{} - Week {} ({} days, {} - {})".format(
            self.site, self.week_number, len(days), self.start_date(), self.end_date())


class User(AbstractBaseUser, PermissionsMixin):
    class Meta:
        unique_together = (('site', 'display_name'),)

    site = models.ForeignKey(Site, null=True)
    email = models.EmailField(unique=True, primary_key=True)
    display_name = models.CharField(max_length=50, help_text='Short name to display in schedule - e.g. KyraG')

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

    def __eq__(self, other):
        return self.email == other.email and self.display_name == other.display_name and self.site == other.site

    def __str__(self):
        return "{} - {}".format(self.email, self.site)

    def send_welcome_email(self):
        """
        Generates a one-use only link for creating a password and sends to the user's email.
        """
        from_email = None
        domain = 'localhost:8000'
        use_https = False
        # TODO: Configure properly

        context = {
            'user': self,
            'domain': domain,
            'uid': urlsafe_base64_encode(force_bytes(self.email)),
            'token': default_token_generator.make_token(self),
            'protocol': 'https' if use_https else 'http',
            # TODO: Add help link
        }

        body = loader.render_to_string('registration/new_user_email.html', context)
        EmailMultiAlternatives('Welcome to the Aim High checkout system!', body, from_email, [self.email]).send()
