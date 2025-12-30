# This is a script to claim a number of devices into Dashboard, create a network for them and bind 
#  the network to a pre-existing template. Optionally you can also claim a license key. Switch networks
#  must be eligible for auto-bind (Auto-bind is not valid unless the switch template has at least
#  one profile and has at most one profile per switch model.)
#
# You need to have Python 3 and the Requests module installed. You
#  can download the module here: https://github.com/kennethreitz/requests
#  or install it using pip.
#
# To run the script, enter:
#  python deploydevices.py -k <Meraki Dashboard API key> -o <Organization Name> -s <List of serial numbers to be claimed> -n <Name of new network> -c <name of configuration template> [-t <list of tags to be added to network> -a <street address for devices> -g <Google API key> -m ignore_error -d <dhcp relay IP's]'
#
# To use the Google Maps API, you must have a Google API key and the following APIs must be enabled:
#     1. Google Maps Geocoding API
#     2. Google Maps Time Zone API
#
# To make script chaining easier, all lines containing informational messages to the user
#  start with the character @
#
# This file was last modified on 
#
# NAI - Original Script deploydevices.py from GitHub
# BTQ and Office site deploye
# V3.0 - BTQ and simple office site creator for WW and China dashboards
# V3.1 - Updated to allow creation of Guest-Wifi only sites, displays info about template being used
# V3.11 - Added Allaia to the dictionary list
# V3.21 - Fixed bugs on subnet configuration for Office templates
# V3.3 - Added support for Large BTQ template
# V3.31 - Updated Large BTQ subnets
# V3.32 - Updated Large BTQ mgmt subnet to /26
# V3.33 - Updated Large BTQ Voice subnet to /26
# V3.4 - Added possibility to configure Guest WiFi tagging on AP's
# V3.5 - Added support for new maison Buccellati
# V3.5.1 - Stop script if invalid S/N is found 
# V3.5.2 - Added Maison Delvaux site codes
# v3.6 - Added support for new ZTNA Office templates
# v3.7 - Added support for new ZTNA Manufacture templates
# v3.71 - Added error handling when checking subnet configuration
# v3.72 - Added support for RIC Manufacturing template
# v3.73 - Minor fix to deploy BUC/DLV btq's in China
# v3.8 - Updated API to v1
# v3.9 - Improvments for API v1 operations
# v3.91 - Improvements for rate limiting return codes
# v3.92 - Improvements for rate limiting return codes
# v3.93 - Several bug fixes for API v1 (v0 calls stopped working)
# v3.94 - Fix for hostnames and tags not being applied properly
# v3.95 - Fix tags not being applied properly on AP's
# v3.97 - Fix issue when adding only a small network with Appliance and AP
# v3.98 - Added support for new maison Vhernier
# v3.99 - Failing to autobind switches no longers stops the script
# v3.991 - Failing to autobind switches no longers stops the script
# v3.992 - Fixed a wrong Manufacture RIC template identification
# v3.993 - Fixed a bug that prevented the retrieval of the full list of networks
# v3.994 - Added support for new maison GVR
# v3.995 - Added support for new VCA France templates
# v4.0 - Added support for CW model WAP's
# v4.1 - Fixed VLAN 200 wrong subnet for ZTNA office
# v4.1 - Added support to add automatically MV and MG devices
# v4.1 - Fixed device counters for SW and MX
# v4.1 - Added support WFI BTQ's
# v4.1.1 - Fixed access to China Dashboard when getting organization networks.
# v4.1.1 - Replaced ICS with GT on team banner

import sys, getopt, requests, json, time, re, meraki

def printteam():
    print('___________________________________________________________________________')
    print('  ___________________')
    print(' /  _____/\__    ___/')
    print('/   \  ___  |    |   ')
    print('\    \_\  \ |    |   ')
    print(' \______  / |____|   ')
    print('        \/           ')
    print()
    print('_________                                    __  .__      .__  __          ')
    print('\_   ___ \  ____   ____   ____   ____  _____/  |_|__|__  _|__|/  |_ ___.__.')
    print('/    \  \/ /  _ \ /    \ /    \_/ __ \/ ___\   __\  \  \/ /  \   __<   |  |')
    print('\     \___(  <_> )   |  \   |  \  ___|  \___|  | |  |\   /|  ||  |  \___  |')
    print(' \______  /\____/|___|  /___|  /\___  >___  >__| |__| \_/ |__||__|  / ____|')
    print('v4.1.1  \/            \/     \/     \/    \/                        \/     ')
    print('___________________________________________________________________________')


def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message)

def printhelp():
    #prints help text

    printusertext('This is a script to claim MR, CW, MS and MX devices into Dashboard, create a new network for them')
    printusertext(' and bind the network to a pre-existing template. The script can also claim license capacity.')
    printusertext('')
    printusertext('To run the script, enter:')
    printusertext('python deploydevices.py -k <Meraki Dashboard API key> -o <Organization Name> -s <List of serial numbers to be claimed> -n <Name of new network> -c <name of configuration template> [-t <list of tags to be added to network> -a <street address for devices> -g <Google API key> -m ignore_error -d <dhcp relay IPs]')
    printusertext('')
    printusertext('Mandatory parameters:')
    printusertext(' -k <key>: Your Meraki Dashboard API key')
    printusertext(' -o <org>: Name of the Meraki Dashboard Organization to modify')
    printusertext(' -s <sn>: Serial number of the devices to claim. Use double quotes and spaces to enter')
    printusertext('       multiple serial numbers. Example: -s "AAAA-BBBB-CCCC DDDD-EEEE-FFFF"')
    printusertext('       You can also enter a license key as a serial number to claim along with devices')
    printusertext(' -n <netw>: Name the new network will have')
    printusertext(' -c <conft>: Name of the config template the new network will be bound to')
    printusertext('')
    printusertext('Optional parameters:')
    printusertext(' -t <tag>: If defined, network will be tagged with the given tags (separate by space)')
    printusertext(' -a <addr>: If defined, devices will be moved to given street address')
    printusertext(' -g <gkey>: Google API key. If defined, time zone will be set to match street address')
    printusertext(' -m ignore_error: If defined, the script will not stop if network exists')
    printusertext('')
    printusertext('Example:')
    printusertext(' python deploydevices.py -k 1234 -o MyCustomer -s XXXX-YYYY-ZZZZ -n "SF Branch" -c MyCfgTemplate')
    printusertext('')
    printusertext('Use double quotes ("") in Windows to pass arguments containing spaces. Names are case-sensitive.')
    
def getorgid(p_apikey, p_orgname):
    #looks up org id for a specific org name
    #on failure returns 'null'
    
    try:
        r = requests.get('https://api.meraki.com/api/v1/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 00: Unable to contact Meraki cloud')
        sys.exit(2)
    
    if r.status_code != requests.codes.ok:
        return 'null'
    
    rjson = r.json()
    
    for record in rjson:
        if record['name'] == p_orgname:
            return record['id']
    return('null')


def getorgidcn(p_apikey, p_orgname):
    #looks up org id for a specific org name
    #on failure returns 'null'
    
    try:
        r = requests.get('https://api.meraki.cn/api/v1/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 00: Unable to contact Meraki China cloud')
        sys.exit(2)
    
    if r.status_code != requests.codes.ok:
        return 'null'
    
    rjson = r.json()
    
    for record in rjson:
        if record['name'] == p_orgname:
            return record['id']
    return('null')

    
