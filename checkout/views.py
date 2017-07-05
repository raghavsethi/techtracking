from typing import List
from datetime import datetime

from django.http import HttpResponseForbidden, HttpResponseServerError, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from checkout.models import TechnologyAssignment, Week, Day, Site, User, SiteAssignment, TeachingTeam, Classroom
from checkout.date_schedule import DateSchedule


@login_required
def index(request):
    """
    Shows the assignments in the current week.
    """
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    user: User = request.user
    site: Site = user.site

    weeks: List[Week] = sorted(list(site.week_set.all()))
    current_week = weeks[0].week_number
    today = datetime.now().date()

    # TODO: Test this logic
    for week in weeks:
        if week.start_date <= today <= week.end_date:
            current_week = week.week_number
            break
        if today <= week.start_date:
            current_week = week.week_number

    if current_week is None:
        return HttpResponseServerError("current_week cannot be None")

    return week_schedule(request, current_week)


@login_required
def week_schedule(request, week_number):
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    user: User = request.user
    site: Site = user.site

    # TODO: Show off days grayed out in the UI
    # TODO: Make this compound key?
    try:
        week: Week = site.week_set.filter(week_number=week_number)[0]
    except IndexError:
        return HttpResponseNotFound()

    days_in_week: List[Day] = sorted(list(week.days.all()))

    week_schedule: List[DateSchedule] = []
    for day in days_in_week:
        week_schedule.append(DateSchedule(site, day.date))

    context = {
        "site": site,
        "week": week,
        "previous_week": None if week.week_number < 2 else (week.week_number - 1),
        "next_week": None if week.week_number > Week.NUM_WEEKS - 2 else (week.week_number + 1),
        "calendar_days": days_in_week,  # TODO: make this all calendar days in week
        "periods": TechnologyAssignment.PERIODS,
        "username": user.email,
        "full_name": user.full_name,
        "week_schedule": week_schedule,
    }

    return render(request, "checkout/week.html", context)


@login_required
def reserve_request(request):
    user: User = request.user
    site_assignment_pk = int(request.GET.get('site_assignment'))
    request_date = datetime.strptime(request.GET.get('date'), '%Y-%m-%d').date()
    period_number = int(request.GET.get('period'))
    site_assignment: SiteAssignment = SiteAssignment.objects.get(pk=site_assignment_pk)
    teams = TeachingTeam.objects.filter(team__email=user.email)

    reservations: List[TechnologyAssignment] = list(TechnologyAssignment.objects.filter(
        technology=site_assignment, date=request_date, period=period_number))
    used_units = 0
    for reservation in reservations:
        used_units += reservation.units

    context = {
        "site": site_assignment.site,
        "site_assignment": site_assignment,
        "request_date": request_date,
        "teams": teams,
        "period": TechnologyAssignment.PERIODS[period_number - 1],
        "free_units": site_assignment.units - used_units,
        "classrooms": Classroom.objects.filter(site=site_assignment.site)
    }

    return render(request, "checkout/request.html", context)


@login_required
def reserve(request):
    site_assignment_pk = int(request.POST['site_assignment_pk'])
    request_date = datetime.strptime(request.POST['request_date'], '%Y-%m-%d').date()
    site_assignment: SiteAssignment = SiteAssignment.objects.get(pk=site_assignment_pk)
    period_number = int(request.POST['period'])
    units = int(request.POST['request_units'])
    team: TeachingTeam = TeachingTeam.objects.get(pk=request.POST['team_pk'])
    classroom: Classroom = Classroom.objects.get(pk=request.POST['classroom_pk'])

    assignment = TechnologyAssignment(site=site_assignment.site, teachers=team, technology=site_assignment, classroom=classroom, units=units, date=request_date, period=period_number)
    assignment.save()

    return redirect('index')
