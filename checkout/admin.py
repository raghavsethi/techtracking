from django import forms
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import SKU, Site, SiteSku, Classroom, Team, Reservation, User, Day, Week, Period


class SuperuserAdminSite(AdminSite):
    site_title = 'Aim High - Checkout System Admin'
    site_header = 'Aim High - Checkout System'
    index_title = 'Superuser Administration'


class SiteDirectorAdminSite(AdminSite):
    site_title = 'Aim High - Checkout System Admin'
    site_header = 'Aim High - Checkout System'
    index_title = "Site Director Administration"


# Source:  https://medium.com/@ramykhuffash/django-authentication-with-just-an-email-and-password-no-username-required\
# -33e47976b517
class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', )

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# Source: https://docs.djangoproject.com/en/1.10/topics/auth/customizing/
class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('email', 'password', 'is_active', 'is_staff', 'site')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('display_name', 'email', 'site', 'is_staff')
    list_filter = ('is_staff', 'site')
    fieldsets = (
        (None, {'fields': ('email', 'password', 'display_name', 'site')}),
        ('Permissions', {'fields': ('is_staff', 'user_permissions')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'site', 'password1', 'password2', 'user_permissions')}),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()


class ClassroomAdmin(admin.ModelAdmin):
    search_fields = ('code', 'name', 'site__name',)
    list_display = ('code', 'name', 'site')
    list_filter = ('site',)

    def get_queryset(self, request):
        qs = super(ClassroomAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)


# noinspection PyMethodMayBeStatic
class ReservationAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    search_fields = ('team__team__display_name',)
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

    def get_queryset(self, request):
        qs = super(ReservationAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site_sku__site=request.user.site)


class SiteSkuAdmin(admin.ModelAdmin):
    list_display = ('sku__display_name', 'units_display', 'site', 'storage_location')
    list_filter = ('site', 'sku__display_name')

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


class SkuAdmin(admin.ModelAdmin):
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


class TeamAdmin(admin.ModelAdmin):
    search_fields = ('team__display_name',)
    list_display = ('team_display', 'site')
    list_filter = ('site',)

    def team_display(self, team: Team):
        return team.__str__()
    team_display.short_description = "Team"

    def get_queryset(self, request):
        qs = super(TeamAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)


# noinspection PyMethodMayBeStatic
class WeekAdmin(admin.ModelAdmin):
    list_display = ('site_week', 'start_date', 'end_date', 'working_days')
    list_filter = ('site',)

    def working_days(self, week: Week):
        return len(week.days.all())

    def site_week(self, week: Week):
        return week.site.name + " - Week " + str(week.week_number)

    def get_queryset(self, request):
        qs = super(WeekAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)


class SiteAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super(SiteAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(id=request.user.site.id)


class PeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'number', 'site')
    list_filter = ('site',)

    def get_queryset(self, request):
        qs = super(PeriodAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(site=request.user.site)

superuser_admin_site = SuperuserAdminSite(name='superuser_admin')
superuser_admin_site.register(User, UserAdmin)
superuser_admin_site.register(Classroom, ClassroomAdmin)
superuser_admin_site.register(Reservation, ReservationAdmin)
superuser_admin_site.register(SiteSku, SiteSkuAdmin)
superuser_admin_site.register(SKU, SkuAdmin)
superuser_admin_site.register(Team, TeamAdmin)
superuser_admin_site.register(Week, WeekAdmin)
superuser_admin_site.register(Site, SiteAdmin)
superuser_admin_site.register(Period, PeriodAdmin)
superuser_admin_site.register(Day)

staff_admin_site = SiteDirectorAdminSite(name='staff_admin')
staff_admin_site.register(User, UserAdmin)
staff_admin_site.register(Classroom, ClassroomAdmin)
staff_admin_site.register(Reservation, ReservationAdmin)
staff_admin_site.register(SiteSku, SiteSkuAdmin)
staff_admin_site.register(Team, TeamAdmin)
staff_admin_site.register(Week, WeekAdmin)
staff_admin_site.register(Site, SiteAdmin)
staff_admin_site.register(Period, PeriodAdmin)

