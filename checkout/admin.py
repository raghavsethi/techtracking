from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.forms.utils import ErrorList
from import_export.admin import ImportExportModelAdmin
from import_export.formats import base_formats

from checkout.bulk_imports import TeamResource, UserResource, SKUResource
from checkout.models import *


class SuperuserOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# Source:  https://medium.com/@ramykhuffash/django-authentication-with-just-an-email-and-password-no-username-required\
# -33e47976b517
@admin.register(User)
class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    resource_class = UserResource

    def send_welcome_email(self, request, queryset):
        users: List[User] = list(queryset)
        for user in users:
            user.send_welcome_email()

        self.message_user(request, "{} users were sent welcome emails.".format(len(users)))
    send_welcome_email.short_description = 'Send welcome email'

    actions = [send_welcome_email]

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('name', 'email', 'site', 'is_staff', 'activated')
    list_filter = ('is_staff', 'site')
    fieldsets = (
        (None, {'fields': ('email', 'password', 'name', 'site')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'user_permissions')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'site', 'password1', 'password2', 'user_permissions')}),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

    def activated(self, user: User):
        return user.has_usable_password()
    activated.boolean = True

    def has_module_permission(self, request):
        return request.user.is_staff

    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)

    def get_export_formats(self):
        return [f for f in [base_formats.CSV, base_formats.XLS, base_formats.XLSX] if f().can_export()]

    def get_import_formats(self):
        return [f for f in [base_formats.CSV, base_formats.XLS, base_formats.XLSX] if f().can_import()]


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    search_fields = ('code', 'name', 'site__name',)
    list_display = ('code', 'name', 'site')
    list_filter = ('site',)

    def has_module_permission(self, request):
        return request.user.is_staff

    def get_queryset(self, request):
        qs = super(ClassroomAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)


# noinspection PyMethodMayBeStatic
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    search_fields = ('team__team__name',)
    list_display = ('date', 'site_sku__sku__display_name', 'classroom__code', 'units', 'team', 'site_sku__site')
    list_filter = ('site_sku__site', 'date', 'site_sku__sku__display_name')

    def classroom__code(self, reservation: Reservation):
        return reservation.classroom.code

    def site_sku__site(self, reservation: Reservation):
        return reservation.site_sku.site
    site_sku__site.short_description = "Site"

    def site_sku__sku__display_name(self, reservation: Reservation):
        return reservation.site_sku.sku.display_name
    site_sku__sku__display_name.short_description = "SKU Name"

    def has_module_permission(self, request):
        return request.user.is_staff

    def get_queryset(self, request):
        qs = super(ReservationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site_sku__site=request.user.site)


