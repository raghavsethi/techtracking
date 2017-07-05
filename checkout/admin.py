from django.contrib import admin

from .models import SKU, Site, SiteAssignment, Classroom, TeachingTeam, TechnologyAssignment, User, Day, Week

admin.site.register(SKU)
admin.site.register(Site)
admin.site.register(SiteAssignment)
admin.site.register(Classroom)
admin.site.register(TeachingTeam)
admin.site.register(TechnologyAssignment)
admin.site.register(Day)
admin.site.register(Week)
admin.site.register(User)
