import json
from datetime import datetime, date, timedelta
from functools import total_ordering
from typing import List

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import MinValueValidator, MinLengthValidator
from django.db import models
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext_lazy as _

from checkout.user_manager import CheckoutUserManager


class SKUType(models.Model):
    name = models.CharField(max_length=50, help_text='e.g. Laptop, Tablet, Projector')

    def __str__(self):
        return self.name


class SKU(models.Model):
    type = models.ForeignKey(SKUType)
    model_identifier = models.CharField(
        max_length=200,
        help_text='e.g. Apple 13.3" MacBook Pro (Mid 2017, Space Gray)')
    display_name = models.CharField(
        max_length=50,
        help_text='Short name to show in schedule - e.g. MacbookPro13-2017')
    units = models.IntegerField(
        help_text='How many total functional units Aim High has available',
        validators=[MinValueValidator(1)])

    def __str__(self):
        return "{} ({}) - {} units" .format(self.display_name, self.model_identifier, self.units)


class Site(models.Model):
    name = models.CharField(
        primary_key=True,
        max_length=100,
        help_text='e.g. Francisco, Western Addition')

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
        default="Site Director's office",
        help_text="e.g. Storage closet in classroom 201")

    units = models.IntegerField(
        help_text='Number of units being assigned to this site',
        validators=[MinValueValidator(1)])

    def clean(self):
        super(SiteSku, self).clean()
        assigned_units = 0
        for site_sku in self.sku.sitesku_set.all():
            if site_sku.site != self.site:
                assigned_units += site_sku.units

        if (self.units + assigned_units) > self.sku.units:
            raise ValidationError(
                'Cannot assign more units ({}) than available ({})'.format(self.units + assigned_units, self.sku.units))

    def __str__(self):
        return "{} - {} ({} units)".format(self.site, self.sku.display_name, self.units)


class Classroom(models.Model):
    class Meta:
        unique_together = (('site', 'code'), ('site', 'name'))

    site = models.ForeignKey(Site)
    name = models.CharField(
        max_length=50,
        help_text='e.g. Classroom 101, Cafeteria')
    code = models.CharField(
        max_length=3,
        help_text='Up to 3 letters to identify classroom in schedule - e.g. 101, CAF')

    def __str__(self):
        return "{} - {}".format(self.code, self.name, self.site)


class Subject(models.Model):
    ACTIVITY_SUBJECT = "Activity/Ad-hoc"

    name = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    site = models.ForeignKey(Site)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL)
    subject = models.ForeignKey(Subject)

    def __str__(self):
        if self.id is None:
            return "In-construction teaching team"

        return ", ".join([member.name for member in self.members.all()]) + " (" + self.subject.__str__() + ")"


@total_ordering
class Period(models.Model):
    number = models.IntegerField(help_text='Determines the ordering of periods in a day. For example, if Period 4 is '
                                           'given number 4, and Activity 1 is given number 5, then Period 4 occurs '
                                           'right before Activity 1', validators=[MinValueValidator(1)])
    name = models.CharField(max_length=12, help_text='e.g. Period 3, Activity 2')

    def __eq__(self, other):
        return self.pk == other.pk

    def __lt__(self, other):
        return self.number < other.number

    def __str__(self):
        return self.name + " (" + str(self.number) + ")"


class UsagePurpose(models.Model):
    OTHER_PURPOSE = "Other"

    purpose = models.CharField(max_length=100, help_text='e.g. Research (Google, Wikipedia, Wolfram Alpha etc.)')

    def __str__(self):
        return self.purpose


@total_ordering
class Reservation(models.Model):
    class Meta:
        unique_together = (('team', 'site_sku', 'classroom', 'date', 'period'),)

    team = models.ForeignKey(Team)
    site_sku = models.ForeignKey(SiteSku)
    classroom = models.ForeignKey(Classroom)
    date = models.DateField()
    period = models.ForeignKey(Period)
    units = models.IntegerField(validators=[MinValueValidator(1)])
    purpose = models.ForeignKey(UsagePurpose, null=True, blank=True)
    collaborative = models.BooleanField()
    creator = models.ForeignKey(settings.AUTH_USER_MODEL)
    comment = models.CharField(max_length=1000, null=True, blank=True)

    def __eq__(self, other):
        return self.pk == other.pk

    def __lt__(self, other):
        if self.date != other.date:
            return self.date < other.date

        if self.period != other.period:
            return self.period < other.period

        if self.site_sku != other.site_sku:
            return self.units < other.units

    def __str__(self):
        return "{} {} {} - {} {}".format(
            self.period, self.classroom.name, self.team, self.units, self.site_sku.sku.display_name)


# Will not be visible in the admin UI by default
@total_ordering
class Week(models.Model):
    class Meta:
        unique_together = (('site', 'week_number'),)

    site = models.ForeignKey(Site)
    week_number = models.IntegerField(validators=[MinValueValidator(0)])
    pickled_days = models.CharField(max_length=1024)

    def start_date(self) -> date:
        return sorted(list(self.days()))[0]

    def end_date(self) -> date:
        return sorted(list(self.days()))[-1]

    def days(self) -> List[date]:
        date_strs: List[str] = json.loads(self.pickled_days)
        return [datetime.strptime(date_str, '%Y-%m-%d').date() for date_str in date_strs]

    def calendar_days(self) -> List[date]:
        i: date = self.start_date()
        end_date = self.end_date()
        calendar_days = []
        while i <= end_date:
            calendar_days.append(i)
            i = i + timedelta(days=1)

        return calendar_days

    def __eq__(self, other):
        return self.site == other.site and self.week_number == other.week_number

    def __lt__(self, other):
        return self.week_number < other.week_number

    def __str__(self):
        days: List[Day] = list(self.days())
        return "{} - Week {} ({} days, {} - {})".format(
            self.site, self.week_number, len(days), self.start_date(), self.end_date())


class User(AbstractBaseUser, PermissionsMixin):
    class Meta:
        unique_together = (('site', 'name'),)

    site = models.ForeignKey(Site, null=True)
    email = models.EmailField(unique=True, primary_key=True)
    name = models.CharField(max_length=100, help_text='Full name')

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
        return self.name

    def get_short_name(self):
        return self.name

    def __eq__(self, other):
        return self.email == other.email and self.name == other.name and self.site == other.site

    def __str__(self):
        return "{} - {}".format(self.email, self.site)

    def has_perm(self, perm, obj=None):
        return True

    def send_welcome_email(self):
        """
        Generates a one-use only link for creating a password and sends to the user's email.
        """
        from_email = 'raghavsethi.rs@gmail.com'
        domain = 'aimhigh-checkout.herokuapp.com'
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
