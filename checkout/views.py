from typing import List

from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from checkout.models import TechnologyAssignment, Week, Day
from checkout.date_schedule import DateSchedule


@login_required
def index(request):
    """
    Shows the assignments in the current week.
    """
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    user = request.user
    site = user.site

    # TODO: Do week math
    weeks: List[Week] = list(site.week_set.all())
    week: Week = weeks[0]

    # TODO: Figure out sorting
    week_schedule: List[DateSchedule] = []
    days_in_week: List[Day] = list(week.days.all())
    for day in days_in_week:
        week_schedule.append(DateSchedule(site, day.date))

    context = {
        "site": site,
        "week": week,
        "days": days_in_week,
        "periods": TechnologyAssignment.PERIODS,
        "username": user.email,
        "full_name": user.full_name,
        "week_schedule": week_schedule,
    }

    return render(request, "checkout/index.html", context)
