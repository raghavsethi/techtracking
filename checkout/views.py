import logging
from typing import Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction, IntegrityError
from django.http import HttpResponseNotFound, HttpResponseBadRequest, StreamingHttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from checkout.models import *
from checkout.movement_schedule import MovementSchedule, get_movement_periods
from checkout.reservation_schedule import ReservationSchedule
from techtracking.error_utils import error_redirect, success_redirect, require_http_post

logger = logging.getLogger(__name__)


@login_required
def index(request):
    user: User = request.user
    site: Site = user.site
    week: Week = resolve_week(user)

    if week is None:
        logger.error("[%s] No week objects found for site %s", user.email, site)

        if user.is_staff:
            messages.error(request, "Please add at least one week for site %s!" % site.name)
            return redirect('/admin/checkout/week/')

        return HttpResponseBadRequest("At least one week must be configured for site %s. Please contact your "
                                      "administrator." % site.name)

    return render_schedule(request, week)


def resolve_week(user: User):
    weeks: List[Week] = sorted(list(user.site.week_set.all()))

    if len(weeks) < 1:
        return None

    today = datetime.now().date()

    if today < weeks[0].start_date():
        return weeks[0]

    if today > weeks[-1].end_date():
        return weeks[-1]

    current_week: Week = weeks[0]

    for week in weeks:
        if week.start_date() <= today <= week.end_date():
            current_week = week
            break
        if today <= week.start_date():
            current_week = week
            break

    logger.info("[%s] Resolved current week for %s to be %s", user.email, user.site, current_week.week_number)
    return current_week


