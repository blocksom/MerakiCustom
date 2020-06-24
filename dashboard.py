#
# Author: Kyle T. Blocksom
# Title: Dashboard
# Date: June 24, 2020
#
# Objective: Meraki Dashboard SDK
#
# Notes: 
#   - 'pip install meraki==1.0.0b9' to runtime environment
#
# Usage:  dashboard.py <action> <var1>...<varN>
#

import meraki, merakiapi, random, sys, getopt, csv, config, os, asyncio, time
from datetime import datetime

###########################################################################################################################################
#
#  throw_error(exception, flag) - Print errors and their corresponding code, reason, and message to Terminal
#
###########################################################################################################################################
def throw_error(exception, flag):
	if flag == 'Meraki_Error':
		print(f'Meraki API error: {exception}')
		print(f'status code = {exception.status}')
		print(f'reason = {exception.reason}')
		print(f'error = {exception.message}')
	else:
		print(f'some other error: {exception}')

###########################################################################################################################################
#
# get_networkname_by_id(my_key, network_ID, orgs) - Return Network Name given a Network ID
#
###########################################################################################################################################
def get_networkname_by_id(dashboard, my_key, network_ID, orgs):
	
	net_name = ''

	# Get  current list of networks
	for org in orgs:
		current_networks = dashboard.organizations.getOrganizationNetworks(org['id'])

		for net in current_networks:
			if net['id'] == network_ID:
				net_name = net['name']
				break
			if net_name == '':
				return -1

	return (net_name)

###########################################################################################################################################
#
# get_networkid_by_name(my_key, network_name, orgs) - Return Network ID given and Network Name
#
###########################################################################################################################################
def get_networkid_by_name(dashboard, my_key, network_name, orgs):

	# Get current list of networks
	for org in orgs:
		current_networks = dashboard.organizations.getOrganizationNetworks(org['id'])

		network_ID = '';

		for net in current_networks:
			net_temp = net['name']

			if net['name'] == network_name:
				network_ID = net['id']
				break
		else:
			if network_ID == '':
				network_ID = -1
		break

	return(network_ID)

###########################################################################################################################################
#
# get_network_routes(dashboard, my_key, network_ID, orgs)) - Return all static routes for network in <Network ID>
#
###########################################################################################################################################
def get_network_routes(dashboard, my_key, network_ID, orgs):

	try:
		network = get_networkname_by_id(dashboard, my_key, network_ID, orgs)
		response = dashboard.appliance.getNetworkApplianceStaticRoutes(network_ID)
		for route in response:
			print ("{} - {}".format(network, route['subnet']))

	except meraki.APIError as e:
		throw_error(e, 'Meraki_Error')

###########################################################################################################################################
#
#  get_global_routes(dashboard, my_key, my_org, orgs)) - Return all static routes advertised by MX(s) in Org <my_org>
#
###########################################################################################################################################
def get_global_routes(dashboard, my_key, my_org, orgs):

	for org in orgs:
		if org['name'] == my_org:
			networks = dashboard.organizations.getOrganizationNetworks(org['id'])
		
			for net in networks:
				get_network_routes(dashboard, my_key, net['id'], orgs)

###########################################################################################################################################
#
# network_exists(csv_writer, clients, data, network_dict, network_name, network_ID, tracker) - Write data returned by earlier method to .csv row-by-row
#
###########################################################################################################################################
def network_exists(dashboard, my_org):
	# Get list of networks in Organization
	try:
		networks = dashboard.organizations.getOrganizationNetworks(my_org)
	# Graceful failover
	except meraki.APIError as e:
		throw_error('Meraki_Error')
		print(f'\nError Networks = {networks}') 

	except Exception as e:
		throw_error('Other_Error')
		print(f'\nError Networks = {networks}')
		

	return networks

