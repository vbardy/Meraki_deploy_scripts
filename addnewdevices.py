#Import new devices to existing network
import json
import sys, getopt, requests, json, time, re
import meraki


# Changelog
# Adjusted API's to work with v1
# Added capability to recognize WW or CN dashboards
# v1.1.1 - Bug Fixes for v1

def printteam():
    print('___________________________________________________________________________')
    print('.____________   _________ ')
    print('|   \_   ___ \ /   _____/ ')
    print('|   /    \  \/ \_____  \  ')
    print('|   \     \____/        \ ')
    print('|___|\______  /_______  / ')
    print('            \/        \/  ')
    print()
    print('_________                                    __  .__      .__  __          ')
    print('\_   ___ \  ____   ____   ____   ____  _____/  |_|__|__  _|__|/  |_ ___.__.')
    print('/    \  \/ /  _ \ /    \ /    \_/ __ \/ ___\   __\  \  \/ /  \   __<   |  |')
    print('\     \___(  <_> )   |  \   |  \  ___|  \___|  | |  |\   /|  ||  |  \___  |')
    print(' \______  /\____/|___|  /___|  /\___  >___  >__| |__| \_/ |__||__|  / ____|')
    print('v1.1.1  \/            \/     \/     \/    \/                        \/     ')
    print('___________________________________________________________________________')

def printhelp():
    #prints help text

    printusertext('This is a script to claim MR and MS and attach the devices to an already existing network')
    printusertext('')
    printusertext('To run the script, enter:')
    printusertext('python addnewdevices.py -k <Meraki Dashboard API key> -o <Organization Name> -s <List of serial numbers to be claimed> -n <Name of new network>')
    printusertext('')
    printusertext('Mandatory parameters:')
    printusertext(' -k <key>: Your Meraki Dashboard API key')
    printusertext(' -o <org>: Name of the Meraki Dashboard Organization to modify')
    printusertext(' -s <sn>: Serial number of the devices to claim. Use double quotes and spaces to enter')
    printusertext('       multiple serial numbers. Example: -s "AAAA-BBBB-CCCC DDDD-EEEE-FFFF"')
    printusertext('       You can also enter a license key as a serial number to claim along with devices')
    printusertext(' -n <netw>: Name the new network will have')
    printusertext('')
    printusertext('Example:')
    printusertext(' python addnewdevices.py -k 1234 -o RISA -s "XXXX-YYYY-ZZZZ AAAA-BBBB-CCCC"-n "CHMEY89_LAB"')
    printusertext('')
    printusertext('Use double quotes ("") in Windows to pass arguments containing spaces. Names are case-sensitive.')
    
def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message)


