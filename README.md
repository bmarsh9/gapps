# Gapps

### Table of Contents
1. [About](#about)
2. [Getting Started](#getting-started)
3. [Roadmap](#roadmap)

### About
Gapps is an Security compliance platform that makes it easy to track your progress against various security frameworks. Currently the only framework supported is SOC2 - however other frameworks will soon be added such as CIS CSC, CMMC and NIST CSF. *Gapps is currently in Alpha mode - while it works great, there may be some breaking changes as it evolves*.
- 200+ controls and 25+ policies out of the box for SOC2 (majority of policies are sourced from [strongdm/comply](https://github.com/strongdm/comply))
- Track the status of each control
- Add custom controls/policies
- WYSIWYG content editor

#### Check out the intro video below!

https://user-images.githubusercontent.com/26391921/203190627-84abcaa8-70ba-47f1-a957-dae7129299a6.mp4

#### Captures from the platform

Home Dashboard          |
:-------------------------:|
![](img/gapps_2.PNG)  |


Complete Controls          |
:-------------------------:|
![](img/gapps_1.PNG)  |


### Getting Started

##### Setting up the server with Docker

The following instructions are to get you started very quickly.

```
$ git clone https://github.com/bmarsh9/gapps.git; cd gapps
$ docker build --tag gapps .
$ export SETUP_DB=yes;docker-compose up -d
```

The server should be running on `http://<your-ip>:5000`  
The default email/password is `admin@example.com:admin`

### Roadmap
- [ ] Add additional frameworks such as NIST CSF, CMMC and CIS CSC
- [ ] Add procedures for SOC2
- [ ] Add evidence collection windows for SOC2
- [ ] Add reminders for control/evidence collection
- [ ] Add tagging support
- [ ] Improve policies and documentation
- [ ] Release endpoint agent to automate collection