###########################################################################################################################################
#
# write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker) - Write data returned by earlier method to .csv row-by-row
#
###########################################################################################################################################
def write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker, flag):

	data[0].update(clients[0])

	index = 0
	while index < len(data) and tracker < len(clients):
		alert = 1
		# Write traffic history to file
		data[index].update(network_dict)
		data[index].update(clients[tracker])

		if flag == 'Signal':
			for key, value in data[index].items():
				alert = 1
				if (key == 'snr' or key == 'rssi') and (not value):
					alert = 0
					break

		if alert:
			csv_writer.writerow(data[index])
		
		index += 1

###########################################################################################################################################
#
# iterate_clients(dashboard, network_name, network_ID, field_names, flag) - Create output .csv file,
#  query list of Clients in network <network_ID>, iterate through Clients, and query "flag" data
#
###########################################################################################################################################
def iterate_clients(dashboard, network_name, network_ID, field_names, flag):

	if network_ID == -1:
		print(f'Network Name: \'{network_name}\' does not exist within your Orgs.')
		quit()

	# Define file to which we will write Client Traffic data
	# Named after Network Name in Meraki Dashboard
	if os.path.exists(f'{network_name}_{flag}.csv'):
		os.remove(f'{network_name}_{flag}.csv')

	file_name = f'{network_name}_{flag}.csv'

	try:
		# Get list of Clients on Network, filtering on timespan of last 14 days
		# def getNetworkClients(self, networkId: str, total_pages=1, direction='next', **kwargs):
		clients = dashboard.networks.getNetworkClients(networkId=network_ID, perPage=1000, total_pages='all')

	# Graceful failover
	except meraki.APIError as e:
		throw_error(e, 'Meraki_Error')

	except Exception as e:
		throw_error(e, 'Other_Error')

	else:
		tracker = 1
		if clients:
			total_client = len(clients)
			# Iterate through Clients on Network
			for client in clients:
				print("Analyzing Clients in Network {} ({} of {})".format(network_name, tracker, total_client))
				#print(f'\nAnalyzing Client {tracker}\'s traffic out of {len(clients)} total Clients:\n')

				# Open file for appendment and set .csv field names to dictonary keys
				output_file = open(f'{file_name}', mode='a', newline='\n')

				csv_writer = csv.DictWriter(output_file, field_names, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

				if tracker == 1:
					csv_writer.writeheader()

				try:
					if flag == 'Talker':
		                # Get traffic history for each Client across each Network
						data = dashboard.networks.getNetworkClientTrafficHistory(networkId=network_ID, clientId=client['id'])
						network_dict = {'Network Name':network_name, 'Network ID':network_ID, 'DNS Request Quantity':len(data)}
					
					elif flag == 'Signal':
						network_dict = {'Network Name':network_name, 'Network ID':network_ID}
						data = dashboard.wireless.getNetworkWirelessSignalQualityHistory(networkId=network_ID, clientId=client['id'])

				# Graceful failover
				except meraki.APIError as e:
					throw_error(e, 'Meraki_Error')

				except Exception as e:
					throw_error(e, 'Other_Error')

				else:
					if data:
						write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker, flag)

				tracker += 1
			
			output_file.close()

###########################################################################################################################################
#
#  get_top_talker(dashboard, my_key, network_name, timespan) - Return .csv list of all clients, sorted by total number of DNS requests
#  
###########################################################################################################################################
def get_top_talker(dashboard, my_key, network_name, orgs, timeSpan=3600):

	# timeSpan = number of seconds
	counter = 0
	total = 0
	network_ID = get_networkid_by_name(dashboard, my_key, network_name, orgs)

	field_names = ['Network Name', 'Network ID', 'DNS Request Quantity', 'id', 'mac', 'description', 'ip',  'ip6', 'ip6Local', 'user', \
	'firstSeen', 'lastSeen', 'manufacturer', 'os', 'recentDeviceSerial', 'recentDeviceName', 'recentDeviceMac', \
	'ssid', 'vlan', 'switchport', 'usage', 'status', 'notes', 'smInstalled', 'groupPolicy8021x', 'application', 'destination', \
	'protocol', 'port', 'ts', 'recv', 'sent', 'numFlows', 'activeSeconds']

	# Get list of Organizations to which API key has access
	organizations = dashboard.organizations.getOrganizations()

	# Iterate through list of organizations
	for org in organizations:
		if org['name'] == network_name:
			print(f'\nAnalyzing Organization {org["name"]}:\n')
			org_id = org['id']

			# Get list of networks in Organization
			networks = network_exists(dashboard, org_id)

			if not networks:
				total = len(networks)
				counter = 1

				# Iterate through list of Networks
				for net in networks:
					print(f'\nFinding Clients in Network {net["name"]} ({counter} of {total})\n')
					iterate_clients(dashboard, network_name, network_ID, field_names, 'Talker')
					counter += 1
		else:
			iterate_clients(dashboard, network_name, network_ID, field_names, 'Talker')
			break

