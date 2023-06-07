import json
import sys

#{'source': 'asvs_v4.0.1', 'id': 'asvs_v4.0.1:14.1.3', 'id_raw': '14.1.3', 'tier_raw': 'Item', 'tier': 1, 'seq': None, 'title': None, 'description': 'Verify that server configuration is hardened as per the recommendations of the application server and frameworks in use.'}
sources = ['cis_csc_v7.1', 'nist_800_171_v1', 'nist_800_53_v4', 'nist_csf_v1.1', 'owasp_10_v3', 'asvs_v4.0.1']

top={}
control_map = {
    "v1": "Architecture, Design and Threat Modeling",
    "v2": "Authentication Verification",
    "v3": "Session Management Verification",
    "v4": "Access Control Verification",
    "v5": "Validation, Sanitization and Encoding Verification",
    "v6": "Stored Cryptography Verification",
    "v7": "Error Handling and Logging Verification",
    "v8": "Data Protection Verification",
    "v9": "Communications Verification",
    "v10": "Malicious Code Verification",
    "v11": "Business Logic Verification",
    "v12": "File and Resources Verification",
    "v13": "API and Web Service Verification",
    "v14": "Configuration Verification"
}

map = {'v1.1': 'Secure Software Development Lifecycle', 'v1.2': 'Authentication Architectural', 'v1.3': 'Session Management Architectural', 'v1.4': 'Access Control Architectural', 'v1.5': 'Input and Output Architectural', 'v1.6': 'Cryptographic Architectural', 'v1.7': 'Errors, Logging and Auditing Architectural', 'v1.8': 'Data Protection and Privacy Architectural', 'v1.9': 'Communications Architectural', 'v1.10': 'Malicious Software Architectural', 'v1.11': 'Business Logic Architectural', 'v1.12': 'Secure File Upload Architectural', 'v1.13': 'API Architectural', 'v1.14': 'Configuration Architectural', 'v2.1': 'Password Security', 'v2.2': 'General Authenticator', 'v2.3': 'Authenticator Lifecycle', 'v2.4': 'Credential Storage', 'v2.5': 'Credential Recovery', 'v2.6': 'Look-up Secret Verifier', 'v2.7': 'Out of Band Verifier', 'v2.8': 'Single or Multi Factor One Time Verifier', 'v2.9': 'Cryptographic Software and Devices Verifier', 'v2.10': 'Service Authentication', 'v3.1': 'Fundamental Session Management', 'v3.2': 'Session Binding', 'v3.3': 'Session Logout and Timeout', 'v3.4': 'Cookie-based Session Management', 'v3.5': 'Token-based Session Management', 'v3.6': 'Re-authentication from a Federation or Assertion', 'v3.7': 'Defenses Against Session Management Exploits', 'v4.1': 'General Access Control Design', 'v4.2': 'Operation Level Access Control', 'v4.3': 'Other Access Control Considerations', 'v5.1': 'Input Validation', 'v5.2': 'Sanitization and Sandboxing', 'v5.3': 'Output encoding and Injection Prevention', 'v5.4': 'Memory, String, and Unmanaged Code', 'v5.5': 'Deserialization Prevention', 'v6.1': 'Data Classification', 'v6.2': 'Algorithms', 'v6.3': 'Random Values', 'v6.4': 'Secret Management', 'v7.1': 'Log Content', 'v7.2': 'Log Processing', 'v7.3': 'Log Protection', 'v7.4': 'Error Handling', 'v8.1': 'General Data Protection', 'v8.2': 'Client-side Data Protection', 'v8.3': 'Sensitive Private Data', 'v9.1': 'Communications Security', 'v9.2': 'Server Communications Security', 'v10.1': 'Code Integrity Controls', 'v10.2': 'Malicious Code Search', 'v10.3': 'Deployed Application Integrity Controls', 'v11.1': 'Business Logic Security', 'v12.1': 'File Upload', 'v12.2': 'File Integrity', 'v12.3': 'File execution', 'v12.4': 'File Storage', 'v12.5': 'File Download', 'v12.6': 'SSRF Protection', 'v13.1': 'Generic Web Service Security Verification', 'v13.2': 'RESTful Web Service Verification', 'v13.3': 'SOAP Web Service Verification', 'v13.4': 'GraphQL and other Web Service Data Layer Security', 'v14.1': 'Build', 'v14.2': 'Dependency', 'v14.3': 'Unintended Security Disclosure', 'v14.4': 'HTTP Security Headers', 'v14.5': 'Validate HTTP Request Header '}

file = "controls.json"
with open(file) as f:
    controls=json.load(f)
    for index, control in enumerate(controls,1):
        if control.get("source") == "asvs_v4.0.1":
          if control["tier_raw"] == "Item":
            id = control.get("id_raw").lower()
            first_dig = id[0]
            first_2_dig = ".".join(id.split(".")[:2])

            category = control_map[f"v{first_dig}"]
            subcategory = map[f"v{first_2_dig}"].strip()

            name = control["title"]
            description = control["description"]
            if name:
              name = name.replace("\u00a0"," ")
            if description:
              description = description.replace("\u00a0"," ")
            new_id = id
#haaaa

            record = {
                "name": name or description,
                "description": description or name,
                "ref_code": "v"+new_id,
                "level": "1",
                "system_level": False,
                "category": category,
                "subcategory": subcategory,
                "dti": "easy",
                "dtc": "easy",
                "meta": {},
                "subcontrols":[]
            }
            top[new_id] = record

#print(json.dumps(top,indent=4))
'''
d= {}
for k,v in map.items():
  print(k,v)
  control_map[k[1]]

  d[k] = {
                "name": v,
                "description": v + " Requirements",
                "ref_code": k,
                "system_level": False,
                "category": ,
                "subcategory": subcategory,
                "dti": "easy",
                "dtc": "easy",
                "meta": {},
                "subcontrols":[]
  }
'''

#print(json.dumps(control_map,indent=4))
data = []
for ref,control in top.items():
 data.append(control)
print(json.dumps(data,indent=4))

#            control_map[name] = {"id":id,"category":category,"subcategory":control.get("tier_raw").lower() or category,"subcontrols":[]}