@admin.register(SiteSku)
class SiteSkuAdmin(SuperuserOnlyAdmin):
    list_display = ('sku__display_name', 'units_display', 'site', 'storage_location')
    list_filter = ('site', 'sku__display_name')
    readonly_fields = ('site', 'sku', 'units')

    def sku__display_name(self, site_sku: SiteSku):
        return site_sku.sku.display_name
    sku__display_name.short_description = "SKU Name"

    def units_display(self, site_sku: SiteSku):
        return site_sku.units
    units_display.short_description = "Assigned Units"

    def get_queryset(self, request):
        qs = super(SiteSkuAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(SKU)
class SkuAdmin(ImportExportModelAdmin, SuperuserOnlyAdmin):
    resource_class = SKUResource

    list_display = ('display_name', 'model_identifier', 'total_units_display', 'assigned_units_display')

    def total_units_display(self, sku: SKU):
        return sku.units
    total_units_display.short_description = "Total Units"

    def assigned_units_display(self, sku: SKU):
        assigned_units: int = 0
        for site_sku in sku.sitesku_set.all():
            assigned_units += site_sku.units

        return assigned_units
    assigned_units_display.short_description = "Assigned Units"

    def get_export_formats(self):
        return [f for f in [base_formats.CSV, base_formats.XLS, base_formats.XLSX] if f().can_export()]

    def get_import_formats(self):
        return [f for f in [base_formats.CSV, base_formats.XLS, base_formats.XLSX] if f().can_import()]


@admin.register(Team)
class TeamAdmin(ImportExportModelAdmin):
    resource_class = TeamResource

    search_fields = ('team__name', 'subject')
    list_display = ('team_display', 'subject', 'site')
    list_filter = ('site', 'subject')

    def team_display(self, team: Team):
        return ", ".join([member.get_short_name() for member in team.members.all()])
    team_display.short_description = "Team"

    def has_module_permission(self, request):
        return request.user.is_staff

    def get_queryset(self, request):
        qs = super(TeamAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)

    def get_export_formats(self):
        return [f for f in [base_formats.CSV, base_formats.XLS, base_formats.XLSX] if f().can_export()]

    def get_import_formats(self):
        return [f for f in [base_formats.CSV, base_formats.XLS, base_formats.XLSX] if f().can_import()]


class WeekForm(forms.ModelForm):
    class Meta:
        model = Week
        fields = ['site', 'week_number']

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                 initial=None, error_class=ErrorList, label_suffix=None,
                 empty_permitted=False, instance: Week=None, use_required_attribute=None):
        super(WeekForm, self).__init__(
            data=data,
            files=files,
            auto_id=auto_id,
            prefix=prefix,
            initial=initial,
            error_class=error_class,
            label_suffix=label_suffix,
            empty_permitted=empty_permitted,
            instance=instance,
            use_required_attribute=use_required_attribute)

        if instance is not None:
            self.initial['start_date'] = instance.start_date()
            self.initial['end_date'] = instance.end_date()

            days = instance.days()
            holidays = []
            d = instance.start_date()
            while d < instance.end_date():
                d = d + timedelta(days=1)
                if d not in days:
                    holidays.append(d)

            for i in range(len(holidays)):
                self.initial['holiday_' + str(i + 1)] = holidays[i]

    def save(self, commit=True):
        start_date = self.cleaned_data['start_date']
        end_date = self.cleaned_data['end_date']

        days_delta = end_date - start_date
        num_days = days_delta.days
        days: List[str] = []

        holidays = [self.cleaned_data['holiday_1'],
                    self.cleaned_data['holiday_2'],
                    self.cleaned_data['holiday_3'],
                    self.cleaned_data['holiday_4']]

        for day_number in range(0, num_days + 1):
            day: datetime = (start_date + timedelta(days=day_number))
            if day not in holidays:
                days.append(day.isoformat())

        self.instance.pickled_days = json.dumps(days)
        return self.instance

    def save_m2m(self):
        pass

    start_date = forms.DateField(label='Start Date', widget=AdminDateWidget)
    end_date = forms.DateField(label='End Date', widget=AdminDateWidget)

    holiday_1 = forms.DateField(label='Holiday', widget=AdminDateWidget, required=False)
    holiday_2 = forms.DateField(label='Holiday', widget=AdminDateWidget, required=False)
    holiday_3 = forms.DateField(label='Holiday', widget=AdminDateWidget, required=False)
    holiday_4 = forms.DateField(label='Holiday', widget=AdminDateWidget, required=False)


# noinspection PyMethodMayBeStatic
@admin.register(Week)
class WeekAdmin(admin.ModelAdmin):
    form = WeekForm

    list_display = ('site_week', 'start_date', 'end_date', 'working_days')
    list_filter = ('site',)

    def working_days(self, week: Week):
        return len(week.days())

    def site_week(self, week: Week):
        return week.site.name + " - Week " + str(week.week_number)

    def has_module_permission(self, request):
        return request.user.is_staff

    def get_queryset(self, request):
        qs = super(WeekAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)


# noinspection PyMethodMayBeStatic
@admin.register(Site)
class SiteAdmin(SuperuserOnlyAdmin):
    list_display = (
        'name',
        'staff',
        'users',
        'classrooms',
        'reservations',
        'allocated')

    def users(self, site: Site):
        active: int = 0
        for user in site.user_set.all():
            if user.has_usable_password():
                active += 1

        return "{} ({} active)".format(site.user_set.count(), active)

    def staff(self, site: Site):
        return ", ".join(user.name for user in site.user_set.filter(is_staff=True).all())

    def classrooms(self, site: Site):
        return site.classroom_set.count()

    def reservations(self, site: Site):
        total: int = 0
        for site_sku in site.sitesku_set.all():
            total += site_sku.reservation_set.count()
        return total

    def allocated(self, site: Site):
        return ", ".join(
            ["{} ({})".format(site_sku.sku.display_name, site_sku.units) for site_sku in site.sitesku_set.all()])


@admin.register(Subject)
class SubjectAdmin(SuperuserOnlyAdmin):
    pass


@admin.register(Period)
class PeriodAdmin(SuperuserOnlyAdmin):
    list_display = ('name', 'number')


@admin.register(UsagePurpose)
class UsagePurposeAdmin(SuperuserOnlyAdmin):
    pass


@admin.register(SKUType)
class SKUTypeAdmin(SuperuserOnlyAdmin):
    pass

admin.site.unregister(Group)
