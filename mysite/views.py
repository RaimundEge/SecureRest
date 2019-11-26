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
    return JsonResponse({"status": "This is the rest-secure-ege backend"})

def list(request):
    # get hello records
    hellos = Hello.objects.order_by('-timestamp')[:25]
    response = "<html><body><h3>List of recent Hello requests</h3><ul>"
    for h in hellos:
        response += "<li>" + str(h) + "</li>"
    response += "</ul></body></heml>"
    return HttpResponse(response)
