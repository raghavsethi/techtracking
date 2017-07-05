from typing import List, Dict, Tuple
from datetime import datetime

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import HttpResponseNotFound, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse

from checkout.models import Reservation, Week, Day, Site, User, SiteSku, Team, Classroom, Period, Subject
from checkout.date_schedule import DateSchedule
from checkout.utils import error_redirect, success_redirect

import logging
logger = logging.getLogger(__name__)


@staff_member_required
def admin(request):
    if request.user.is_superuser:
        return redirect(reverse('superuser_admin:index'))

    return redirect(reverse('staff_admin:index'))


@login_required
def index(request):
    user: User = request.user
    site: Site = user.site

    weeks: List[Week] = sorted(list(site.week_set.all()))

    if len(weeks) < 1:
        logger.error("[%s] No week objects found for site %s", user.email, site)
        return HttpResponseBadRequest("At least one week must be configured for site %s" % site.name)

    week_number = weeks[0].week_number
    today = datetime.now().date()

    # TODO: Test this logic
    for week in weeks:
        if week.start_date() <= today <= week.end_date():
            week_number = week.week_number
            break
        if today <= week.start_date():
            week_number = week.week_number

    logger.info("[%s] Resolved current week for %s to be %s", user.email, site, week_number)
    week: Week = site.week_set.filter(week_number=week_number).first()

    return render_schedule(request, site, week)


