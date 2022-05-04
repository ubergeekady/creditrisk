import requests

url = 'http://realangels.in/result'
r = requests.post(url, json={'S1':5,'S2':5.4,'S3':4,'S4':8,'S5':10.1,'S6':3,'S7':2,'S8':2,'S9':3,'S10':4,'S11':4.18,'S12':3,'S13':1})

print(r.json())