def getnwid(p_apikey, shardurl, p_orgid, p_nwname):
    #looks up network id for a network name
    #on failure returns 'null'
    
    print("Searching for network ID for ",p_nwname)
    
    dashboard = meraki.DashboardAPI(
        p_apikey,
        base_url='https://'+shardurl+'/api/v1',
        output_log=False,
        print_console=False
    )
    organization_id = p_orgid
    response = dashboard.organizations.getOrganizationNetworks(organization_id, total_pages='all')
    
    """
    try:
        r = requests.get('https://%s/api/v1/organizations/%s/networks' % (p_shardurl, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 02: Unable to contact Meraki cloud')
        sys.exit(2)

    if r.status_code != requests.codes.ok:
        print (r.status_code)
        print (r.text)
        return 'null'
    """
    
    for record in response:
        if record['name'] == p_nwname:
            return record['id']
    return('null') 
    """
    
    print(p_nwname)
    
    if r.ok:
        print("Searching for Network ID, retrieved networks lists!")
        rjson = r.json()
        for record in rjson:
            if record['name'] == p_nwname:
                print("Found ID for the network")
                print(record['name'])
                return record['id']
        
    else:
        print("Error getnwid #1")
        print (r.status_code)
        print (r.text)
        return 'null'
    
    #If no records found return null
    print("Returning null")
    return('null')
    """
    
