from typing import List
from datetime import datetime

from django.http import HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

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
        logger.error("No week objects found for site %s", site)
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

    logger.info("Resolved current week for %s to be %s", site, week_number)
    return week_schedule(request, week_number)


@login_required
def week_schedule(request, week_number):
    user: User = request.user
    site: Site = user.site

    logger.info("Processing week %s schedule for %s", week_number, site)

    # TODO: Show holidays grayed out in the UI
    try:
        week: Week = site.week_set.filter(week_number=week_number)[0]
    except IndexError:
        logger.warning("Received request for nonexistent week %s at site %s", week_number, site)
        return HttpResponseNotFound("Week %s was not found for %s" % (week_number, site.name))

    days_in_week: List[Day] = sorted(list(week.days.all()))

    schedule: List[DateSchedule] = []
    for day in days_in_week:
        schedule.append(DateSchedule(site, day.date))

    context = {
        "site": site,
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
        logger.warning("User %s is not part of any teams, creating new team..", user)
        new_team: Team = Team.objects.create(site=site_sku.site)
        new_team.team = [user]
        new_team.save()
        teams = [new_team]

    reservations: List[Reservation] = list(Reservation.objects.filter(
        site_sku=site_sku, date=request_date, period=period_number))
    used_units = 0
    for reservation in reservations:
        used_units += reservation.units

    context = {
        "site": site_sku.site,
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
    units = int(request.POST['request_units'])
    classroom: Classroom = Classroom.objects.get(pk=request.POST['classroom_pk'])

    logger.info("Creating new reservation: Team: %s, SKU: %s, Classroom: %s, Units: %s, Date: %s, Period %s",
                team, site_sku, classroom, units, request_date, period_number)

    Reservation.objects.create(
        team=team, site_sku=site_sku, classroom=classroom, units=units, date=request_date, period=period_number)

    return redirect('index')
