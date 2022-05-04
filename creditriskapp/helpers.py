from flask import Flask, request, jsonify, request
from urllib.request import urlopen
from creditriskapp.globalvars import search, loan_apps, bank_id, gambling_apps
from creditriskapp.models import username_table, userid_table
from creditriskapp import app, api
from werkzeug.security import safe_str_cmp
import traceback
from datetime import datetime, timedelta
import pprint
import json
import pandas as pd
import re
import time
import mysql.connector

#global db connection
connection = mysql.connector.connect(host='phoneparloan-v2.cit046eedl5m.ap-south-1.rds.amazonaws.com',
                                         database='pplv2',
                                         user='admin',
                                         port='3306',
                                         password='!phoneparloan1234')

def authenticate(username, password):
    user = username_table.get(username, None)
    if user and safe_str_cmp(user.password.encode('utf-8'), password.encode('utf-8')):
        return user

def identity(payload):
    user_id = payload['identity']
    return userid_table.get(user_id, None)

# Load and Parse JSON
def returnParse(data,key):
    return pd.DataFrame(data[key])

# Contact info
def findContactInfo(name,data):
    international = 0
    indian = 0
    count = 0
    contactBook = []
    #print(data)
    for contact in data:
        #print(contact)
        #Create a contact book
        if(isNaN(contact)):
            pass
        else:

            contactBook.append({'name':name[count],'contact':contact})

            # Check for contacts
            count += 1
            Cont = re.findall("(\+91?)|^[0-9]{10}$|^[0-9]{5,6}( )[0-9]{5}", contact, re.IGNORECASE)
            #print("cont+++++++")
            if (Cont):
                #debug("Indian: "+ str(contact))
                indian += 1
                #print("cont+++++++1")
            else:  
                if(len(contact)<7):
                    pass
                else:
                    #debug("International: "+ str(contact))
                    international += 1
                    #print("cont+++++++2")
    #print("count++++++3")
    return indian, international, contactBook


