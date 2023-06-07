import csv
import json
import os

'''
control_dict = {}

with open('controls.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t',quotechar='"')
    for row in reader:
        if row["Category"] not in control_dict:
            control_dict[row["CIS Controls"]] = {
              "name":row["Category"],"description":"","ref_code":f"cis{row['CIS Controls']}",
              "system_level":False,"category":row["Category"],"subcategory":row["subcategory"],"dti":"easy","dtc":"easy","meta":{},"subcontrols":[]
            }

print(json.dumps(control_dict,indent=4))
'''

'''
'''

controls = {
    "1": {
        "name": "Inventory and Control of Enterprise Assets",
        "description": "",
        "ref_code": "cis1",
        "system_level": False,
        "category": "Inventory and Control of Enterprise Assets",
        "subcategory": "Devices",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2": {
        "name": "Inventory and Control of Software Assets",
        "description": "",
        "ref_code": "cis2",
        "system_level": False,
        "category": "Inventory and Control of Software Assets",
        "subcategory": "Applications",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3": {
        "name": "Data Protection",
        "description": "",
        "ref_code": "cis3",
        "system_level": False,
        "category": "Data Protection",
        "subcategory": "Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "4": {
        "name": "Secure Configuration of Enterprise Assets and Software",
        "description": "",
        "ref_code": "cis4",
        "system_level": False,
        "category": "Secure Configuration of Enterprise Assets and Software",
        "subcategory": "Devices",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "5": {
        "name": "Account Management",
        "description": "",
        "ref_code": "cis5",
        "system_level": False,
        "category": "Account Management",
        "subcategory": "Users",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6": {
        "name": "Access Control Management",
        "description": "",
        "ref_code": "cis6",
        "system_level": False,
        "category": "Access Control Management",
        "subcategory": "Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "7": {
        "name": "Continuous Vulnerability Management",
        "description": "",
        "ref_code": "cis7",
        "system_level": False,
        "category": "Continuous Vulnerability Management",
        "subcategory": "Applications",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8": {
        "name": "Audit Log Management",
        "description": "",
        "ref_code": "cis8",
        "system_level": False,
        "category": "Audit Log Management",
        "subcategory": "Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9": {
        "name": "Email and Web Browser Protections",
        "description": "",
        "ref_code": "cis9",
        "system_level": False,
        "category": "Email and Web Browser Protections",
        "subcategory": "Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10": {
        "name": "Malware Defenses",
        "description": "",
        "ref_code": "cis10",
        "system_level": False,
        "category": "Malware Defenses",
        "subcategory": "Devices",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11": {
        "name": "Data Recovery",
        "description": "",
        "ref_code": "cis11",
        "system_level": False,
        "category": "Data Recovery",
        "subcategory": "Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12": {
        "name": "Network Infrastructure Management",
        "description": "",
        "ref_code": "cis12",
        "system_level": False,
        "category": "Network Infrastructure Management",
        "subcategory": "Devices",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "13": {
        "name": "Network Monitoring and Defense",
        "description": "",
        "ref_code": "cis13",
        "system_level": False,
        "category": "Network Monitoring and Defense",
        "subcategory": "Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "14": {
        "name": "Security Awareness and Skills Training",
        "description": "",
        "ref_code": "cis14",
        "system_level": False,
        "category": "Security Awareness and Skills Training",
        "subcategory": "N/A",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "15": {
        "name": "Service Provider Management",
        "description": "",
        "ref_code": "cis15",
        "system_level": False,
        "category": "Service Provider Management",
        "subcategory": "Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "16": {
        "name": "Application Software Security",
        "description": "",
        "ref_code": "cis16",
        "system_level": False,
        "category": "Application Software Security",
        "subcategory": "Applications",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "17": {
        "name": "Incident Response Management",
        "description": "",
        "ref_code": "cis17",
        "system_level": False,
        "category": "Incident Response Management",
        "subcategory": "N/A",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "18": {
        "name": "Penetration Testing",
        "description": "",
        "ref_code": "cis18",
        "system_level": False,
        "category": "Penetration Testing",
        "subcategory": "N/A",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    }
}

#haaaaaaaaaa

with open('controls.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t',quotechar='"')
    for row in reader:
        id = row["CIS Controls"]
        ref_code = row["CIS Safeguards"]
#        print(row["g3"])

        if row["g1"]:
            level = 1
        elif row["g2"]:
            level = 2
        else:
            level = 3
        controls[id]["subcontrols"].append(
          {"name":row["Title"],"description":row["Description"],"ref_code":f"{row['CIS Safeguards']}","mitigation":"","meta":{},"implementation_group":level}
        )

#print(json.dumps(controls,indent=4))

d=[]
for k,v in controls.items():
  d.append(v)
print(json.dumps(d,indent=4))
