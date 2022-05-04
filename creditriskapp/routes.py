from flask import Flask, request, jsonify, request
from urllib.request import urlopen
from flask_restful import Resource, Api, reqparse
from creditriskapp.globalvars import search, loan_apps, bank_id, gambling_apps
from creditriskapp.helpers import returnParse, findContactInfo, findSMSInfo, findAPPInfo, getEmiInfo, getBillOverdueInfo, getSpendingInfo, getOverdueEmiInfo, authenticate, getUserJsonData, mergeJsonFiles, getUserBasicInfo, identity, debug
from creditriskapp import app, api
#from flask_jwt import JWT, jwt_required, current_identity
from werkzeug.security import safe_str_cmp
from functools import wraps
import statistics
import json
import pandas as pd
import re
import time
import os
from datetime import datetime, timedelta
import numpy as np
import pickle
from collections import Counter
import collections, functools, operator 
from itertools import chain
import requests

#jwt = JWT(app, authenticate, identity)

def checkuser(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_identity.username == 'user1':
            return func(*args, **kwargs)
        return abort(401)
    return wrapper

def userPredictor(data):
    predict_data = np.array(data).reshape(1,14)
    model = pickle.load(open("model.sav","rb"))
    prediction = model.predict(predict_data)
    return prediction

# Testing API
class HelloWorld(Resource):
    #decorators = [checkuser, jwt_required()]
    def get(self):
        return {'API Status':'Running'}
    def post(self):
        json_file = request.get_json()
        return {'File:',json_file}, 201 

class MergeFile(Resource):
    def get(self):
        #r = requests.get('https://phoneparloan-v2.s3.amazonaws.com/underwriting_file/1590629184_3731093975ecf1340c422d.json')
        #r2 = requests.get('https://phoneparloan-v2.s3.amazonaws.com/underwriting_file/1590642560_1603084165ecf4780dc4a6.json')
        #data = r.json()
        #data2 = r2.json()

        jsonString1 = '{"1":"akh", "2":"kum"}'
        jsonString2 = '{"1":"akh", "2":"kum", "3":"ttt"}'
        
        #jsonString1 = #str(data).replace("'", '"')
        #return jsonString1
        #jsonString2 = #str(data2).replace("'", '"')

        dictA = json.loads(jsonString1)
        dictB = json.loads(jsonString2)
        #return jsonString1

        merged_dict = {key: value for (key, value) in (dictA.items() | dictB.items())}

        # string dump of the merged dict
        jsonString_merged = json.dumps(merged_dict)
        return jsonString_merged

        


        #return "hello"
        #return mergeJsonFiles()


class Predict(Resource):    
    def post(self):
        predict_data = request.get_json(force=True)
        predict_data = [np.array(list(predict_data.values()))]
        #predict_data = [element * 60 for element in predict_data] 
        print(predict_data)
        predict_data = np.append(predict_data,np.sum(predict_data))
        print(predict_data)
        result = userPredictor(predict_data)
        print(result)
        if result == [1.]:
            prediction = False # Normal User
        else:
            prediction = True # Wilful Defaulter
        return {"status": bool(prediction)},201    


# Get basic information from underwriting data
class GetBasicInformation(Resource):
    def post(self):
        userId = request.args.get('userId')
        filename = getUserJsonData(userId)
        r = requests.get('https://phoneparloan-v2.s3.amazonaws.com/'+filename[0]['stored_path'])
        JSONFile = r.json()
        
        contactParse = returnParse(JSONFile,'contact_list')
        contacts = [0,0]	
        if(not contactParse.empty):
            contacts = findContactInfo(contactParse['contactName'],contactParse['contactNumber'])
        apps = [0]
        apps = findAPPInfo(JSONFile['app_list'])
        

        return {'total_contacts':contacts[0],'international_contacts':contacts[1],'total_apps':apps[0],
        'whatsapp_installed':apps[1],'social_apps':apps[2],'finance_apps':apps[3],
        'productivity_apps':apps[4],'gambling_apps':apps[5], 'gambling_apps_list':apps[8],'micro_loan_app_count':apps[6],'loan_apps_list':apps[7]},201   


# Get contact information from underwriting data
class GetContact(Resource):
    def post(self):
        userId = request.args.get('userId')
        filename = getUserJsonData(userId)
        r = requests.get('https://phoneparloan-v2.s3.amazonaws.com/'+filename[0]['stored_path'])
        JSONFile = r.json()
        contactParse = returnParse(JSONFile,'contact_list')
        contacts = [0,0]	
        if(not contactParse.empty):
            contacts = findContactInfo(contactParse['contactName'],contactParse['contactNumber'])
        apps = [0]
        apps = findAPPInfo(JSONFile['app_list'])
        return {'contacts':contacts[2]},201   


# Get bank information from underwriting data
class GetBankInformation(Resource):
    def post(self):
        Sal = 0
        CompanyName = ""
        salaried = 0
        try:
            userId = request.args.get('userId')
            basicInfo = getUserBasicInfo(userId)
            filename = getUserJsonData(userId)
            if(filename != []):
                r = requests.get('https://phoneparloan-v2.s3.amazonaws.com/'+filename[0]['stored_path'])
                JSONFile = r.json()
                if(basicInfo != []):
                    Sal = basicInfo[1]['content']
                    CompanyName = basicInfo[2]['content']
                    #print("akhlesh1235")
                    if(basicInfo[0]['content'] == 'Salaried'):
                        salaried = "1"  
                    else:
                        salaried = "0"
                #print("akhlesh123456")
                contactParse = returnParse(JSONFile,'contact_list')
                #print("akhlesh1234567")
                contacts = [0,0]	
                if(not contactParse.empty):
                    contacts = findContactInfo(contactParse['contactName'],contactParse['contactNumber'])
                #print("test@@@@@@@12345678")
                smsParse = returnParse(JSONFile,'sms_list')
                #print("test@@@@@@@123456789")
                salary = [0]
                apps = [0]
                if(not smsParse.empty): 
                    salary = findSMSInfo(smsParse['body'],smsParse['date_get'],smsParse['address'], Sal, salaried, CompanyName)
                #apps = findAPPInfo(JSONFile['app_list'])
                #print("test@@@@@@@12346")
                transactions = Counter(chain.from_iterable(e.keys() for e in salary[6]))
                return {'salary_acc':salary[4],'transaction_data':transactions,'last_sms':salary[7]},201
            else:
                return {'status':'false', 'msg':'User does not exists'}
            
        except Exception as e:
            return {'No data found'+str(e)},201

           
       
# Find default patterns, emi dues etc
class defaultPatterns(Resource):
    def post(self):
        try:
            userId = request.args.get('userId')
            filename = getUserJsonData(userId)
            r = requests.get('https://phoneparloan-v2.s3.amazonaws.com/'+filename[0]['stored_path'])
            data = r.json()
            emi = getEmiInfo(data)
            billoverdue = getBillOverdueInfo(data)
            #OverdueEmi = getOverdueEmiInfo(data)
        except Exception as e:
            return {'Error: E10':'API Error ->'+str(e)},201
        return {'emi':emi,'billoverdue':billoverdue},201  
# Finance apps list    
class finarray(Resource):
    def post(self):
        try:
            finarr = []
            data=request.get_json()
            data = returnParse(data, 'sms_list')
            if(not data.empty):
                for add in data['address']:
                    for i in range(len(search)):
                        if add in search[i]:
                           if loan_apps[i] not in finarr:
                               finarr.append(loan_apps[i])
        except Exception as e:
            return {'Error: E10':'API Error ->'+str(e)},201
        return finarr,201



class ECSBounce(Resource):
    def post(self):
        try:
            data=request.get_json()
            ECSBounce={'sms':[],'count':0}
            ECSBouncekey=[]
            ECSBouncekey.append(["Ecs","insufficient funds"])
            ECSBouncekey.append(["Ecs","Insufficient balance"])
            ECSBouncekey.append(["Ecs","Loan A/c","Bounced"])
            ECSBouncekey.append(["Ecs","Loan account","Bounced"])
            ECSBouncekey.append(["Ecs","Returned"])
            ECSBouncekey.append(["Ecs","Emi","Loan","Bounced"])
            for i in range(len(data['sms_list'])): 
                for o in range(len(ECSBouncekey)):
                    c=False
                    stri={}
                    for p in range(len(ECSBouncekey[o])):
                        c= (ECSBouncekey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                        if c==True :
                            break
                        elif (p==(len(ECSBouncekey[o])-1)):
                            stri=data['sms_list'][i]
                    if stri!={}:
                        ECSBounce['sms'].append(stri)
                        break                   
        except Exception as e:
            return {'Error: E10':'JSON file Parse Error ->'+str(e)},201
        if (ECSBounce['sms'] != []):
            ECSBounce['count']=len(ECSBounce['sms'])
            return ECSBounce, 201
        else:
            return {'sms':[],'count':0},201



class ChequeBounceInwardOutward(Resource):
    def post(self):
        try:
            data=request.get_json()
            ChequeBounceInwardOutward={'sms':[],'count':0}
            ChequeBounceInwardOutwardkey=[]
            ChequeBounceInwardOutwardkey.append(["Cheque no.","Account No.","bounced"])
            ChequeBounceInwardOutwardkey.append(["Cheque","NACH dishonoured"])
            ChequeBounceInwardOutwardkey.append(["Cheque returned","Insufficient funds"])
            ChequeBounceInwardOutwardkey.append(["cheque bounce","EMI amount returned"])
            for i in range(len(data['sms_list'])):  
                for o in range(len(ChequeBounceInwardOutwardkey)):
                    c=False
                    stri={}
                    for p in range(len(ChequeBounceInwardOutwardkey[o])):
                        c= (ChequeBounceInwardOutwardkey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                        if c==True :
                            break
                        elif (p==(len(ChequeBounceInwardOutwardkey[o])-1)):
                            stri=data['sms_list'][i]
                    if stri!={}:
                        ChequeBounceInwardOutward['sms'].append(stri)
                        break
        except Exception as e:
            return {'Error: E10':'JSON file Parse Error ->'+str(e)},201
        if (ChequeBounceInwardOutward['sms'] != []):
            ChequeBounceInwardOutward['count']=len(ChequeBounceInwardOutward['sms'])
            return ChequeBounceInwardOutward, 201
        else:
            return {'sms':[],'count':0},201       



class InsufficientBal(Resource):
    def post(self):
        try:
            data=request.get_json()
            InsufficientBal={'sms':[],'count':0}
            InsufficientBalkey=[]
            InsufficientBalkey.append(["Declined","Insufficient limit"])
            InsufficientBalkey.append(["Declined","Insufficient Funds"])
            InsufficientBalkey.append(["Could not","Insufficient account balance"])
            InsufficientBalkey.append(["Declined","Insufficient balance","Bank credit card name"])
            InsufficientBalkey.append(["Declined","Insufficient credit limit"])
            for i in range(len(data['sms_list'])):  
                for o in range(len(InsufficientBalkey)):
                    c=False
                    stri={}
                    for p in range(len(InsufficientBalkey[o])):
                        c= (InsufficientBalkey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                        if c==True :
                            break
                        elif (p==(len(InsufficientBalkey[o])-1)):
                            stri=data['sms_list'][i]
                    if stri!={}:
                        InsufficientBal['sms'].append(stri)
                        break
        except Exception as e:
            return {'Error: E10':'JSON file Parse Error ->'+str(e)},201
        if (InsufficientBal['sms'] != []):
            InsufficientBal['count']=len(InsufficientBal['sms'])
            return InsufficientBal, 201
        else:
            return {'sms':[],'count':0},201       

class spendingPattern(Resource):
    def post(self):
        userId = request.args.get('userId')
        userInfo = getUserBasicInfo(userId)
        filename = getUserJsonData(userId)
        if(filename != []):

            r = requests.get('https://phoneparloan-v2.s3.amazonaws.com/'+filename[0]['stored_path'])
            data = r.json()
            sal = 0
            if(userInfo != []):
                sal = userInfo[1]['content']
            data = returnParse(data, 'sms_list')
            Bal = getSpendingInfo(data['body'], data['date_get'], data['address'],sal)
            avg_atm = 0
            for atmDat in Bal[8]:
                avg_atm += atmDat
            avg_atm /= len(Bal[8])
            res_list = [] 
            for i in range(len(Bal[14])): 
                if Bal[14][i] not in Bal[14][i + 1:]: 
                    res_list.append(Bal[14][i])
            return {'avg_monthly_balance_all':Bal[0],'all_account_balance':Bal[11],'all_account_credit':Bal[12],'all_account_debit':Bal[13],'all_accounts':res_list},201
        else:
            return {'status':'false', 'msg':'User does not exists'}

class creditcard(Resource):
    def post(self):
        try:
            data=request.get_json()
            creditcardlist=[]
            creditcardblockedlist=[]
            for sms in data:
                p=[]
                p.append(re.findall(r' Credit[ ]*Card \d\d\d\d[ ]*[Xx*]*[ ]*[Xx*]*[ ]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card XX[X]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card \*\*[*]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card ending with [X]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card ending with [*]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card ending [#]*[ ]*XX[X]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card ending [#]*[ ]*\*\*[*]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card a/c ending with \d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card no[.]* XX\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card no[.]* \*\*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card no[.]* ending with \d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card ending \d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card account ending with \d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card Account [\d]*x[x]*\d\d\d\d',sms,re.IGNORECASE))
                p.append(re.findall(r' Credit[ ]*Card ending in [Xx*]*\d\d\d\d',sms,re.IGNORECASE))
                r=[]
                while [] in p:
                    p.remove([])
                if len(p)<2:    
                    r.append(re.findall(r' Credit[ ]*Card [\d]* ',sms,re.IGNORECASE))    
                    if len(p)==0:
                        p.append(r)
                    else:
                        if len(r[0])==2:
                            if r[0][0] not in p[0][0]:
                                p.append([r[0][0]])
                            if r[0][1] not in p[0][0]:
                                p.append([r[0][1]])                        
                print (p)
                r=[]
                if len(p)==2:
                    r.append(p[0][0])
                    r.append(p[1][0])
                if len(p[0])==2:
                    r.append(p[0][0])
                    r.append(p[0][1])    
                print (r)   
                if len(r)!=0:    
                    r[0]=re.search(r'\d+$',r[0])
                    r[0]=r[0].group()
                    if len(r)!=1:
                        r[1]=re.search(r'\d+$',r[1]) 
                        r[1]=r[1].group()
                if r[0] not in creditcardlist:    
                    creditcardlist.append(r[0])
                if len(r)==2:
                    if r[1] not in creditcardlist:    
                        creditcardlist.append(r[1])     
                creditcardblockedkey=[]
                creditcardblockedkey.append([" creditcard "," Blocked"])
                creditcardblockedkey.append([" credit card "," Blocked"])
                for o in range(len(creditcardblockedkey)):
                    c=False
                    for p in range(len(creditcardblockedkey[o])):
                        c= (creditcardblockedkey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                        if c==True :
                            break
                        elif (p==(len(creditcardblockedkey[o])-1)):
                            if r[0] not in creditcardblockedlist:    
                                creditcardblockedlist.append(r[0])
            return {'totalcreditcardlist':creditcardlist,'countTotalCreditCard':len(creditcardlist),'creditcardblockedlist':creditcardblockedlist,'countCreditCardBlockedEver':len(creditcardblockedlist), 'creditcardActivelist':[x for x in creditcardlist if x not in creditcardblockedlist], 'countActiveCreditCards':len(creditcardlist)-len(creditcardblockedlist)}                               
        except Exception as e:
            return {'Error: E10':'JSON file Parse Error ->'+str(e)},201
            

class ccoverdue(Resource):
    def post(self):
        try:
            data=request.get_json()
            ccoverdue={'sms':[],'count':0}
            ccoverduekey=[]
            ccoverduekey.append([" credit card "," overdue "])
            ccoverduekey.append([" credit card "," minimum payment"])
            ccoverduekey.append([" credit card "," total outstanding bal"])
            ccoverduekey.append([" creditcard "," overdue "])
            ccoverduekey.append([" creditcard "," minimum payment"])
            ccoverduekey.append([" creditcard "," total outstanding bal"])
            for i in range(len(data['sms_list'])): 
                for o in range(len(ccoverduekey)):
                    c=False
                    stri={}
                    for p in range(len(ccoverduekey[o])):
                        c= (ccoverduekey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                        if c==True :
                            break
                        elif (p==(len(ccoverduekey[o])-1)):
                            stri=data['sms_list'][i]
                            stri['duedate']=''
                    if stri!={}:
                        d= re.search(r'[12][90]\d\d[-/. ]*jan[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-01-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*feb[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-02-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*mar[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-03-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*apr[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-04-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*may[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-05-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*jun[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-06-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*jul[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-07-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*aug[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-08-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*sep[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-09-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*oct[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-10-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*nov[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-11-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*dec[-/. ]*[0123]\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-12-'+d.group()[:4]
                        d= re.search(r'[0123]\d[-/. ]*jan[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-01-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*feb[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-02-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*mar[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-03-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*apr[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-04-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*may[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-05-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*jun[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-06-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*jul[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-07-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*aug[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-08-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*sep[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-09-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*oct[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-10-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*nov[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-11-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*dec[-/. ]*[12][90]\d\d',stri['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-12-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/.][01]\d[-/.][12][90]\d\d',stri['body'])
                        if d:
                            stri['duedate']= d.group()[:2]+"-"+d.group()[3:5]+"-"+d.group()[6:]    
                        d= re.search(r'[12][90]\d\d[-/.][01]\d[-/.][0123]\d',stri['body'])
                        if d:
                            stri['duedate']= d.group()[-2:]+"-"+d.group()[5:7]+"-"+d.group()[:4]
                        if stri['duedate']=='':
                            d= re.search(r'\d[\d]*[ ]*\w+[ ]*day[s]*',stri['body'],re.IGNORECASE)
                            if d:
                                p= re.search(r'\d+',d)
                                month =(time.strftime('%m', time.localtime(int(stri['data_get'][:10]))))
                                day =(time.strftime('%d', time.localtime(int(stri['data_get'][:10]))))
                                year =(time.strftime('%y', time.localtime(int(stri['data_get'][:10]))))
                                specific_date = datetime(year, month, day)
                                new_date = str(specific_date + timedelta(int(p.group())))[:10]
                                stri['duedate']= d.group()[-2:]+"-"+d.group()[5:7]+"-"+d.group()[:4]    
                        ccoverdue['sms'].append(stri)
                        break                    
        except Exception as e:
            return {'Error: E10':'JSON file Parse Error ->'+str(e)},201
        if (ccoverdue['sms'] != []):
            ccoverdue['count']=len(ccoverdue['sms'])
            return ccoverdue, 201
        else:
            return {'sms':[],'count':0}, 201



# List API end-points here
api.add_resource(HelloWorld,'/')
api.add_resource(GetBasicInformation,'/getBasicInfo')
api.add_resource(GetBankInformation,'/getBankInfo')
api.add_resource(GetContact,'/getContactBook')
api.add_resource(spendingPattern,'/getOtherAccounts')
api.add_resource(defaultPatterns,'/defaultPatterns')
api.add_resource(finarray,'/finarray')
api.add_resource(ChequeBounceInwardOutward,'/ChequeBounceInwardOutward')
api.add_resource(ECSBounce,'/ECSBounce')
api.add_resource(InsufficientBal,'/InsufficientBal')
api.add_resource(creditcard,'/creditcardcount')
api.add_resource(ccoverdue,'/ccoverduedetails')
api.add_resource(Predict,'/result')
api.add_resource(MergeFile,'/mergeFile')