# Extract data from SMS
def findSMSInfo(data, smsDate, sender, sal, salaried, company=None):
    
    msg = list()
    banks = []
    found = []
    salary = 0.0
    pat = 0
    amount = 0
    prev_amount = 0
    date = 0
    year = 0
    month = 0
    months = []
    senderId = []
    trans_data = []
    amounts = []
    dictionary = []
    highest_amount = 0.0
    total_trans = 0
    fromBank = False
    same = False    
    last_sms = []
    senderBank = ""
    i = 0
    patFound = False
    if(company):
        company_abbr = "".join(e[0] for e in company.split())
    else:
        company_abbr = ""    
    last_sms.append({"date":time.strftime('%d-%m-%Y', time.localtime(int(smsDate[i][:10])))})
    #print("smssssssss")
    #print(last_sms)
    for sms in data:
        # Check for salary sms
        #debug(sms)
        #debug("----------------------")
        salaryPat = re.findall("salary|[^a-zA-Z]salry|[^a-zA-Z]sal[^a-zA-Z]", sms, re.IGNORECASE) # Salary pattern
        creditedPat = re.findall("credited", sms, re.IGNORECASE) # Credit pattern
        debitedPat = re.findall("debited", sms, re.IGNORECASE) # Debit pattern

        DepositedPat = re.findall("deposited", sms, re.IGNORECASE) # Deposited pattern
        NEFTPat = re.findall("NEFT", sms, re.IGNORECASE) # NEFT pattern
        overDue = re.findall("overdue", sms, re.IGNORECASE) # Overdue pattern
        # Find company name in sms for salary account verification
        if company_abbr:
            companyPat = re.findall(company+"|"+company_abbr, sms, re.IGNORECASE)
        else:
            companyPat = "" 
           
        promos = re.findall("yatra|makemytrip|trip|vacation|travel", sms, re.IGNORECASE)
        
        pat1 = re.findall("INR\s+\w*\,?\w*\,?\w*.?\w*", sms, re.IGNORECASE)
        pat2 = re.findall("\s+\w*\,?\w*\,?\w*.?\w Deposited", sms, re.IGNORECASE)
        pat3 = re.findall("Rs.?\s?\d*\d,?\d*.?\d*", sms, re.IGNORECASE)
        
        for l in range(len(bank_id)):
                if ((bank_id[l] in sender[i])):
                    fromBank = True
                    senderBank = bank_id[l]
        #print("qqqqqq123^^^^^")   
        if (fromBank and (senderBank not in banks)):
            banks.append(senderBank)
        #print("qqqqqq1234^^^^^") 
        if ((((salaryPat and creditedPat) or  (salaryPat and DepositedPat) or (salaryPat and NEFTPat)) or (companyPat and creditedPat) or (companyPat and DepositedPat) and not (salaryPat and overDue) and not(salaryPat and promos)) and  salaried == "1"):
            #print("qqqqqq12345^^^^^")                                    
            patterns = [pat1, pat2, pat3]
            for found in patterns:
                if(found and fromBank): # If matching pattern is found and it's from the bank
                    #print("qqqqqq123456^^^^^")
                    captured_values = found
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d", captured_values[0], re.IGNORECASE)
                    if (amount):
                        
                        prev_month = month
                        amount = float(amount[0].replace(',',''))
                        year = time.strftime('%Y', time.localtime(int(smsDate[i][:10])))
                        month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                        date = time.strftime('%d', time.localtime(int(smsDate[i][:10])))
                        if((months is not None and prev_amount != amount)):
                            if((month != prev_month)):
                                months.append(date+"/"+month+"/"+year)
                                msg.append(sms)
                                senderId.append(senderBank)
                                amounts.append(amount)
                                same = True 
                                patFound = True   
                                dictionary.append({"month":months[-1], "message":msg[-1], "sender":senderId[-1], "amount":amounts[-1]})
                            else:
                                months.append(date+"/"+month+"/"+year)
                                msg.append(sms)
                                senderId.append(senderBank)
                                amounts.append(amount)
                                patFound = True
                                if(same and dictionary[-1]['month'][3:5] == month):
                                    del dictionary[-1]
                                    same = False                                    
                                dictionary.append({"month":months[-1], "message":msg[-1], "sender":senderId[-1], "amount":amounts[-1]})                            
                        prev_amount = amount
                        #print("akh$$$$")                                                            
                        break
                    else:    
                        break
        else:
            #print("else********")
            #print(salaried)
            patterns = [pat1, pat2, pat3]
            for found in patterns:
                if(found):
                    if(not promos and fromBank): 
                        total_trans +=1
                        trans_data.append({senderBank:"1"})
                        if (salaried == "0"): # If the user is not salaried i.e, self-employed
                            
                            if(creditedPat and not debitedPat): # Has detected a credit sms
                                captured_values = found
                                amount = re.findall("[^a-zA-Z\\*:.]\d*,?\d*.?\d*\d", captured_values[0], re.IGNORECASE)
                                #print("non salaried******")
                                amount = amount[0].replace(',', '')
                                #print(amount[0],highest_amount)
                                #print(amount)
                                if (amount):
                                    if(float(amount) > float(highest_amount)): # Find the highest amount 
                                        #print("akk")
                                        #print(amount,highest_amount)
                                        highest_amount = (amount)
                                        #print("hellllooooosssss")
                                        dictionary = ({"message":sms, "sender":senderBank, "amount":highest_amount}) # Capture the sms
                                        #print("akh&&&&&&&&")

        i+=1   
        fromBank = False        
                
    return msg, amounts, months, senderId, dictionary, banks, trans_data, last_sms

