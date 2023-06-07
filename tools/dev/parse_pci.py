import csv
import json
import os
import sys

'''
control_dict = {}
with open('pci_controls.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t',quotechar='"')
    for row in reader:
        cid = row["CID"]
        print(cid)
        if cid.count(".") == 1:
          control = " ".join(row["CONTROL"].split(" ")[1:])
          guidance = row["GUIDANCE"]
          for i in ["\u201c","\u201d","\u2019"]:
              control = control.replace(i,"'")
              guidance = guidance.replace(i,"'")

          control = control.replace("\u2014","-")
          guidance = guidance.replace("\u2014","-")
          control = control.replace("\uf0b7","")
          guidance = guidance.replace("\uf0b7","")
          control = control.replace("     "," ")
          guidance = guidance.replace("     "," ")

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
          control_dict[cid] = record

print(json.dumps(control_dict,indent=4))

exit()
'''

controls = {
    "1.1": {
        "name": "Establish and implement firewall and router configuration standards that include the following:",
        "description": "Firewalls and routers are key components of the architecture that controls entry to and exit from the network. These devices are software or hardware devices that block unwanted access and manage authorized access into and out of the network. Configuration standards and procedures will help to ensure that the organization's first line of defense in the protection of its data remains strong.",
        "ref_code": "1.1",
        "system_level": False,
        "category": "Requirement 1: Install and maintain a firewall configuration to protect cardholder data",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "1.2": {
        "name": "Build firewall and router configurations that restrict connections between untrusted networks and any system components in the cardholder data environment. Note: An 'untrusted network' is any network that is external to the networks belonging to the entity under review, and/or which is out of the entity's ability to control or manage.",
        "description": "It is essential to install network protection between the internal, trusted network and any untrusted network that is external and/or out of the entity's ability to control or manage. Failure to implement this measure correctly results in the entity being vulnerable to unauthorized access by malicious individuals or software. For firewall functionality to be effective, it must be properly configured to control and/or limit traffic into and out of the entity's network.",
        "ref_code": "1.2",
        "system_level": False,
        "category": "Requirement 1: Install and maintain a firewall configuration to protect cardholder data",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "1.3": {
        "name": "Prohibit direct public access between the Internet and any system component in the cardholder data environment.",
        "description": "A firewall's intent is to manage and control all connections between public systems and internal systems, especially those that store, process or transmit cardholder data. If direct access is allowed between public systems and the CDE, the protections offered by the firewall are bypassed, and system components storing cardholder data may be exposed to compromise.",
        "ref_code": "1.3",
        "system_level": False,
        "category": "Requirement 1: Install and maintain a firewall configuration to protect cardholder data",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "1.4": {
        "name": "Install personal firewall software on any mobile and/or employee-owned devices that connect to the Internet when outside the network (for example, laptops used by employees), and which are also used to access the network. Firewall configurations include: Specific configuration settings are defined for personal firewall software. Personal firewall software is actively running. Personal firewall software is not alterable by users of mobile and/or employee-owned devices.",
        "description": "Portable computing devices that are allowed to connect to the Internet from outside the corporate firewall are more vulnerable to Internet-based threats. Use of a personal firewall helps to protect devices from Internet-based attacks, which could use the device to gain access the organization's systems and data once the device is re-connected to the network. The specific firewall configuration settings are determined by the organization. Note: The intent of this requirement applies to employee-owned and company-owned computers. Systems that cannot be managed by corporate policy introduce weaknesses to the perimeter and provide opportunities that malicious individuals may exploit. Allowing untrusted systems to connect to an organization's network could result in access being granted to attackers and other malicious users.",
        "ref_code": "1.4",
        "system_level": False,
        "category": "Requirement 1: Install and maintain a firewall configuration to protect cardholder data",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "1.5": {
        "name": "Ensure that security policies and operational procedures for managing firewalls are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures to ensure firewalls and routers are continuously managed to prevent unauthorized access to the network.",
        "ref_code": "1.5",
        "system_level": False,
        "category": "Requirement 1: Install and maintain a firewall configuration to protect cardholder data",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2.1": {
        "name": "Always change vendor-supplied defaults and remove or disable unnecessary default accounts before installing a system on the network. This applies to ALL default passwords, including but not limited to those used by operating systems, software that provides security services, application and system accounts, point-of-sale (POS) terminals, Simple Network Management Protocol (SNMP) community strings, etc.).",
        "description": "Malicious individuals (external and internal to an organization) often use vendor default settings, account names, and passwords to compromise operating system software, applications, and the systems on which they are installed. Because these default settings are often published and are well known in hacker communities, changing these settings will leave systems less vulnerable to attack. Even if a default account is not intended to be used, changing the default password to a strong unique password and then disabling the account will prevent a malicious individual from re-enabling the account and gaining access with the default password.",
        "ref_code": "2.1",
        "system_level": False,
        "category": "Requirement 2: Do not use vendor-supplied defaults for system passwords and other security parameters",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2.2": {
        "name": "Develop configuration standards for all system components. Assure that these standards address all known security vulnerabilities and are consistent with industry-accepted system hardening standards. Sources of industry-accepted system hardening standards may include, but are not limited to: Center for Internet Security (CIS) International Organization for Standardization (ISO) SysAdmin Audit Network Security (SANS) Institute National Institute of Standards Technology (NIST).",
        "description": "There are known weaknesses with many operating systems, databases, and enterprise applications, and there are also known ways to configure these systems to fix security vulnerabilities. To help those that are not security experts, a number of security organizations have established system-hardening guidelines and recommendations, which advise how to correct these weaknesses. Examples of sources for guidance on configuration standards include, but are not limited to: www.nist.gov, www.sans.org, and www.cisecurity.org, www.iso.org, and product vendors. System configuration standards must be kept up to date to ensure that newly identified weaknesses are corrected prior to a system being installed on the network.",
        "ref_code": "2.2",
        "system_level": False,
        "category": "Requirement 2: Do not use vendor-supplied defaults for system passwords and other security parameters",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2.3": {
        "name": "Encrypt all non-console administrative access using strong cryptography. Use technologies such as SSH, VPN, or TLS for web-based management and other non-console administrative access. Note: SSL and early TLS are not considered strong cryptography and cannot be used as a security control after June 30, 2016. Prior to this date, existing implementations that use SSL and/or early TLS must have a formal Risk Mitigation and Migration Plan in place. Effective immediately, new implementations must not use SSL or early TLS. POS POI terminals (and the SSL/TLS termination points to which they connect) that can be verified as not being susceptible to any known exploits for SSL and early TLS may continue using these as a security control after June 30, 2016.",
        "description": "If non-console (including remote) administration does not use secure authentication and encrypted communications, sensitive administrative or operational level information (like administrator's IDs and passwords) can be revealed to an eavesdropper. A malicious individual could use this information to access the network, become administrator, and steal data. Clear-text protocols (such as HTTP, telnet, etc.) do not encrypt traffic or logon details, making it easy for an eavesdropper to intercept this information. (Continued on next page) To be considered 'strong cryptography,' industry- recognized protocols with appropriate key strengths and key management should be in place as applicable for the type of technology in use. (Refer to \"strong cryptography' in the PCI DSS and PA-DSS Glossary of Terms, Abbreviations, and Acronyms, and industry standards and best practices such as NIST SP 800-52 and SP 800-57, OWASP, etc.) Regarding use of SSL/early TLS: Entities using SSL and early TLS must work towards upgrading to a strong cryptographic protocol as soon as possible. Additionally, SSL and/or early TLS must not be introduced into environments where they don't already exist. At the time of publication, the known vulnerabilities are difficult to exploit in POS POI payment environments. However, new vulnerabilities could emerge at any time, and it is up to the organization to remain up-to-date with vulnerability trends and determine whether or not they are susceptible to any known exploits. Refer to the PCI SSC Information Supplement Migrating from SSL and Early TLS for further guidance on the use of SSL/early TLS.",
        "ref_code": "2.3",
        "system_level": False,
        "category": "Requirement 2: Do not use vendor-supplied defaults for system passwords and other security parameters",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2.4": {
        "name": "Maintain an inventory of system components that are in scope for PCI DSS.",
        "description": "Maintaining a current list of all system components will enable an organization to accurately and efficiently define the scope of their environment for implementing PCI DSS controls. Without an inventory, some system components could be forgotten, and be inadvertently excluded from the organization's configuration standards.",
        "ref_code": "2.4",
        "system_level": False,
        "category": "Requirement 2: Do not use vendor-supplied defaults for system passwords and other security parameters",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2.5": {
        "name": "Ensure that security policies and operational procedures for managing vendor defaults and other security parameters are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and daily operational procedures to ensure vendor defaults and other security parameters are continuously managed to prevent insecure configurations.",
        "ref_code": "2.5",
        "system_level": False,
        "category": "Requirement 2: Do not use vendor-supplied defaults for system passwords and other security parameters",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "2.6": {
        "name": "Shared hosting providers must protect each entity's hosted environment and cardholder data. These providers must meet specific requirements as detailed in Appendix A: Additional PCI DSS Requirements for Shared Hosting Providers.",
        "description": "This is intended for hosting providers that provide shared hosting environments for multiple clients on the same server. When all data is on the same server and under control of a single environment, often the settings on these shared servers are not manageable by individual clients. This allows clients to add insecure functions and scripts that impact the security of all other client environments; and thereby make it easy for a malicious individual to compromise one client's data and thereby gain access to all other clients' data. See Appendix A for details of requirements.",
        "ref_code": "2.6",
        "system_level": False,
        "category": "Requirement 2: Do not use vendor-supplied defaults for system passwords and other security parameters",
        "subcategory": "Build and Maintain a Secure Network",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.1": {
        "name": "Keep cardholder data storage to a minimum by implementing data retention and disposal policies, procedures and processes that include at least the following for all cardholder data (CHD) storage: Limiting data storage amount and retention time to that which is required for legal, regulatory, and/or business requirements Specific retention requirements for cardholder data Processes for secure deletion of data when no longer needed A quarterly process for identifying and securely deleting stored cardholder data that exceeds defined retention.",
        "description": "A formal data retention policy identifies what data needs to be retained, and where that data resides so it can be securely destroyed or deleted as soon as it is no longer needed. The only cardholder data that may be stored after authorization is the primary account number or PAN (rendered unreadable), expiration date, cardholder name, and service code. Understanding where cardholder data is located is necessary so it can be properly retained or disposed of when no longer needed. In order to define appropriate retention requirements, an entity first needs to understand their own business needs as well as any legal or regulatory obligations that apply to their industry, and/or that apply to the type of data being retained. (Continued on next page) Identifying and deleting stored data that has exceeded its specified retention period prevents unnecessary retention of data that is no longer needed. This process may be automated or manual or a combination of both. For example, a programmatic procedure (automatic or manual) to locate and remove data and/or a manual review of data storage areas could be performed. Implementing secure deletion methods ensure that the data cannot be retrieved when it is no longer needed. Remember, if you don't need it, don't store it!",
        "ref_code": "3.1",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.2": {
        "name": "Do not store sensitive authentication data after authorization (even if encrypted). If sensitive authentication data is received, render all data unrecoverable upon completion of the authorization process. It is permissible for issuers and companies that support issuing services to store sensitive authentication data if: There is a business justification and The data is stored securely. Sensitive authentication data includes the data as cited in the following Requirements 3.2.1 through 3.2.3:",
        "description": "Sensitive authentication data consists of full track data, card validation code or value, and PIN data. Storage of sensitive authentication data after authorization is prohibited! This data is very valuable to malicious individuals as it allows them to generate counterfeit payment cards and create fraudulent transactions. Entities that issue payment cards or that perform or support issuing services will often create and control sensitive authentication data as part of the issuing function. It is allowable for companies that perform, facilitate, or support issuing services to store sensitive authentication data ONLY IF they have a legitimate business need to store such data. It should be noted that all PCI DSS requirements apply to issuers, and the only exception for issuers and issuer processors is that sensitive authentication data may be retained if there is a legitimate reason to do so. A legitimate reason is one that is necessary for the performance of the function being provided for the issuer and not one of convenience. Any such data must be stored securely and in accordance with all PCI DSS and specific payment brand requirements. For non-issuing entities, retaining sensitive authentication data post-authorization is not permitted.",
        "ref_code": "3.2",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.3": {
        "name": "Mask PAN when displayed (the first six and last four digits are the maximum number of digits to be displayed), such that only personnel with a legitimate business need can see the full PAN. Note: This requirement does not supersede stricter requirements in place for displays of cardholder data-for example, legal or payment card brand requirements for point-of-sale (POS) receipts.",
        "description": "The display of full PAN on items such as computer screens, payment card receipts, faxes, or paper reports can result in this data being obtained by unauthorized individuals and used fraudulently. Ensuring that full PAN is only displayed for those with a legitimate business need to see the full PAN minimizes the risk of unauthorized persons gaining access to PAN data. This requirement relates to protection of PAN displayed on screens, paper receipts, printouts, etc., and is not to be confused with Requirement 3.4 for protection of PAN when stored in files, databases, etc.",
        "ref_code": "3.3",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.4": {
        "name": "Render PAN unreadable anywhere it is stored (including on portable digital media, backup media, and in logs) by using any of the following approaches: One-way hashes based on strong cryptography, (hash must be of the entire PAN)   Truncation (hashing cannot be used to replace the truncated segment of PAN) Index tokens and pads (pads must be securely stored) Strong cryptography with associated key-management processes and procedures. Note: It is a relatively trivial effort for a malicious individual to reconstruct original PAN data if they have access to both the truncated and hashed version of a PAN. Where hashed and truncated versions of the same PAN are present in an entity's environment, additional controls must be in place to ensure that the hashed and truncated versions cannot be correlated to reconstruct the original PAN.",
        "description": "PANs stored in primary storage (databases, or flat files such as text files spreadsheets) as well as non-primary storage (backup, audit logs, exception or troubleshooting logs) must all be protected. One-way hash functions based on strong cryptography can be used to render cardholder data unreadable. Hash functions are appropriate when there is no need to retrieve the original number (one-way hashes are irreversible). It is recommended, but not currently a requirement, that an additional, random input value be added to the cardholder data prior to hashing to reduce the feasibility of an attacker comparing the data against (and deriving the PAN from) tables of pre- computed hash values. The intent of truncation is to permanently remove a segment of PAN data so that only a portion (generally not to exceed the first six and last four digits) of the PAN is stored. An index token is a cryptographic token that replaces the PAN based on a given index for an unpredictable value. A one-time pad is a system in which a randomly generated private key is used only once to encrypt a message that is then decrypted using a matching one-time pad and key. The intent of strong cryptography (as defined in the PCI DSS and PA-DSS Glossary of Terms, Abbreviations, and Acronyms) is that the encryption be based on an industry-tested and accepted algorithm (not a proprietary or \"home- grown\" algorithm) with strong cryptographic keys. By correlating hashed and truncated versions of a given PAN, a malicious individual may easily derive the original PAN value. Controls that prevent the correlation of this data will help ensure that the original PAN remains unreadable.",
        "ref_code": "3.4",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.5": {
        "name": "Document and implement procedures to protect keys used to secure stored cardholder data against disclosure and misuse: Note: This requirement applies to keys used to encrypt stored cardholder data, and also applies to key-encrypting keys used to protect data-encrypting keys- such key-encrypting keys must be at least as strong as the data-encrypting key.",
        "description": "Cryptographic keys must be strongly protected because those who obtain access will be able to decrypt data. Key-encrypting keys, if used, must be at least as strong as the data-encrypting key in order to ensure proper protection of the key that encrypts the data as well as the data encrypted with that key. The requirement to protect keys from disclosure and misuse applies to both data-encrypting keys and key-encrypting keys. Because one key- encrypting key may grant access to many data- encrypting keys, the key-encrypting keys require strong protection measures.",
        "ref_code": "3.5",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.6": {
        "name": "Fully document and implement all key-management processes and procedures for cryptographic keys used for encryption of cardholder data, including the following: Note: Numerous industry standards for key management are available from various resources including NIST, which can be found at http://csrc.nist.gov.",
        "description": "The manner in which cryptographic keys are managed is a critical part of the continued security of the encryption solution. A good key- management process, whether it is manual or automated as part of the encryption product, is based on industry standards and addresses all key elements at 3.6.1 through 3.6.8. Providing guidance to customers on how to securely transmit, store and update cryptographic keys can help prevent keys from being mismanaged or disclosed to unauthorized entities. This requirement applies to keys used to encrypt stored cardholder data, and any respective key- encrypting keys. Note: Testing Procedure 3.6.a is an additional procedure that only applies if the entity being assessed is a service provider.",
        "ref_code": "3.6",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "3.7": {
        "name": "Ensure that security policies and operational procedures for protecting stored cardholder data are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and documented operational procedures for managing the secure storage of cardholder data on a continuous basis.",
        "ref_code": "3.7",
        "system_level": False,
        "category": "Requirement 3: Protect stored cardholder data",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "4.1": {
        "name": "Use strong cryptography and security protocols (for example, TLS, IPSEC, SSH, etc.) to safeguard sensitive cardholder data during transmission over open, public networks, including the following: Only trusted keys and certificates are accepted. The protocol in use only supports secure versions or configurations. The encryption strength is appropriate for the encryption methodology in use. Note: SSL and early TLS are not considered strong cryptography and cannot be used as a security control after June 30, 2016. Prior to this date, existing implementations that use SSL and/or early TLS must have a formal Risk Mitigation and Migration Plan in place. Effective immediately, new implementations must not use SSL or early TLS. POS POI terminals (and the SSL/TLS termination points to which they connect) that can be verified as not being susceptible to any known exploits for SSL and early TLS may continue using these as a security control after June 30, 2016. Examples of open, public networks include but are not limited to:   The Internet   Wireless technologies, including 802.11 and Bluetooth   Cellular technologies, for example, Global System for Mobile communications (GSM), Code division multiple access (CDMA)   General Packet Radio Service (GPRS)   Satellite communications",
        "description": "Sensitive information must be encrypted during transmission over public networks, because it is easy and common for a malicious individual to intercept and/or divert data while in transit. Secure transmission of cardholder data requires using trusted keys/certificates, a secure protocol for transport, and proper encryption strength to encrypt cardholder data. Connection requests from systems that do not support the required encryption strength, and that would result in an insecure connection, should not be accepted. Note that some protocol implementations (such as SSL, SSH v1.0, and early TLS) have known vulnerabilities that an attacker can use to gain control of the affected system. Whichever security protocol is used, ensure it is configured to use only secure versions and configurations to prevent use of an insecure connection-for example, by using only trusted certificates and supporting only strong encryption (not supporting weaker, insecure protocols or methods). Verifying that certificates are trusted (for example, have not expired and are issued from a trusted source) helps ensure the integrity of the secure connection. (Continued on next page) Generally, the web page URL should begin with \"HTTPS\" and/or the web browser display a padlock icon somewhere in the window of the browser. Many TLS certificate vendors also provide a highly visible verification seal- sometimes referred to as a 'security seal,' \"secure site seal,\" or 'secure trust seal')-which may provide the ability to click on the seal to reveal information about the website. Refer to industry standards and best practices for information on strong cryptography and secure protocols (e.g. NIST SP 800-52 and SP 800-57, OWASP, etc.) Regarding use of SSL/early TLS: Entities using SSL and early TLS must work towards upgrading to a strong cryptographic protocol as soon as possible.  Additionally, SSL and/or early TLS must not be introduced into environments where they don't already exist. At the time of publication, the known vulnerabilities are difficult to exploit in POS POI payment environments. However, new vulnerabilities could emerge at any time, and it is up to the organization to remain up-to-date with vulnerability trends and determine whether or not they are susceptible to any known exploits. Refer to the PCI SSC Information Supplement: Migrating from SSL and Early TLS for further guidance on the use of SSL/early TLS.",
        "ref_code": "4.1",
        "system_level": False,
        "category": "Requirement 4: Encrypt transmission of cardholder data across open, public networks",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "4.2": {
        "name": "Never send unprotected PANs by end- user messaging technologies (for example, e- mail, instant messaging, SMS, chat, etc.).",
        "description": "E-mail, instant messaging, SMS, and chat can be easily intercepted by packet-sniffing during delivery across internal and public networks. Do not utilize these messaging tools to send PAN unless they are configured to provide strong encryption. Additionally, if an entity requests PAN via end- user messaging technologies, the entity should provide a tool or method to protect these PANs using strong cryptography or render PANs unreadable before transmission.",
        "ref_code": "4.2",
        "system_level": False,
        "category": "Requirement 4: Encrypt transmission of cardholder data across open, public networks",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "4.3": {
        "name": "Ensure that security policies and operational procedures for encrypting transmissions of cardholder data are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures for managing the secure transmission of cardholder data on a continuous basis.",
        "ref_code": "4.3",
        "system_level": False,
        "category": "Requirement 4: Encrypt transmission of cardholder data across open, public networks",
        "subcategory": "Protect Cardholder Data",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "5.1": {
        "name": "Deploy anti-virus software on all systems commonly affected by malicious software (particularly personal computers and servers).",
        "description": "There is a constant stream of attacks using widely published exploits, often called \"zero day\" (an attack that exploits a previously unknown vulnerability), against otherwise secured systems. Without an anti-virus solution that is updated regularly, these new forms of malicious software can attack systems, disable a network, or lead to compromise of data.",
        "ref_code": "5.1",
        "system_level": False,
        "category": "Requirement 5: Use and regularly update anti-virus software or programs ",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "5.2": {
        "name": "Ensure that all anti-virus mechanisms are maintained as follows: Are kept current, Perform periodic scans Generate audit logs which are retained per PCI DSS Requirement 10.7.",
        "description": "Even the best anti-virus solutions are limited in effectiveness if they are not maintained and kept current with the latest security updates, signature files, or malware protections. Audit logs provide the ability to monitor virus and malware activity and anti-malware reactions. Thus, it is imperative that anti-malware solutions be configured to generate audit logs and that these logs be managed in accordance with Requirement 10.",
        "ref_code": "5.2",
        "system_level": False,
        "category": "Requirement 5: Use and regularly update anti-virus software or programs ",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "5.3": {
        "name": "Ensure that anti-virus mechanisms are actively running and cannot be disabled or altered by users, unless specifically authorized by management on a case-by-case basis for a limited time period. Note: Anti-virus solutions may be temporarily disabled only if there is legitimate technical need, as authorized by management on a case-by-case basis. If anti-virus protection needs to be disabled for a specific purpose, it must be formally authorized. Additional security measures may also need to be implemented for the period of time during which anti-virus protection is not active.",
        "description": "Anti-virus that continually runs and is unable to be altered will provide persistent security against malware. Use of policy-based controls on all systems to ensure anti-malware protections cannot be altered or disabled will help prevent system weaknesses from being exploited by malicious software. Additional security measures may also need to be implemented for the period of time during which anti-virus protection is not active-for example, disconnecting the unprotected system from the Internet while the anti-virus protection is disabled, and running a full scan after it is re-enabled.",
        "ref_code": "5.3",
        "system_level": False,
        "category": "Requirement 5: Use and regularly update anti-virus software or programs ",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "5.4": {
        "name": "Ensure that security policies and operational procedures for protecting systems against malware are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures to ensure systems are protected from malware on a continuous basis.",
        "ref_code": "5.4",
        "system_level": False,
        "category": "Requirement 5: Use and regularly update anti-virus software or programs ",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.1": {
        "name": "Establish a process to identify security vulnerabilities, using reputable outside sources for security vulnerability information, and assign a risk ranking (for example, as 'high,' 'medium,' or 'low') to newly discovered security vulnerabilities. Note: Risk rankings should be based on industry best practices as well as consideration of potential impact. For example, criteria for ranking vulnerabilities may include consideration of the CVSS base score, and/or the classification by the vendor, and/or type of systems affected. Methods for evaluating vulnerabilities and assigning risk ratings will vary based on an organization's environment and risk- assessment strategy. Risk rankings should, at a minimum, identify all vulnerabilities considered to be a 'high risk' to the environment. In addition to the risk ranking, vulnerabilities may be considered 'critical' if they pose an imminent threat to the environment, impact critical systems, and/or would result in a potential compromise if not addressed. Examples of critical systems may include security systems, public-facing devices and systems, databases, and other systems that store, process, or transmit cardholder data.",
        "description": "The intent of this requirement is that organizations keep up to date with new vulnerabilities that may impact their environment. Sources for vulnerability information should be trustworthy and often include vendor websites, industry news groups, mailing list, or RSS feeds. Once an organization identifies a vulnerability that could affect their environment, the risk that the vulnerability poses must be evaluated and ranked. The organization must therefore have a method in place to evaluate vulnerabilities on an ongoing basis and assign risk rankings to those vulnerabilities. This is not achieved by an ASV scan or internal vulnerability scan, rather this requires a process to actively monitor industry sources for vulnerability information. Classifying the risks (for example, as 'high,' 'medium,' or 'low') allows organizations to identify, prioritize, and address the highest risk items more quickly and reduce the likelihood that vulnerabilities posing the greatest risk will be exploited.",
        "ref_code": "6.1",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.2": {
        "name": "Ensure that all system components and software are protected from known vulnerabilities by installing applicable vendor- supplied security patches. Install critical security patches within one month of release. Note: Critical security patches should be identified according to the risk ranking process defined in Requirement 6.1.",
        "description": "There is a constant stream of attacks using widely published exploits, often called \"zero day\" (an attack that exploits a previously unknown vulnerability), against otherwise secured systems. If the most recent patches are not implemented on critical systems as soon as possible, a malicious individual can use these exploits to attack or disable a system, or gain access to sensitive data. Prioritizing patches for critical infrastructure ensures that high-priority systems and devices are protected from vulnerabilities as soon as possible after a patch is released. Consider prioritizing patch installations such that security patches for critical or at-risk systems are installed within 30 days, and other lower-risk patches are installed within 2-3 months. This requirement applies to applicable patches for all installed software.",
        "ref_code": "6.2",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.3": {
        "name": "Develop internal and external software applications (including web-based administrative access to applications) securely, as follows: In accordance with PCI DSS (for example, secure authentication and logging) Based on industry standards and/or best practices. Incorporating information security throughout the software-development life cycle Note: this applies to all software developed internally as well as bespoke or custom software developed by a third party.",
        "description": "Without the inclusion of security during the requirements definition, design, analysis, and testing phases of software development, security vulnerabilities can be inadvertently or maliciously introduced into the production environment. Understanding how sensitive data is handled by the application-including when stored, transmitted, and when in memory-can help identify where data needs to be protected.",
        "ref_code": "6.3",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.4": {
        "name": "Follow change control processes and procedures for all changes to system components. The processes must include the following:",
        "description": "Without properly documented and implemented change controls, security features could be inadvertently or deliberately omitted or rendered inoperable, processing irregularities could occur, or malicious code could be introduced.",
        "ref_code": "6.4",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.5": {
        "name": "Address common coding vulnerabilities in software-development processes as follows: Train developers in secure coding techniques, including how to avoid common coding vulnerabilities, and understanding how sensitive data is handled in memory. Develop applications based on secure coding guidelines. Note: The vulnerabilities listed at 6.5.1 through 6.5.10 were current with industry best practices when this version of PCI DSS was published. However, as industry best practices for vulnerability management are updated (for example, the OWASP Guide, SANS CWE Top 25, CERT Secure Coding, etc.), the current best practices must be used for these requirements.",
        "description": "The application layer is high-risk and may be targeted by both internal and external threats. Requirements 6.5.1 through 6.5.10 are the minimum controls that should be in place, and organizations should incorporate the relevant secure coding practices as applicable to the particular technology in their environment. Application developers should be properly trained to identify and resolve issues related to these (and other) common coding vulnerabilities. Having staff knowledgeable of secure coding guidelines should minimize the number of security vulnerabilities introduced through poor coding practices. Training for developers may be provided in-house or by third parties and should be applicable for technology used. As industry-accepted secure coding practices change, organizational coding practices and developer training should likewise be updated to address new threats-for example, memory scraping attacks. The vulnerabilities identified in 6.5.1 through 6.5.10 provide a minimum baseline. It is up to the organization to remain up to date with vulnerability trends and incorporate appropriate measures into their secure coding practices.",
        "ref_code": "6.5",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.6": {
        "name": "For public-facing web applications, address new threats and vulnerabilities on an ongoing basis and ensure these applications are protected against known attacks by either of the following methods: Reviewing public-facing web applications via manual or automated application vulnerability security assessment tools or methods, at least annually and after any changes Note: This assessment is not the same as the vulnerability scans performed for Requirement 11.2. Installing an automated technical solution that detects and prevents web- based attacks (for example, a web- application firewall) in front of public- facing web applications, to continually check all traffic.",
        "description": "Public-facing web applications are primary targets for attackers, and poorly coded web applications provide an easy path for attackers to gain access to sensitive data and systems. The requirement for reviewing applications or installing web-application firewalls is intended to reduce the number of compromises on public-facing web applications due to poor coding or application management practices. Manual or automated vulnerability security assessment tools or methods review and/or test the application for vulnerabilities Web-application firewalls filter and block non- essential traffic at the application layer. Used in conjunction with a network-based firewall, a properly configured web-application firewall prevents application-layer attacks if applications are improperly coded or configured. This can be achieved through a combination of technology and process. Process-based solutions must have mechanisms that facilitate timely responses to alerts in order to meet the intent of this requirement, which is to prevent attacks. Note: 'An organization that specializes in application security' can be either a third-party company or an internal organization, as long as the reviewers specialize in application security and can demonstrate independence from the development team.",
        "ref_code": "6.6",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "6.7": {
        "name": "Ensure that security policies and operational procedures for developing and maintaining secure systems and applications are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures to ensure systems and applications are securely developed and protected from vulnerabilities on a continuous basis.",
        "ref_code": "6.7",
        "system_level": False,
        "category": "Requirement 6: Develop and maintain secure systems and applications",
        "subcategory": "Maintain a Vulnerability Management Program",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "7.1": {
        "name": "Limit access to system components and cardholder data to only those individuals whose job requires such access.",
        "description": "The more people who have access to cardholder data, the more risk there is that a user's account will be used maliciously. Limiting access to those with a legitimate business reason for the access helps an organization prevent mishandling of cardholder data through inexperience or malice.",
        "ref_code": "7.1",
        "system_level": False,
        "category": "Requirement 7: Restrict access to cardholder data by business need to know",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "7.2": {
        "name": "Establish an access control system for systems components that restricts access based on a user's need to know, and is set to 'deny all' unless specifically allowed. This access control system must include the following:",
        "description": "Without a mechanism to restrict access based on user's need to know, a user may unknowingly be granted access to cardholder data. An access control system automates the process of restricting access and assigning privileges. Additionally, a default 'deny-all' setting ensures no one is granted access until and unless a rule is established specifically granting such access. Note: Some access control systems are set by default to 'allow-all,' thereby permitting access unless/until a rule is written to specifically deny it.",
        "ref_code": "7.2",
        "system_level": False,
        "category": "Requirement 7: Restrict access to cardholder data by business need to know",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "7.3": {
        "name": "Ensure that security policies and operational procedures for restricting access to cardholder data are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures to ensure that access is controlled and based on need- to-know and least privilege, on a continuous basis.",
        "ref_code": "7.3",
        "system_level": False,
        "category": "Requirement 7: Restrict access to cardholder data by business need to know",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.1": {
        "name": "Define and implement policies and procedures to ensure proper user identification management for non- consumer users and administrators on all system components as follows:",
        "description": "By ensuring each user is uniquely identified- instead of using one ID for several employees-an organization can maintain individual responsibility for actions and an effective audit trail per employee. This will help speed issue resolution and containment when misuse or malicious intent occurs. Note: These requirements are applicable for all accounts, including point-of-sale accounts, with administrative capabilities and all accounts used to view or access cardholder data or to access systems with cardholder data. This includes accounts used by vendors and other third parties (for example, for support or maintenance). However, Requirements 8.1.1, 8.2, 8.5, 8.2.3 through 8.2.5, and 8.1.6 through 8.1.8 are not intended to apply to user accounts within a point-of- sale payment application that only have access to one card number at a time in order to facilitate a single transaction (such as cashier accounts).",
        "ref_code": "8.1",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.2": {
        "name": "In addition to assigning a unique ID, ensure proper user-authentication management for non-consumer users and administrators on all system components by employing at least one of the following methods to authenticate all users: Something you know, such as a password or passphrase Something you have, such as a token device or smart card Something you are, such as a biometric.",
        "description": "These authentication methods, when used in addition to unique IDs, help protect users' IDs from being compromised, since the one attempting the compromise needs to know both the unique ID and the password (or other authentication used). Note that a digital certificate is a valid option for 'something you have' as long as it is unique for a particular user. Since one of the first steps a malicious individual will take to compromise a system is to exploit weak or nonexistent passwords, it is important to implement good processes for authentication management.",
        "ref_code": "8.2",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.3": {
        "name": "Incorporate two-factor authentication for remote network access originating from outside the network by personnel (including users and administrators) and all third parties, (including vendor access for support or maintenance). Note: Two-factor authentication requires that two of the three authentication methods (see Requirement 8.2 for descriptions of authentication methods) be used for authentication. Using one factor twice (for example, using two separate passwords) is not considered two-factor authentication. Examples of two-factor technologies include remote authentication and dial-in service (RADIUS) with tokens; terminal access controller access control system (TACACS) with tokens; and other technologies that facilitate two-factor authentication.",
        "description": "Two-factor authentication requires two forms of authentication for higher-risk accesses, such as those originating from outside the network This requirement is intended to apply to all personnel-including general users, administrators, and vendors (for support or maintenance) with remote access to the network-where that remote access could lead to access to the cardholder data environment. If remote access is to an entity's network that has appropriate segmentation, such that remote users cannot access or impact the cardholder data environment, two-factor authentication for remote access to that network would not be required. However, two-factor authentication is required for any remote access to networks with access to the cardholder data environment, and is recommended for all remote access to the entity's networks.",
        "ref_code": "8.3",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.4": {
        "name": "Document and communicate authentication policies and procedures to all users including: Guidance on selecting strong authentication credentials Guidance for how users should protect their authentication credentials Instructions not to reuse previously used passwords  Instructions to change passwords if there is any suspicion the password could be compromised.",
        "description": "Communicating password/authentication policies and procedures to all users helps those users understand and abide by the policies. For example, guidance on selecting strong passwords may include suggestions to help personnel select hard-to-guess passwords that don't contain dictionary words, and that don't contain information about the user (such as the user ID, names of family members, date of birth, etc.). Guidance for protecting authentication credentials may include not writing down passwords or saving them in insecure files, and being alert for malicious individuals who may attempt to exploit their passwords (for example, by calling an employee and asking for their password so the caller can 'troubleshoot a problem'). Instructing users to change passwords if there is a chance the password is no longer secure can prevent malicious users from using a legitimate password to gain unauthorized access.",
        "ref_code": "8.4",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.5": {
        "name": "Do not use group, shared, or generic IDs, passwords, or other authentication methods as follows: Generic user IDs are disabled or removed.  Shared user IDs do not exist for system administration and other critical functions. Shared and generic user IDs are not used to administer any system components.",
        "description": "If multiple users share the same authentication credentials (for example, user account and password), it becomes impossible to trace system access and activities to an individual. This in turn prevents an entity from assigning accountability for, or having effective logging of, an individual's actions, since a given action could have been performed by anyone in the group that has knowledge of the authentication credentials.",
        "ref_code": "8.5",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.6": {
        "name": "Where other authentication mechanisms are used (for example, physical or logical security tokens, smart cards, certificates, etc.), use of these mechanisms must be assigned as follows: Authentication mechanisms must be assigned to an individual account and not shared among multiple accounts. Physical and/or logical controls must be in place to ensure only the intended account can use that mechanism to gain access.",
        "description": "If user authentication mechanisms such as tokens, smart cards, and certificates can be used by multiple accounts, it may be impossible to identify the individual using the authentication mechanism. Having physical and/or logical controls (for example, a PIN, biometric data, or a password) to uniquely identify the user of the account will prevent unauthorized users from gaining access through use of a shared authentication mechanism.",
        "ref_code": "8.6",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.7": {
        "name": "All access to any database containing cardholder data (including access by applications, administrators, and all other users) is restricted as follows:  All user access to, user queries of, and user actions on databases are through programmatic methods. Only database administrators have the ability to directly access or query databases. Application IDs for database applications can only be used by the applications (and not by individual users or other non-application processes).",
        "description": "Without user authentication for access to databases and applications, the potential for unauthorized or malicious access increases, and such access cannot be logged since the user has not been authenticated and is therefore not known to the system. Also, database access should be granted through programmatic methods only (for example, through stored procedures), rather than via direct access to the database by end users (except for DBAs, who may need direct access to the database for their administrative duties).",
        "ref_code": "8.7",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "8.8": {
        "name": "Ensure that security policies and operational procedures for identification and authentication are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures for managing identification and authorization on a continuous basis.",
        "ref_code": "8.8",
        "system_level": False,
        "category": "Requirement 8: Assign a unique ID to each person with computer access",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.1": {
        "name": "Ensure that security policies and operational procedures for restricting physical access to cardholder data are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures for restricting physical access to cardholder data and CDE systems on a continuous basis.",
        "ref_code": "9.1",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.2": {
        "name": "Develop procedures to easily distinguish between onsite personnel and visitors, to include: Identifying onsite personnel and visitors (for example, assigning badges) Changes to access requirements Revoking or terminating onsite personnel and expired visitor identification (such as ID badges).",
        "description": "Identifying authorized visitors so they are easily distinguished from onsite personnel prevents unauthorized visitors from being granted access to areas containing cardholder data.",
        "ref_code": "9.2",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.3": {
        "name": "Control physical access for onsite personnel to sensitive areas as follows: Access must be authorized and based on individual job function. Access is revoked immediately upon termination, and all physical access mechanisms, such as keys, access cards, etc., are returned or disabled.",
        "description": "Controlling physical access to sensitive areas helps ensure that only authorized personnel with a legitimate business need are granted access. When personnel leave the organization, all physical access mechanisms should be returned or disabled promptly (as soon as possible) upon their departure, to ensure personnel cannot gain physical access to sensitive areas once their employment has ended.",
        "ref_code": "9.3",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.4": {
        "name": "Implement procedures to identify and authorize visitors. Procedures should include the following:",
        "description": "Visitor controls are important to reduce the ability of unauthorized and malicious persons to gain access to facilities (and potentially, to cardholder data). Visitor controls ensure visitors are identifiable as visitors so personnel can monitor their activities, and that their access is restricted to just the duration of their legitimate visit. Ensuring that visitor badges are returned upon expiry or completion of the visit prevents malicious persons from using a previously authorized pass to gain physical access into the building after the visit has ended. A visitor log documenting minimum information on the visitor is easy and inexpensive to maintain and will assist in identifying physical access to a building or room, and potential access to cardholder data.",
        "ref_code": "9.4",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.5": {
        "name": "Physically secure all media.",
        "description": "Controls for physically securing media are intended to prevent unauthorized persons from gaining access to cardholder data on any type of media. Cardholder data is susceptible to unauthorized viewing, copying, or scanning if it is unprotected while it is on removable or portable media, printed out, or left on someone's desk.",
        "ref_code": "9.5",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.6": {
        "name": "Maintain strict control over the internal or external distribution of any kind of media, including the following:",
        "description": "Procedures and processes help protect cardholder data on media distributed to internal and/or external users. Without such procedures data can be lost or stolen and used for fraudulent purposes.",
        "ref_code": "9.6",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.7": {
        "name": "Maintain strict control over the storage and accessibility of media.",
        "description": "Without careful inventory methods and storage controls, stolen or missing media could go unnoticed for an indefinite amount of time. If media is not inventoried, stolen or lost media may not be noticed for a long time or at all.",
        "ref_code": "9.7",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.8": {
        "name": "Destroy media when it is no longer needed for business or legal reasons as follows:",
        "description": "If steps are not taken to destroy information contained on hard disks, portable drives, CD/DVDs, or paper prior to disposal, malicious individuals may be able to retrieve information from the disposed media, leading to a data compromise. For example, malicious individuals may use a technique known as 'dumpster diving,' where they search through trashcans and recycle bins looking for information they can use to launch an attack. Securing storage containers used for materials that are going to be destroyed prevents sensitive information from being captured while the materials are being collected. For example, 'to-be-shredded' containers could have a lock preventing access to its contents or physic ally prevent access to the inside of the container. Examples of methods for securely destroying electronic media include secure wiping, degaussing, or physical destruction (such as grinding or shredding hard disks).",
        "ref_code": "9.8",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "9.9": {
        "name": "Protect devices that capture payment card data via direct physical interaction with the card from tampering and substitution. Note: These requirements apply to card- reading devices used in card-present transactions (that is, card swipe or dip) at the point of sale. This requirement is not intended to apply to manual key-entry components such as computer keyboards and POS keypads. Note: Requirement 9.9 is a best practice until June 30, 2015, after which it becomes a requirement.",
        "description": "Criminals attempt to steal cardholder data by stealing and/or manipulating card-reading devices and terminals. For example, they will try to steal devices so they can learn how to break into them, and they often try to replace legitimate devices with fraudulent devices that send them payment card information every time a card is entered. Criminals will also try to add 'skimming' components to the outside of devices, which are designed to capture payment card details before they even enter the device-for example, by attaching an additional card reader on top of the legitimate card reader so that the payment card details are captured twice: once by the criminal's component and then by the device's legitimate component. In this way, transactions may still be completed without interruption while the criminal is 'skimming' the payment card information during the process. This requirement is recommended, but not required, for manual key-entry components such as computer keyboards and POS keypads. Additional best practices on skimming prevention are available on the PCI SSC website.",
        "ref_code": "9.9",
        "system_level": False,
        "category": "Requirement 9: Restrict physical access to cardholder data",
        "subcategory": "Implement Strong Access Control Measures",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.1": {
        "name": "Implement audit trails to link all access to system components to each individual user.",
        "description": "It is critical to have a process or system that links user access to system components accessed. This system generates audit logs and provides the ability to trace back suspicious activity to a specific user.",
        "ref_code": "10.1",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.2": {
        "name": "Implement automated audit trails for all system components to reconstruct the following events:",
        "description": "Generating audit trails of suspect activities alerts the system administrator, sends data to other monitoring mechanisms (like intrusion detection systems), and provides a history trail for post- incident follow-up. Logging of the following events enables an organization to identify and trace potentially malicious activities",
        "ref_code": "10.2",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.3": {
        "name": "Record at least the following audit trail entries for all system components for each event:",
        "description": "By recording these details for the auditable events at 10.2, a potential compromise can be quickly identified, and with sufficient detail to know who, what, where, when, and how.",
        "ref_code": "10.3",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.4": {
        "name": "Using time-synchronization technology, synchronize all critical system clocks and times and ensure that the following is implemented for acquiring, distributing, and storing time. Note: One example of time synchronization technology is Network Time Protocol (NTP).",
        "description": "Time synchronization technology is used to synchronize clocks on multiple systems. When clocks are not properly synchronized, it can be difficult, if not impossible, to compare log files from different systems and establish an exact sequence of event (crucial for forensic analysis in the event of a breach). For post-incident forensics teams, the accuracy and consistency of time across all systems and the time of each activity is critical in determining how the systems were compromised.",
        "ref_code": "10.4",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.5": {
        "name": "Secure audit trails so they cannot be altered.",
        "description": "Often a malicious individual who has entered the network will attempt to edit the audit logs in order to hide their activity. Without adequate protection of audit logs, their completeness, accuracy, and integrity cannot be guaranteed, and the audit logs can be rendered useless as an investigation tool after a compromise.",
        "ref_code": "10.5",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.6": {
        "name": "Review logs and security events for all system components to identify anomalies or suspicious activity. Note: Log harvesting, parsing, and alerting tools may be used to meet this Requirement.",
        "description": "Many breaches occur over days or months before being detected. Regular log reviews by personnel or automated means can identify and proactively address unauthorized access to the cardholder data environment. The log review process does not have to be manual. The use of log harvesting, parsing, and alerting tools can help facilitate the process by identifying log events that need to be reviewed.",
        "ref_code": "10.6",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.7": {
        "name": "Retain audit trail history for at least one year, with a minimum of three months immediately available for analysis (for example, online, archived, or restorable from backup).",
        "description": "Retaining logs for at least a year allows for the fact that it often takes a while to notice that a compromise has occurred or is occurring, and allows investigators sufficient log history to better determine the length of time of a potential breach and potential system(s) impacted. By having three months of logs immediately available, an entity can quickly identify and minimize impact of a data breach. Storing logs in off-line locations could prevent them from being readily available, resulting in longer time frames to restore log data, perform analysis, and identify impacted systems or data.",
        "ref_code": "10.7",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "10.8": {
        "name": "Ensure that security policies and operational procedures for monitoring all access to network resources and cardholder data are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and daily operational procedures for monitoring all access to network resources and cardholder data on a continuous basis.",
        "ref_code": "10.8",
        "system_level": False,
        "category": "Requirement 10: Track and monitor all access to network resources and cardholder data",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11.1": {
        "name": "Implement processes to test for the presence of wireless access points (802.11), and detect and identify all authorized and unauthorized wireless access points on a quarterly basis. Note: Methods that may be used in the process include but are not limited to wireless network scans, physical/logical inspections of system components and infrastructure, network access control (NAC), or wireless IDS/IPS. Whichever methods are used, they must be sufficient to detect and identify both authorized and unauthorized devices.",
        "description": "Implementation and/or exploitation of wireless technology within a network are some of the most common paths for malicious users to gain access to the network and cardholder data. If a wireless device or network is installed without a company's knowledge, it can allow an attacker to easily and 'invisibly' enter the network. Unauthorized wireless devices may be hidden within or attached to a computer or other system component, or be attached directly to a network port or network device, such as a switch or router. Any such unauthorized device could result in an unauthorized access point into the environment. Knowing which wireless devices are authorized can help administrators quickly identify non- authorized wireless devices, and responding to the identification of unauthorized wireless access points helps to proactively minimize the exposure of CDE to malicious individuals. Due to the ease with which a wireless access point can be attached to a network, the difficulty in detecting their presence, and the increased risk presented by unauthorized wireless devices, these processes must be performed even when a policy exists prohibiting the use of wireless technology. The size and complexity of a particular environment will dictate the appropriate tools and processes to be used to provide sufficient assurance that a rogue wireless access point has not been installed in the environment. (Continued on next page)",
        "ref_code": "11.1",
        "system_level": False,
        "category": "Requirement 11: Regularly test security systems and processes",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11.2": {
        "name": "Run internal and external network vulnerability scans at least quarterly and after any significant change in the network (such as new system component installations, changes in network topology, firewall rule modifications, product upgrades). Note: Multiple scan reports can be combined for the quarterly scan process to show that all systems were scanned and all applicable vulnerabilities have been addressed. Additional documentation may be required to verify non-remediated vulnerabilities are in the process of being addressed. For initial PCI DSS compliance, it is not required that four quarters of passing scans be completed if the assessor verifies 1) the most recent scan result was a passing scan, 2) the entity has documented policies and procedures requiring quarterly scanning, and 3) vulnerabilities noted in the scan results have been corrected as shown in a re-scan(s). For subsequent years after the initial PCI DSS review, four quarters of passing scans must have occurred.",
        "description": "A vulnerability scan is a combination of automated or manual tools, techniques, and/or methods run against external and internal network devices and servers, designed to expose potential vulnerabilities that could be found and exploited by malicious individuals. There are three types of vulnerability scanning required for PCI DSS: Internal quarterly vulnerability scanning by qualified personnel (use of a PCI SSC Approved Scanning Vendor (ASV) is not required) External quarterly vulnerability scanning, which must be performed by an ASV Internal and external scanning as needed after significant changes Once these weaknesses are identified, the entity corrects them and repeats the scan until all vulnerabilities have been corrected. Identifying and addressing vulnerabilities in a timely manner reduces the likelihood of a vulnerability being exploited and potential compromise of a system component or cardholder data.",
        "ref_code": "11.2",
        "system_level": False,
        "category": "Requirement 11: Regularly test security systems and processes",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11.3": {
        "name": "Implement a methodology for penetration testing that includes the following: Is based on industry-accepted penetration testing approaches (for example, NIST SP800-115) Includes coverage for the entire CDE perimeter and critical systems Includes testing from both inside and outside the network Includes testing to validate any segmentation and scope-reduction controls Defines application-layer penetration tests to include, at a minimum, the vulnerabilities listed in Requirement 6.5 Defines network-layer penetration tests to include components that support network functions as well as operating systems Includes review and consideration of threats and vulnerabilities experienced in the last 12 months Specifies retention of penetration testing results and remediation activities results. Note: This update to Requirement 11.3 is a best practice until June 30, 2015, after which it becomes a requirement. Prior to this date, PCI DSS v2.0 requirements for penetration testing must be followed until version 3 is in place.",
        "description": "The intent of a penetration test is to simulate a real-world attack situation with a goal of identifying how far an attacker would be able to penetrate into an environment. This allows an entity to gain a better understanding of their potential exposure and develop a strategy to defend against attacks. A penetration test differs from a vulnerability scan, as a penetration test is an active process that may include exploiting identified vulnerabilities. Conducting a vulnerability scan may be one of the first steps a penetration tester will perform in order to plan the testing strategy, although it is not the only step. Even if a vulnerability scan does not detect known vulnerabilities, the penetration tester will often gain enough knowledge about the system to identify possible security gaps. Penetration testing is generally a highly manual process. While some automated tools may be used, the tester uses their knowledge of systems to penetrate into an environment. Often the tester will chain several types of exploits together with a goal of breaking through layers of defenses. For example, if the tester finds a means to gain access to an application server, they will then use the compromised server as a point to stage a new attack based on the resources the server has access to. In this way, a tester is able to simulate the methods performed by an attacker to identify areas of potential weakness in the environment. Penetration testing techniques will be different for different organizations, and the type, depth, and complexity of the testing will depend on the specific environment and the organization's risk assessment.",
        "ref_code": "11.3",
        "system_level": False,
        "category": "Requirement 11: Regularly test security systems and processes",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11.4": {
        "name": "Use intrusion-detection and/or intrusion-prevention techniques to detect and/or prevent intrusions into the network. Monitor all traffic at the perimeter of the cardholder data environment as well as at critical points in the cardholder data environment, and alert personnel to suspected compromises. Keep all intrusion-detection and prevention engines, baselines, and signatures up to date.",
        "description": "Intrusion detection and/or intrusion prevention techniques (such as IDS/IPS) compare the traffic coming into the network with known 'signatures' and/or behaviors of thousands of compromise types (hacker tools, Trojans, and other malware), and send alerts and/or stop the attempt as it happens. Without a proactive approach to unauthorized activity detection, attacks on (or misuse of) computer resources could go unnoticed in real time. Security alerts generated by these techniques should be monitored so that the attempted intrusions can be stopped.",
        "ref_code": "11.4",
        "system_level": False,
        "category": "Requirement 11: Regularly test security systems and processes",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11.5": {
        "name": "Deploy a change-detection mechanism (for example, file-integrity monitoring tools) to alert personnel to unauthorized modification (including changes, additions, and deletions) of critical system files, configuration files, or content files; and configure the software to perform critical file comparisons at least weekly. Note: For change-detection purposes, critical files are usually those that do not regularly change, but the modification of which could indicate a system compromise or risk of compromise. Change-detection mechanisms such as file-integrity monitoring products usually come pre- configured with critical files for the related operating system. Other critical files, such as those for custom applications, must be evaluated and defined by the entity (that is, the merchant or service provider).",
        "description": "Change-detection solutions such as file-integrity monitoring (FIM) tools check for changes, additions, and deletions to critical files, and notify when such changes are detected. If not implemented properly and the output of the change-detection solution monitored, a malicious individual could add, remove, or alter configuration file contents, operating system programs, or application executables. Unauthorized changes, if undetected, could render existing security controls ineffective and/or result in cardholder data being stolen with no perceptible impact to normal processing.",
        "ref_code": "11.5",
        "system_level": False,
        "category": "Requirement 11: Regularly test security systems and processes",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "11.6": {
        "name": "Ensure that security policies and operational procedures for security monitoring and testing are documented, in use, and known to all affected parties.",
        "description": "Personnel need to be aware of and following security policies and operational procedures for security monitoring and testing on a continuous basis.",
        "ref_code": "11.6",
        "system_level": False,
        "category": "Requirement 11: Regularly test security systems and processes",
        "subcategory": "Regularly Monitor and Test Networks",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.1": {
        "name": "Implement an incident response plan. Be prepared to respond immediately to a system breach.",
        "description": "Without a thorough security incident response plan that is properly disseminated, read, and understood by the parties responsible, confusion and lack of a unified response could create further downtime for the business, unnecessary public media exposure, as well as new legal liabilities.",
        "ref_code": "12.1",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.2": {
        "name": "Implement a risk-assessment process that: Is performed at least annually and upon significant changes to the environment (for example, acquisition, merger, relocation, etc.), Identifies critical assets, threats, and vulnerabilities, and Results in a formal, documented analysis of risk. Examples of risk-assessment methodologies include but are not limited to OCTAVE, ISO 27005 and NIST SP 800-30.",
        "description": "A risk assessment enables an organization to identify threats and associated vulnerabilities with the potential to negatively impact their business. Resources can then be effectively allocated to implement controls that reduce the likelihood and/or the potential impact of the threat being realized. Performing risk assessments at least annually and upon significant changes allows the organization to keep up to date with organizational changes and evolving threats, trends, and technologies.",
        "ref_code": "12.2",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.3": {
        "name": "Develop usage policies for critical technologies and define proper use of these technologies. Note: Examples of critical technologies include, but are not limited to, remote access and wireless technologies, laptops, tablets, removable electronic media, e- mail usage and Internet usage. Ensure these usage policies require the following:",
        "description": "Personnel usage policies can either prohibit use of certain devices and other technologies if that is company policy, or provide guidance for personnel as to correct usage and implementation. If usage policies are not in place, personnel may use the technologies in violation of company policy, thereby allowing malicious individuals to gain access to critical systems and cardholder data.",
        "ref_code": "12.3",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.4": {
        "name": "Ensure that the security policy and procedures clearly define information security responsibilities for all personnel.",
        "description": "Without clearly defined security roles and responsibilities assigned, there could be inconsistent interaction with the security group, leading to unsecured implementation of technologies or use of outdated or unsecured technologies.",
        "ref_code": "12.4",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.5": {
        "name": "Assign to an individual or team the following information security management responsibilities:",
        "description": "Each person or team with responsibilities for information security management should be clearly aware of their responsibilities and related tasks, through specific policy. Without this accountability, gaps in processes may open access into critical resources or cardholder data.",
        "ref_code": "12.5",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.6": {
        "name": "Implement a formal security awareness program to make all personnel aware of the importance of cardholder data security.",
        "description": "If personnel are not educated about their security responsibilities, security safeguards and processes that have been implemented may become ineffective through errors or intentional actions.",
        "ref_code": "12.6",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.7": {
        "name": "Screen potential personnel prior to hire to minimize the risk of attacks from internal sources. (Examples of background checks include previous employment history, criminal record, credit history, and reference checks.) Note: For those potential personnel to be hired for certain positions such as store cashiers who only have access to one card number at a time when facilitating a transaction, this requirement is a recommendation only.",
        "description": "Performing thorough background investigations prior to hiring potential personnel who are expected to be given access to cardholder data reduces the risk of unauthorized use of PANs and other cardholder data by individuals with questionable or criminal backgrounds.",
        "ref_code": "12.7",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.8": {
        "name": "Maintain and implement policies and procedures to manage service providers with whom cardholder data is shared, or that could affect the security of cardholder data, as follows:",
        "description": "If a merchant or service provider shares cardholder data with a service provider, certain requirements apply to ensure continued protection of this data will be enforced by such service providers.",
        "ref_code": "12.8",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "12.9": {
        "name": "Additional requirement for service providers only: Service providers acknowledge in writing to customers that they are responsible for the security of cardholder data the service provider possesses or otherwise stores, processes, or transmits on behalf of the customer, or to the extent that they could impact the security of the customer's cardholder data environment. Note: This requirement is a best practice until June 30, 2015, after which it becomes a requirement. Note: The exact wording of an acknowledgement will depend on the agreement between the two parties, the details of the service being provided, and the responsibilities assigned to each party. The acknowledgement does not have to include the exact wording provided in this requirement.",
        "description": "Note: This requirement applies only when the entity being assessed is a service provider. In conjunction with Requirement 12.8.2, this requirement is intended to promote a consistent level of understanding between service providers and their customers about their applicable PCI DSS responsibilities. The acknowledgement of the service providers evidences their commitment to maintaining proper security of cardholder data that it obtains from its clients. The service provider's internal policies and procedures related to their customer engagement process and any templates used for written agreements should include provision of an applicable PCI DSS acknowledgement to their customers. The method by which the service provider provides written acknowledgment should be agreed between the provider and their customers.",
        "ref_code": "12.9",
        "system_level": False,
        "category": "Requirement 12: Maintain a policy that addresses information security for all personnel",
        "subcategory": "Maintain an Information Security Policy",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "A.1": {
        "name": "Protect each entity's (that is, merchant, service provider, or other entity) hosted environment and data, per A.1.1 through A.1.4: A hosting provider must fulfill these requirements as well as all other relevant sections of the PCI DSS. Note: Even though a hosting provider may meet these requirements, the compliance of the entity that uses the hosting provider is not guaranteed. Each entity must comply with the PCI DSS and validate compliance as applicable.",
        "description": "Appendix A of PCI DSS is intended for shared hosting providers who wish to provide their merchant and/or service provider customers with a PCI DSS compliant hosting environment.",
        "ref_code": "A.1",
        "system_level": False,
        "category": "Requirement A.1: Shared hosting providers must protect the cardholder data environment ",
        "subcategory": "Appendix A: Additional PCI DSS Requirements for Shared Hosting Providers",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    }
}


d_controls = {
    "DE.1": {
        "name": "Executive management shall establish responsibility for the protection of cardholder data and a PCI DSS compliance program to include:    Overall accountability for maintaining PCI DSS compliance Defining a charter for a PCI DSS compliance program    Providing updates to executive management and board of directors on PCI DSS compliance initiatives and issues, including remediation activities, at least annually PCI DSS Reference: Requirement 12",
        "description": "Executive management assignment of PCI  DSS compliance responsibilities ensures executive-level visibility into the PCI DSS compliance program and allows for the opportunity to ask appropriate questions to determine the effectiveness of the program and influence strategic priorities. Overall responsibility for the PCI DSS compliance program may be assigned to individual roles and/or to business units within the organization.",
        "ref_code": "DE.1",
        "system_level": False,
        "category": "DE.1  Implement a PCI DSS compliance program.",
        "subcategory": "Designated Entities Supplemental Validation",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "DE.2": {
        "name": "Document and confirm the accuracy of PCI DSS scope at least quarterly and upon significant changes to the in-scope environment. At a minimum, the quarterly scoping validation should include:    Identifying all in-scope networks and system components    Identifying all out-of-scope networks and justification for networks being out of scope, including descriptions of all segmentation controls implemented    Identifying all connected entities-e.g., third-party entities with access to the cardholder data environment (CDE) PCI DSS Reference: Scope of PCI DSS Requirements",
        "description": "Validation of PCI DSS scope should be performed as frequently as possible to ensure PCI DSS scope remains up to date and aligned with changing business objectives.",
        "ref_code": "DE.2",
        "system_level": False,
        "category": "DE.2  Document and validate PCI DSS scope.",
        "subcategory": "Designated Entities Supplemental Validation",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "DE.3": {
        "name": "Implement a process to immediately detect and alert on critical security control failures. Examples of critical security controls include, but are not limited to: Firewalls IDS/IPS FIM Anti-virus    Physical access controls    Logical access controls    Audit logging mechanisms    Segmentation controls (if used) PCI DSS Reference: Requirements 1-12",
        "description": "Without formal processes for the prompt (as soon as possible) detection and alerting of critical security control failures, failures may go undetected for extended periods and provide attackers ample time to compromise systems and steal sensitive data from the cardholder data environment.",
        "ref_code": "DE.3",
        "system_level": False,
        "category": "DE.3  Validate PCI DSS is incorporated into business-as-usual (BAU) activities.",
        "subcategory": "Designated Entities Supplemental Validation",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "DE.4": {
        "name": "Review user accounts and access privileges to in-scope system components at least every six months to ensure user accounts and access remain appropriate based on job function, and authorized. PCI DSS Reference: Requirement 7",
        "description": "Access requirements evolve over time as individuals change roles or leave the company, and as job functions change. Management needs to regularly review, revalidate, and update user access, as necessary, to reflect changes in personnel, including third parties, and users' job functions.",
        "ref_code": "DE.4",
        "system_level": False,
        "category": "DE.4  Control and manage logical access to the cardholder data environment.",
        "subcategory": "Designated Entities Supplemental Validation",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    },
    "DE.5": {
        "name": "Implement a methodology for the timely identification of attack patterns and undesirable behavior across systems-for example, using coordinated manual reviews and/or centrally-managed or automated log correlation tools-to include at least the following:    Identification of anomalies or suspicious activity as they occur    Issuance of timely alerts upon detection of suspicious activity or anomaly to responsible personnel    Response to alerts in accordance with documented response procedures PCI DSS Reference: Requirements 10, 12",
        "description": "The ability to identify attack patterns and undesirable behavior across systems is critical in preventing, detecting, or minimizing the impact of a data compromise. The presence of logs in all environments allows thorough tracking, alerting, and analysis when something goes wrong. Determining the cause of a compromise is very difficult, if not impossible, without a process to corroborate information from critical system components, and systems that perform security functions-such as firewalls, IDS/IPS, and file-integrity monitoring (FIM) systems. Thus, logs for all critical systems components and systems that perform security functions should be collected, correlated, and maintained. This could include the use of software products and service methodologies to provide real-time analysis, alerting, and reporting-such as security information and event management (SIEM), file-integrity monitoring (FIM), or change detection.",
        "ref_code": "DE.5",
        "system_level": False,
        "category": "DE.5  Identify and respond to suspicious events.",
        "subcategory": "Designated Entities Supplemental Validation",
        "dti": "easy",
        "dtc": "easy",
        "meta": {},
        "subcontrols": []
    }
}

with open('pci_controls.csv') as csvfile:
    reader = csv.DictReader(csvfile, delimiter='\t',quotechar='"')
    for row in reader:
        cid = row["CID"]
        if cid.count(".") != 1:
#haaaaaaa
          control = " ".join(row["CONTROL"].split(" ")[1:])
          guidance = row["GUIDANCE"]
          test = " ".join(row["TEST"].split(" ")[1:])
          for i in ["\u201c","\u201d","\u2019"]:
              control = control.replace(i,"'")
              guidance = guidance.replace(i,"'")
              test = test.replace(i,"'")

          control = control.replace("\u2014","-")
          guidance = guidance.replace("\u2014","-")
          test = test.replace("\u2014","-")
          control = control.replace("\uf0b7","")
          guidance = guidance.replace("\uf0b7","")
          test = test.replace("\uf0b7","")
          control = control.replace("     "," ")
          guidance = guidance.replace("     "," ")
          test = test.replace("     "," ")

          parent_cid = row["CID"].split(".")
          parent_cid = f"{parent_cid[0]}.{parent_cid[1][0]}"

          record = {
            "name":control,
            "description":guidance,
            "mitigation":test,
            "ref_code":cid,
            "meta":{},
          }
          d_controls[parent_cid]["subcontrols"].append(
            record
          )


#print(json.dumps(d_controls,indent=4))
d=[]
for k,v in d_controls.items():
  d.append(v)
print(json.dumps(d,indent=4))
