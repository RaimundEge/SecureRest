from django.urls import path

from . import views, tasks

urlpatterns = [
    path('', views.index, name='index'),
    path('member/<userid>', views.member, name='member'),
    path('register', views.register, name='register'),
    path('login', views.login, name='login'),
    path('list/<id>', views.list, name='list'),
    path('keys/<id>', views.keys, name='keys'),
    path('download/<id>/<name>', views.download, name='download'),
    path('delete/<path>/<id>/<name>', views.delete, name='delete'),
    path('upload', views.upload, name='upload'),
    path('process', tasks.process),
    path('crypt', tasks.crypt),
]