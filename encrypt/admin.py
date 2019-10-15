from django.contrib import admin

from .models import Member, Prospect, KeyData, History

admin.site.register(Member)
admin.site.register(Prospect)
admin.site.register(KeyData)
admin.site.register(History)
