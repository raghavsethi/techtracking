import datetime

from collections import defaultdict
from typing import Dict

from checkout.models import *


class ReservationSchedule:
    def __init__(self, site: Site, schedule_date: datetime.date):
        self.date: datetime.date = schedule_date
        self.periods: List[PeriodInfo] = []

        site_inventory_list: List[SiteInventory] = list(site.siteinventory_set.all())
        periods: List[Period] = sorted(list(Period.objects.all()))
        assignments: List[Reservation] = \
            list(Reservation.objects.filter(site_inventory__site=site, date=self.date).all())

        grouped_inventory: Dict[TechnologyCategory, List[SiteInventory]] = defaultdict(list)
        grouped_inventory_totals: Dict[TechnologyCategory, int] = defaultdict(int)
        for inventory in site_inventory_list:
            grouped_inventory[inventory.inventory.type].append(inventory)
            grouped_inventory_totals[inventory.inventory.type] += inventory.units

        for period in periods:
            reservations = []
            period_grouped_inventory = grouped_inventory_totals.copy()
            for category in grouped_inventory.keys():
                for site_inventory in grouped_inventory[category]:
                    for assignment in assignments:
                        if assignment.period == period and assignment.site_inventory == site_inventory:
                            reservations.append(assignment)
                            period_grouped_inventory[category] -= assignment.units

            self.periods.append(PeriodInfo(period, period_grouped_inventory, reservations))

    def print(self):
        for period in self.periods:
            print(period)


class PeriodInfo:
    def __init__(self, period, free, reservations):
        self.period: Period = period
        self.free: Dict[TechnologyCategory, int] = dict(free)
        self.reservations: List[Reservation] = reservations

    def __str__(self):
        return "{} - Free ({}), Used ({})".format(self.period.number, self.free, self.reservations)