@login_required
def week_schedule(request, week_number):
    user: User = request.user
    site: Site = user.site

    week: Week = site.week_set.filter(week_number=week_number).first()
    if week is None:
        logger.warning("[%s] Received request for nonexistent week %s at site %s", user.email, week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    logger.info("[%s] Processing week %s schedule for %s", user.email, week, site)

    return render_schedule(request, week)


def render_schedule(request, week: Week):
    site: Site = request.user.site

    working_days = sorted(list(week.days()))

    schedule: List[ReservationSchedule] = []
    for day in working_days:
        schedule.append(ReservationSchedule(site, day))

    previous_week = (site.week_set.filter(week_number=week.week_number - 1).first(),)
    next_week = (site.week_set.filter(week_number=week.week_number + 1).first(),)

    if previous_week[0]:
        previous_week = (previous_week[0], reverse('schedule', args=[previous_week[0].week_number]))
    if next_week[0]:
        next_week = (next_week[0], reverse('schedule', args=[next_week[0].week_number]))

    context = {
        "sites": Site.objects.all(),
        "week": week,
        "previous_week": previous_week,
        "next_week": next_week,
        "calendar_days": week.calendar_days(),
        "periods": sorted(Period.objects.all()),
        "schedule": schedule,
    }

    return render(request, "checkout/week_reservations.html", context)


def get_available_inventory(site: Site, category: TechnologyCategory, request_date: date) -> \
        Dict[SiteInventory, Dict[Period, int]]:
    reservations: List[Reservation] = list(Reservation.objects.filter(
        site_inventory__inventory__type=category, site_inventory__site=site, date=request_date))
    category_inventory: List[SiteInventory] = list(site.siteinventory_set.filter(inventory__type=category))

    free_units: Dict[SiteInventory, Dict[Period, int]] = {}
    for inventory in category_inventory:
        free_units[inventory] = {}
        for period in sorted(Period.objects.all()):
            free_units[inventory][period] = inventory.units

    for existing_reservation in reservations:
        free_units[existing_reservation.site_inventory][existing_reservation.period] = max(0, free_units[
            existing_reservation.site_inventory][existing_reservation.period] - existing_reservation.units)

    return free_units


def pick_inventory(available: Dict[SiteInventory, Dict[Period, int]], selected_period: Period) -> SiteInventory:
    """
    Heuristic to pick the 'best' available inventory item. The 'best' item is the one most likely to
    satisfy the current request (keeping in mind that the requester may want to select several periods
    after the current one), and the one least likely to go 'out of stock' (i.e. the one with most
    availability) and prevent other users from reserving it.
    """

    best_item: SiteInventory = None
    best_avg_availability: int = 0
    for item, item_availability in available.items():
        availability_sum = 0.0
        availability_count = 0
        for period, available_count in item_availability.items():
            if period >= selected_period:
                availability_sum += available_count
                availability_count += 1

        item_avg_availability = availability_sum / availability_count
        if item_avg_availability > best_avg_availability and available[item][selected_period] > 0:
            best_avg_availability = item_avg_availability
            best_item = item

    return best_item


def render_reservation_request(request, request_date, selected_period, selected_item, item_inventory, category):
    user: User = request.user
    site: Site = user.site

    if user.is_staff:
        teams = Team.objects.filter(site=user.site)
    else:
        teams: List[Team] = Team.objects.filter(members__email=user.email).all()

    if len(teams) == 0:
        logger.warning("[%s] User is not part of any teams, creating new team..", user.email)
        new_team: Team = Team.objects.create(site=site, subject=Subject.objects.get(name=Subject.ACTIVITY_SUBJECT))
        new_team.members = [user]
        new_team.save()
        teams = [new_team]

    classrooms: List[Classroom] = list(Classroom.objects.filter(site=selected_item.site))
    if len(classrooms) == 0:
        return error_redirect(request, "No classrooms have been set up at {}. Please contact your site director or "
                                       "administrator".format(site.name))

    context = {
        "sites": Site.objects.all(),
        "selected_item": selected_item,
        "category_items": [item for item in site.siteinventory_set.filter(inventory__type=category) if
                           item != selected_item],
        "request_date": request_date,
        "teams": teams,
        "selected_period": selected_period,
        "free_units": item_inventory,
        "classrooms": classrooms,
        "purpose_list": UsagePurpose.objects.all(),
    }
    return render(request, "checkout/request.html", context)


@login_required
def reserve_request(request):
    user: User = request.user
    request_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
    selected_period: Period = get_object_or_404(Period, pk=request.GET.get('period'))

    item_inventory: Dict[Period, int] = None
    category: TechnologyCategory = None
    if 'site_inventory' in request.GET:
        selected_item = SiteInventory.objects.get(pk=request.GET['site_inventory'])
        category = selected_item.inventory.type
        item_inventory = get_available_inventory(user.site, selected_item.inventory.type, request_date)[selected_item]
    elif 'technology_category' in request.GET:
        category = TechnologyCategory.objects.get(pk=request.GET['technology_category'])
        category_inventory = get_available_inventory(user.site, category, request_date)
        selected_item = pick_inventory(category_inventory, selected_period)
        if not selected_item:
            logger.warning("No item could be selected for technology category %s in %s at site %s on date %s", category,
                           selected_period, user.site, request_date)
            logger.warning("Available: %s", category_inventory)
            return error_redirect(request, "This type of item is no longer available, please try again.")

        item_inventory = category_inventory[selected_item]
    else:
        return error_redirect(request, "Reservation request must contain site inventory or category")

    return render_reservation_request(request, request_date, selected_period, selected_item, item_inventory, category)


@login_required
@transaction.atomic
@require_http_post
def reserve(request):
    user: User = request.user
    request_date = datetime.strptime(request.POST['request_date'], '%Y-%m-%d').date()
    site_inventory: SiteInventory = get_object_or_404(SiteInventory, pk=request.POST['site_inventory'])
    team: Team = get_object_or_404(Team, pk=request.POST['team'])
    purpose: UsagePurpose = get_object_or_404(UsagePurpose, pk=request.POST['purpose'])
    collaborative: bool = 'collaborative' in request.POST

    selected_periods = []
    for period in sorted(Period.objects.all()):
        checkbox_id = 'period_' + str(period.id)

        if checkbox_id in request.POST:
            selected_periods.append(period)

    try:
        requested_units = int(request.POST['request_units'])
    except ValueError:
        return error_redirect(request, "Requested units must be set to a valid number")

    comment = request.POST['comment']
    classroom: Classroom = Classroom.objects.get(pk=request.POST['classroom'])

    if requested_units < 1:
        return error_redirect(request,
                              "You must request at least 1 unit of {}".format(site_inventory.inventory.display_name))

    # First, validate all the reservations
    for period in selected_periods:
        existing_reservations: List[Reservation] = list(Reservation.objects.filter(
            site_inventory=site_inventory, date=request_date, period=period))
        used_units = 0
        for existing_reservation in existing_reservations:
            used_units += existing_reservation.units
        free_units = site_inventory.units - used_units

        if requested_units > free_units:
            return error_redirect(request, "Cannot reserve {} units of {} in {}, only {} are available".format(
                requested_units, site_inventory.inventory.display_name, period.name, free_units))

    # Then, create them all. This works because this entire handler is atomic.
    reserved_periods: List[str] = []
    for period in selected_periods:
        logger.info("[%s] Creating reservation: Team: %s, Inventory: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                    request.user.email, team, site_inventory, classroom, requested_units, request_date, period)

        try:
            Reservation.objects.create(
                team=team,
                site_inventory=site_inventory,
                classroom=classroom,
                units=requested_units,
                date=request_date,
                period=period,
                purpose=purpose,
                collaborative=collaborative,
                creator=user,
                comment=comment)
        except IntegrityError:
            return error_redirect(request, "Failed to make reservation - another reservation by this team for {} "
                                           "in {} during {} already exists. Please delete the existing reservation and "
                                           "try again".format(site_inventory.inventory.display_name, classroom.name,
                                                              period.name))

        reserved_periods.append(period.name)

    messages.success(request, "Reservation confirmed for {} unit(s) of {} in {}".format(
        requested_units, site_inventory.inventory.display_name, ", ".join(reserved_periods)))

    # Figure out which week this was in
    weeks: List[Week] = sorted(list(request.user.site.week_set.all()))
    for week in weeks:
        if week.start_date() <= request_date <= week.end_date():
            return redirect('schedule', week.week_number)

    return redirect('index')


@login_required
def reservations(request):
    user: User = request.user

    teams: List[Team] = Team.objects.filter(members__email=user.email).all()
    past_reservations: List[Reservation] = []
    future_reservations: List[Reservation] = []

    for team in teams:
        for reservation in Reservation.objects.filter(team=team):
            if reservation.date < datetime.now().date():
                past_reservations.append(reservation)
            else:
                future_reservations.append(reservation)

    context = {
        "sites": Site.objects.all(),
        "user": user,
        "past_reservations": sorted(past_reservations),
        "future_reservations": sorted(future_reservations)
    }

    return render(request, "checkout/reservations.html", context)


@login_required
def movements(request):
    user: User = request.user

    week: Week = resolve_week(user)
    return render_movements(request, week)


@login_required
def week_movements(request, week_number):
    user: User = request.user
    site: Site = user.site

    week: Week = site.week_set.filter(week_number=week_number).first()
    if week is None:
        logger.warning("[%s] Received request for nonexistent week %s at site %s", user.email, week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    logger.info("[%s] Processing week %s movements for %s", user.email, week, site)

    return render_movements(request, week)


@login_required
def render_movements(request, week: Week):
    user: User = request.user
    site: Site = user.site

    if week is None:
        logger.error("[%s] No week objects found for site %s", user.email, site)

        if user.is_staff:
            messages.error(request, "Please add at least one week for site %s!" % site.name)
            return redirect('/admin/checkout/week/')

        return HttpResponseBadRequest("At least one week must be configured for site %s. Please contact your "
                                      "administrator." % site.name)

    schedule: List[MovementSchedule] = []
    working_days = sorted(list(week.days()))

    for day in working_days:
        schedule.append(MovementSchedule(site, day))

    previous_week = (site.week_set.filter(week_number=week.week_number - 1).first(),)
    next_week = (site.week_set.filter(week_number=week.week_number + 1).first(),)

    if previous_week[0]:
        previous_week = (previous_week[0], reverse('movements', args=[previous_week[0].week_number]))
    if next_week[0]:
        next_week = (next_week[0], reverse('movements', args=[next_week[0].week_number]))

    context = {
        "sites": Site.objects.all(),
        "week": week,
        "previous_week": previous_week,
        "next_week": next_week,
        "calendar_days": week.calendar_days(),
        "periods": get_movement_periods(),
        "schedule": schedule,
    }

    return render(request, "checkout/week_movements.html", context)


@login_required
@require_http_post
def delete(request):
    reservation: Reservation = get_object_or_404(Reservation, pk=request.POST['reservation_pk'])

    if not (request.user in reservation.team.members.all() or request.user.is_staff):
        return error_redirect(request,
                              "You must be an administrator or a member of the team that made the reservation to "
                              "delete it")

    reservation.delete()
    logger.info("[%s] Reservation deleted: Team: %s, Inventory: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                request.user.email,
                reservation.team,
                reservation.site_inventory,
                reservation.classroom,
                reservation.units,
                reservation.date,
                reservation.period)

    inventory_name: str = reservation.site_inventory.inventory.display_name
    return success_redirect(request,
                            "Deleted reservation for {} unit(s) of {}".format(reservation.units, inventory_name),
                            "/reservations")


@user_passes_test(lambda u: u.is_superuser)
def export(request):
    def generate_csv_output():
        yield ','.join([
            'Site', 'User', 'Teaching Team', 'Subject', 'Classroom', 'Date', 'Week', 'Period', 'Units', 'Type', 'SKU',
            'Purpose', 'Collaborative', 'Total Teams at Site']) + '\n'

        # Cache for performance, otherwise server timeouts can happen
        site_teams: Dict[Site, int] = {}
        site_weeks: Dict[Site, List[Week]] = {}
        team_members: Dict[Team, List[User]] = {}
        siteinventory_inventory: Dict[SiteInventory, InventoryItem] = {}

        for reservation in Reservation.objects.all():
            site: Site = reservation.site_inventory.site

            if site not in site_weeks:
                site_weeks[site] = site.week_set.all()
            if site not in site_teams:
                site_teams[site] = len(site.team_set.all())
            if reservation.team not in team_members:
                team_members[reservation.team] = reservation.team.members.all()
            if reservation.site_inventory not in siteinventory_inventory:
                siteinventory_inventory[reservation.site_inventory] = reservation.site_inventory.inventory

            weeks: List[Week] = site_weeks[site]
            week_number = 0
            for week in weeks:
                if reservation.date in week.days():
                    week_number = week.week_number

            yield ','.join([str(cell) for cell in [
                site.name,
                reservation.creator.name + " (" + reservation.creator.email + ")",
                ", ".join([member.name for member in team_members[reservation.team]]),
                reservation.team.subject.name,
                reservation.classroom.name,
                reservation.date,
                week_number,
                reservation.period.number,
                reservation.units,
                siteinventory_inventory[reservation.site_inventory].type.name,
                siteinventory_inventory[reservation.site_inventory].display_name,
                reservation.purpose.purpose if reservation.purpose else UsagePurpose.OTHER_PURPOSE,
                1 if reservation.collaborative else 0,
                site_teams[site]
            ]]) + '\n'

    return StreamingHttpResponse(generate_csv_output(), status=200, content_type='text/csv')


@user_passes_test(lambda u: u.is_superuser)
@require_http_post
def change_site(request):
    user: User = request.user
    site: Site = get_object_or_404(Site, pk=request.POST['site_pk'])

    user.site = site
    user.save()

    return success_redirect(request, "Changed site to {}".format(site.name))