###########################################################################################################################################
#
#  get_wireless_signal(dashboard, my_key, network_name, orgs, timespan) - Return SNR and RSSI data for all Clients on network <network_name>
#  
###########################################################################################################################################
def get_wireless_signal(dashboard, my_key, network_name, orgs, timeSpan=3600):

	network_ID = get_networkid_by_name(dashboard, my_key, network_name, orgs)

	if network_ID == '':
		print('Network for {network_name} not found!')
		quit()

	network_ID = get_networkid_by_name(dashboard, my_key, network_name, orgs)

	field_names = ['Network Name', 'Network ID', 'id', 'mac', 'description', 'ip',  'ip6', 'ip6Local', 'user', 'startTs', 'endTs', \
	'snr', 'rssi', 'firstSeen', 'lastSeen', 'manufacturer', 'os', 'recentDeviceSerial', 'recentDeviceName', 'recentDeviceMac', \
	'ssid', 'vlan', 'switchport', 'usage', 'status', 'notes', 'smInstalled', 'groupPolicy8021x', 'application', 'destination', \
	'protocol', 'port', 'ts', 'recv', 'sent', 'numFlows', 'activeSeconds']


	iterate_clients(dashboard, network_name, network_ID, field_names, 'Signal')


###########################################################################################################################################
#
#  bulk_deploy(dashboard, my_key, network_name, orgs, timespan) - Return SNR and RSSI data for all Clients on network <network_name>
#  
###########################################################################################################################################
def bulk_deploy(dashboard, my_key, my_org, orgs):

	# Confirming if Org already exists
	for org in orgs:
		if my_org == org['name']:
			print(f'\nDeleting = {my_org}\n')

			old_networks = network_exists(dashboard, org['id'])

			for net in old_networks:
				dashboard.networks.deleteNetwork(net['id'])

			templates = dashboard.organizations.getOrganizationConfigTemplates(org['id'])

			for template in templates:
				template_id = template['id']
				print(f'\nTemplate = {template_id}')
				dashboard.organizations.deleteOrganizationConfigTemplate(org['id'], template['id'])

			dashboard.organizations.deleteOrganization(org['id'])
			exit()

	# Org does not exist so create Org
	print(f'\nCreating = {my_org}\n')

	new_org = dashboard.organizations.createOrganization(my_org)

	# Read from .csv to Create Networks and Claim Devices
	with open('Network_Device_List.csv', mode='r') as csv_file:
		csv_reader = csv.DictReader(csv_file)

		network_dict = {}
		for row in csv_reader:
			for column, value in row.items():
				column = column.replace('\ufeff', '')
				network_dict.setdefault(column, []).append(value)

	key_count = 0
	devices = []

	for key in network_dict:
		for value in network_dict[key]:
			flag = 0

			# Check if Network exists, if not then Create Network
			if key == 'Network Name':
				new_networks = network_exists(dashboard, new_org['id'])

				if not new_networks:
					print(f'\nHere - 1: Key = {key}, value = {value}')
					dashboard.organizations.createOrganizationNetwork(new_org['id'], value, ['wireless','switch','appliance'])

					network_ID = get_networkid_by_name(dashboard, my_key, value, orgs)
					template = dashboard.organizations.createOrganizationConfigTemplate(new_org['id'], 'Test-Template')

					template_ID = template['id']
					print(f'\nnetwork_ID = {network_ID}, template_ID = {template_ID}')

					dashboard.networks.bindNetwork(network_ID, template['id'])
				else:
					for net in new_networks:
						if value == net['name']:
							flag = 1

					if flag == 0:
						print(f'\nHere - 2: Key = {key}, value = {value}')			
						dashboard.organizations.createOrganizationNetwork(new_org['id'], value, ['wireless','switch','appliance'])

						time.sleep(3)

						network_ID = get_networkid_by_name(dashboard, my_key, value, orgs)
						template = dashboard.organizations.createOrganizationConfigTemplate(new_org['id'], 'Test-Template')
						dashboard.networks.bindNetwork(network_ID, template['id'])

			else:
				# Claim Devices by Serial Number
				devices.append(value)
				dashboard.networks.claimNetworkDevices(net['id'], devices)
				devices.pop(0)
	
	# createOrganizationActionBatch(new_org['id'], create)