@login_required
def week_schedule(request, week_number):
    user: User = request.user
    site: Site = user.site

    week: Week = site.week_set.filter(week_number=week_number).first()
    if week is None:
        logger.warning("[%s] Received request for nonexistent week %s at site %s", user.email, week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    logger.info("[%s] Processing week %s schedule for %s", user.email, week, site)

    return render_schedule(request, site, week)


def site_schedule(request, site_id):
    site: Site = get_object_or_404(Site, pk=site_id)
    weeks: List[Week] = sorted(list(site.week_set.all()))

    if len(weeks) < 1:
        logger.error("[logged-out] No week objects found for site %s", site)
        return HttpResponseBadRequest("At least one week must be configured for site %s. Please contact your "
                                      "administrator" % site.name)

    week_number = weeks[0].week_number
    today = datetime.now().date()

    # TODO: Test this logic
    for week in weeks:
        if week.start_date() <= today <= week.end_date():
            week_number = week.week_number
            break
        if today <= week.start_date():
            week_number = week.week_number

    logger.info("[logged-out] Resolved current week for %s to be %s", site, week_number)
    week: Week = site.week_set.filter(week_number=week_number).first()

    return render_schedule(request, site, week)


def site_week_schedule(request, site_id, week_number: int):
    site: Site = get_object_or_404(Site, pk=site_id)

    week: Week = site.week_set.filter(week_number=week_number).first()
    if week is None:
        logger.warning("[logged-out] Received request for nonexistent week %s at site %s", week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    logger.info("[logged-out] Processing week %s schedule for %s", week_number, site)

    return render_schedule(request, site, week)


def render_schedule(request, site: Site, week: Week):
    days_in_week: List[Day] = sorted(list(week.days.all()))

    schedule: List[DateSchedule] = []
    for day in days_in_week:
        schedule.append(DateSchedule(site, day.date))

    previous_week: Week = site.week_set.filter(week_number=week.week_number - 1).first()
    next_week: Week = site.week_set.filter(week_number=week.week_number + 1).first()

    context = {
        "aimhigh_site": site,
        "week": week,
        "previous_week": previous_week,
        "next_week": next_week,
        "calendar_days": days_in_week,  # TODO: make this all calendar days in week
        "periods": sorted(site.period_set.all()),
        "schedule": schedule,
    }

    return render(request, "checkout/week.html", context)


@login_required
def reserve_request(request):
    user: User = request.user
    request_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
    selected_period: Period = get_object_or_404(Period, pk=request.GET.get('period'))
    site_sku: SiteSku = get_object_or_404(SiteSku, pk=request.GET.get('site_assignment'))

    if user.is_staff:
        teams = Team.objects.filter(site=user.site)
    else:
        teams: List[Team] = Team.objects.filter(team__email=user.email).all()

    if len(teams) == 0:
        logger.warning("[%s] User is not part of any teams, creating new team..", user.email)
        new_team: Team = Team.objects.create(
            site=site_sku.site,
            subject=Subject.objects.get(name=Subject.ACTIVITY_SUBJECT))

        new_team.members = [user]
        new_team.save()
        teams = [new_team]

    existing_reservations: List[Reservation] = list(Reservation.objects.filter(
        site_sku=site_sku, date=request_date))

    used_units: Dict[int, int] = {}
    for period in sorted(user.site.period_set.all()):
        used_units[period] = 0

    for existing_reservation in existing_reservations:
        used_units[existing_reservation.period] += existing_reservation.units

    free_units: Dict[Tuple[int, str], int] = {}
    for period, used in used_units.items():
        free_units[period] = site_sku.units - used

    context = {
        "aimhigh_site": site_sku.site,
        "site_sku": site_sku,
        "request_date": request_date,
        "teams": teams,
        "selected_period": selected_period,
        "free_units": free_units,
        "classrooms": Classroom.objects.filter(site=site_sku.site)
    }

    return render(request, "checkout/request.html", context)


@login_required
@transaction.atomic
def reserve(request):
    user: User = request.user
    request_date = datetime.strptime(request.POST['request_date'], '%Y-%m-%d').date()
    site_sku: SiteSku = get_object_or_404(SiteSku, pk=request.POST['site_assignment_pk'])
    team: Team = get_object_or_404(Team, pk=request.POST['team_pk'])

    selected_periods = []
    for period in sorted(user.site.period_set.all()):
        checkbox_id = 'period_' + str(period.id)

        if checkbox_id in request.POST:
            selected_periods.append(period)

    try:
        requested_units = int(request.POST['request_units'])
    except ValueError:
        return error_redirect(request, "Requested units must be set to a valid number")

    comment = request.POST['comment']
    classroom: Classroom = Classroom.objects.get(pk=request.POST['classroom_pk'])

    if requested_units < 1:
        return error_redirect(request, "You must request at least 1 unit of {}".format(site_sku.sku.display_name))

    # First, validate all the reservations
    for period in selected_periods:
        existing_reservations: List[Reservation] = list(Reservation.objects.filter(
            site_sku=site_sku, date=request_date, period=period))
        used_units = 0
        for existing_reservation in existing_reservations:
            used_units += existing_reservation.units
        free_units = site_sku.units - used_units

        if requested_units > free_units:
            return error_redirect(request, "Cannot reserve {} units of {} in {}, only {} are available".format(
                requested_units, site_sku.sku.display_name, period.name, free_units))

    # Then, create them all. This works because this entire handler is atomic.
    reserved_periods: List[str] = []
    for period in selected_periods:
        logger.info("[%s] Creating new reservation: Team: %s, SKU: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                    request.user.email, team, site_sku, classroom, requested_units, request_date, period)

        Reservation.objects.create(
            team=team,
            site_sku=site_sku,
            classroom=classroom,
            units=requested_units,
            date=request_date,
            period=period,
            comment=comment)

        reserved_periods.append(period.name)

    messages.success(request, "Reservation confirmed for {} unit(s) of {} in {}".format(
        requested_units, site_sku.sku.display_name, ", ".join(reserved_periods)))

    # Figure out which week this was in
    weeks: List[Week] = sorted(list(request.user.site.week_set.all()))
    for week in weeks:
        if week.start_date() <= request_date <= week.end_date():
            return redirect('week_schedule', week.week_number)

    return redirect('index')


@login_required
def reservations(request):
    user: User = request.user

    teams: List[Team] = Team.objects.filter(team__email=user.email).all()
    user_reservations: List[Reservation] = []

    for team in teams:
        user_reservations.extend(Reservation.objects.filter(team=team))

    context = {
        "aimhigh_site": user.site,
        "user": user,
        "reservations": sorted(user_reservations)
    }

    return render(request, "checkout/reservations.html", context)


@login_required
def delete(request):
    reservation: Reservation = get_object_or_404(Reservation, pk=request.POST['reservation_pk'])

    if not (request.user in reservation.team.members.all() or request.user.is_staff):
        return error_redirect(request,
                              "You must be an administrator or a member of the team that made the reservation to "
                              "delete it")

    reservation.delete()
    logger.info("[%s] Reservation deleted: Team: %s, SKU: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                request.user.email,
                reservation.team,
                reservation.site_sku,
                reservation.classroom,
                reservation.units,
                reservation.date,
                reservation.period)

    return success_redirect(request,
                            "Deleted reservation for {} unit(s) of {}".format(reservation.units,
                                                                              reservation.site_sku.sku.display_name),
                            "/reservations")
