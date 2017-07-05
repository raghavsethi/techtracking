from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import SKU, Site, SiteSku, Classroom, Team, Reservation, User, Day, Week


admin.site.register(Site)
admin.site.register(Team)
admin.site.register(Day)
admin.site.register(Week)
admin.site.unregister(Group)


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


# noinspection PyMethodMayBeStatic
class ReservationAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
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


class SiteSkuAdmin(admin.ModelAdmin):
    list_display = ('sku__display_name', 'units_display', 'total_units_display', 'site', 'storage_location')
    list_filter = ('site', 'sku__display_name')

    def sku__display_name(self, site_sku: SiteSku):
        return site_sku.sku.display_name
    sku__display_name.short_description = "SKU Name"

    def units_display(self, site_sku: SiteSku):
        return site_sku.units
    units_display.short_description = "Assigned Units"

    def total_units_display(self, site_sku: SiteSku):
        return site_sku.sku.units
    total_units_display.short_description = "Total Units"


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


admin.site.register(User, UserAdmin)
admin.site.register(Classroom, ClassroomAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(SiteSku, SiteSkuAdmin)
admin.site.register(SKU, SkuAdmin)
