from typing import List
from datetime import datetime

from django.http import HttpResponseForbidden
from django.shortcuts import render
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

    # TODO: Do week math
    # TODO: Show off days grayed out in the UI
    weeks: List[Week] = sorted(list(site.week_set.all()))
    week: Week = weeks[0]

    days_in_week: List[Day] = sorted(list(week.days.all()))

    week_schedule: List[DateSchedule] = []
    for day in days_in_week:
        week_schedule.append(DateSchedule(site, day.date))

    context = {
        "site": site,
        "week": week,
        "calendar_days": days_in_week,  # TODO: make this all calendar days in week
        "periods": TechnologyAssignment.PERIODS,
        "username": user.email,
        "full_name": user.full_name,
        "week_schedule": week_schedule,
    }

    return render(request, "checkout/index.html", context)


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

    return index(request)
