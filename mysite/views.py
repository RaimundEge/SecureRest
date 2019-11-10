from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from encrypt.models import Hello

def index(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    h = Hello(IP=ip)
    h.save()
    return HttpResponse("Welcome to rest-secure-ege backend")
