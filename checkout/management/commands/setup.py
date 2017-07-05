from datetime import date, datetime
from typing import List

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from checkout.models import Site, User, Subject


def read_date(prompt: str) -> date:
    date_str: str = input(prompt + ": ")
    return datetime.strptime(date_str, "%Y-%m-%d").date()


class Command(BaseCommand):
    help = 'Runs the setup process for the checkout application'

    def handle(self, *args, **options):
        superusers: List[User] = list(get_user_model().objects.filter(is_superuser=True))
        if len(superusers) == 0:
            self.stderr.write("No superusers found, please run 'python manage.py createsuperuser'")
            exit(1)

        if len(superusers) > 1:
            self.stdout.write('Multiple superusers are present, skipping step..')
            self.stdout.write('')

        sites: List[Site] = list(Site.objects.all())
        if len(sites) == 0:
            self.stdout.write('No sites present in database')
            site_name = input('Enter the name of any one site (e.g. Western Addition): ')
            sites = [Site.objects.create(name=site_name)]

        for superuser in superusers:
            if superuser.name is None or superuser.name == '':
                name = input('Enter full name for superuser with email {}: '.format(superuser.email))
                superuser.name = name
                superuser.save()
                self.stdout.write('')

            if superuser.site is None:
                self.stdout.write("Setting site for {} to '{}'..".format(superuser.name, sites[0].name))
                self.stdout.write('')
                superuser.site = sites[0]
                superuser.save()

        if Subject.objects.filter(name=Subject.ACTIVITY_SUBJECT).first() is None:
            self.stdout.write("Creating default subject '{}'..".format(Subject.ACTIVITY_SUBJECT))
            self.stdout.write('')
            Subject.objects.create(name=Subject.ACTIVITY_SUBJECT)
        else:
            self.stdout.write("Default subject '{}' present in database, skipping..".format(Subject.ACTIVITY_SUBJECT))
            self.stdout.write('')

        self.stdout.write('Setup completed successfully!')
