from typing import List, Tuple

from checkout.models import *

import datetime


class DateSchedule:
    def __init__(self, site: Site, date: datetime.date):
        self.site: Site = site
        self.date: datetime.date = date
        self.periods: List[PeriodTechAvailability] = []

        site_skus: List[SiteAssignment] = list(self.site.siteassignment_set.all())
        periods: Tuple[Tuple[int, str]] = TechnologyAssignment.PERIODS
        assignments: List[TechnologyAssignment] = \
            list(TechnologyAssignment.objects.filter(site=self.site, date=self.date).all())

        for period in periods:
            period_sku_availability = []
            for site_sku in site_skus:
                site_sku_reservations = []
                for assignment in assignments:
                    if assignment.period == period[0] and assignment.technology == site_sku:
                        site_sku_reservations.append(assignment)

                period_sku_availability.append(PeriodSKUAvailability(site_sku, site_sku_reservations))

            self.periods.append(PeriodTechAvailability(period, period_sku_availability))

    def print(self):
        for period in self.periods:
            print(period)


class PeriodTechAvailability:
    def __init__(self, period, skus):
        self.period_number: int = period[0]
        self.period_text: str = period[1]
        self.skus: List[PeriodSKUAvailability] = skus

    def __str__(self):
        return "{} - {}".format(self.period_text, ", ".join([sku.__str__() for sku in self.skus]))


class PeriodSKUAvailability:
    def __init__(self, site_sku: SiteAssignment, reservations: List[TechnologyAssignment]):
        self.site_sku: SiteAssignment = site_sku
        self.reservations: List[TechnologyAssignment] = reservations

        used_count = 0
        for reservation in reservations:
            used_count += reservation.units

        self.free_count = site_sku.units - used_count

    def __str__(self):
        return "{} {} free ({} total)".format(self.site_sku.sku.shortname, self.free_count, self.site_sku.units)
