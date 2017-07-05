from datetime import date, datetime
from typing import List

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from checkout.models import Site, User, Subject, UsagePurpose, Period

def read_date(prompt: str) -> date:
    date_str: str = input(prompt + ": ")
    return datetime.strptime(date_str, "%Y-%m-%d").date()


class Command(BaseCommand):
    help = 'Runs the setup process for the checkout application'

    def handle(self, *args, **options):
        setup_actions_performed: bool = False
        superusers: List[User] = list(get_user_model().objects.filter(is_superuser=True))
        if len(superusers) == 0:
            self.stderr.write("No superusers found, please run 'python manage.py createsuperuser'")
            exit(1)

        if len(superusers) >= 1:
            self.stdout.write('✔ Superusers are present in the database')

        sites: List[Site] = list(Site.objects.all())
        if len(sites) == 0:
            self.stdout.write('! No sites present in database')
            site_name = input('Enter the name of any one site (e.g. Western Addition): ')
            sites = [Site.objects.create(name=site_name)]
            self.stdout.write('✔ Site created')
            setup_actions_performed = True

        if len(sites) >= 1:
            self.stdout.write('✔ Sites are present in the database')

        for superuser in superusers:
            if superuser.name is None or superuser.name == '':
                self.stdout.write('! Superuser {} does not have a name'.format(superuser.email))
                name = input('Enter full name for {}: '.format(superuser.email))
                superuser.name = name
                superuser.save()
                setup_actions_performed = True
                self.stdout.write('✔ Superuser name saved')

            if superuser.site is None:
                self.stdout.write('! Superuser {} does not have an associated initial site'.format(superuser.name))
                superuser.site = sites[0]
                superuser.save()
                self.stdout.write("✔ Set initial site for {} to '{}'..".format(superuser.name, sites[0].name))
                setup_actions_performed = True

        if Subject.objects.filter(name=Subject.ACTIVITY_SUBJECT).first() is None:
            self.stdout.write('! Default subject was not present in the database')
            Subject.objects.create(name=Subject.ACTIVITY_SUBJECT)
            self.stdout.write("✔ Created default subject '{}'..".format(Subject.ACTIVITY_SUBJECT))
            setup_actions_performed = True
        else:
            self.stdout.write("✔ Default subject '{}' present in database".format(Subject.ACTIVITY_SUBJECT))

        if UsagePurpose.objects.filter(purpose=UsagePurpose.OTHER_PURPOSE).first() is None:
            self.stdout.write('! Default purpose was not present in the database')
            UsagePurpose.objects.create(purpose=UsagePurpose.OTHER_PURPOSE)
            self.stdout.write("✔ Created default purpose '{}'..".format(UsagePurpose.OTHER_PURPOSE))
            setup_actions_performed = True
        else:
            self.stdout.write("✔ Default purpose '{}' present in database.".format(UsagePurpose.OTHER_PURPOSE))

        periods: List[Period] = list(Period.objects.all())
        if len(periods) == 0:
            self.stdout.write('! Periods not present in database')
            self.stdout.write('Enter the period names (e.g. Period 1, Activity 2) in order now. Hit enter after each '
                              'period. Hit enter on a blank line to stop and move to the next step:')

            period_number: int = 1
            period_name: str = input().strip()
            while period_name != '':
                Period.objects.create(number=period_number, name=period_name)
                print("Added '{}' to database".format(period_name))
                period_number += 1
                period_name = input().strip()

            self.stdout.write("✔ Added {} periods to database".format(period_number - 1))
        else:
            self.stdout.write("✔ {} Periods present in database".format(len(periods)))

        self.stdout.write('')
        if setup_actions_performed:
            self.stdout.write('✔ Setup completed successfully!')
        else:
            self.stdout.write('✔ Setup checks passed. No actions were taken.')
