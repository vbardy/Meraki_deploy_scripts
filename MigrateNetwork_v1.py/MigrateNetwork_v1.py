#Script to Migrate a Network between templates
import sys, getopt, requests, json, time, re, csv,meraki 
import json

def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message)

def printhelp():
    #prints help text

    print('This is a script to migrate an existing Network bound to a template to a new template')
    print('')
    print('To run the script, enter:')
    print('python MigrateNetwork_v1.exe -k <Meraki Dashboard API key> -o <Organization Name> -n <Name of network to migrate> -t <name of destination configuration template>')
    new_func()
    print('')
    print('Use double quotes ("") in Windows to pass arguments containing spaces. Names are case-sensitive.')

def new_func():
    # Print a command to run a program with proper quotation marks
    print("python MigrateNetwork_v1.exe -k 6a33a1785286a84f8fd37a378af75aaa10802cc9 -o 'RISA' -n 'GBTEST_MTB' -t 'EMEA - Template BTQ LTE #2'")

# Print a command to run a program with proper quotation marks
print("python MigrateNetwork_v1.exe -k 6a33a1785286a84f8fd37a378af75aaa10802cc9 -o 'RISA' -n 'GBTEST_MTB' -t 'EMEA - Template BTQ LTE #2'")

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



def gettemplatelist(p_apikey, p_shardurl, p_orgid):
    #returns a list of all networks in an organization
    #on failure returns a single record with 'null' name and id
    try:
        r = requests.get('https://%s/api/v1/organizations/%s/configTemplates' % (p_shardurl, p_orgid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 01: Unable to retrieve templates list')
        sys.exit(2)
        
    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'name': 'null', 'id': 'null'})
        return(returnvalue)
    
    return(r.json())


def gettemplatenetworks(p_apikey, p_shardurl, p_orgid,p_templateid):
    #Description......
    try:
        r = requests.get('https://%s/api/v1/organizations/%s/networks?configTemplateId=%s' % (p_shardurl, p_orgid,p_templateid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 02: Unable to retrieve template networks')
        sys.exit(2)
        
        
    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'name': 'null', 'id': 'null'})
        return(returnvalue)
    
    return(r.json())


def getnwvlanips(p_apikey, p_shardurl, p_nwid):
    #returns MX VLANs for a network
    try:
        r = requests.get('https://%s/api/v1/networks/%s/appliance/vlans' % (p_shardurl, p_nwid), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})
    except:
        printusertext('ERROR 03: Unable to retrieve network vlans ')
        sys.exit(2)
    
    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'id': 'null'})
        return(returnvalue)
    #Rate limit mechanism
    elif r.status_code == 429:
        print ("Got response 429, chilling a bit...")
        time.sleep(int(response.headers["Retry-After"])) # pyright: ignore[reportUndefinedVariable]
    else:
        return(r.json())



#MAIN starts here !!!

