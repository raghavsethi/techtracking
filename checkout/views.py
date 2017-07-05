from typing import List
from datetime import datetime

from django.http import HttpResponseNotFound, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from checkout.models import Reservation, Week, Day, Site, User, SiteSku, Team, Classroom
from checkout.date_schedule import DateSchedule

import logging
logger = logging.getLogger(__name__)


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
        if week.start_date <= today <= week.end_date:
            week_number = week.week_number
            break
        if today <= week.start_date:
            week_number = week.week_number

    logger.info("[%s] Resolved current week for %s to be %s", user.email, site, week_number)
    return week_schedule(request, week_number)


def site_schedule(request, site_id):
    site: Site = get_object_or_404(Site, pk=site_id)
    weeks: List[Week] = sorted(list(site.week_set.all()))

    if len(weeks) < 1:
        logger.error("[logged-out] No week objects found for site %s", site)
        return HttpResponseBadRequest("At least one week must be configured for site %s" % site.name)

    week_number = weeks[0].week_number
    today = datetime.now().date()

    # TODO: Test this logic
    for week in weeks:
        if week.start_date <= today <= week.end_date:
            week_number = week.week_number
            break
        if today <= week.start_date:
            week_number = week.week_number

    logger.info("[logged-out] Resolved current week for %s to be %s", site, week_number)

    return site_week_schedule(request, site_id, week_number)


def site_week_schedule(request, site_id, week_number):
    site: Site = get_object_or_404(Site, pk=site_id)

    try:
        week: Week = site.week_set.filter(week_number=week_number)[0]
    except IndexError:
        logger.warning("[logged-out] Received request for nonexistent week %s at site %s", week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    logger.info("[logged-out] Processing week %s schedule for %s", week_number, site)

    days_in_week: List[Day] = sorted(list(week.days.all()))

    schedule: List[DateSchedule] = []
    for day in days_in_week:
        schedule.append(DateSchedule(site, day.date))

    context = {
        "aimhigh_site": site,
        "week": week,
        "previous_week": None if week.week_number < 2 else (week.week_number - 1),
        "next_week": None if week.week_number > Week.NUM_WEEKS - 1 else (week.week_number + 1),
        "calendar_days": days_in_week,  # TODO: make this all calendar days in week
        "periods": Reservation.PERIODS,
        "schedule": schedule,
    }

    return render(request, "checkout/week.html", context)


@login_required
def week_schedule(request, week_number):
    user: User = request.user
    site: Site = user.site

    logger.info("[%s] Processing week %s schedule for %s", user.email, week_number, site)

    # TODO: Show holidays grayed out in the UI
    try:
        week: Week = site.week_set.filter(week_number=week_number)[0]
    except IndexError:
        logger.warning("[%s] Received request for nonexistent week %s at site %s", user.email, week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    days_in_week: List[Day] = sorted(list(week.days.all()))

    schedule: List[DateSchedule] = []
    for day in days_in_week:
        schedule.append(DateSchedule(site, day.date))

    context = {
        "aimhigh_site": site,
        "week": week,
        "previous_week": None if week.week_number < 2 else (week.week_number - 1),
        "next_week": None if week.week_number > Week.NUM_WEEKS - 1 else (week.week_number + 1),
        "calendar_days": days_in_week,  # TODO: make this all calendar days in week
        "periods": Reservation.PERIODS,
        "user": user,
        "schedule": schedule,
    }

    return render(request, "checkout/week.html", context)


@login_required
def reserve_request(request):
    user: User = request.user
    request_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
    period_number = int(request.GET.get('period'))
    site_sku: SiteSku = get_object_or_404(SiteSku, pk=request.GET.get('site_assignment'))
    teams: List[Team] = Team.objects.filter(team__email=user.email).all()

    if len(teams) == 0:
        logger.warning("[%s] User is not part of any teams, creating new team..", user.email)
        new_team: Team = Team.objects.create(site=site_sku.site)
        new_team.team = [user]
        new_team.save()
        teams = [new_team]

    existing_reservations: List[Reservation] = list(Reservation.objects.filter(
        site_sku=site_sku, date=request_date, period=period_number))
    used_units = 0
    for existing_reservation in existing_reservations:
        used_units += existing_reservation.units

    context = {
        "aimhigh_site": site_sku.site,
        "site_sku": site_sku,
        "request_date": request_date,
        "teams": teams,
        "period": Reservation.PERIODS[period_number - 1],
        "free_units": site_sku.units - used_units,
        "classrooms": Classroom.objects.filter(site=site_sku.site)
    }

    return render(request, "checkout/request.html", context)


@login_required
def reserve(request):
    request_date = datetime.strptime(request.POST['request_date'], '%Y-%m-%d').date()
    site_sku: SiteSku = get_object_or_404(SiteSku, pk=request.POST['site_assignment_pk'])
    team: Team = get_object_or_404(Team, pk=request.POST['team_pk'])

    period_number = int(request.POST['period'])
    requested_units = int(request.POST['request_units'])
    comment = request.POST['comment']
    classroom: Classroom = Classroom.objects.get(pk=request.POST['classroom_pk'])

    existing_reservations: List[Reservation] = list(Reservation.objects.filter(
        site_sku=site_sku, date=request_date, period=period_number))
    used_units = 0
    for existing_reservation in existing_reservations:
        used_units += existing_reservation.units
    free_units = site_sku.units - used_units

    if requested_units > free_units:
        messages.error(request, "Cannot reserve {} units of {} in this period, only {} are available".format(
            requested_units, site_sku.sku.display_name, free_units))
        return redirect('index')

    if requested_units < 1:
        messages.error(request, "You must request at least 1 unit of {}".format(site_sku.sku.display_name))
        return redirect('index')

    logger.info("[%s] Creating new reservation: Team: %s, SKU: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                request.user.email, team, site_sku, classroom, requested_units, request_date, period_number)

    Reservation.objects.create(
        team=team, site_sku=site_sku, classroom=classroom, units=requested_units, date=request_date, period=period_number, comment=comment)

    messages.success(request, "Reservation confirmed for {} unit(s) of {}".format(requested_units, site_sku.sku.display_name))

    # Figure out which week this was in
    weeks: List[Week] = sorted(list(request.user.site.week_set.all()))
    for week in weeks:
        if week.start_date <= request_date <= week.end_date:
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
        "reservations": sorted(user_reservations),
        "period_mapping": Reservation.PERIODS,
    }

    return render(request, "checkout/reservations.html", context)


@login_required
def delete(request):
    reservation: Reservation = get_object_or_404(Reservation, pk=request.POST['reservation_pk'])

    if request.user in reservation.team.team.all() or request.user.is_staff:
        reservation.delete()
        logger.info("[%s] Reservation deleted: Team: %s, SKU: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                    request.user.email,
                    reservation.team,
                    reservation.site_sku,
                    reservation.classroom,
                    reservation.units,
                    reservation.date,
                    reservation.period)
        messages.success(request, "Reservation for {} unit(s) of {} was deleted".format(reservation.units,
                                                                                        reservation.site_sku.sku.display_name))
    else:
        messages.error(request, "You must be an administrator or a member of the team that made the reservation to "
                                "delete it")

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/reservations'))
