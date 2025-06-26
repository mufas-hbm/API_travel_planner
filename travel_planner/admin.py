from django.contrib import admin
from .models import CustomUser, Destination, TravelPlan, TravelPlanDestination,Activity, Comment
# Register your models here.
admin.site.register(CustomUser)
admin.site.register(Destination)
admin.site.register(TravelPlan)
admin.site.register(TravelPlanDestination)
admin.site.register(Activity)
admin.site.register(Comment)