import logging

from collections import defaultdict, OrderedDict
from typing import Dict

from checkout.models import *

DEFAULT_STORAGE_LOCATION = "Site Director's Office"
logger = logging.getLogger(__name__)


class Movement:
    def __init__(self, site_inventory: SiteInventory, units: int, origin: Classroom, destination: Classroom, comment: str = None):
        self.site_inventory: SiteInventory = site_inventory
        self.units: int = units
        self.origin: Classroom = origin
        self.destination: Classroom = destination
        self.comment: str = comment

    def __str__(self) -> str:
        return "From {} move {}x {} to {}".format(self.origin.name, self.units, self.site_inventory.inventory.display_name, self.destination.name)

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


def get_movement_periods() -> List[Period]:
    movement_periods = []
    last_normal_period_number = 0
    for period in sorted(list(Period.objects.all())):
        period.name = "Before " + period.name
        movement_periods.append(period)
        if period.number > last_normal_period_number:
            last_normal_period_number = period.number

    movement_periods.append(Period(pk=0, number=last_normal_period_number + 1, name="Cleanup"))
    return movement_periods


class MovementSchedule:
    def __init__(self, site: Site, date: date):
        self.date: datetime.date = date
        self.periods: List[PeriodMovements] = []
        movements: Dict[Period, List[Movement]] = OrderedDict()

        periods: List[Period] = get_movement_periods()
        for period in periods:
            movements[period] = []

        items = list(site.siteinventory_set.all())
        for item in items:
            storage_location = item.storage_location

            storage_location = Classroom(pk=0, site=site, code="DEF", name=storage_location)
            origin = storage_location

            # Assumption: All items can be picked up at the beginning of the day at the storage location
            units_by_location: Dict[Classroom, int] = {origin: item.units}

            for period in periods:
                postmove_units_by_location: Dict[Classroom, int] = defaultdict(int)
                reservations = list(Reservation.objects.filter(site_inventory=item, date=date, period=period).all())
                sorted_reservations = sorted(reservations, key=lambda x: x.units, reverse=True)

                for reservation in sorted_reservations:
                    remaining_units = reservation.units
                    while remaining_units > 0:
                        candidates = order_candidates(reservation, units_by_location)
                        if len(candidates) <= 0:
                            # Some reservations cannot be serviced (site inventory has reduced)
                            logger.warning("Cannot satisfy reservation %s (units required: %s, available: %s)",
                                           reservation, remaining_units, units_by_location)
                            break

                        for origin, available_count in candidates:
                            moved_units = min(remaining_units, available_count)

                            assert moved_units > 0
                            destination = reservation.classroom

                            if origin != destination:
                                movements[period].append(
                                    Movement(item, moved_units, origin, destination, reservation.comment))

                            postmove_units_by_location[destination] += moved_units
                            remaining_units -= moved_units

                            units_by_location[origin] -= moved_units
                            if units_by_location[origin] == 0:
                                del units_by_location[origin]

                            break

                # Send all unused items back to storage location
                for location, count in list(units_by_location.items()):
                    if location != storage_location:
                        movements[period].append(Movement(item, count, location, storage_location))
                    postmove_units_by_location[storage_location] += count

                # Update units_by_location
                units_by_location = {}
                for location, count in postmove_units_by_location.items():
                    if count > 0:
                        units_by_location[location] = count

        for period in movements:
            self.periods.append(PeriodMovements(period, sorted(movements[period])))


class PeriodMovements:
    def __init__(self, period: Period, movements: List[Movement]):
        self.period: Period = period
        self.movements: List[Movement] = movements

    def __str__(self):
        return "{} - {}".format(self.period.number, ", ".join([movement.__str__() for movement in self.movements]))
