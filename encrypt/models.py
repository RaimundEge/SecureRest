from django.db import models

class Member(models.Model):
    userid = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    firstname = models.CharField(max_length=50)
    type = models.CharField(max_length=1)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=50)
    IP = models.CharField(max_length=20)
    address = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    status = ''
    def __str__(self):
        return self.userid + " (" + self.email + ")"       
    def checkPassword(self, password):
        return self.password == password
    def toJSON(self):
        fields = []
        d = {}
        d['userId'] = self.id 
        d['userName'] = self.userid
        d['loginType'] = self.type
        d['email'] = self.email
        d['ipNumber'] = self.IP
        d['status'] = 'User OK'
        return d

class Prospect(models.Model):
    userid = models.CharField(max_length=50)
    password = models.CharField(max_length=100)
    email = models.CharField(max_length=50)
    code = models.CharField(max_length=24)
    def __str__(self):
        return self.code + " (" + self.email + ")"

class KeyData(models.Model):
    algorithm= models.CharField(max_length=50)
    keysize = models.IntegerField()
    mode = models.CharField(max_length=3)
    keybytes = models.CharField(max_length=256)
    ivbytes = models.CharField(max_length=256)
    def __str__(self):
        return str(self.id) + " (" + self.algorithm + "-" + self.mode + ")"

class History(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    userid = models.ForeignKey(Member, on_delete=models.CASCADE)
    IP = models.CharField(max_length=20)
    filename = models.CharField(max_length=256)
    action = models.CharField(max_length=1)
    keyid = models.ForeignKey(KeyData, on_delete=models.CASCADE)
    def __str__(self):
        return str(self.keyid) + " (" + self.action + " for file: " + self.filename + "): " + str(self.timestamp)

class Hello(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    IP = models.CharField(max_length=20)
    def __str__(self):
        return str(self.id) + " (" + self.timestamp + "-" + self.IP + ")"   
        