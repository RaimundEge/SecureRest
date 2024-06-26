import os, json
from os.path import join, splitext
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from .models import KeyData, History, Member
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
backend = default_backend()
BLOCKSIZE = 1024
import logging
logger = logging.getLogger(__name__)
# from settings import CAPTCHA_V3_KEY
from django.conf import settings
import requests

def process(request):
    if request.method == 'POST':
        logger.warn('processing ...')
        logger.info(request.body)        
        rData = json.loads(request.body) 
        # get IP number
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR') 
        # get member
        member = Member.objects.get(id=rData['userId'])     
        # get key
        keyId = rData.get('keyId')
        if keyId != None:
            logger.info('key lokup: ' + keyId)
            key = KeyData.objects.get(id=keyId)
        else:
            logger.warn('key not found ')
            keyStyle = rData['keyStyle']
            if keyStyle == 'password':
                keySize = rData['keySize']
                ivSize = rData['ivSize']
                # generate key and iv data based on size and and password
                keyData = generatePBESecret(rData['password'], rData['keySize'])
                ivData = generatePBESecret(rData['password'], rData['ivSize'])
            else:
                keyData = bytes(rData['keyData'], 'utf-8')
                ivData = bytes(rData['ivData'], 'utf-8')
            # check whether key already exists, if not create and store
            try:
                key = KeyData.objects.get(keysize=rData['keySize'], algorithm=rData['algorithm'], keybytes=keyData, ivbytes=ivData, mode=rData['mode'])
                logger.info('re-using key')
            except ObjectDoesNotExist:   
                key = KeyData(keysize=rData['keySize'], algorithm=rData['algorithm'], keybytes=keyData, ivbytes=ivData, mode=rData['mode'])
                key.save()
        # have key, open files
        fs = FileSystemStorage()
        filename = rData['fileName']
        logger.error('filename: ' + filename)
        inFile = fs.open(join(str(rData['userId']), filename), 'rb')
        if rData['op'] == 'encrypt':
            filename += '.crypt'
        else:
            name, ext = splitext(filename)
            if ext == '.crypt':
                filename = name
            else:
                filename += '.decrypt'
        if fs.exists(join(str(rData['userId']), filename)):
            fs.delete(join(str(rData['userId']), filename))
        outFile = fs.open(join(str(rData['userId']), filename), 'wb')
        # now do the crypt operation
        logger.info('key: ' + str(key))
        if key.algorithm == 'AES':
            algo = algorithms.AES(key.keybytes)
        if key.algorithm == "DES" or key.algorithm == "DESede":
            algo = algorithms.TripleDES(key.keybytes)
        if key.mode == 'CBC':
            cipher = Cipher(algo, modes.CBC(key.ivbytes), backend=backend)
        else:
            cipher = Cipher(algo, modes.ECB(), backend=backend)          
        cryptor = cipher.encryptor() if (rData['op'] == 'encrypt') else cipher.decryptor()
        # read file, feed cryptor, write file
        data = inFile.read()
        if rData['op'] == 'encrypt':
            padder = padding.PKCS7(algo.block_size).padder()
            padded_data = padder.update(data) + padder.finalize()
            outFile.write(cryptor.update(padded_data))
            outFile.write(cryptor.finalize())
        else:
            unpadder = padding.PKCS7(algo.block_size).unpadder()
            padded_plaintext = cryptor.update(data) + cryptor.finalize()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
            outFile.write(plaintext)
        outFile.close()
        inFile.close()
        # record crypt operation
        action = 'E' if (rData['op'] =='encrypt') else 'D'
        rec = History(userid=member, IP=ip, action=action, filename=filename, keyid=key)
        rec.save()
        # construct response
        size = fs.size(join(str(rData['userId']), filename))
        return JsonResponse({'status': rData['op'] + 'ed', 'name': filename, 'member': member.id, 'size': str(size)})

    return JsonResponse({'status': 'nothing processed'}) 

def crypt(request):
    if request.method == 'POST':
        logger.info(request.POST)
        logger.info(request.FILES)
        # check for robot
        gData = {
            'response': request.POST['token'],
            'secret': settings.CAPTCHA_V3_KEY
        }
        # logger.info('Token: ' + request.POST['token'])
        resp = requests.post('https://www.google.com/recaptcha/api/siteverify', data=gData)
        logger.info(resp.status_code)
        if resp.status_code == 200:
            op = request.POST['op']
            password = request.POST['pwd']
            inFile = request.FILES['file']
            # prepare output file path
            filename = inFile.name 
            if op == 'Encrypt':
                filename += '.crypt'
            else:
                name, ext = splitext(filename)
                if ext == '.crypt':
                    filename = name
                else:
                    filename += '.decrypt'
            fs = FileSystemStorage()
            os.makedirs(join(fs.location, 'XX'), exist_ok=True)
            if fs.exists(join('XX', filename)):
                fs.delete(join('XX', filename))
            outFile = fs.open(join('XX', filename), 'wb')
            # prepare key/iv from password
            key, iv = generateSecrets(password)
            # prepare AES/CBC
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
            cryptor = cipher.encryptor() if (op == 'Encrypt') else cipher.decryptor()
            # read file, feed cryptor, write file
            data = inFile.read()
            if op == 'Encrypt':
                padder = padding.PKCS7(algorithms.AES.block_size).padder()
                padded_data = padder.update(data) + padder.finalize()
                outFile.write(cryptor.update(padded_data))
                outFile.write(cryptor.finalize())
            else:
                unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
                padded_plaintext = cryptor.update(data) + cryptor.finalize()
                plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
                outFile.write(plaintext)
            outFile.close()
            size = fs.size(join('XX', filename))
            return JsonResponse({'status': op + 'ed', 'name': filename, 'member': 'XX', 'size': str(size)})
        else:
            return JsonResponse({'status': 'Captcha failed'}) 
    return JsonResponse({'status': 'nothing processed'}) 

def generateSecrets(password):
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    for i in range(0, 256):
        digest.update(bytes(password, 'utf-8'))
    hashValue = digest.finalize()
    key = hashValue[0:16]
    iv = hashValue[16:32]
    return (key, iv)

def generatePBESecret(password, size):
    # Salts should be randomly generated
    salt = b'010101010101'
    length = int(size/8)
    # derive
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA512(),
        length=length,
        salt=salt,
        iterations=100000,
        backend=backend
    )
    return kdf.derive(password.encode('utf-8'))