from datetime import date, datetime, timedelta
from typing import List

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from checkout.models import Day, Site, User


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
            self.stdout.write()

        sites: List[Site] = list(Site.objects.all())
        if len(sites) == 0:
            self.stdout.write('No sites present in database')
            site_name = input('Enter the name of any one site (e.g. Western Addition): ')
            sites = [Site.objects.create(name=site_name)]

        superuser = superusers[0]
        if superuser.site is None:
            self.stdout.write("Setting superuser site to '{}'..".format(sites[0].name))
            self.stdout.write('')
            superuser.site = sites[0]
            superuser.save()

        if superuser.name is None or superuser.name == '':
            name = input('Superuser name (e.g. Russel Gong): ')
            superuser.name = name
            superuser.save()

        self.stdout.write('')
        start_date = read_date('Earliest start date of program across all sites (e.g. 2017-06-01)')
        end_date = read_date('Latest end date of program across all sites (e.g. 2017-08-01)')

        self.stdout.write('')
        self.stdout.write('Creating days..')

        days_delta: timedelta = end_date - start_date
        num_days = days_delta.days
        created_days = 0
        for day_number in range(0, num_days + 1):
            day = start_date + timedelta(days=day_number)

            try:
                Day.objects.get(date=day)
            except ObjectDoesNotExist:
                Day.objects.create(date=day)
                created_days += 1

        self.stdout.write('Created {} days'.format(created_days))
        self.stdout.write('')

        self.stdout.write('Setup completed successfully!')
        self.stdout.write('')

        self.stdout.write('If you are making changes to the system on your computer:')
        self.stdout.write("1. Run 'python manage.py runserver'")
        self.stdout.write("2. Open 'http://localhost:8000/admin' in your favorite browser")
        self.stdout.write('')

        self.stdout.write('If you are running this on Heroku:')
        self.stdout.write("1. You're done! Just open up the site in your browser, and head to the admin interface")