def main(argv):
    
    btq_vlans = [10,20,30,50,100,400]
    sameSubnetVLANS = [2,3,5,6,9,800]
    vlan_records = []
    config_template_id = ""

    
    
    
    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:n:t:')
    except getopt.GetoptError:
        printhelp()
        sys.exit(2)

    for opt, arg in opts:
        if   opt == '-h':
            printhelp()
            sys.exit()
        elif opt == '-k':
            arg_apikey  = str(arg)
        elif opt == '-o':
            arg_org     = arg
        elif opt == '-n':
            arg_network = arg
        elif opt == '-t':
            arg_template = arg

    #check if all parameters that are required parameters have been given
    if arg_apikey == 'null' or arg_org == 'null' or arg_network == 'null' or arg_template == 'null':
        #print (arg_subnet)
        printhelp()
        sys.exit(2)


    p_apikey = arg_apikey
    dashboard = meraki.DashboardAPI(arg_apikey,output_log=False,print_console=True)
    #dashboard = meraki.DashboardAPI(arg_apikey,output_log=False,print_console=False)
    p_shardurl = 'api.meraki.com'
    p_orgname = arg_org
    p_filepath = 'testing.csv'
    recordstring = []
    targetTemplate = arg_template
    targetNetwork = arg_network

    print("Network to migrate is: "+arg_network)
    print("\nDestination template is: "+arg_template)
    input("Press Enter to continue...")


    
    #Get URL and OrgID
    print("Getting Organization ID")
    organization_id = getorgid(p_apikey, p_orgname)
    
    #Get templates list
    print("Getting list of organization templates")
    templatesList = dashboard.organizations.getOrganizationConfigTemplates(organization_id)
    
    print("Searching for template in templates list")
    for template in templatesList:
        if targetTemplate in template['name']:
            print(template['id'],' ',template['name'])
            config_template_id = template['id']
            #Network found, exit for loop
            break
    
    #If not finding template iD stop script
    if not config_template_id:
        print("\nConfiguration template not found, exiting...")
        sys.exit()
    
    #Get NetworkID
    print("Getting Organization networks")
    network_list = dashboard.organizations.getOrganizationNetworks(organization_id, total_pages='all')
    print("Searching for network...")
    for network in network_list:
        if targetNetwork in network['name']:
            print(network['id'],' ',network['name'])
            network_name = network['name']
            network_id = network['id']
            #Network found, exit for loop
            break

    #Get Network VLAN information
    print("Getting network VLAN information from ",network_name)
    network_vlans = dashboard.appliance.getNetworkApplianceVlans(network_id)
    #print(network_vlans)
    

    for vlan in network_vlans:
        
        
        #print(vlan)
        """
        for i in vlan:
            print (i)
        """
        print("VLAN id: ",vlan['id'])
        print("VLAN name: ",vlan['name'])
        print("VLAN subnet: ",vlan['subnet'])
        print("VLAN appliance IP: ",vlan['applianceIp'])
        print("DHCP handling: ",vlan['dhcpHandling'])
        print("Mandatory DHCP? ",vlan['mandatoryDhcp'])
        if vlan['dhcpHandling'] == "Relay DHCP to another server":
            vlan_records.append({'id': vlan['id'], 'name': vlan['name'], 'applianceIp': vlan['applianceIp'], 'subnet': vlan['subnet'], 'fixedIpAssignments': vlan['fixedIpAssignments'], 'reservedIpRanges': vlan['reservedIpRanges'], 'dnsNameservers': vlan['dnsNameservers'], 'dhcpRelayServerIps': vlan['dhcpRelayServerIps'], 'dhcpHandling': vlan['dhcpHandling'], 'mandatoryDhcp': {'enabled': vlan['mandatoryDhcp']}, 'localDHCP': False})
        elif vlan['dhcpHandling'] != "Do not respond to DHCP requests":
            print("DHCP Lease Time: ",vlan['dhcpLeaseTime'])
            print("DHCP Boot options: ",vlan['dhcpBootOptionsEnabled'])
            print("DHCP Options: ",vlan['dhcpOptions'])
            print("DHCP fixed IP assignments: ",vlan['fixedIpAssignments'])
            print("DHCP reserved IP Ranges: ",vlan['reservedIpRanges'])
            print("DHCP DNS servers: ",vlan['dnsNameservers'])
            vlan_records.append({'id': vlan['id'], 'name': vlan['name'], 'applianceIp': vlan['applianceIp'], 'subnet': vlan['subnet'], 'fixedIpAssignments': vlan['fixedIpAssignments'], 'reservedIpRanges': vlan['reservedIpRanges'], 'dnsNameservers': vlan['dnsNameservers'],'dhcpHandling': vlan['dhcpHandling'], 'dhcpLeaseTime': vlan['dhcpLeaseTime'],'dhcpBootOptionsEnabled': vlan['dhcpBootOptionsEnabled'], 'dhcpOptions': vlan['dhcpOptions'], 'mandatoryDhcp': {'enabled': vlan['mandatoryDhcp']}, 'localDHCP': True})
        else:
            vlan_records.append({'id': vlan['id'], 'name': vlan['name'], 'applianceIp': vlan['applianceIp'], 'subnet': vlan['subnet'], 'fixedIpAssignments': vlan['fixedIpAssignments'], 'reservedIpRanges': vlan['reservedIpRanges'], 'dnsNameservers': vlan['dnsNameservers'],'dhcpHandling': vlan['dhcpHandling'], 'mandatoryDhcp': {'enabled': vlan['mandatoryDhcp']}, 'localDHCP': False})
        
        #print("Interface ID: ",vlan['interfaceId'])
        #print("IPv6? ",vlan['ipv6'])
        
        #print("\nVlan Records")
        #vlan_records = [{'id': vlan['id'], 'name': vlan['name'], 'applianceIp': vlan['applianceIp'], 'subnet': vlan['subnet'], 'fixedIpAssignments': vlan['fixedIpAssignments'], 'reservedIpRanges': vlan['reservedIpRanges'], 'dnsNameservers': vlan['dnsNameservers'],'dhcpHandling': vlan['dhcpHandling'], 'dhcpLeaseTime': vlan['dhcpLeaseTime'],'dhcpBootOptionsEnabled': vlan['dhcpBootOptionsEnabled'], 'dhcpOptions': vlan['dhcpOptions'], 'mandatoryDhcp': {'enabled': vlan['mandatoryDhcp']}}]
        
        #print (vlan_records)
        print ()
        
    
    
    #unbind network from current Template
    try:
        print("\nUnbinding network from template\n")
        response = dashboard.networks.unbindNetwork(network_id, retainConfigs=True)
        print (response)
    except:
        print('Warning - Network is possibly not bound to a network')
        pass
    
    
    #Waiting to make sure unbinding is finished in Meraki Dashboard
    print('ZZzzz')
    time.sleep(2.5)
    
    
    #bind network to target template
    print("\nBinding network to target template\n")
    response = dashboard.networks.bindNetwork(network_id, config_template_id, autoBind=False)
    print (response)

    print("Restoring Network subnet configuration...")
    try:
        for vlan in vlan_records:
            print("\nUpdating subnets for VLAN ",vlan['id'])
            
            if vlan['dhcpHandling'] == 'Do not respond to DHCP requests':
            
                    response = dashboard.appliance.updateNetworkApplianceVlan(
                        network_id, vlan['id'], 
                        subnet=vlan['subnet'], 
                        applianceIp=vlan['applianceIp'],
                        cidr=vlan['subnet'],
                        dhcpHandling=vlan['dhcpHandling']
                    )
                    
                    print (response)
                
            elif vlan['dhcpHandling'] == 'Relay DHCP to another server':

                response = dashboard.appliance.updateNetworkApplianceVlan(
                    network_id, vlan['id'], 
                    subnet=vlan['subnet'], 
                    applianceIp=vlan['applianceIp'],
                    cidr=vlan['subnet'],
                    dhcpHandling=vlan['dhcpHandling'], 
                    dhcpRelayServerIps=vlan['dhcpRelayServerIps']
                )
                
                print (response)
                
                
                
            elif vlan['dhcpHandling'] == 'Run a DHCP server':
                if vlan['id'] in sameSubnetVLANS:
                    response = dashboard.appliance.updateNetworkApplianceVlan(
                        network_id, vlan['id'], 
                        dhcpHandling=vlan['dhcpHandling'],
                        dhcpLeaseTime=vlan['dhcpLeaseTime'], 
                        dhcpBootOptionsEnabled=vlan['dhcpBootOptionsEnabled'], 
                        fixedIpAssignments=vlan['fixedIpAssignments'], 
                        reservedIpRanges=vlan['reservedIpRanges'], 
                        dnsNameservers=vlan['dnsNameservers'], 
                        dhcpOptions=vlan['dhcpOptions'], 
                    )
                
                else:

                    response = dashboard.appliance.updateNetworkApplianceVlan(
                        network_id, vlan['id'], 
                        subnet=vlan['subnet'], 
                        applianceIp=vlan['applianceIp'],
                        cidr=vlan['subnet'],
                        dhcpHandling=vlan['dhcpHandling'],
                        dhcpLeaseTime=vlan['dhcpLeaseTime'], 
                        dhcpBootOptionsEnabled=vlan['dhcpBootOptionsEnabled'], 
                        fixedIpAssignments=vlan['fixedIpAssignments'], 
                        reservedIpRanges=vlan['reservedIpRanges'], 
                        dnsNameservers=vlan['dnsNameservers'], 
                        dhcpOptions=vlan['dhcpOptions'], 
                    )
                    
                    print (response)
                
            else:
                print("Error, could not identify DHCP handling option")
                sys.exit()
            
    except:
        print('ERROR XX: .........')
        pass
        #sys.exit(2)


print("All done!")

if __name__ == '__main__':
    main(sys.argv[1:])