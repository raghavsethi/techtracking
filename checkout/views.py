from typing import List

from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from checkout.models import TechnologyAssignment, Week, Day, Site, User
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
        "days": days_in_week,
        "periods": TechnologyAssignment.PERIODS,
        "username": user.email,
        "full_name": user.full_name,
        "week_schedule": week_schedule,
    }

    return render(request, "checkout/index.html", context)
