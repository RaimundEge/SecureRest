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

def process(request):
    if request.method == 'POST':
        print(request.body)  
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
            key = KeyData.objects.get(id=keyId)
        else:
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
                print('re-using key')
            except ObjectDoesNotExist:   
                key = KeyData(keysize=rData['keySize'], algorithm=rData['algorithm'], keybytes=keyData, ivbytes=ivData, mode=rData['mode'])
                key.save()
        # have key, open files
        fs = FileSystemStorage()
        filename = rData['fileName']
        inFile = fs.open(join('UpFiles', str(rData['userId']), filename), 'rb')
        if rData['op'] == 'encrypt':
            filename += '.crypt'
        else:
            name, ext = splitext(filename)
            if ext == '.crypt':
                filename = name
            else:
                filename += '.decrypt'
        dirname = join('DownFiles', str(member.id))
        os.makedirs(dirname, exist_ok=True)
        outFile = fs.open(join(dirname, filename), 'wb')
        # now do the crypt operation
        print('type of key.keybytes: ', type(key.keybytes))
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
        size = fs.size(join('DownFiles', str(rData['userId']), filename))
        return JsonResponse({'status': rData['op'] + 'ed', 'name': filename, 'member': member.id, 'size': str(size)})

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
        os.makedirs('XX', exist_ok=True)
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