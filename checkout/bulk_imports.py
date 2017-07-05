from typing import List

from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from checkout.models import Team, Subject, User, Site


class TeamResource(resources.ModelResource):
    subject = fields.Field(
        column_name='subject',
        attribute='subject',
        widget=ForeignKeyWidget(Subject, 'name'))

    members = fields.Field(
        column_name='members',
        attribute='members',
        widget=ManyToManyWidget(User, ',', 'display_name'))

    class Meta:
        model = Team
        fields = ('subject', 'members')

    def before_import_row(self, row, **kwargs):
        if kwargs['user'].is_superuser:
            raise ValueError("Superusers are not allowed to import teams from files")
        row['resolved_site'] = kwargs['user'].site

    def get_instance(self, instance_loader, row):
        if 'Subject' not in row or 'Members' not in row:
            raise ValueError("Both 'Subject' and 'Members' columns must exist. Found: {}".format(list(row.keys())))

        subject: Subject = Subject.objects.filter(name__icontains=row['Subject']).first()
        if subject is None:
            raise ValueError("Subject {} not found in database".format(row['Subject']))

        member_names: List[str] = row['Members'].split(",")
        team_qs = Team.objects.filter(site=row['resolved_site'], subject=subject)
        for member_name in member_names:
            member: User = row['resolved_site'].user_set.filter(display_name__icontains=member_name.strip()).first()
            if member is None:
                raise ValueError("Teacher {} not found in database. Please use the previously uploaded display name"
                                 .format(member_name))

            team_qs = team_qs.filter(members__email=member.email)

        return team_qs.first()

    def init_instance(self, row=None):
        if 'Subject' not in row or 'Members' not in row:
            raise ValueError("Both 'Subject' and 'Members' columns must exist. Found: {}".format(list(row.keys())))

        subject: Subject = Subject.objects.filter(name__icontains=row['Subject']).first()
        if subject is None:
            raise ValueError("Subject {} not found in database".format(row['Subject']))

        member_names: List[str] = row['Members'].split(",")
        team: Team = Team.objects.create(subject=subject, site=row['resolved_site'])
        for member_name in member_names:
            member = row['resolved_site'].user_set.filter(display_name__icontains=member_name.strip()).first()
            if member is None:
                raise ValueError("Teacher {} not found in database. Please use the previously uploaded display name"
                                 .format(member_name))

            team.members.add(member)

        team.save()
        return team


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('site', 'email', 'display_name')
        import_id_fields = ('email',)

    site = fields.Field(
        column_name='site',
        attribute='site',
        widget=ForeignKeyWidget(Site, 'name'))

    def before_import_row(self, row, **kwargs):
        user: User = kwargs['user']

        if row['site'] is None:
            row['site'] = user.site.name

        if not user.is_superuser:
            if row['site'] != user.site.name:
                raise ValueError("Cannot import users for site '{}', only '{}'".format(row['site'], user.site))
