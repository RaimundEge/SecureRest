from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from random import randint
from django.core.mail import send_mail
import json, time, mimetypes
from os.path import join
from os import makedirs
from .models import Member, Prospect, KeyData, History
from django.http import HttpResponse
from django.contrib.auth.hashers import check_password, make_password
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import logging
logger = logging.getLogger(__name__)


def index(request):
    return HttpResponse("Hello, world. You're at the encrypt index.")

def member(request, userid):
    d = {'userid': userid}
    try:
        m = Member.objects.get(userid=userid)
        d = m.toJSON()
    except ObjectDoesNotExist:
        d['status'] = 'User not found'
    logger.info(userid)
    return JsonResponse(d)

def register(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        logger.info(data)
        # delete all previous Prospect entries
        Prospect.objects.filter(userid=data['userName']).delete()
        # generate 6 digit random code
        code = ''
        for i in range(0,6):
            code += str(randint(0,9))
        # create new Prospect record
        hash = make_password(data['password'])
        p = Prospect(userid=data['userName'], password=hash, email=data['email'], code=code)
        p.save()
        print('need to send email to: ' + data['email'])
        htmlMsg = "Dear " + data['userName'] + "!<p>Welcome as new member of SimplySecure.<p>Click here to activate your membership: <a href='" + data['addr'] + "/activate/" + code + "'>Activation Link</a><p> Regards, <br>&nbsp;&nbsp;SimpleSecure Admin";
        plainMsg = "Dear " + data['userName'] + "\n\nWelcome as new member of SimplySecure.\nCopy this link into your webbrowser to activate your membership: \n\n    " + data['addr'] + "/activate/" + code + "\n\nRegards, \n    SimpleSecure Admin";

        send_mail(
            'Greetings from SimplySecure',
            plainMsg,
            'secure@ege.com',
            [data['email']],
            html_message=htmlMsg,
            fail_silently=False,
        )
        d = {'message': 'Success: Verification email sent to: ' + data['email'] + '\ncheck your email and click on the link within for validation'}
        return JsonResponse(d)

    return JsonResponse({'message': 'no registration performed'})

def login(request):
    if request.method == 'GET':
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        code = request.GET["code"]
        # activate member
        # get prospect record from code
        try:
            p = Prospect.objects.get(code=code)   
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'User unknown or code incorrect'})

        # insert new member record
        m = Member(userid=p.userid, type='m', password=p.password, email=p.email, IP=ip)
        m.save()
        # delete prospect record
        Prospect.objects.filter(code=code).delete()
        # return member JSON       
        return JsonResponse(m.toJSON())

    if request.method == 'POST':
        data = json.loads(request.body)
        logger.info(data)
        # lookup member
        try:
            m = Member.objects.get(userid=data['userName'])   
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'User unknown or code incorrect'})        

        # check password
        if check_password(data['password'], m.password):
            logger.info('Member authenticated: ' + m.userid)
            return JsonResponse(m.toJSON())
        else:
            return JsonResponse({'status': 'User unknown or code incorrect'})

    return JsonResponse({'message': 'no login performed'})

def list(request, id):
    fs = FileSystemStorage()
    logger.info(fs.location)
    allFiles = []
    if fs.exists(id):
        list = fs.listdir(id)[1]
        for file in list:
            entry = {'dir': '.', 'date': fs.get_modified_time(join(id, file)).strftime("%a, %d %b %Y %H:%M:%S") , 'name': file}
            allFiles.append(entry)
    logger.info(allFiles)
    return JsonResponse(allFiles, safe=False)

def keys(request, id):
    # get keys for userid
    keys = KeyData.objects.filter(history__userid=id).distinct()
    # find files used with key
    allKeys = []
    for key in keys:
        keyRec = { "id": key.id, "algorithm": key.algorithm, "keySize": key.keysize, "mode": key.mode }
        keyRec['files'] = []
        histories = key.history_set.all()
        for hist in histories:
            tf = hist.timestamp.strftime("%a, %d %b %Y %H:%M:%S")
            keyRec['files'].append({tf: hist.filename})
        allKeys.append(keyRec)
    logger.info(allKeys)
    return JsonResponse(allKeys, safe=False)

def download(request, id, name):
    filename = join(id, name)
    logger.info('filename: ' + filename)
    fs = FileSystemStorage()
    file = fs.open(filename)
    mime_type, _ = mimetypes.guess_type(filename)
    response = HttpResponse(file, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % name
    return response

def delete(request, id, name):
    filename = join(id, name)
    logger.info('filename: ' + filename)
    fs = FileSystemStorage()
    fs.delete(filename)
    return JsonResponse({'message': name + ' deleted'})

def upload(request):
    if request.method == 'POST':
        logger.info(request.POST)
        logger.info(request.FILES)
        file = request.FILES['file']
        id = request.POST['userId']
        fs = FileSystemStorage()
        makedirs(join(fs.location, id), exist_ok=True)
        filename = join(id, file.name)       
        if fs.exists(filename):
            fs.delete(filename)
        fs.save(filename, file)
        return JsonResponse({'status': 'uploaded (' + str(fs.size(filename)) + ' bytes)'})
    return JsonResponse({'status': 'nothing uploaded'})