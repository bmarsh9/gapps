import csv
import json
import os

control_dict = []

counter = {
  1:"a",
  2:"b",
  3:"c",
  4:"d",
  5:"e",
  6:"f",
  7:"g",
  8:"h",
  9:"i",
  10:"j",
  11:"k",
  12:"l",
  13:"m",
  14:"n",
  15:"o",
  16:"p",
}
ext_dict = {}
with open('cmmc_ext.tsv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t',quotechar='"')
    for row in reader:
      id = row["CMMCv2 Practice"].lower().strip()
      if id.startswith("rm."):
          id = "ra.{}".format(".".join(id.split(".")[1:]))
      ext_dict[id] = row

#print("ra.l2-3.11.1" in ext_dict.keys())
#print(json.dumps(ext_dict,indent=4))
with open('cmmc_controls.tsv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t',quotechar='"')
    for row in reader:
        ext = ext_dict[row["Reference"].lower().strip()]
        for i in ["Requirement","Determination Statements","Guidance","CMMCv2 Domains"]:
            row[i] = ext[i]

        subcontrols = []
        code = row["Reference"].split("-")[1]
        parsed_statements = [x for x in row["Determination Statements"].split(code) if x]
        for enum,i in enumerate(parsed_statements,1):
            subcontrol_name = i.strip().capitalize()
            if "]" in i:
                subcontrol_name = i.split("]")[1].strip().capitalize()
            subcontrol_code = f"{code}.{counter[enum]}"
            subcontrols.append({
                "ref_code":subcontrol_code,
                "name":subcontrol_name,
                "description":subcontrol_name,
                "meta":{}
            })

        mitigation=" ".join([x.strip() for x in row["Mitigation"].split("- ") if x])
        mitigation = f"{row['Guidance']}{mitigation}"
        record = {
          "name": row["Name"],
          "description":row["Requirement"],
          "mitigation":mitigation,
          "ref_code": row["Reference"],
          "system_level": False,
          "subcategory": row["kill-chain"].split("-")[1].strip(),
#          "subcategory": row["tech-considerations"],
          "category": row["CMMCv2 Domains"],
          "dti": "easy",
          "dtc": "easy",
          "meta": {},
          "subcontrols": subcontrols
        }
        if row["level-1"] == "x":
            level = 1
        else:
            level = 2
        record["level"] = level
        recs = {}
        mapping = {}
        for key in row.keys():
            if key.startswith("s-"):
                recs[key.split("-")[1]] = [x.strip() for x in row[key].split("-") if x]
            elif key.startswith("m-"):
                fw_key = key.split("-")[1].lower().replace(" ","_")
                mapping[fw_key] = [x.strip().lower() for x in row[key].split(" ") if x]
        record["mapping"] = mapping
        record["vendor_recommendations"] = recs
        record["vendor_recommendations"]["enterprise"] = record["vendor_recommendations"]["enterprice"]
        record["vendor_recommendations"].pop("enterprice",None)
        control_dict.append(record)

print(json.dumps(control_dict,indent=4))


'''
          record = {
          "name": control,
          "description": guidance,
          "ref_code": cid,
          "system_level": False,
          "category": row["REQUIREMENT"],
          "subcategory": row["DOMAIN"],
          "dti": "easy",
          "dtc": "easy",
          "meta": {},
          "subcontrols": []
          }
'''
'''
    {
        "Reference": "SI.L2-3.14.7",
        "Name": "Identify unauthorized use of organizational systems.",
        "Mitigation": "- Administrative: documented policies, standards & procedures - Administrative: supporting documentation to demonstrate Indicators of Compromise (IoC) - Administrative: supporting documentation to demonstrate how Network Intrusion Detection / Prevention (NIDS/NIPS) are deployed and maintained - Administrative: supporting documentation to demonstrate how File Integrity Monitoring (FIM) are deployed and maintained - Administrative: supporting documentation of threat intelligence feeds to maintain situational awareness - Administrative: supporting documentation of role-based security training being performed - Administrative: supporting documentation of professional competence by individual(s) performing event log analysis and response roles - Technical: screen shot of logs from SIEM - Technical: screen shot of logs from NIDS/NIPS - Technical: screen shot of logs from FIM",
        "kill-chain": "17 - Personnel Security",
        "level-1": "N/A",
        "level-2": "x",
        "tech-considerations": "Network Baselines Security Information & Event Management (SIEM)",
        "s-micro": "- Untangle - Suricata - Kiwi Syslog Server - CUICK TRAC",
        "s-small": "- Untangle - Suricata - NeQter Labs - Paessler PRTG - CUICK TRAC",
        "s-medium": "- Barracuda CloudGen - Cisco NGIPS - NeQter Labs - Paessler PRTG - Splunk - AlienVault (AT&T Security)",
        "s-large": "- Cisco NGIPS - F5  - Palo Alto  - Juniper - Splunk",
        "s-enterprice": "- Cisco NGIPS - F5  - Palo Alto  - Juniper - Splunk",
        "m-FAR 52.204-21": "",
        "m-NIST 800-171": "3.14.7",
        "": "MON:SG1.SP3",
        "m-ISO 27002:2013": "",
        "m-ISO 27002:2022": "8.15",
        "m-NIST CSF": "DE.CM-1 DE.CM-7",
        "m-CIS v7.1": "",
        "m-CIS v8.0": "3.14 8.0 8.1 8.2 8.3 8.4 8.5 8.6 8.7 8.8 8.9 8.12 12.1 13.0 13.6",
        "m-Secure Controls Framework": "MON-02.1"
    }
'''
