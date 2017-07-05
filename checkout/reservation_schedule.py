import datetime

from checkout.models import *


class ReservationSchedule:
    def __init__(self, site: Site, date: datetime.date):
        self.date: datetime.date = date
        self.periods: List[PeriodTechAvailability] = []

        site_inventory_list: List[SiteInventory] = list(site.siteinventory_set.all())
        periods: List[Period] = sorted(list(Period.objects.all()))
        assignments: List[Reservation] = \
            list(Reservation.objects.filter(site_inventory__site=site, date=self.date).all())

        for period in periods:
            period_availability = []
            for site_inventory in site_inventory_list:
                reservations = []
                for assignment in assignments:
                    if assignment.period == period and assignment.site_inventory == site_inventory:
                        reservations.append(assignment)

                period_availability.append(PeriodItemAvailability(site_inventory, reservations))

            self.periods.append(PeriodTechAvailability(period, period_availability))

    def print(self):
        for period in self.periods:
            print(period)


class PeriodTechAvailability:
    def __init__(self, period, items):
        self.period: Period = period
        self.items: List[PeriodItemAvailability] = items

    def __str__(self):
        return "{} - {}".format(self.period.number, ", ".join([item.__str__() for item in self.items]))


class PeriodItemAvailability:
    def __init__(self, site_inventory: SiteInventory, reservations: List[Reservation]):
        self.site_inventory: SiteInventory = site_inventory
        self.reservations: List[Reservation] = reservations

        used_count = 0
        for reservation in reservations:
            used_count += reservation.units

        self.free_count = site_inventory.units - used_count

    def __str__(self):
        return "{} {} free ({} total)".format(
            self.site_inventory.inventory.model_identifier, self.free_count, self.site_inventory.units)