def createnw(p_apikey, p_shardurl, p_dstorg, p_nwdata):
    #creates network if one does not already exist with the same name
    printusertext('Creating new Site...')
    
    #Creating list of tags to use in API call
    nwtags = p_nwdata['tags']
    
    #check if network exists
    getnwresult = getnwid(p_apikey, p_shardurl, p_dstorg, p_nwdata['name'])
    if getnwresult != 'null':
        printusertext('WARNING: Skipping network "%s" (Already exists)' % p_nwdata['name'])
        return('null')
    
    
    if p_nwdata['type'] == 'combined':
        #find actual device types
        nwtype = ["appliance","switch","wireless"]

    else:
        nwtype = p_nwdata['type']
        nwtype = nwtype.split(" ")
        
    
    if nwtype != 'systems manager':
        try:
            r = requests.post('https://%s/api/v1/organizations/%s/networks' % (p_shardurl, p_dstorg), data=json.dumps({'timeZone': p_nwdata['timeZone'], 'tags': nwtags, 'name': p_nwdata['name'], 'organizationId': p_dstorg, 'productTypes': nwtype}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            #Debug
            print (r.status_code)
            print (r.text)
            print (p_nwdata['type'])
            print (nwtype)
        except:
            printusertext('ERROR 03: Unable to contact Meraki cloud')
            sys.exit(2)
    else:
        printusertext('WARNING: Skipping network "%s" (Cannot create SM networks)' % p_nwdata['name'])
        return('null')
        
    return('ok')
    
def updatenw(p_apikey, p_shardhost, p_nwid, p_field, p_value):
    #updates network data    
        
    #time.sleep(API_EXEC_DELAY)
    try:
        r = requests.put('https://%s/api/v1/networks/%s' % (p_shardhost, p_nwid), data=json.dumps({p_field: p_value}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 21: Unable to contact Meraki cloud')
        sys.exit(2)
            
    if r.status_code != requests.codes.ok:
        return ('null')
    
    return('ok')
    
def gettemplateid(p_apikey, p_shardurl, p_orgid, p_tname):
    #looks up config template id for a config template name
    #on failure returns 'null'
    notratelimit = False
    
    """
    
    while not notratelimit:
        try:
            r = requests.get('https://%s/api/v1/organizations/%s/configTemplates' % (p_shardurl, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        except:
            printusertext('ERROR 04: Unable to contact Meraki cloud')
            sys.exit(2)
            
        # 392
        if r.status_code == 429:
            print("Rate limit response received, waiting to retry\n")
            time.sleep(int(response.headers["Retry-After"]))
            print("Retrying...")

        elif r.status_code != requests.codes.ok:
            return 'null'
            notratelimit == True
        else:
            print("Done get templates")
            notratelimit == True
    """
    try:
        r = requests.get('https://%s/api/v1/organizations/%s/configTemplates' % (p_shardurl, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 04: Unable to contact Meraki cloud')
        sys.exit(2)

    if r.status_code != requests.codes.ok:
        return 'null'
    else:
        print("Done get templates")

    rjson = r.json()
    
    for record in rjson:
        if record['name'] == p_tname:
            return record['id']
    return('null') 
    
def bindnw(p_apikey, p_shardurl, p_nwid, p_templateid, p_autobind):
    #binds a network to a template
    printusertext('Binding devices to template...')
    autobindvalue = 'true'
    """    
    if p_autobind:
        autobindvalue = 'true'
    else:
        autobindvalue = 'false'
    """
    try:
        r = requests.post('https://%s/api/v1/networks/%s/bind' % (p_shardurl, p_nwid), data=json.dumps({'configTemplateId': p_templateid, 'autoBind': autobindvalue}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 05: Unable to contact Meraki cloud')
        sys.exit(2)
        
    if r.status_code != requests.codes.ok:
        print("Autobind code NOK!")
        print(r.status_code)
        print(r.content)
        
        autobindvalue = 'false'
        
        printusertext("Warning 19: Trying again without autobinding the switches")
        
        try:
            r = requests.post('https://%s/api/v1/networks/%s/bind' % (p_shardurl, p_nwid), data=json.dumps({'configTemplateId': p_templateid, 'autoBind': autobindvalue}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        except:
            printusertext('ERROR 05: Unable to contact Meraki cloud')
            sys.exit(2)
        
        if r.status_code != requests.codes.ok:
            print("Autobind code NOK!")
            print(r.status_code)
            print(r.content)
            return 'null'
        
    return('ok')
    
def claimdeviceorg(p_apikey, p_shardurl, p_orgid, p_devserial):
    #claims a device into an org without adding to a network
    time.sleep(0.5)
    try:
        r = requests.post('https://%s/api/v1/organizations/%s/inventory/claim' % (p_shardurl, p_orgid), data=json.dumps({'serials': p_devserial}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        print('Claiming device to RISA\n')
        
        if r.status_code == 429:
            while r.status_code == 429:
                print('Got status code 429 for rate limit')
                time.sleep(1.5)
                print('Retrying...')
                r = requests.post('https://%s/api/v1/organizations/%s/inventory/claim' % (p_shardurl, p_orgid), data=json.dumps({'serials': p_devserial}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
                print('Claiming device to RISA\n')
        
        if r.status_code != requests.codes.ok:
            print(r.status_code)
            print(r.content)
        
    except:
        printusertext('ERROR 06: Unable to contact Meraki cloud')
        sys.exit(2)
    
    return(0)
    
def claimlicenseorg(p_apikey, p_shardurl, p_orgid, p_licensekey):
    #claims a license key into an org
    
    try:
        r = requests.post('https://%s/api/v1/organizations/%s/inventory/claim' % (p_shardurl, p_orgid), data=json.dumps({'licenses': p_licensekey, 'mode': 'addDevices'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 07: Unable to contact Meraki cloud')
        sys.exit(2)
    
    return(0)
    
def claimdevice(p_apikey, p_shardurl, p_nwid, p_devserial):
    #claims a device into a network
    print('Claiming device S/N '+str(p_devserial)+' to the new site')
    try:
        r = requests.post('https://%s/api/v1/networks/%s/devices/claim' % (p_shardurl, p_nwid), data=json.dumps({'serials': p_devserial}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 08: Unable to contact Meraki cloud')
        sys.exit(2)
        
    if r.status_code != requests.codes.ok:
        print(r.status_code)
        print(r.content)
        sys.exit(2)
    
    return(0)
    
def getdeviceinfo(p_apikey, p_shardurl, p_nwid, p_serial):
    #returns info for a single device
    #on failure returns lone device record, with serial number 'null'
    try:
        r = requests.get('https://%s/api/v1/devices/%s' % (p_shardurl, p_serial), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Accept': 'application/json'})
    except:
        printusertext('ERROR 09: Unable to contact Meraki cloud')
        sys.exit(2)
    
    returnvalue = []
    if r.status_code != requests.codes.ok:
        print(r.status_code)
        print(r.content)
        returnvalue = {'serial':'null', 'model':'null'}
        return(returnvalue)
    
    rjson = r.json()
    
    return(rjson) 
    
def setdevicedata(p_apikey, p_shardurl, p_nwid, p_devserial, p_field, p_value, p_nwtags, p_movemarker):
    #modifies value of device record. Returns the new value
    #on failure returns one device record, with all values 'null'
    #p_movemarker is boolean: True/False
    
    print("Serial is: "+p_devserial)
    print("Tags are: ")
    print(p_nwtags)
    
    movevalue = "false"
    if p_movemarker:
        movevalue = "true"
    
    try:
        #r = requests.put('https://%s/api/v1/networks/%s/devices/%s' % (p_shardurl, p_nwid, p_devserial), data=json.dumps({p_field: p_value, 'moveMapMarker': movevalue, 'tags': p_nwtags}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        r = requests.put('https://%s/api/v1/devices/%s' % (p_shardurl, p_devserial), data=json.dumps({p_field: p_value, 'moveMapMarker': movevalue, 'tags': p_nwtags}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 10: Unable to contact Meraki cloud')
        sys.exit(2)
            
    if r.status_code != requests.codes.ok:
        print(r.status_code)
        print(r.content)
        return ('null')
    
    return('ok')

def getorgdeviceinfo(p_apikey, p_shardurl, p_orgid, p_devserial):
    #gets basic device info from org inventory. device does not need to be part of a network
    time.sleep(0.2)
    try:
        r = requests.get('https://%s/api/v1/organizations/%s/inventory/devices/%s' % (p_shardurl, p_orgid, p_devserial), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 11: Unable to contact Meraki cloud')
        sys.exit(2)
    
    returnvalue = {}
    if r.status_code != requests.codes.ok:
        print(r.status_code)
        returnvalue = {'serial':'null', 'model':'null'}
        return(returnvalue)
    
    record = r.json()
    #print(record)
    
    returnvalue = {'mac': record['mac'], 'serial': record['serial'], 'networkId': record['networkId'], 'model': record['model'], 'claimedAt': record['claimedAt']}
                
    return(returnvalue) 

### Check DCHP parameters ###

def checkdhcp(p_apikey, p_shardurl, p_nwid):
    try:
        r = requests.get('https://%s/api/v1/networks/%s/appliance/vlans' % (p_shardurl, p_nwid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR XX: Unable to contact Meraki cloud')
        sys.exit(2)
        
    if r.status_code != requests.codes.ok:
        printusertext("Something went wrong checking DHCP settings, exiting...")
        print(r.status_code)
        print(r.content)
        sys.exit(2)
    
    rjson = r.json()
    return rjson


### Update VLAN Starts ###    

def updatevlanbtq(p_apikey, p_shardurl, nwid, p_subnet):
    #updates vlans subnets for new network
    printusertext('-== BTQ ==-')
    printusertext('Updating VLAN subnets...')
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
#    try:
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
        time.sleep(0.5)
        if vlan['id'] == 10 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/10' % (p_shardurl, nwid), data=json.dumps({'name': '10-Voice', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 10 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/10' % (p_shardurl, nwid), data=json.dumps({'name': '10-Voice', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message

        elif vlan['id'] == 20 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/20' % (p_shardurl, nwid), data=json.dumps({'name': '20-POS-HUB', 'applianceIp': str(p_subnet)+'97', 'subnet': str(p_subnet)+'96/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content)
        elif vlan['id'] == 20 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/20' % (p_shardurl, nwid), data=json.dumps({'name': '20-POS-HUB', 'applianceIp': str(p_subnet)+'97', 'subnet': str(p_subnet)+'96/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        
        elif vlan['id'] == 30 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/30' % (p_shardurl, nwid), data=json.dumps({'name': '30-CC_Terms', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content)
        elif vlan['id'] == 30 and vlan['dhcpHandling'] != relay:    
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/30' % (p_shardurl, nwid), data=json.dumps({'name': '30-CC_Terms', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
                
        elif vlan['id'] == 50 and vlan['dhcpHandling'] == relay:        
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/50' % (p_shardurl, nwid), data=json.dumps({'name': '50-PCs-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content)
        elif vlan['id'] == 50 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/50' % (p_shardurl, nwid), data=json.dumps({'name': '50-PCs-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
        
        # Vlan 55 is only used in BUC BTQ's
        
        elif vlan['id'] == 55 and vlan['dhcpHandling'] == relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/55' % (p_shardurl, nwid), data=json.dumps({'name': '55-Printers', 'applianceIp': str(p_subnet)+'209', 'subnet': str(p_subnet)+'208/28','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('BUC/DLV/VHE Response >>> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        elif vlan['id'] == 55 and vlan['dhcpHandling'] != relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/55' % (p_shardurl, nwid), data=json.dumps({'name': '55-Printers', 'applianceIp': str(p_subnet)+'209', 'subnet': str(p_subnet)+'208/28'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('BUC/DLV/VHE Response ->> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        
        
        elif vlan['id'] == 60 and vlan['dhcpHandling'] == relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/60' % (p_shardurl, nwid), data=json.dumps({'name': '60-NonIT', 'applianceIp': str(p_subnet)+'225', 'subnet': str(p_subnet)+'224/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content)
        elif vlan['id'] == 60 and vlan['dhcpHandling'] != relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/60' % (p_shardurl, nwid), data=json.dumps({'name': '60-NonIT', 'applianceIp': str(p_subnet)+'225', 'subnet': str(p_subnet)+'224/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content)
                
        elif vlan['id'] == 80 and vlan['dhcpHandling'] == relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/80' % (p_shardurl, nwid), data=json.dumps({'name': '80-Reserved', 'applianceIp': str(p_subnet)+'209', 'subnet': str(p_subnet)+'208/28','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>-> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        elif vlan['id'] == 80 and vlan['dhcpHandling'] != relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/80' % (p_shardurl, nwid), data=json.dumps({'name': '80-Reserved', 'applianceIp': str(p_subnet)+'209', 'subnet': str(p_subnet)+'208/28'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->-> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
         
        elif vlan['id'] == 100 and vlan['dhcpHandling'] == relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-Reserved', 'applianceIp': str(p_subnet)+'161', 'subnet': str(p_subnet)+'160/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        elif vlan['id'] == 100 and vlan['dhcpHandling'] != relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-Reserved', 'applianceIp': str(p_subnet)+'161', 'subnet': str(p_subnet)+'160/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        
        elif vlan['id'] == 400:
            r8 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/400' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/28'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r8.status_code)) #Remove comment for troubleshooting
            if r8.status_code != 200:
                print (r8.content)
                printusertext('Vlan 400 has local DHCP enabled??')
    """        
    except:
        printusertext('ERROR 12: Unable to contact Meraki cloud')
        sys.exit(2)
        """
    try:
        if r1.status_code == r2.status_code == r3.status_code == r4.status_code == r5.status_code == r6.status_code == r7.status_code == r8.status_code != requests.codes.ok:
            printusertext('Please confirm Vlan subnets are OK')
            return ('null')
        printusertext('Finished updating VLANs')   
        return('ok')
    except:
        print()
        printusertext("WARNING!")
        printusertext("Something wrong with subnet confituration, please check on Dashboard")
        print()

def updatevlanlargebtq(p_apikey, p_shardurl, nwid, p_subnet):
    #updates vlans subnets for new network
    
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    print (p_subnet)
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== Large BTQ ==-')
    printusertext('Updating VLAN subnets...')

    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
        time.sleep(0.5)
        if vlan['id'] == 10 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/10' % (p_shardurl, nwid), data=json.dumps({'name': '10-Voice', 'applianceIp': str(p_subnet)+'1',
                                                                                                              'subnet': str(p_subnet)+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 10 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/10' % (p_shardurl, nwid), data=json.dumps({'name': '10-Voice', 'applianceIp': str(p_subnet)+'1',
                                                                                                              'subnet': str(p_subnet)+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message

        elif vlan['id'] == 20 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/20' % (p_shardurl, nwid), data=json.dumps({'name': '20-POS-HUB', 'applianceIp': str(p_subnet)+'65',
                                                                                                              'subnet': str(p_subnet)+'64/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content)
        elif vlan['id'] == 20 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/20' % (p_shardurl, nwid), data=json.dumps({'name': '20-POS-HUB', 'applianceIp': str(p_subnet)+'65',
                                                                                                              'subnet': str(p_subnet)+'64/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        
        elif vlan['id'] == 30 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/30' % (p_shardurl, nwid), data=json.dumps({'name': '30-CC_Terms', 'applianceIp': str(p_subnet)+'129',
                                                                                                              'subnet': str(p_subnet)+'128/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content)
        elif vlan['id'] == 30 and vlan['dhcpHandling'] != relay:    
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/30' % (p_shardurl, nwid), data=json.dumps({'name': '30-CC_Terms', 'applianceIp': str(p_subnet)+'129',
                                                                                                              'subnet': str(p_subnet)+'128/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
                print ('Vlan 30 subnet is: '+str(p_subnet)+'128/26')
                
        elif vlan['id'] == 50 and vlan['dhcpHandling'] == relay:        
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/50' % (p_shardurl, nwid), data=json.dumps({'name': '50-PCs-Printers', 'applianceIp': subnet2+'1',
                                                                                                              'subnet': subnet2+'0/25','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content)
        elif vlan['id'] == 50 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/50' % (p_shardurl, nwid), data=json.dumps({'name': '50-PCs-Printers', 'applianceIp': subnet2+'1',
                                                                                                              'subnet': subnet2+'0/25'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message    
        
        elif vlan['id'] == 60 and vlan['dhcpHandling'] == relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/60' % (p_shardurl, nwid), data=json.dumps({'name': '60-NonIT', 'applianceIp': subnet2+'129',
                                                                                                              'subnet': subnet2+'128/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content)
        elif vlan['id'] == 60 and vlan['dhcpHandling'] != relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/60' % (p_shardurl, nwid), data=json.dumps({'name': '60-NonIT', 'applianceIp': subnet2+'129',
                                                                                                              'subnet': subnet2+'128/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content)

        elif vlan['id'] == 100 and vlan['dhcpHandling'] == relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-CCTV', 'applianceIp': subnet2+'193',
                                                                                                               'subnet': subnet2+'192/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        elif vlan['id'] == 100 and vlan['dhcpHandling'] != relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-CCTV', 'applianceIp': subnet2+'193',
                                                                                                               'subnet': subnet2+'192/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        
        elif vlan['id'] == 400:
            r8 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/400' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': str(p_subnet)+'193',
                                                                                                               'subnet': str(p_subnet)+'192/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r8.status_code)) #Remove comment for troubleshooting
            if r8.status_code != 200:
                print (r8.content)
                printusertext('Vlan 400 has local DHCP enabled??')
    """        
    except:
        printusertext('ERROR 12: Unable to contact Meraki cloud')
        sys.exit(2)
        """
    
    if r1.status_code == r2.status_code == r3.status_code == r4.status_code == r5.status_code == r7.status_code == r8.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')


def updatevlanoff(p_apikey, p_shardurl, nwid, p_subnet):
    #updates Simple Officevlans subnets for new network
    print (p_subnet)
    relay = 'Relay DHCP to another server'
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== Simple Office ==-')
    printusertext('Updating VLAN subnets...')
        
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
       
        time.sleep(0.2)
        if vlan['id'] == 100 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-PCs-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/24','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 100 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-PCs-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/24'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message

        elif vlan['id'] == 300 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content)
        elif vlan['id'] == 300 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        
        elif vlan['id'] == 600 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/600' % (p_shardurl, nwid), data=json.dumps({'name': '600-Non-IT-CCTV', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content)
        elif vlan['id'] == 600 and vlan['dhcpHandling'] != relay:    
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/600' % (p_shardurl, nwid), data=json.dumps({'name': '600-Non-IT-CCTV', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
                
        elif vlan['id'] == 999:        
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'193', 'subnet': subnet2+'192/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content)
                printusertext('Vlan 999 has local DHCP enabled??')
        """
        elif vlan['id'] == 999 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'193', 'subnet': subnet2+'192/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
        """
        """
    except:
        printusertext('ERROR 12: Uho... something went wrong!')
        sys.exit(2)
        """
    if r1.status_code == r2.status_code == r3.status_code == r4.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')


def updatevlanztoff(p_apikey, p_shardurl, nwid, p_subnet):
    #updates Simple Officevlans subnets for new network
    print (p_subnet)
    relay = 'Relay DHCP to another server'
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== ZTNA Office ==-')
    printusertext('Updating VLAN subnets...')
    
        
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
       
        
        if vlan['id'] == 200 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': subnet2+'65', 'subnet': str(p_subnet)+'64/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 200 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': subnet2+'65', 'subnet': str(p_subnet)+'64/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message

        elif vlan['id'] == 300 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content)
        elif vlan['id'] == 300 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        
        elif vlan['id'] == 600 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/600' % (p_shardurl, nwid), data=json.dumps({'name': '600-Non-IT-CCTV', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content)
        elif vlan['id'] == 600 and vlan['dhcpHandling'] != relay:    
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/600' % (p_shardurl, nwid), data=json.dumps({'name': '600-Non-IT-CCTV', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
                
        elif vlan['id'] == 999:        
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'193', 'subnet': subnet2+'192/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content)
                printusertext('Vlan 999 has local DHCP enabled??')
        """
        elif vlan['id'] == 999 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'193', 'subnet': subnet2+'192/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
        """
        """
    except:
        printusertext('ERROR 12: Uho... something went wrong!')
        sys.exit(2)
        """
    if r1.status_code == r2.status_code == r3.status_code == r4.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')



def updatevlanztmanuf(p_apikey, p_shardurl, nwid, p_subnet):
    #updates Simple Officevlans subnets for new network
    print (p_subnet)
    relay = 'Relay DHCP to another server'
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== ZTNA Manufacture ==-')
    printusertext('Updating VLAN subnets...')
    
        
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
       
        
        if vlan['id'] == 200 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 200 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        
        if vlan['id'] == 731 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/731' % (p_shardurl, nwid), data=json.dumps({'name': '731-Non-IT', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        elif vlan['id'] == 731 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/731' % (p_shardurl, nwid), data=json.dumps({'name': '731-Non-IT', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        
        if vlan['id'] == 732 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/732' % (p_shardurl, nwid), data=json.dumps({'name': '732-CCTV', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
        elif vlan['id'] == 732 and vlan['dhcpHandling'] != relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/732' % (p_shardurl, nwid), data=json.dumps({'name': '732-CCTV', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message

        if vlan['id'] == 711 and vlan['dhcpHandling'] == relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/711' % (p_shardurl, nwid), data=json.dumps({'name': '711-TustedManuf', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
        elif vlan['id'] == 711 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/711' % (p_shardurl, nwid), data=json.dumps({'name': '711-TustedManuf', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message

        if vlan['id'] == 811 and vlan['dhcpHandling'] == relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/811' % (p_shardurl, nwid), data=json.dumps({'name': '811-UntrustedManuf', 'applianceIp': str(p_subnet)+'225', 'subnet': str(p_subnet)+'224/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content) #Print error message
        elif vlan['id'] == 811 and vlan['dhcpHandling'] != relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/811' % (p_shardurl, nwid), data=json.dumps({'name': '811-UntrustedManuf', 'applianceIp': str(p_subnet)+'225', 'subnet': str(p_subnet)+'224/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content) #Print error message

        elif vlan['id'] == 300 and vlan['dhcpHandling'] == relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        elif vlan['id'] == 300 and vlan['dhcpHandling'] != relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content) #Print error message
        
        elif vlan['id'] == 152 and vlan['dhcpHandling'] == relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/152' % (p_shardurl, nwid), data=json.dumps({'name': '152-RCCWH', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        elif vlan['id'] == 152 and vlan['dhcpHandling'] != relay:    
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/152' % (p_shardurl, nwid), data=json.dumps({'name': '152-RCCWH', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content) #Print error message
                
        elif vlan['id'] == 999:        
            r8 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'193', 'subnet': subnet2+'192/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r8.status_code)) #Remove comment for troubleshooting
            if r8.status_code != 200:
                print (r8.content)
                printusertext('Vlan 999 has local DHCP enabled??')

    if r1.status_code == r2.status_code == r3.status_code == r4.status_code == r5.status_code == r6.status_code == r7.status_code == r8.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')


def updatevlanmanuf(p_apikey, p_shardurl, nwid, p_subnet):
    #updates Simple Officevlans subnets for new network
    print (p_subnet)
    relay = 'Relay DHCP to another server'
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== Manufacture RIC ==-')
    printusertext('Updating VLAN subnets...')
    
        
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
       
        
        if vlan['id'] == 300 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 300 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        
        if vlan['id'] == 731 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/731' % (p_shardurl, nwid), data=json.dumps({'name': '731-Non-IT', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        elif vlan['id'] == 731 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/731' % (p_shardurl, nwid), data=json.dumps({'name': '731-Non-IT', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        
        if vlan['id'] == 732 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/732' % (p_shardurl, nwid), data=json.dumps({'name': '732-CCTV', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
        elif vlan['id'] == 732 and vlan['dhcpHandling'] != relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/732' % (p_shardurl, nwid), data=json.dumps({'name': '732-CCTV', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r3.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message

        if vlan['id'] == 711 and vlan['dhcpHandling'] == relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/711' % (p_shardurl, nwid), data=json.dumps({'name': '711-TustedManuf', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
        elif vlan['id'] == 711 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/711' % (p_shardurl, nwid), data=json.dumps({'name': '711-TustedManuf', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message

        if vlan['id'] == 811 and vlan['dhcpHandling'] == relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/811' % (p_shardurl, nwid), data=json.dumps({'name': '811-UntrustedManuf', 'applianceIp': str(p_subnet)+'225', 'subnet': str(p_subnet)+'224/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content) #Print error message
        elif vlan['id'] == 811 and vlan['dhcpHandling'] != relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/811' % (p_shardurl, nwid), data=json.dumps({'name': '811-UntrustedManuf', 'applianceIp': str(p_subnet)+'225', 'subnet': str(p_subnet)+'224/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content) #Print error message

        elif vlan['id'] == 100 and vlan['dhcpHandling'] == relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-PCs-Printers', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/25','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        elif vlan['id'] == 100 and vlan['dhcpHandling'] != relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/100' % (p_shardurl, nwid), data=json.dumps({'name': '100-PCs-Printers', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/25'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content) #Print error message
        
        elif vlan['id'] == 152 and vlan['dhcpHandling'] == relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/152' % (p_shardurl, nwid), data=json.dumps({'name': '152-RCCWH', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        elif vlan['id'] == 152 and vlan['dhcpHandling'] != relay:    
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/152' % (p_shardurl, nwid), data=json.dumps({'name': '152-RCCWH', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content) #Print error message
                
        elif vlan['id'] == 999:        
            r8 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'193', 'subnet': subnet2+'192/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r8.status_code)) #Remove comment for troubleshooting
            if r8.status_code != 200:
                print (r8.content)
                printusertext('Vlan 999 has local DHCP enabled??')

    if r1.status_code == r2.status_code == r3.status_code == r4.status_code == r5.status_code == r6.status_code == r7.status_code == r8.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')


#VCA France Templates

def updatevlanvcamanuf(p_apikey, p_shardurl, nwid, p_subnet):
    #updates Simple Officevlans subnets for new network
    print (p_subnet)
    relay = 'Relay DHCP to another server'
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== VCA France Manufacture ==-')
    printusertext('Updating VLAN subnets...')
    
        
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
       
        
        if vlan['id'] == 200 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 200 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': str(p_subnet)+'193', 'subnet': str(p_subnet)+'192/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        
        if vlan['id'] == 731 and vlan['dhcpHandling'] == relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/731' % (p_shardurl, nwid), data=json.dumps({'name': '731-Non-IT', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
        elif vlan['id'] == 731 and vlan['dhcpHandling'] != relay:
            r2 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/731' % (p_shardurl, nwid), data=json.dumps({'name': '731-Non-IT', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r2.status_code)) #Remove comment for troubleshooting
            if r2.status_code != 200:
                print (r2.content) #Print error message
                
        elif vlan['id'] == 152 and vlan['dhcpHandling'] == relay:
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/152' % (p_shardurl, nwid), data=json.dumps({'name': '152-RCCWH', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content)
        elif vlan['id'] == 152 and vlan['dhcpHandling'] != relay:    
            r3 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/152' % (p_shardurl, nwid), data=json.dumps({'name': '152-RCCWH', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r3.status_code != 200:
                print (r3.content) #Print error message
                
        if vlan['id'] == 711 and vlan['dhcpHandling'] == relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/711' % (p_shardurl, nwid), data=json.dumps({'name': '711-TustedManuf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
        elif vlan['id'] == 711 and vlan['dhcpHandling'] != relay:
            r4 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/711' % (p_shardurl, nwid), data=json.dumps({'name': '711-TustedManuf', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r4.status_code)) #Remove comment for troubleshooting
            if r4.status_code != 200:
                print (r4.content) #Print error message
                
        if vlan['id'] == 811 and vlan['dhcpHandling'] == relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/811' % (p_shardurl, nwid), data=json.dumps({'name': '811-UntrustedManuf', 'applianceIp': subnet2+'65', 'subnet': subnet2+'64/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content) #Print error message
        elif vlan['id'] == 811 and vlan['dhcpHandling'] != relay:
            r5 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/811' % (p_shardurl, nwid), data=json.dumps({'name': '811-UntrustedManuf', 'applianceIp': subnet2+'65', 'subnet': subnet2+'64/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r5.status_code)) #Remove comment for troubleshooting
            if r5.status_code != 200:
                print (r5.content) #Print error message
                
        elif vlan['id'] == 300 and vlan['dhcpHandling'] == relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': str(p_subnet)+'161', 'subnet': str(p_subnet)+'160/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        elif vlan['id'] == 300 and vlan['dhcpHandling'] != relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': str(p_subnet)+'161', 'subnet': str(p_subnet)+'160/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content) #Print error message
        
        elif vlan['id'] == 910 and vlan['dhcpHandling'] == relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/910' % (p_shardurl, nwid), data=json.dumps({'name': '910-Cybervision', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/27','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        elif vlan['id'] == 910 and vlan['dhcpHandling'] != relay:    
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/910' % (p_shardurl, nwid), data=json.dumps({'name': '910-Cybervision', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/27'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content) #Print error message
                
        elif vlan['id'] == 999:        
            r8 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': subnet2+'129', 'subnet': subnet2+'128/25'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r8.status_code)) #Remove comment for troubleshooting
            if r8.status_code != 200:
                print (r8.content)
                printusertext('Vlan 999 has local DHCP enabled??')

    if r1.status_code == r2.status_code == r3.status_code == r4.status_code == r5.status_code == r6.status_code == r7.status_code == r8.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')



def updatevlanvcaoffice(p_apikey, p_shardurl, nwid, p_subnet):
    #updates Simple Officevlans subnets for new network
    print (p_subnet)
    relay = 'Relay DHCP to another server'
    octets = re.split(r'\.|/', p_subnet)
    #print(Octets)
    octet3=int(octets[2])+1
    #print (Octet3)
    subnet2=(str(octets[0])+"."+str(octets[1])+"."+str(octet3)+".")
    print (subnet2)
    printusertext('-== VCA France Office ==-')
    printusertext('Updating VLAN subnets...')
    
        
    dhcpsettings = checkdhcp(p_apikey, p_shardurl, nwid)
    # DHCP relay message
    relay = 'Relay DHCP to another server'
    
    printusertext('Please check if all Responses are 200 (OK)')
    
    for vlan in dhcpsettings:
       
        
        if vlan['id'] == 200 and vlan['dhcpHandling'] == relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
        elif vlan['id'] == 200 and vlan['dhcpHandling'] != relay:
            r1 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/200' % (p_shardurl, nwid), data=json.dumps({'name': '200-Printers', 'applianceIp': str(p_subnet)+'1', 'subnet': str(p_subnet)+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r1.status_code)) #Remove comment for troubleshooting
            if r1.status_code != 200:
                print (r1.content) #Print error message
                        
        elif vlan['id'] == 300 and vlan['dhcpHandling'] == relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content)
        elif vlan['id'] == 300 and vlan['dhcpHandling'] != relay:
            r6 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/300' % (p_shardurl, nwid), data=json.dumps({'name': '300-Voice-VideoConf', 'applianceIp': str(p_subnet)+'65', 'subnet': str(p_subnet)+'64/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->>' + str(r6.status_code)) #Remove comment for troubleshooting
            if r6.status_code != 200:
                print (r6.content) #Print error message
        
        elif vlan['id'] == 600 and vlan['dhcpHandling'] == relay:
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/600' % (p_shardurl, nwid), data=json.dumps({'name': '600-CCTV', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26','dhcpRelayServerIps': vlan['dhcpRelayServerIps']}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response >>> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content)
        elif vlan['id'] == 600 and vlan['dhcpHandling'] != relay:    
            r7 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/600' % (p_shardurl, nwid), data=json.dumps({'name': '600-CCTV', 'applianceIp': subnet2+'1', 'subnet': subnet2+'0/26'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response ->> ' + str(r7.status_code)) #Remove comment for troubleshooting
            if r7.status_code != 200:
                print (r7.content) #Print error message
                
        elif vlan['id'] == 999:        
            r8 = requests.put('https://%s/api/v1/networks/%s/appliance/vlans/999' % (p_shardurl, nwid), data=json.dumps({'name': 'Management', 'applianceIp': str(p_subnet)+'129', 'subnet': str(p_subnet)+'128/25'}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
            print ('Response --> ' + str(r8.status_code)) #Remove comment for troubleshooting
            if r8.status_code != 200:
                print (r8.content)
                printusertext('Vlan 999 has local DHCP enabled??')

    if r1.status_code == r6.status_code == r7.status_code == r8.status_code != requests.codes.ok:
        return ('null')
    printusertext('Finished updating VLANs')   
    return('ok')



### Update VLAN ends ###
    
def getgoogletimezone(p_googlekey, p_address):
    #returns the timezone associated to a specified address by using Google Maps APIs
    try:
        r = requests.get('https://maps.googleapis.com/maps/api/geocode/json?address=%s&key=%s' % (p_address, p_googlekey) )
    except:
        printusertext('WARNING: Unable to contact Google cloud')
        return('null')
        
    rjson = r.json()
    if rjson['status'] != 'OK':
        return('null')

    glatitude  = rjson['results'][0]['geometry']['location']['lat']
    glongitude = rjson['results'][0]['geometry']['location']['lng']
    
    try:
        s = requests.get('https://maps.googleapis.com/maps/api/timezone/json?location=%s,%s&timestamp=%f&key=%s' % (glatitude, glongitude, time.time(), p_googlekey) )
    except:
        printusertext('WARNING: Unable to contact Google cloud')
        return('null')

    sjson = s.json()
    
    if sjson['status'] == 'OK':
        return(sjson['timeZoneId'])

    return('null')


def firstTwo(string):
    return string[:2]
    
def main(argv):
    # Define Variables
    mx_count = 0
    mr_count = 0
    ms_count = 0
    mv_count = 0
    mg_count = 0
    mrtags = []
    # Print team logo
    printteam()
    printusertext('Merakifying...')
    #set default values for command line arguments
    arg_apikey = 'null'
    arg_orgname = 'null'
    arg_serial = 'null'
    arg_nwname = 'null'
    arg_template = 'null'
    arg_subnet = 'null'
    arg_modexisting = 'null'
    arg_address = 'null'
    arg_nwtags = []
    arg_guestwifi = 'null'
    arg_googlekey = ''

    
    # 2-Letter Maison code
    Code2L = ("LS","BM","CA","CH","DU","IW","JL","LA","MB","PA","PI","PU","RD","RI","SH","VA","VC","SE","AA","BU","DL","VH","GV","WF","LB")

    # 3-Letter Maison code
    Code3L = ("ALS","BEM","CAR","CHL","DUN","IWC","JLC","LAN","MTB","PAN","PIA","PUR","RDU","RIC","SHT","VAC","VCA","SER","AAL","BUC","DLV","VHE","GVR","WFI","LAB")

    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:s:n:c:w:m:a:x:g:t:')
    except getopt.GetoptError:
        printhelp()
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            printhelp()
            sys.exit()
        elif opt == '-k':
            arg_apikey = arg
        elif opt == '-o':
            arg_orgname = arg
        elif opt == '-s':
            arg_serial = arg
        elif opt == '-n':
            arg_nwname = arg
        elif opt == '-c':
            arg_template = arg
        elif opt == '-w':
            arg_subnet = arg
        elif opt == '-m':
            arg_modexisting = arg
        elif opt == '-a':
            arg_address = arg
        elif opt == '-t':
            arg_nwtags = arg
        elif opt == '-x':
            arg_guestwifi = arg
        elif opt == '-g':
            arg_googlekey = arg
    
    if firstTwo(arg_nwname) == 'CN':
        arg_orgname = 'RISA CN'
    else:
        arg_orgname = 'RISA'
    

                
    #check if all parameters that are required parameters have been given
    if arg_apikey == 'null' or arg_orgname == 'null' or arg_serial == 'null' or arg_nwname == 'null' or arg_template == 'null' or arg_subnet == 'null':
        #print (arg_subnet)
        printhelp()
        sys.exit(2)
    
    printusertext('Template is ---> "' + arg_template + '"')
    
    #set optional flag to ignore error if network already exists
    stoponerror = True
    if arg_modexisting == 'ignore_error':
        stoponerror = False
    
    
    #Check what dashboard to use (China or WW)
#    if (arg_template.find('CN') != -1):
    if arg_orgname == 'RISA CN':
 #       dashboard = 'CN'
        print('--== RISA CN Dashboard ==--')
        orgid = getorgidcn(arg_apikey, arg_orgname)
        shardurl = 'api.meraki.cn'
    else:
        print('--== RISA Dashboard ==--')
#        dashboard = 'WW'
        orgid = getorgid(arg_apikey, arg_orgname)
        shardurl = 'api.meraki.com'    
    
       
    if orgid == 'null':
        print('Dashboard is ' + arg_orgname)
        printusertext('ERROR 12: Fetching organization failed (wrong password?)')
        sys.exit(2)
    printusertext('Fetching organization OK')
    
    
    #make sure that a network does not already exist with the same name    
    nwid = getnwid(arg_apikey, shardurl, orgid, arg_nwname)
    if nwid != 'null' and stoponerror:
        printusertext('ERROR 14: Network with that name already exists')
        sys.exit(2)    
        
    #get template ID for template name argument
    templateid = gettemplateid(arg_apikey, shardurl, orgid, arg_template)
    if templateid == 'null':
        printusertext('ERROR 15: Unable to find template: ' + arg_template)
        sys.exit(2)    
        
    #get serial numbers from parameter -s
    devicelist = {}
    devicelist['serial'] = arg_serial.split(" ")
    devicelist['model'] = []
    
    for i in range (0, len(devicelist['serial']) ):
        deviceserial = []
        deviceserial = [devicelist['serial'][i]]
        
        #claimdeviceorg(arg_apikey, shardurl, orgid, devicelist['serial'][i])
        claimdeviceorg(arg_apikey, shardurl, orgid, deviceserial)
        
        #check if device has been claimed successfully
        #deviceinfo = getorgdeviceinfo(arg_apikey, shardurl, orgid, devicelist['serial'][i])
        deviceinfo = getorgdeviceinfo(arg_apikey, shardurl, orgid, devicelist['serial'][i])
        if deviceinfo['serial'] == 'null':
            printusertext('INFO: Serial number %s is a license or unsupported device?' % devicelist['serial'][i])
            printusertext('Exiting script, please review S/Ns')
            exit()
            claimlicenseorg(arg_apikey, shardurl, orgid, devicelist['serial'][i])
        devicelist['model'].append(deviceinfo['model'])
        
    #compile list of different product types in order to create correct type of network
    devicetypes = {'mx': False, 'ms': False, 'mr': False, 'mv': False, 'mg': False}
    for record in devicelist['model']:
        print('Device Type '+ record)
        if record [:2] == 'MX' or record [:1] == 'Z':
            devicetypes['mx'] = True
        elif record [:2] == 'MS':
            devicetypes['ms'] = True
        elif record [:2] == 'MR' or record [:2] == 'CW':
            devicetypes['mr'] = True
        elif record [:2] == 'MV':
            devicetypes['mv'] = True
        elif record [:2] == 'MG':
            devicetypes['mg'] = True
            
    #build network type string for network creation
    nwtypestring = ""
    if devicetypes['mx']:
        if len(nwtypestring) > 0:
            nwtypestring += ' appliance'
        else:
            nwtypestring = 'appliance'

    if devicetypes['mr']:
        if len(nwtypestring) > 0:
            nwtypestring += ' wireless'
        else:
            nwtypestring = 'wireless'
    
    if devicetypes['ms']:
        if len(nwtypestring) > 0:
            nwtypestring += ' switch'
        else:
            nwtypestring = 'switch'
    if devicetypes['mv']:
        if len(nwtypestring) > 0:
            nwtypestring += ' camera'
        else:
            nwtypestring = 'camera'
    if devicetypes['mg']:
        if len(nwtypestring) > 0:
            nwtypestring += ' cellularGateway'
        else:
            nwtypestring = 'cellularGateway'
    
        
    #Debug
    print ("Network type string is: "+nwtypestring)
                
    #compile parameters to create network
    arg_nwtags = arg_nwtags.split(" ")
    nwtags = []
    print(type(arg_nwtags))
    print(type(nwtags))
    if arg_nwtags != 'null':
        nwtags = arg_nwtags
    ### NOTE THAT TIMEZONE IS HARDCODED IN THIS SCRIPT. EDIT THE LINE BELOW TO MODIFY ###
    nwparams = {'name': arg_nwname, 'timeZone': 'Europe/Helsinki', 'tags': nwtags, 'organizationId': orgid, 'type': nwtypestring}
        
    #create network and get its ID
    if nwid == 'null':
        createstatus = createnw(arg_apikey, shardurl, orgid, nwparams)
        if createstatus == 'null':
            printusertext('ERROR 16: Unable to create network')
            sys.exit(2)
        nwid = getnwid(arg_apikey, shardurl, orgid, arg_nwname)
        if nwid == 'null':
            printusertext('ERROR 17: Unable to get ID for new network')
            sys.exit(2)    
    
    #clean up serials list to filter out licenses
    validserials = []
    for i in range (0, len(devicelist['serial']) ):
        if devicelist['model'][i][:2] == 'MR' or devicelist['model'][i][:2] == 'CW' or devicelist['model'][i][:2] == 'MS' or devicelist['model'][i][:2] == 'MX' or devicelist['model'][i][:2] == 'MV' or devicelist['model'][i][:2] == 'MG':
            validserials.append(devicelist['serial'][i])
            
            
    # split sitecode and brand code
    splitcode = arg_nwname.split("_",1)
    print(splitcode)
    # Search for index of 3 letter maison code
    index = Code3L.index(splitcode[1])
    # Get 2 letter maison code
    maison = Code2L[index]
    
    print("GuestWifi? "+arg_guestwifi)
    print(arg_nwtags)
    
    if (arg_guestwifi == "Guest"):
        tagguest = "Guest_"+splitcode[1]
        mrtags = arg_nwtags
        print(mrtags)
        mrtags.append(tagguest)
        print ("Tag Guest is: "+tagguest)
        print ("AP tags are: ")
        print(mrtags)
    else:
        mrtags = arg_nwtags
    
    
    if (arg_template.find('Office') != -1):
        sitetype = 'O'
    else:
        sitetype = 'B'
    
    #Claim devices into newly created network
    claimdevice(arg_apikey, shardurl, nwid, validserials)
    
    #critical stuff:
    for devserial in validserials:
        #Limit ammount of API calls per second
        time.sleep(0.2)
        #claim device into newly created network
        #claimdevice(arg_apikey, shardurl, nwid, devserial)
    
        #check if device has been claimed successfully
        deviceinfo = getdeviceinfo(arg_apikey, shardurl, nwid, devserial)
        #Debug's
        """
        print('debugging...')
        print(deviceinfo['model'])
        print(deviceinfo['serial'])
        """
        #Set hostname NAI
        if deviceinfo['serial'] == 'null':
            printusertext('ERROR 18: Claiming or moving device unsuccessful')
            sys.exit(2)
        elif deviceinfo['model'][:2] == 'MX':
            mx_count = mx_count + 1
            hostname = 'N' + splitcode[0] + maison + sitetype + 'SG0' + str(mx_count)
            setdevicedata(arg_apikey, shardurl, nwid, devserial, 'name', hostname, arg_nwtags, False)
            if arg_address != 'null':
                printusertext('Setting device location...')
                setdevicedata(arg_apikey, shardurl, nwid, devserial, 'address', arg_address, arg_nwtags, True)
                
        elif deviceinfo['model'][:2] == 'MS':
            ms_count = ms_count + 1
            if mr_count < 10:
                hostname = 'N' + splitcode[0] + maison + sitetype + 'SW0' + str(ms_count)
            else:
                hostname = 'N' + splitcode[0] + maison  + sitetype + 'SW' + str(mr_count)
                
            setdevicedata(arg_apikey, shardurl, nwid, devserial, 'name', hostname, arg_nwtags, False)
            if arg_address != 'null':
                printusertext('Setting device location...')
                setdevicedata(arg_apikey, shardurl, nwid, devserial, 'address', arg_address, arg_nwtags, True)
                
        elif deviceinfo['model'][:2] == 'MR' or deviceinfo['model'][:2] == 'CW':
            mr_count = mr_count + 1
            if mr_count < 10:
                hostname = 'N' + splitcode[0] + maison  + sitetype + 'WA0' + str(mr_count)
            else:
                hostname = 'N' + splitcode[0] + maison  + sitetype + 'WA' + str(mr_count)
            print ("Setting AP tags are:")
            print (mrtags)
            setdevicedata(arg_apikey, shardurl, nwid, devserial, 'name', hostname, mrtags, False)
            if arg_address != 'null':
                printusertext('Setting device location...')
                setdevicedata(arg_apikey, shardurl, nwid, devserial, 'address', arg_address, mrtags, True)
        
        elif deviceinfo['model'][:2] == 'MV':
            mv_count = mv_count + 1
            hostname = 'N' + splitcode[0] + maison + sitetype + 'MV0' + str(mv_count)
            setdevicedata(arg_apikey, shardurl, nwid, devserial, 'name', hostname, arg_nwtags, False)
            if arg_address != 'null':
                printusertext('Setting device location...')
                setdevicedata(arg_apikey, shardurl, nwid, devserial, 'address', arg_address, arg_nwtags, True)
                
        elif deviceinfo['model'][:2] == 'MG':
            mg_count = mg_count + 1
            hostname = 'N' + splitcode[0] + maison + sitetype + 'MG0' + str(mg_count)
            setdevicedata(arg_apikey, shardurl, nwid, devserial, 'name', hostname, arg_nwtags, False)
            if arg_address != 'null':
                printusertext('Setting device location...')
                setdevicedata(arg_apikey, shardurl, nwid, devserial, 'address', arg_address, arg_nwtags, True)
            
        printusertext('Setting Hostname ' + hostname + ' for device ' + deviceinfo['model'])
        
    #bind network to template. If switches in template, attempt to autobind them
    bindstatus = bindnw(arg_apikey, shardurl, nwid, templateid, devicetypes['ms'])
    if bindstatus == 'null' and stoponerror:
        printusertext('Error 19: Unable to bind network to template')
        print (bindstatus)


    #Updates the device VLAN subnets
    if (arg_template.find('ZTNA Office') != -1):
        #Simple ZTNA Office VLAN's
        updatevlanstatus = updatevlanztoff(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
    
    elif (arg_template.find('EMEA - VCA France Office Template') != -1):
        #Update VCA FR Office
        updatevlanstatus = updatevlanvcaoffice(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
            
    elif (arg_template.find('EMEA - VCA France Manufacture Template') != -1):
        #Update VCA FR manufacture 
        updatevlanstatus = updatevlanvcamanuf(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
    
    elif (arg_template.find('ZTNA Manufacture') != -1):
        #ZTNA Manufacture VLAN's
        updatevlanstatus = updatevlanztmanuf(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
            
    elif (arg_template.find('Manufacture RIC') != -1):
        #RIC Manufacture VLAN's
        updatevlanstatus = updatevlanmanuf(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
    
    elif (arg_template.find('Office') != -1):
        #Simple Office VLAN's
        updatevlanstatus = updatevlanoff(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
    
    elif (arg_template.find('Large') != -1):
        #Simple Office VLAN's
        updatevlanstatus = updatevlanlargebtq(arg_apikey, shardurl, nwid, arg_subnet)
        if updatevlanstatus == 'null' and stoponerror:
            printusertext('ERROR 20: Unable to update subnets')
            sys.exit(2)
        
    else:
        #BTQ VLAN's
        if devicetypes['mx']:
            updatevlanstatus = updatevlanbtq(arg_apikey, shardurl, nwid, arg_subnet)
            if updatevlanstatus == 'null' and stoponerror:
                printusertext('ERROR 20: Unable to update subnets')
                sys.exit(2)
        else:
            print('Guest WiFi only!!!')

    #best effort stuff, applies to all claimed devices
    for devserial in validserials:
        """
 #       #set device hostname
  #      print(deviceinfo['model'])
   #     hostname = deviceinfo['model'] + '_' + devserial
    #    setdevicedata(arg_apikey, shardurl, nwid, devserial, 'name', hostname, arg_nwtags, False)
    
        #if street address is given as a parameter, set device location
#        if arg_address != 'null':
 #           printusertext('Setting device location...')
  #          setdevicedata(arg_apikey, shardurl, nwid, devserial, 'address', arg_address, arg_nwtags, True)
    #attempt to override template timezone by fetching the right one from Google API
    """
    flag_unabletosettime = True
    if arg_googlekey != '' and arg_address != 'null':
        gtimezone = getgoogletimezone(arg_googlekey, arg_address)
        if gtimezone != 'null':
            udstatus = updatenw(arg_apikey, shardurl, nwid, 'timeZone', gtimezone)
            if udstatus == 'ok':
                flag_unabletosettime = False
        if flag_unabletosettime:
            printusertext('WARNING: Unable to set time zone using Google Maps API')
    
    
    printusertext('All done, have a nice day!!!')
            
if __name__ == '__main__':
    main(sys.argv[1:])
    
    