###########################################################################################################################################
#
# print_usage() - Print out possible commands for CLI usage
#
###########################################################################################################################################
def print_usage():
	print ();
	print ("Some usage examples:")
	print ("\tpython3 dashboard.py --getsignal <Network Name> or -S <Network Name>          [Show SNR/RSSI data for clients on <network>]")
	print ("\tpython3 dashboard.py --toptalker <Network Name> or -T <Network Name>          [Show top talker clients on <network> ]")
	print ("\tpython3 dashboard.py --getroutes <Org Name> or -R <Org Name>                  [Show global route table for <org>]")
	print ("\tpython3 dashboard.py --bulkDeploy <Org Name> or -B <Org Name>                 [Network creation and bulk device claim for <org>]")

###########################################################################################################################################
#
# main() - Driver for Meraki Dashboard SDK
#
###########################################################################################################################################
def main():

	dashboard = meraki.DashboardAPI(
		api_key=config.apikey,
		base_url='https://api.meraki.com/api/v1',
		output_log=False,
		print_console=False
	)

	# Setting up initital variables
	debug = False
	not_debug = not debug
	no_update = True
	my_serial = ''
	my_name =  ''
	mode = "CLI"
	my_file = None
	delnet = None
	my_network = None
	get_ssids = False
	get_details = False
	cloneNet = ''
	newNet = ''
	addtonet = False
	sourceSSID = ''

	orgs = dashboard.organizations.getOrganizations()

	# Grab and process the command line options
	try:
		options, remainder = getopt.getopt(sys.argv[1:], 'B:S:T:R:', ['bulkDeploy', 'getsignal','toptalker', 'getroutes'])

	except getopt.GetoptError as err:
		# Print help information and exit:
		print (err)  # Will print something like "option -a not recognized"
		print_usage()
		sys.exit(2)

	else:
		if options:

			for opt, arg in options:
				if remainder:
					arg = arg + ' ' + remainder[0]

				if opt in ('-R', '--getRoutes'):
					my_org = arg
					get_global_routes(dashboard, config.apikey, my_org, orgs)

				elif opt in ('-T', '--topTalker'):
					my_network = arg
					get_top_talker(dashboard, config.apikey, my_network, orgs)

				elif opt in ('-S', '--getSignal'):
					my_network = arg
					get_wireless_signal(dashboard, config.apikey, my_network, orgs)

				elif opt in ('-B', '--bulkDeploy'):
					my_org = arg
					bulk_deploy(dashboard, config.apikey, my_org, orgs)

				else:
					print_usage()
		else:
			print('\nYou forgot to pass arguments!')
			print_usage()

if __name__ == '__main__':
	start_time = datetime.now()
	main()
	end_time = datetime.now()
	print(f'\nScript complete, total runtime {end_time - start_time}')