def getorgid(p_apikey, p_orgname):
    #looks up org id for a specific org name
    #on failure returns 'null'
    
    try:
        r = requests.get('https://dashboard.meraki.com/api/v1/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
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
    
def getnwid2(p_apikey,p_orgid,p_nwname):
    dashboard=meraki.DashboardAPI(p_apikey)
    networks=dashboard.organizations.getOrganizationNetworks(organizationId=p_orgid)
    for record in networks:
        if record['name'] == p_nwname:
            return record['id']
    return('null')

def getnwid(p_apikey, p_shardurl, p_orgid, p_nwname):
    #looks up network id for a network name
    #on failure returns 'null'

    try:
        r = requests.get('https://%s/api/v1/organizations/%s/networks' % (p_shardurl, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 02: Unable to contact Meraki cloud')
        sys.exit(2)
    
    #debug
    #print(r.json)
    
    if r.status_code != requests.codes.ok:
        return 'null'
    
    rjson = r.json()
    
    for record in rjson:
        if record['name'] == p_nwname:
            return record['id']
    return('null')


def getdevicelist(p_apikey, p_shardurl, p_nwid):

    #returns a list of all devices in a network
    
    r = requests.get('https://%s/api/v1/networks/%s/devices' % (p_shardurl, p_nwid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        
    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'serial': 'null', 'model': 'null'})
        return(returnvalue)
    
    return(r.json())


def claimdeviceorg(p_apikey, p_shardurl, p_orgid, p_devserial):
    #claims a device into an org without adding to a network
    
    try:
        r = requests.post('https://%s/api/v1/organizations/%s/claim' % (p_shardurl, p_orgid), data=json.dumps({'serials':[ p_devserial ]}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 06: Unable to contact Meraki cloud')
        sys.exit(2)
    
    return(0)


def getorgdeviceinfo (p_apikey, p_shardurl, p_orgid, p_devserial):
    #gets basic device info from org inventory. device does not need to be part of a network
    
    try:
        r = requests.get('https://%s/api/v1/organizations/%s/inventory/devices/%s' % (p_shardurl, p_orgid,p_devserial), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 11: Unable to contact Meraki cloud')
        sys.exit(2)
    
    returnvalue = {}
    if r.status_code != requests.codes.ok:
        returnvalue = {'serial':'null', 'model':'null'}
        return(returnvalue)
    
    rjson = r.json()
    

    """
    foundserial = False
    for record in rjson:
        if record['serial'] == p_devserial:
            foundserial = True
            returnvalue = {'mac': record['mac'], 'serial': record['serial'], 'networkId': record['networkId'], 'model': record['model'], 'claimedAt': record['claimedAt'], 'publicIp': record['publicIp']}
                
    if not foundserial:
        returnvalue = {'serial':'null', 'model':'null'}
    
    """
    
    return(rjson) 


def claimdevice(p_apikey, p_shardurl, p_nwid, p_devserial):
    #claims a device into a network
    print('Claiming device S/N '+str(p_devserial))
    try:
        r = requests.post('https://%s/api/v1/networks/%s/devices/claim' % (p_shardurl, p_nwid), data=json.dumps({'serials': [p_devserial]}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        print(r.status_code)
        print(r.reason)
        if r.status_code != requests.codes.ok:
            print('Error XX: Device already claimed?')
    except:
        printusertext('ERROR 08: Unable to contact Meraki cloud')
        sys.exit(2)
    
    return(0)


def getdeviceinfo(p_apikey, p_shardurl, p_nwid, p_serial):
    #returns info for a single device
    #on failure returns lone device record, with serial number 'null'

    try:
        #r = requests.get('https://%s/api/v1/networks/%s/devices/%s' % (p_shardurl, p_nwid, p_serial), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
        r = requests.get('https://%s/api/v1/devices/%s' % (p_shardurl, p_serial), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 09: Unable to contact Meraki cloud')
        sys.exit(2)
    
    returnvalue = []
    if r.status_code != requests.codes.ok:
        print(r.status_code)
        print(r.reason)
        returnvalue = {'serial':'null', 'model':'null'}
        return(returnvalue)
    
    rjson = r.json()
    
    return(rjson)


def setdevicedata(p_apikey, p_shardurl, p_nwid, p_devserial, p_field, p_value, p_nwtags, p_movemarker):
    #modifies value of device record. Returns the new value
    #on failure returns one device record, with all values 'null'
    #p_movemarker is boolean: True/False
    
    movevalue = "false"
    if p_movemarker:
        movevalue = "true"
    
    try:
        r = requests.put('https://%s/api/v1/networks/%s/devices/%s' % (p_shardurl, p_nwid, p_devserial), data=json.dumps({p_field: p_value, 'moveMapMarker': movevalue, 'tags': p_nwtags}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 10: Unable to contact Meraki cloud')
        sys.exit(2)
            
    if r.status_code != requests.codes.ok:
        return ('null')
    
    return('ok')
    
def main(argv):
    
    printteam()
    
    #set default values for command line arguments
    arg_apikey = 'null'
    arg_orgname = 'null'
    arg_serials = 'null'
    arg_nwname = 'null'    
    
    #get command line arguments    
    try:
        opts, args = getopt.getopt(argv, 'hk:o:s:n:')
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
            arg_serials = arg
        elif opt == '-n':
            arg_nwname = arg

    if arg_apikey == 'null' or arg_orgname == 'null' or arg_serials == 'null' or arg_nwname == 'null':
        print(arg_apikey+","+arg_orgname+","+arg_serials+","+arg_nwname)
        printhelp()
        sys.exit()

    if arg_orgname == 'RISA':
        p_shardurl = 'api.meraki.com'
    elif arg_orgname == 'RISA CN':
        p_shardurl = 'api.meraki.cn'
    else:
        print('Error - Organization name not recognized')
        sys.exit(2)
    
    p_orgid = getorgid(arg_apikey, arg_orgname)
    
    p_nwid = getnwid(arg_apikey, p_shardurl, p_orgid, arg_nwname)
    p_nwid2=getnwid2(arg_apikey, p_orgid, arg_nwname)
    print(p_nwid2, arg_nwname)
    #Check if network exists
    if p_nwid == 'null':
        print('Network '+arg_nwname+' does not exist, please confirm the name on the Dashboard')
        sys.exit()

    print ('Reading device data of '+arg_nwname)

    devicelist = getdevicelist(arg_apikey, p_shardurl, p_nwid)
    ms_count = 0
    mr_count = 0
    for device in devicelist:

        #Count number of switches and AP's, get address and tags
        if device['serial'] == 'null':
            printusertext('ERROR: No Serial')
            sys.exit(2)
        elif device['model'][:2] == 'MS':
            ms_count = ms_count + 1
            p_mstags = device['tags']
            p_address = device['address']
            p_hostname = device['name'][:11]
        elif device['model'][:2] == 'MR':
            mr_count = mr_count + 1
            p_mrtags = device['tags']
            p_address = device['address']
            p_hostname = device['name'][:11]
        elif mr_count == 0 and device['model'][:2] == 'MR':
            #if Switch or AP's don't exist already use info from MX
            print('No Switches or APs on this network until now, retrieving address and tags from MX appliance')
            p_address = device['address']
            p_mrtags = device['tags']
            p_mstags = device['tags']
            p_hostname = device['name'][:11]
        elif ms_count == 0 and device['model'][:2] == 'MS':
            #if Switch or AP's don't exist already use info from MX
            print('No Switches or APs on this network until now, retrieving address and tags from MX appliance')
            p_address = device['address']
            p_mrtags = device['tags']
            p_mstags = device['tags']
            p_hostname = device['name'][:11]
            
    print()
    print('Network has #Switches: '+str(ms_count)+' -- Network has #APs: '+str(mr_count))
    print()
    if mr_count > 0:
        print ('AP tags -> '+str(p_mrtags))
    if ms_count > 0:
        print ('Switch tags -> '+str(p_mstags))
    print()
    print ('Network address is: '+p_address)
    print()
    printusertext('Adding new devices to network '+arg_nwname)

    #get serial numbers from parameter -s
    devicelist = {}
    devicelist['serial'] = arg_serials.split(" ")
    devicelist['model'] = []
    
    for i in range (0, len(devicelist['serial']) ):
        #print('Debug#1 - '+devicelist['serial'][i])
        deviceinfo = getorgdeviceinfo(arg_apikey, p_shardurl, p_orgid, devicelist['serial'][i])
        print (deviceinfo)
        try:
            if deviceinfo['networkId'] == None and deviceinfo['serial'] != 'null':
                print ('Device is available from Inventory')
            else:
                printusertext('Device '+deviceinfo['model']+' with S/N: '+deviceinfo['serial'] +' is already attached to a network, please check on the Dashboard')
                sys.exit(2)
        except:
            print('ERROR - Is device available from inventory?')
    
    for i in range (0, len(devicelist['serial']) ):
        claimdeviceorg(arg_apikey, p_shardurl, p_orgid, devicelist['serial'][i])
        
        #check if device has been claimed successfully
        deviceinfo = getorgdeviceinfo (arg_apikey, p_shardurl, p_orgid, devicelist['serial'][i])
        if deviceinfo['serial'] == 'null':
            printusertext('INFO: Serial number %s is a license or unsupported device' % devicelist['serial'][i])
        devicelist['model'].append(deviceinfo['model'])
        
    #compile list of different product types in order to create correct type of network
    devicetypes = {'mx': False, 'ms': False, 'mr': False}
    for record in devicelist['model']:
        print('Device Type '+ record)
        if record [:2] == 'MX' or record [:1] == 'Z':
            devicetypes['mx'] = True
        elif record [:2] == 'MS':
            devicetypes['ms'] = True
        elif record [:2] == 'MR':
            devicetypes['mr'] = True
            
    #build network type string for network creation
    nwtypestring = ''
    if devicetypes['mr']:
        nwtypestring += 'wireless'
    if len(nwtypestring) > 0:
        nwtypestring += ' '
    if devicetypes['ms']:
        nwtypestring += 'switch'
    if len(nwtypestring) > 0:
        nwtypestring += ' '
    if devicetypes['mx']:
        nwtypestring += 'appliance'
                
    #Filter from table validserials
    
    validserials = []
    for i in range (0, len(devicelist['serial']) ):
        if devicelist['model'][i][:2] == 'MR' or devicelist['model'][i][:2] == 'MS':
            validserials.append(devicelist['serial'][i])
            
        #critical stuff:
    for devserial in validserials:
        #claim device into newly created network
        claimdevice(arg_apikey, p_shardurl, p_nwid, devserial)
    
        #check if device has been claimed successfully
        deviceinfo = getdeviceinfo(arg_apikey, p_shardurl, p_nwid, devserial)
        #print(deviceinfo['model'])

        #Set hostname NAI
        if deviceinfo['serial'] == 'null':
            printusertext('ERROR 18: Claiming or moving device unsuccessful')
            sys.exit(2)
        elif deviceinfo['model'][:2] == 'MS':
            ms_count = ms_count + 1
            hostname = p_hostname + 'SW0' + str(ms_count)
            setdevicedata(arg_apikey, p_shardurl, p_nwid, devserial, 'name', hostname, p_mstags, False)
            setdevicedata(arg_apikey, p_shardurl, p_nwid, devserial, 'address', p_address, p_mstags, True) 
        elif deviceinfo['model'][:2] == 'MR':
            mr_count = mr_count + 1
            if mr_count < 10:
                hostname = p_hostname + 'WA0' + str(mr_count)
            else:
                hostname = p_hostname + 'WA' + str(mr_count)
            setdevicedata(arg_apikey, p_shardurl, p_nwid, devserial, 'name', hostname, p_mrtags, False)
            setdevicedata(arg_apikey, p_shardurl, p_nwid, devserial, 'address', p_address, p_mrtags, True)   
        
        printusertext('Setting Hostname, Address and tags ' + hostname + ' for device ' + deviceinfo['model'])
 
    printusertext('')
    printusertext('All done, have a nice day!')
    printusertext('')
    
if __name__ == '__main__':
    main(sys.argv[1:])