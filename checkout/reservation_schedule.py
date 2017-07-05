import datetime

from checkout.models import *


class ReservationSchedule:
    def __init__(self, site: Site, date: datetime.date):
        self.date: datetime.date = date
        self.periods: List[PeriodTechAvailability] = []

        site_skus: List[SiteSku] = list(site.sitesku_set.all())
        periods: List[Period] = sorted(list(Period.objects.all()))
        assignments: List[Reservation] = \
            list(Reservation.objects.filter(site_sku__site=site, date=self.date).all())

        for period in periods:
            period_sku_availability = []
            for site_sku in site_skus:
                site_sku_reservations = []
                for assignment in assignments:
                    if assignment.period == period and assignment.site_sku == site_sku:
                        site_sku_reservations.append(assignment)

                period_sku_availability.append(PeriodSKUAvailability(site_sku, site_sku_reservations))

            self.periods.append(PeriodTechAvailability(period, period_sku_availability))

    def print(self):
        for period in self.periods:
            print(period)


class PeriodTechAvailability:
    def __init__(self, period, skus):
        self.period: Period = period
        self.skus: List[PeriodSKUAvailability] = skus

    def __str__(self):
        return "{} - {}".format(self.period.number, ", ".join([sku.__str__() for sku in self.skus]))


class PeriodSKUAvailability:
    def __init__(self, site_sku: SiteSku, reservations: List[Reservation]):
        self.site_sku: SiteSku = site_sku
        self.reservations: List[Reservation] = reservations

        used_count = 0
        for reservation in reservations:
            used_count += reservation.units

        self.free_count = site_sku.units - used_count

    def __str__(self):
        return "{} {} free ({} total)".format(self.site_sku.sku.shortname, self.free_count, self.site_sku.units)
