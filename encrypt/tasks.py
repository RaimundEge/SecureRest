import os
from os.path import join, splitext
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
from .model import KeyData
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
backend = default_backend()
BLOCKSIZE = 1024

def process(request):
    if request.method == 'POST':
        print(request.POST)
        print(request.FILES)   
        # get IP number
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')      
        # get key
        keyId = request.POST['keyId']
        if keyId:
            key = KeyData.object.get(id=keyId)
        else:
            keyStyle = request.POST['keyStyle']
            if keyStyle == 'password':
                keySize = request.POST['keySize']
                ivSize = request.POST['ivSize']
                # generate key and iv data based on size and and password
                keyData = generatePBESecret(request.POST['password'], request.POST['keySize'])
                ivData = generatePBESecret(request.POST['password'], request.POST['ivSize'])
            else:
                keyData = bytes(request.POST['keyData'], 'utf-8')
                ivData = bytes(request.POST['ivData'], 'utf-8')
            # check whether key already exists, if not create and store
            try:
                key = KeyData.objects.get(keysize=request.POST['keySize'], algorithm=request.POST['algorithm'], keydata=keyData, ivdata=ivData, mode=request.POST['mode'])
            except ObjectDoesNotExist:   
                key = KeyData(keysize=request.POST['keySize'], algorithm=request.POST['algorithm'], keydata=keyData, ivdata=ivData, mode=request.POST['mode'])
                key.save()
        # have key
        if key.algorithm == 'AES':
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
            
        cryptor = cipher.encryptor() if (op == 'Encrypt') else cipher.decryptor()





    return JsonResponse({'status': 'nothing processed'}) 

def crypt(request):
    if request.method == 'POST':
        print(request.POST)
        print(request.FILES)
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
        outFile = fs.open(join('DownFiles', 'XX', filename), 'wb')
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
            unpadder = padding.PKCS7(128).unpadder()
            padded_plaintext = cryptor.update(data) + cryptor.finalize()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
            outFile.write(plaintext)
        outFile.close()
        size = fs.size(join('DownFiles', 'XX', filename))
        return JsonResponse({'status': op + 'ed', 'name': filename, 'member': 'XX', 'size': str(size)})
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
    # derive
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA512(),
        length=size,
        salt=salt,
        iterations=100000,
        backend=backend
    )
    return kdf.derive(password)