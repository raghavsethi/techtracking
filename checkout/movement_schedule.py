from collections import defaultdict, OrderedDict
from typing import Dict

from checkout.models import *

DEFAULT_STORAGE_LOCATION = "Site Director's Office"


class Movement:
    def __init__(self, site_sku: SiteSku, units: int, origin: Classroom, destination: Classroom):
        self.site_sku: SiteSku = site_sku
        self.units: int = units
        self.origin: Classroom = origin
        self.destination: Classroom = destination

    def __str__(self) -> str:
        return "From {} move {}x {} to {}".format(self.origin.name, self.units, self.site_sku.sku.display_name, self.destination.name)

    def __repr__(self):
        return self.__str__()

    def __lt__(self, other):
        return self.origin.name < other.origin.name and self.destination.name < other.destination.name and self.units < other.units


def order_candidates(reservation: Reservation, units_by_location: Dict[Classroom, int]):
    # First, consider items already at location
    destination = reservation.classroom
    candidates = []
    if destination in units_by_location:
        candidates.append((reservation.classroom, units_by_location[reservation.classroom]))

    # Then greedily select from the location with most items (not necessarily optimal)
    for origin, count in sorted(units_by_location.items(), key=lambda x: x[1], reverse=True):
        if origin != destination:
            candidates.append((origin, count))

    return candidates


class MovementSchedule:
    def __init__(self, site: Site, date: date):
        movements: Dict[Period, List[Movement]] = OrderedDict()
        for period in sorted(site.period_set.all()):
            movements[period] = []

        for site_sku in list(site.sitesku_set.all()):
            self.date: datetime.date = date
            self.periods: List[PeriodMovements] = []

            storage_location = site_sku.storage_location

            storage_location = Classroom(pk=0, site=site, code="DEF", name=storage_location)
            origin = storage_location

            # Assumption: All items can be picked up at the beginning of the day at the storage location
            units_by_location: Dict[Classroom, int] = {origin: site_sku.units}

            periods = sorted(site.period_set.all())
            for period in periods:
                postmove_units_by_location: Dict[Classroom, int] = defaultdict(int)
                reservations = list(Reservation.objects.filter(site_sku=site_sku, date=date, period=period).all())
                sorted_reservations = sorted(reservations, key=lambda x: x.units, reverse=True)

                for reservation in sorted_reservations:
                    remaining_units = reservation.units
                    while remaining_units > 0:
                        candidates = order_candidates(reservation, units_by_location)
                        for origin, available_count in candidates:
                            moved_units = min(remaining_units, available_count)

                            assert moved_units > 0
                            destination = reservation.classroom

                            if origin != destination:
                                movements[period].append(Movement(site_sku, moved_units, origin, destination))

                            postmove_units_by_location[destination] += moved_units
                            remaining_units -= moved_units

                            units_by_location[origin] -= moved_units
                            if units_by_location[origin] == 0:
                                del units_by_location[origin]

                            break

                # Send all unused SKUs back to storage location
                for location, count in list(units_by_location.items()):
                    if location != storage_location:
                        movements[period].append(Movement(site_sku, count, location, storage_location))
                        postmove_units_by_location[storage_location] = count
                        del units_by_location[location]

                # Update location mappings
                for destination, count in postmove_units_by_location.items():
                    if destination not in units_by_location:
                        units_by_location[destination] = 0

                    units_by_location[destination] += count

        for period in movements:
            self.periods.append(PeriodMovements(period, sorted(movements[period])))


class PeriodMovements:
    def __init__(self, period: Period, movements: List[Movement]):
        self.period: Period = period
        self.movements: List[Movement] = movements

    def __str__(self):
        return "{} - {}".format(self.period.number, ", ".join([movement.__str__() for movement in self.movements]))