# Check if the user has specific Apps installed
def findAPPInfo(data):
    app = []
    whatsApp = False
    totalApps = 0
    socialApps = 0
    loanApps = 0
    financeApps = 0
    productivityApps = 0
    gambling = 0
    loan_app_list = []
    gambling_app_list = []
    
    for apps in data:
        app = re.match("^([A-Za-z]{1}[A-Za-z\d_]*\.)+[A-Za-z][A-Za-z\d_]*$", apps['pakageNm'], re.IGNORECASE) 
        # Regex for social apps installed 
        
        wApp = re.match("com.whatsapp", apps['pakageNm'], re.IGNORECASE)
        fb = re.match("com.facebook.katana", apps['pakageNm'], re.IGNORECASE)
        messenger = re.match("com.facebook.orca", apps['pakageNm'], re.IGNORECASE)
        twitter = re.match("com.twitter.android", apps['pakageNm'], re.IGNORECASE) 
        telegram = re.match("org.telegram.messenger", apps['pakageNm'], re.IGNORECASE)
        instagram = re.match("com.instagram.android", apps['pakageNm'], re.IGNORECASE)
        
        socialRegex = [fb, messenger, twitter, telegram, instagram, wApp]


        # Regex for finance apps
        
        payTm = re.match("net.one97.paytm", apps['pakageNm'], re.IGNORECASE)
        mobiQk = re.match("com.mobikwik_new", apps['pakageNm'], re.IGNORECASE)
        phonePe = re.match("com.phonepe.app", apps['pakageNm'], re.IGNORECASE)
        fedbook = re.match("in.co.federalbank.mpassbook", apps['pakageNm'], re.IGNORECASE)
        sbiyono = re.match("com.sbi.lotusintouch", apps['pakageNm'], re.IGNORECASE)
        gpay = re.match("com.google.android.apps.nbu.paisa.user", apps['pakageNm'], re.IGNORECASE)

        financeRegex = [payTm, mobiQk, phonePe, fedbook, sbiyono, gpay]
        
        # Regex for productivity apps

        gmail =  re.match("com.google.android.gm", apps['pakageNm'], re.IGNORECASE)
        htcMail = re.match("com.htc.android.mail", apps['pakageNm'], re.IGNORECASE)
        samsungMail = re.match("com.sec.android.email", apps['pakageNm'], re.IGNORECASE)
        yahooMail = re.match("com.yahoo.mobile.client.android.mail ", apps['pakageNm'], re.IGNORECASE)
        dropBox = re.match("com.dropbox.android", apps['pakageNm'], re.IGNORECASE)
        everNote = re.match("com.evernote", apps['pakageNm'], re.IGNORECASE)
        gDrive = re.match("com.google.android.apps.docs", apps['pakageNm'], re.IGNORECASE)
        
        productivityRegex = [gmail, htcMail, samsungMail, yahooMail, dropBox, everNote, gDrive]
        
        # Gambling Apps list
        
        for app_name in loan_apps:
            if(apps['appName'].lower()==app_name.lower()):
                loanApps += 1
                loan_app_list.append(apps['appName'].lower())
        for gambApps in gambling_apps:
            if(apps['pakageNm'].lower()==gambApps.lower()):
                gambling += 1
                gambling_app_list.append(apps['appName'].lower())
        for regex in socialRegex:
            social = regex
            if social:
                socialApps += 1
        for regex in financeRegex:
            finance = regex
            if finance:
                financeApps += 1  
        for regex in productivityRegex:
            productivity  = regex
            if productivity:
                productivityApps += 1                
        if (app):
            totalApps += 1
            app = []
        if (wApp):
            whatsApp = True
        
    return  totalApps, whatsApp, socialApps, financeApps, productivityApps, gambling, loanApps, loan_app_list, gambling_app_list

def percentage(part, whole):
  return 100 * float(part)/float(whole)
  
