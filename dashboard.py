#
# Author: Kyle T. Blocksom
# Title: Dashboard
# Date: July 24, 2020
#
# Objective: Meraki Dashboard SDK
#
# Notes: 
#   - 'pip install meraki==1.0.0b9' to runtime environment
#
# Usage: python3 dashboard.py <action> <var1>...<varN>
#

import meraki, merakiapi, random, sys, getopt, csv, config, os, asyncio, time
from datetime import datetime, timedelta
from faker import Faker

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
		org_name = org['name']
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

	network_ID = '';

	# Get current list of networks
	for org in orgs:
		if org['id'] == '294497':
			current_networks = dashboard.organizations.getOrganizationNetworks(org['id'])
			org_name = org['name']

			for net in current_networks:
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
# network_exists(dashboard, my_org) - Return Networks within <my_org>, empty list returned if no Networks exists
#
###########################################################################################################################################
def network_exists(dashboard, my_org):
	networks = ''

	# Get list of networks in Organization
	try:
		networks = dashboard.organizations.getOrganizationNetworks(my_org)
	# Graceful failover
	except meraki.APIError as e:
		throw_error(e, 'Meraki_Error')

	except Exception as e:
		throw_error(e, 'Other_Error')

	return networks

###########################################################################################################################################
#
# write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker) - Write data returned by earlier method to CSV row-by-row
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
def iterate_clients(dashboard, network_name, network_ID, field_names, start_time, end_time, flag):

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
		tracker = 0
		if clients:

			# TO DO: Parse clients based on SSID match

			total_client = len(clients)
			# Iterate through Clients on Network
			for client in clients:
				print("Analyzing Clients in Network {} ({} of {})".format(network_name, tracker + 1, total_client))

				# Open file for appendment and set .csv field names to dictonary keys
				output_file = open(f'{file_name}', mode='a', newline='\n')
				csv_writer = csv.DictWriter(output_file, field_names, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

				if tracker == 0:
					csv_writer.writeheader()

				try:
					print(f'\nStart = {start_time}')

					start = start_time.split(' ', 1)
					end = end_time.split(' ', 1)
					new_start = '2020-' + start[0] + 'T' + start[1] + ':00Z'
					new_end = '2020-' + end[0] + 'T' + end[1] + ':00Z'

					print(f'\nstart_time = {start_time}, start[0] = {start[0]}, start[1] = {start[1]}\n')
			
					if flag == 'Talker':
		                # Get traffic history for each Client across each Network
						data = dashboard.networks.getNetworkClientTrafficHistory(networkId=network_ID, clientId=client['id'])
						network_dict = {'Network Name':network_name, 'Network ID':network_ID, 'DNS Request Quantity':len(data)}
					
					elif flag == 'Signal':
						# Return SNR/RSSI data based on specified time window <new_start> to <new_end>
						network_dict = {'Network Name':network_name, 'Network ID':network_ID}
						data = dashboard.wireless.getNetworkWirelessSignalQualityHistory(networkId=network_ID, clientId=client['id'], t0=new_start, t1=new_end, autoResolution=True)

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
#  get_top_talker_template(dashboard, my_key, network_name, orgs, timespan) - Return .csv list of all clients, sorted by total number of DNS requests
#   takes org and template ID
#  
###########################################################################################################################################
"""def get_top_talker_template(dashboard, my_key, network_name, orgs, timeSpan=3600):

	orgs = get organizations

	for org in orgs:
		templates = get templates organizations

		template_ID = template_nametoID_converter(template_name)

		for template in templates:
			if template_ID == template['id']:


"""

###########################################################################################################################################
#
#  get_top_talker(dashboard, my_key, network_name, start_time, end_time, orgs) - Return .csv list of all clients, sorted by total number of DNS requests
#   during specified time range beginning at <start_time> and terminating at <end_time>
#  
###########################################################################################################################################
def get_top_talker(dashboard, my_key, network_name, start_time, end_time, orgs):

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
					iterate_clients(dashboard, network_name, network_ID, field_names, start_time, end_time, 'Talker')
					counter += 1
		else:
			iterate_clients(dashboard, network_name, network_ID, field_names, start_time, end_time, 'Talker')
			break

###########################################################################################################################################
#
#  get_wireless_signal(dashboard, my_key, network_name, start_time, end_time, orgs) - Return SNR and RSSI data for all Clients on network <network_name>
#   during specified time range beginning at <start_time> and terminating at <end_time>
#  
###########################################################################################################################################
def get_wireless_signal(dashboard, my_key, network_name, start_time, end_time, orgs):

	network_ID = get_networkid_by_name(dashboard, my_key, network_name, orgs)

	if network_ID == '':
		print('Network for {network_name} not found!')
		quit()

	network_ID = get_networkid_by_name(dashboard, my_key, network_name, orgs)

	field_names = ['Network Name', 'Network ID', 'id', 'mac', 'description', 'ip',  'ip6', 'ip6Local', 'user', 'startTs', 'endTs', \
	'snr', 'rssi', 'firstSeen', 'lastSeen', 'manufacturer', 'os', 'recentDeviceSerial', 'recentDeviceName', 'recentDeviceMac', \
	'ssid', 'vlan', 'switchport', 'usage', 'status', 'notes', 'smInstalled', 'groupPolicy8021x', 'application', 'destination', \
	'protocol', 'port', 'ts', 'recv', 'sent', 'numFlows', 'activeSeconds']

	iterate_clients(dashboard, network_name, network_ID, field_names, start_time, end_time, 'Signal')

###########################################################################################################################################
#
#  bulk_deploy(dashboard, my_key, my_org, orgs) - Create Organization <my_org> passed via CLI and bulk deploy 'Network_Device_List.csv' 
#	Network Names and Serial Numbers
#  
###########################################################################################################################################
def bulk_deploy(dashboard, my_key, my_org, orgs):

	# Deleting Org if it already exists
	"""for org in orgs:
		if my_org == org['name']:
			print(f'\nDeleting Org {my_org}\'s Store Networks\n')

			devices = dashboard.organizations.getOrganizationDevices(org['id'])
			old_networks = network_exists(dashboard, org['id'])

			for net in old_networks:
				if net["name"].startswith('Store'):
					net_name = net['name']
					print(f'Deleting Network {net_name}')
					dashboard.networks.deleteNetwork(net['id'])

			templates = dashboard.organizations.getOrganizationConfigTemplates(org['id'])

			for template in templates:
				template_id = template['id']
				template_name = template['name']
				print(f'Deleting Template {template_name}')
				dashboard.organizations.deleteOrganizationConfigTemplate(org['id'], template['id'])
			
			#dashboard.organizations.deleteOrganization(org['id'])
			exit()"""

	# Checking if Org exists, if not, Create Org
	for org in orgs:
		if org['name'] == my_org:
			org_name = org['name']
			org_id = org['id']
			print(f'\nOrg \'{org_name}\' exists - Beginning Network add sequence:\n')
			break
		else:
			new_org = dashboard.organizations.createOrganization(my_org)
			org_name = new_org['name']
			org_id = new_org['id']
			print(f'\nCreating Org \'{org_name}\'\n')
			break

	# Read from .csv to Create Networks and Claim Devices
	with open('Network_Device_List.csv', mode='r') as csv_file:
		csv_reader = csv.DictReader(csv_file)

		network_dict = {}
		for row in csv_reader:
			for column, value in row.items():
				column = column.replace('\ufeff', '')
				network_dict.setdefault(column, []).append(value)

	iterate = 0

	for key in network_dict:
		for value in network_dict[key]:
			flag = 0

			# Check if Network exists, if not then Create Network
			if key == 'Network Name':
				new_networks = network_exists(dashboard, org_id)

				if not new_networks:
					network = dashboard.organizations.createOrganizationNetwork(org_id, value, productTypes=['wireless','switch','appliance'])
					print('Adding Network \'' + network['name'] + '\' to Org \'' + org_name + '\'')
				else:
					for net in new_networks:
						if value == net['name']:
							flag = 1

					if flag == 0:		
						network = dashboard.organizations.createOrganizationNetwork(org_id, value, productTypes=['wireless','switch','appliance'])
						print('Adding Network \'' + network['name'] + '\' to Org \'' + org_name + '\'')

		ser = []

		template_id = 'L_647955396387958867'
		template_name = 'East Store Template'

		print();
		for net in new_networks:
			if net["name"].startswith('Store'):
				for value in network_dict['Serial Number']:
					if value != '':
						ser.append(value)
						print('Network \'' + net['name'] + '\' claiming Serial ''\'' + ser[0] + '\'')
						dashboard.networks.claimNetworkDevices(net['id'], ser)
						network_dict['Serial Number'].remove(value)
						ser.remove(value)
						break
					else:
						network_dict['Serial Number'].remove(value)

				print('Binding Network \'' + net['name'] + '\' to Template \'' + template_name + '\'\n')
				dashboard.networks.bindNetwork(net['id'], template_id)
		

		addr = []
		addr_index = 0
		devices = dashboard.organizations.getOrganizationDevices(org_id)
		
		"""print();
		for device in devices:
			if device['serial'].startswith('Q2ED'):
				for value in network_dict['Serial Number']:

					Serials = len(network_dict['Address'])
					print(f'\nNetwork-Dict[Address] = {Serials}')

					addr.append(network_dict['Address'].pop(addr_index))
					print('Device '+device['serial'] +' located at ' + addr[0] + '\n')
					dashboard.devices.updateDevice(device['serial'], address=addr[0])
					addr.pop(0)
					addr_index += 2"""

		return

###########################################################################################################################################
#
# print_usage() - Print out possible commands for CLI usage
#
###########################################################################################################################################
def print_usage():
	print ();
	print ("Some usage examples:")
	print ("\tpython3 dashboard.py --getsignal <Network Name> or -S <Network Name> <Start Time> <End Time>	\n\t   [Show SNR/RSSI data for clients on <network> during <start time> <end time>]")
	print ("\tpython3 dashboard.py --toptalker <Network Name> or -T <Network Name> <Start Time> <End Time>	\n\t   [Show top talker clients on <network> during <start time> <end time>]")
	print ("\n\tTime format for -S and -T functions must match: 'Month-Day Hour:Minute' and be no longer than 31 days from today\n")
	print ("\tpython3 dashboard.py --getroutes <Org Name> or -R <Org Name>	\n\t   [Show global route table for <org>]")
	print ("\tpython3 dashboard.py --bulkDeploy <Org Name> or -B <Org Name>	\n\t   [Network creation and bulk device claim for <org>]\n")
	sys.exit(2)

###########################################################################################################################################
#
# main() - Driver for Meraki Dashboard SDK
#
###########################################################################################################################################
def main():

	# Instantiate API session with Meraki Dashboard
	dashboard = meraki.DashboardAPI(
		api_key=config.apikey,
		base_url='https://api.meraki.com/api/v1',
		output_log=False,
		print_console=False
	)

	# Set up initital variables
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

	# Get list of Orgs associated with <api_key>
	orgs = dashboard.organizations.getOrganizations()

	# Grab and process the command line options
	try:
		commands, argument = getopt.getopt(sys.argv[1:], 'B:S:T:R:', ['bulkDeploy', 'getsignal','toptalker', 'getroutes'])

	except getopt.GetoptError as err:
		# Print help information and exit:
		print (err)
		print_usage()

	else:
		# Proper usage - parse command line
		if commands:
			for command, arg in commands:

				if command in ('-R', '--getRoutes'):
					my_org = arg
					get_global_routes(dashboard, config.apikey, my_org, orgs)

				elif command in ('-T', '--topTalker'):
					if len(argument) > 1:
						start_time = argument[0]
						end_time = argument[1]
					else:
						print('\nYou forgot to pass the Start and End Time arguments!')
						print_usage()				
					
					my_network = arg
					get_top_talker(dashboard, config.apikey, my_network, start_time, end_time, orgs)

				elif command in ('-S', '--getSignal'):
					if len(argument) > 1:
						start_time = argument[0]
						end_time = argument[1]
					else:
						print('\nYou forgot to pass the Start and End Time arguments!')
						print_usage()
					
					my_network = arg
					get_wireless_signal(dashboard, config.apikey, my_network, start_time, end_time, orgs)

				elif command in ('-B', '--bulkDeploy'):
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