def getSpendingInfo(data, smsDate, sender, sal):

    first = 0
    prev_month = 0
    prev_amount = 0

    first2 = 0
    prev_month2 = 0
    prev_amount2 = 0

    first3 = 0
    prev_month3 = 0
    prev_amount3 = 0

    first4 = 0
    prev_month4 = 0
    prev_amount4 = 0

    first5 = 0
    prev_month5 = 0
    prev_amount5 = 0

    first6 = 0
    prev_month6 = 0
    prev_amount6 = 0

    first7 = 0
    prev_month7 = 0
    prev_amount7 = 0
    
    total = 0
    avg = 0
    debit = 0
    cheque = 0
    atm = 0	
    internet = 0
    transfer = 0

    avg_bal = [] # Avg
    total_bal = [] # Credit
    debit_bal = [] # Debit
    cheque_bal = [] # Cheque
    atm_bal = [] # ATM
    internet_bal = [] # Internet Banking
    transfer_bal = [] # Fund transfer

    avg_data = []
    total_data = []
    debit_data = []
    atm_data = []
    accounts_monthly_bal = []
    accounts_monthly_credit = []
    accounts_monthly_debit = []
    accounts_monthly_bal = []
    all_accounts = []

    count = 0
    fromBank = False
    balance = 0
    senderBank = ""	
    amount = 0
    i = 0

    total_counted = False
    debit_counted = False
    avg_counted = False
    cheque_counted = False
    atm_counted = False
    internet_counted = False
    transfer_counted = False

    for sms in data:
        for l in range(len(bank_id)):
            if ((bank_id[l] in sender[i])):
                fromBank = True # SMS is from bank
                senderBank = bank_id[l]
        if (fromBank):		
            Fail_Pat = re.findall("declined|insufficient|unsuccessful",sms, re.IGNORECASE)
            pattern = re.findall("avl|[^a-zA-Z]available|[^a-zA-Z]avbl[^a-zA-Z]",sms, re.IGNORECASE) # Balance pattern
            pattern2 = re.findall("credited",sms, re.IGNORECASE) # Credit pattern
            pattern3 = re.findall("debited|w\/d",sms, re.IGNORECASE) # Debit pattern
            patternX = re.findall("deposited|amount due",sms, re.IGNORECASE)
            pattern4 = re.findall("cheque",sms, re.IGNORECASE) # Cheque pattern
            pattern5 = re.findall("atm|card",sms, re.IGNORECASE) # ATM Withdrawals pattern
            pattern6 = re.findall("internet banking",sms, re.IGNORECASE) # Internet banking pattern
            pattern7 = re.findall("transferred to",sms, re.IGNORECASE) # Fund transfer pattern
            patternXI = re.findall("your",sms, re.IGNORECASE) 

            # Avg Balance across all accounts each month
            if(pattern != [] and not Fail_Pat):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                
                if (fetchBalance != [] and len(fetchBalance) == 2):
                    amount = re.findall("[^a-zA-Z\\*:.]\d*,?\d*.?\d*\d",fetchBalance[1], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                    
                else:
                    continue	
                if (prev_month != 0 and prev_month != month):
                    if(first):
                        avg_counted = True
                        avg += prev_amount
                        count += 1
                        avg /= count 
                        avg_bal.append({prev_month:avg})
                        avg_data.append(avg)
                        avg = 0
                if (amount) != []:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    accounts_monthly_bal.append({'Bank':senderBank, 'Amount':amount, "date":time.strftime('%d-%m-%Y', time.localtime(int(smsDate[i][:10])))})
                    all_accounts.append({'Bank':senderBank})
                   #print(accounts_monthly_bal)
                    first = 1
                    avg += amount	
                    count += 1		
                    prev_amount = amount
                    prev_month = month
                    

            # Total credit across all accounts each month
            if(pattern2 != []):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                if (fetchBalance != []):
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d",fetchBalance[0], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                else:
                    continue	
                if (prev_month2 != 0 and prev_month2 != month):
                    if(first2):
                        total_counted = True
                        print(total)
                        total += prev_amount2
                        total_bal.append({prev_month2:total})
                        total_data.append(total)
                        total = 0
                if (amount) != 0:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    pc = percentage(amount,sal)
                    if(pc<=120.00):
                        trns_type = "Normal"
                    elif(pc >= 120.0 and pc < 140.0):
                        trns_type = "High"  
                    else:
                        trns_type = "Abnormal"
                    accounts_monthly_credit.append({'Bank':senderBank, 'Amount':amount, "date":time.strftime('%d-%m-%Y', time.localtime(int(smsDate[i][:10]))), 'transaction_type':trns_type })
                    first2 = 1
                    total += amount	
                    prev_amount2 = amount
                    prev_month2 = month	


            # Total debit across all accounts each month
            if( pattern3 != []):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                #print(fetchBalance)
                if (fetchBalance != []):
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d",fetchBalance[0], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                else:
                    continue	
                if (prev_month3 != 0 and prev_month3 != month):
                    if(first3):
                        debit_counted = True
                        debit += prev_amount3
                        debit_bal.append({prev_month3:debit/2})
                        debit_data.append(debit)
                        debit = 0
                if (amount) != []:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    pc = percentage(amount,sal)
                    if(pc<=120.00):
                        trns_type = "Normal"
                    elif(pc > 120.0 and pc <= 140.0):
                        trns_type = "High"  
                    else:
                        trns_type = "Abnormal"
                    accounts_monthly_debit.append({'Bank':senderBank, 'Amount':amount, "date":time.strftime('%d-%m-%Y', time.localtime(int(smsDate[i][:10]))), 'transaction_type':trns_type })
                    first3 = 1
                    debit += amount	
                    prev_amount3 = amount
                    prev_month3 = month

            # Total cheque debits all accounts each month 
            if(patternX != [] and pattern4 != []):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                if (fetchBalance != [] and len(fetchBalance) == 2):
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d",fetchBalance[0], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                else:
                    continue	
                if (prev_month4 != 0 and prev_month4 != month):
                    if(first4):
                        cheque_counted = True
                        cheque += prev_amount4
                        cheque_bal.append({prev_month4:cheque})
                        cheque = 0
                if (amount) != []:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    first4 = 1
                    cheque += amount	
                    prev_amount4 = amount
                    prev_month4 = month		

            # Total ATM withdrawals across all accounts each month
            if(pattern5 != [] and not(Fail_Pat or pattern2)):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                if (fetchBalance != [] and len(fetchBalance) == 2):
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d",fetchBalance[0], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                    #print(fetchBalance)
                else:
                    continue	
                if (prev_month5 != 0 and prev_month5 != month):
                    if(first5):
                        atm_counted = True
                        atm += prev_amount5
                        atm_bal.append({prev_month5:atm})
                        atm_data.append(atm)
                        atm = 0
                if (amount) != []:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    first5 = 1
                    atm += amount	
                    prev_amount5 = amount
                    prev_month5 = month	
                            
            # Total internet banking debit across all accounts each month
            if(pattern6 != [] and not patternX):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                if (fetchBalance != []):
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d",fetchBalance[0], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                else:
                    continue	
                if (prev_month6 != 0 and prev_month6 != month):
                    if(first6):
                        internet_counted = True
                        internet += prev_amount6
                        internet_bal.append({prev_month6:atm})
                        internet = 0
                if (amount) != []:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    first6 = 1
                    internet += amount	
                    prev_amount6 = amount
                    prev_month6 = month	

            # Total fund transfer across all accounts each month
            if(pattern7 != [] and not patternXI):
                fetchBalance = re.findall("INR\s?\d,?\d,?\d\d.?\d.?\d*.?\d*|bal-+\w*\,?\w*\,?\w*.?\w* |Rs.?\s?\d*\d,?\d*.?\d*|INR\s?\d\d\d.?\d\d|INR\s?\d*.?\d*|Bal*?\s?\d\d*.?\d*", sms, re.IGNORECASE)
                if (fetchBalance != [] and len(fetchBalance) == 2):
                    amount = re.findall("[^a-zA-Z\\/*:.]\d*,?\d*.?\d*\d",fetchBalance[0], re.IGNORECASE)
                    month = time.strftime('%m', time.localtime(int(smsDate[i][:10])))
                else:
                    continue	
                if (prev_month7 != 0 and prev_month7 != month):
                    if(first7):
                        transfer_counted = True
                        transfer += prev_amount6
                        transfer_bal.append({prev_month7:transfer})
                if (amount) != []:
                    amount = amount[0].replace(',','')				
                    amount = float(amount)
                    first7 = 1
                    transfer += amount	
                    prev_amount7 = amount
                    prev_month7 = month	

        i += 1
        fromBank = False		
    if(not avg_counted):
        avg_counted = True
        avg += prev_amount
        if(first):
            count = 1
        else:
            count += 1	
        avg /= count
        avg_bal.append({prev_month:avg})
        avg_data.append(total)

    if(not total_counted):
        total_counted = True
        if(first2):
            total = prev_amount2
        else:
            total += prev_amount2
        total_bal.append({prev_month2:total})
        total_data.append(total)

    if(not debit_counted):
        debit_counted = True
        if(first3):
            debit = prev_amount3
        else:
            debit += prev_amount3	
        debit_bal.append({prev_month3:(debit)})
        debit_data.append(debit)

    if(not cheque_counted):
        cheque_counted = True
        if(first4):
            cheque = prev_amount4
        else:
            cheque += prev_amount4
        cheque_bal.append({prev_month4:cheque})

    if(not atm_counted):
        atm_counted = True
        if(first5):
            atm = prev_amount5
        else:
            atm += prev_amount5
        atm_bal.append({prev_month5:atm})
        atm_data.append(atm)

    if(not internet_counted):
        internet_counted = True
        if(first6):
            internet = prev_amount6
        else:
            internet += prev_amount6
        internet_bal.append({prev_month6:internet})	

    if(not transfer_counted):
        transfer_counted = True
        if(first7):
            transfer = prev_amount7
        else:
            transfer += prev_amount7
        transfer += prev_amount7
        transfer_bal.append({prev_month7:transfer})			

    return avg_bal, total_bal, debit_bal, avg_data, total_data, debit_data, cheque_bal, atm_bal, atm_data, internet_bal, transfer_bal, accounts_monthly_bal,accounts_monthly_credit,accounts_monthly_debit,all_accounts																			

# Fetch all EMI related information
def getEmiInfo(data):
    try:
        overdue=[]
        overduekey=[]
        overduekey.append(["EMI","Amount","Bank ","loan a/c no.","due date"])
        overduekey.append(["Gold loan"])
        overduekey.append(["amount","deposited","a/c no.","date","imps"])
        overduekey.append(["Payment record","loan a/c no."])
        overduekey.append([" emi","amount","loan a/c","due date"])
        overduekey.append(["cash payment","amount","agreement No."])
        overduekey.append(["Loan has been Disbursed"])
        overduekey.append(["Loan","Deposited"])
        overduekey.append(["Loan amount","Credited"])
        overduekey.append([" Emi"," Amount"])
        overduekey.append(["Money","Transferred","your account"])
        overduekey.append(["cash payment","amount", "agreement No."])
        overduekey.append([" Emi","Due Date"])
        overduekey.append(["New Loan","Requested","Payment","Amount"])
        overduekey.append(["Payment","due"])
        overduekey.append(["a/c","credited","DISBURSE"])
        overduekey.append(["ready to be transferred","account"])       
        for i in range(len(data['sms_list'])):    
            for o in range(len(overduekey)):
                c=False
                stri={'amount':'','duedate':'','sms':{}}
                for p in range(len(overduekey[o])):
                    c= (overduekey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                    if c==True :
                        break
                    elif (p==(len(overduekey[o])-1)):
                        stri['sms']=data['sms_list'][i]
                        x= re.search(r' Rs([\. ]+)*[\d\,]+', stri['sms']['body'],re.IGNORECASE)
                        if not x:
                            x= re.search(r' INR([\. ]+)*[\d\,]+',stri['sms']['body'],re.IGNORECASE)
                        if x:
                            x=x.group()
                            x = (re.search(r'\d+', x.replace(',','')))
                        if x:
                            stri['amount']=x.group()
                        d= re.search(r'[12][90]\d\d[-/. ]*jan[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-01-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*feb[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-02-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*mar[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-03-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*apr[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-04-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*may[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-05-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*jun[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-06-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*jul[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-07-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*aug[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-08-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*sep[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-09-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*oct[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-10-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*nov[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-11-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*dec[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-12-'+d.group()[:4]
                        d= re.search(r'[0123]\d[-/. ]*jan[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-01-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*feb[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-02-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*mar[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-03-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*apr[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-04-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*may[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-05-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*jun[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-06-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*jul[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-07-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*aug[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-08-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*sep[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-09-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*oct[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-10-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*nov[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-11-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*dec[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-12-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/.][01]\d[-/.][12][90]\d\d',stri['sms']['body'])
                        if d:
                            stri['duedate']= d.group()[:2]+"-"+d.group()[3:5]+"-"+d.group()[6:]    
                        d= re.search(r'[12][90]\d\d[-/.][01]\d[-/.][0123]\d',stri['sms']['body'])
                        if d:
                            stri['duedate']= d.group()[-2:]+"-"+d.group()[5:7]+"-"+d.group()[:4]
                        if stri['duedate']=='':
                            d= re.search(r'\d[\d]*[ ]*\w+[ ]*day[s]*',stri['sms']['body'],re.IGNORECASE)
                            if d:
                                p= re.search(r'\d+',str(d))
                                #print(stri['sms']['date_get'])
                                month =(time.strftime('%m', time.localtime(int(stri['sms']['date_get'][:10]))))
                                day =(time.strftime('%d', time.localtime(int(stri['sms']['date_get'][:10]))))
                                year =(time.strftime('%y', time.localtime(int(stri['sms']['date_get'][:10]))))
                                specific_date = datetime(int(year), int(month), int(day))
                                new_date = str(specific_date + timedelta(int(p.group())))[:10]
                                #print(new_date)

                                #stri['duedate']= d.group()[-2:]+"-"+d.group()[5:7]+"-"+d.group()[:4]
                if stri['sms']!={}:
                    overdue.append(stri)
                    break                    
    except Exception as e:
        print(traceback.format_exc())
        return {'Error: E11':'API Error ->'+str(e)}
    if (overdue != []):
        return overdue,201
    else:
        return {'amount':'','duedate':'','sms':{}},201

# Check for EMI overdue information from sms
def getOverdueEmiInfo(data):
    try:
        overdue=[]
        overduekey=[]
        overduekey.append([" Loan amount "," overdue "])
        overduekey.append([" Emi "," Unpaid "])
        overduekey.append([" Emi "," amount "," Non-payment "])
        overduekey.append([" EMI ","OUTSTANDING"])
        overduekey.append([" re-payment "," over-due "])
        overduekey.append([" reminder "," overdue payment "])
        overduekey.append([" Loan "," still due "])
        overduekey.append([" emi is overdue "])
        overduekey.append([" emi has been overdue "])
        overduekey.append([" Attention "," Emi "," not paid "])
        overduekey.append([" Loan "," overdue "," since "])
        overduekey.append([" Emi "," overdue "," since "])
        overduekey.append([" Emi "," still not paid "])
        overduekey.append([" Loan account "," overdue "])
        overduekey.append([" Payment Pending "])
        overduekey.append([" Emi "," Pending "])
        overduekey.append([" Agmt no"," Overdue "])
        overduekey.append([" Emi overdue"])        
        for i in range(len(data['sms_list'])):    
            for o in range(len(overduekey)):
                c=False
                stri={'amount':'','duedate':'','sms':{}}
                for p in range(len(overduekey[o])):
                    c= (overduekey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                    if c==True :
                        break
                    elif (p==(len(overduekey[o])-1)):
                        stri['sms']=data['sms_list'][i]
                        x= re.search(r' Rs([\. ]+)*[\d\,]+', stri['sms']['body'],re.IGNORECASE)
                        if not x:
                            x= re.search(r' INR([\. ]+)*[\d\,]+',stri['sms']['body'],re.IGNORECASE)
                        if x:
                            x=x.group()
                            x = (re.search(r'\d+', x.replace(',','')))
                        if x:
                            stri['amount']=x.group()
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*jan[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-01-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*feb[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-02-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*mar[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-03-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*apr[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-04-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*may[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-05-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*jun[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-06-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*jul[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-07-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*aug[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-08-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*sep[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-09-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*oct[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-10-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*nov[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-11-'+duePattern.group()[:4]
                        duePattern= re.search(r'[12][90]\d\d[-/. ]*dec[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+'-12-'+duePattern.group()[:4]
                        duePattern= re.search(r'[0123]\d[-/. ]*jan[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-01-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*feb[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-02-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*mar[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-03-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*apr[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-04-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*may[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-05-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*jun[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-06-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*jul[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-07-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*aug[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-08-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*sep[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-09-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*oct[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-10-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*nov[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-11-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/. ]*dec[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-12-"+duePattern.group()[-4:]
                        duePattern= re.search(r'[0123]\d[-/.][01]\d[-/.][12][90]\d\d',stri['sms']['body'])
                        if duePattern:
                            stri['duedate']= duePattern.group()[:2]+"-"+duePattern.group()[3:5]+"-"+duePattern.group()[6:]    
                        duePattern= re.search(r'[12][90]\d\d[-/.][01]\d[-/.][0123]\d',stri['sms']['body'])
                        if duePattern:
                            stri['duedate']= duePattern.group()[-2:]+"-"+duePattern.group()[5:7]+"-"+duePattern.group()[:4]
                        if stri['duedate']=='':
                            duePattern= re.search(r'\d[\d]*[ ]*\w+[ ]*day[s]*',stri['body'],re.IGNORECASE)
                            if duePattern:
                                p= re.search(r'\d+',duePattern)
                                month =(time.strftime('%m', time.localtime(int(stri['data_get'][:10]))))
                                day =(time.strftime('%d', time.localtime(int(stri['data_get'][:10]))))
                                year =(time.strftime('%y', time.localtime(int(stri['data_get'][:10]))))
                                specific_date = datetime(year, month, day)
                                new_date = str(specific_date + timedelta(int(p.group())))[:10]
                                stri['duedate']= duePattern.group()[-2:]+"-"+duePattern.group()[5:7]+"-"+duePattern.group()[:4]
                if stri['sms']!={}:
                    overdue.append(stri)
                    break                    
    except Exception as e:
        print(traceback.format_exc())
        return {'Error: E11':'API Error ->'+str(e)}
    if (overdue != []):
        return overdue,201
    else:
        return {'amount':'','duedate':'','sms':{}},201


def getBillOverdueInfo(data):
    try:
        billoverdue=[]
        billoverduekey=[]
        billoverduekey.append(["Broadband","bill overdue"])
        billoverduekey.append(["Bill overdue"])
        billoverduekey.append(["Postpaid","bill overdue"])
        billoverduekey.append(["overdue","Airtel"])
        billoverduekey.append(["overdue","Idea"])
        billoverduekey.append(["Landline","bill overdue"])
        billoverduekey.append(["Electricity", "bill overdue"])
        billoverduekey.append(["Elec.Bill o/d"])
        for i in range(len(data['sms_list'])):    
            for o in range(len(billoverduekey)):
                c=False
                stri={'amount':'','duedate':'','sms':{}}
                for p in range(len(billoverduekey[o])):
                    c= (billoverduekey[o][p].lower() not in data['sms_list'][i]['body'].lower()) or c
                    if c==True :
                        break
                    elif (p==(len(billoverduekey[o])-1)):
                        stri['sms']=data['sms_list'][i]
                        x= re.search(r' Rs([\. ]+)*([\d\,]+)', stri['sms']['body'],re.IGNORECASE)
                        if not x:
                            x= re.search(r' INR([\. ]+)*[\d\,]+',stri['sms']['body'],re.IGNORECASE)
                        if x:
                            x=x.group()
                            x = (re.search(r'\d+', x.replace(',','')))
                        if x:
                            stri['amount']=x.group()
                        d= re.search(r'[12][90]\d\d[-/. ]*jan[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-01-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*feb[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-02-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*mar[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-03-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*apr[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-04-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*may[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-05-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*jun[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-06-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*jul[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-07-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*aug[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-08-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*sep[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-09-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*oct[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-10-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*nov[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-11-'+d.group()[:4]
                        d= re.search(r'[12][90]\d\d[-/. ]*dec[-/. ]*[0123]\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[-2:]+'-12-'+d.group()[:4]
                        d= re.search(r'[0123]\d[-/. ]*jan[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-01-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*feb[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-02-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*mar[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-03-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*apr[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-04-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*may[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-05-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*jun[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-06-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*jul[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-07-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*aug[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-08-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*sep[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-09-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*oct[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-10-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*nov[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-11-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/. ]*dec[-/. ]*[12][90]\d\d',stri['sms']['body'],re.IGNORECASE)
                        if d:
                            stri['duedate']= d.group()[:2]+"-12-"+d.group()[-4:]
                        d= re.search(r'[0123]\d[-/.][01]\d[-/.][12][90]\d\d',stri['sms']['body'])
                        if d:
                            stri['duedate']= d.group()[:2]+"-"+d.group()[3:5]+"-"+d.group()[6:]    
                        d= re.search(r'[12][90]\d\d[-/.][01]\d[-/.][0123]\d',stri['sms']['body'])
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
                if stri['sms']!={}:
                    billoverdue.append(stri)
                    break
    except Exception as e:
        print(traceback.format_exc())
        return {'Error: E12':'API Error ->'+str(e)},201
    if (billoverdue != []):
        return billoverdue,201
    else:
        return {'amount':'','duedate':'','sms':{}},201

def debug(message):
    if isinstance(message, str):
        print("\033[92m DEBUG: {}\033[00m" .format(message))
    else:
        print("\033[92m DEBUG: ")
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(message)
        print("\033[00m")

def debugred(message):
    print("\033[91m {}\033[00m" .format(message)) 

def debugpurple(message):
    print("\033[95m {}\033[00m" .format(message)) 

def getUserJsonData(userId):
    query_total_users = "SELECT stored_path FROM uploads where user_id="+str(userId)+" and extension='json' order by id desc limit 1"
    cursor = connection.cursor()
    cursor.execute(query_total_users)
    row_headers=[x[0] for x in cursor.description] #this will extract row headers
    rv = cursor.fetchall()
    json_data=[]
    for result in rv:
            json_data.append(dict(zip(row_headers,result)))
    print(json_data)
    return json_data

def getUserBasicInfo(userId):
    query_total_users = "SELECT content FROM pplv2.answers where user_id = "+str(userId)+" and question_id in (21, 22, 37)"
    cursor = connection.cursor()
    cursor.execute(query_total_users)
    row_headers=[x[0] for x in cursor.description] #this will extract row headers
    rv = cursor.fetchall()
    json_data=[]
    for result in rv:
            json_data.append(dict(zip(row_headers,result)))
    print(json_data)
    return json_data

def mergeJsonFiles():
    result = []
    for f in glob.glob("*.json"):
        with open(f, "rb") as infile:
            result.append(json.load(infile))

    with open("merged_file.json", "wb") as outfile:
        return json.dump(result, outfile)

def isNaN(num):
    return num != num

