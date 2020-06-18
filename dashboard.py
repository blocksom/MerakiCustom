#
# Author: Kyle T. Blocksom
# Title: Dashboard
# Date: June 16, 2020
#
# Objective: Merakio Dashboard SDK
#
# Notes: 
#   - 'pip install meraki==1.0.0b9' to runtime environment
#
# Usage:  dashboard.py <action> <var1>...<varN>
#

import meraki, random, sys, getopt, csv, config, os, asyncio
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
def get_networkname_by_id(my_key, network_ID, orgs):
	
	net_name = ''

	# Get  current list of networks
	for org in orgs:
		current_networks = meraki.getnetworklist(my_key, org['id'], None, True)

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
def get_networkid_by_name(my_key, network_name, orgs):

	# Get current list of networks
	for org in orgs:
		current_networks = meraki.getnetworklist(my_key, org['id'], None, True)

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
		network = get_networkname_by_id(my_key, network_ID, orgs)
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
			networks = meraki.getnetworklist(my_key, org['id'], None, True)
		
			for net in networks:
				get_network_routes(dashboard, my_key, net['id'], orgs)

###########################################################################################################################################
#
# write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker) - Write data returned by earlier method to .csv row-by-row
#
###########################################################################################################################################
def write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker):

	data[0].update(clients[0])

	index = 0
	while index < len(data) and tracker < len(clients):
		# Write traffic history to file
		data[index].update(network_dict)
		data[index].update(clients[tracker])
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
						write_csv(csv_writer, clients, data, network_dict, network_name, network_ID, tracker)

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
	network_ID = get_networkid_by_name(my_key, network_name, orgs)

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
			try:
				networks = dashboard.organizations.getOrganizationNetworks(org_id)

			# Graceful failover
			except meraki.APIError as e:
				throw_error('Meraki_Error')
				continue

			except Exception as e:
				throw_error('Other_Error')
				continue

			else:
				total = len(networks)
				counter = 1

				# Iterate through list of Networks
				for net in networks:
					print(f'\nFinding Clients in Network {net["name"]} ({counter} of {total})\n')
					iterate_clients(dashboard, network_name, network_ID, field_names, 'Talker')
					counter += 1
		else:
			print('\nEntering Iterate\n')
			iterate_clients(dashboard, network_name, network_ID, field_names, 'Talker')
			break

###########################################################################################################################################
#
#  get_wireless_signal(dashboard, my_key, network_name, orgs, timespan) - Return SNR and RSSI data for all Clients on network <network_name>
#  
###########################################################################################################################################
def get_wireless_signal(dashboard, my_key, network_name, orgs, timeSpan=3600):

	network_ID = get_networkid_by_name(my_key, network_name, orgs)

	if network_ID == '':
		print('Network for {network_name} not found!')
		quit()

	network_ID = get_networkid_by_name(my_key, network_name, orgs)

	field_names = ['Network Name', 'Network ID', 'id', 'mac', 'description', 'ip',  'ip6', 'ip6Local', 'user', 'startTs', 'endTs', \
	'snr', 'rssi', 'firstSeen', 'lastSeen', 'manufacturer', 'os', 'recentDeviceSerial', 'recentDeviceName', 'recentDeviceMac', \
	'ssid', 'vlan', 'switchport', 'usage', 'status', 'notes', 'smInstalled', 'groupPolicy8021x', 'application', 'destination', \
	'protocol', 'port', 'ts', 'recv', 'sent', 'numFlows', 'activeSeconds']


	iterate_clients(dashboard, network_name, network_ID, field_names, 'Signal')

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
		options, remainder = getopt.getopt(sys.argv[1:], 'S:T:R:', ['getsignal','toptalker', 'getroutes'])

	except getopt.GetoptError as err:
		# Print help information and exit:
		print (err)  # Will print something like "option -a not recognized"
		print_usage()
		sys.exit(2)

	else:
		if options:

			print(f'\nOptions = {options}, Remainder = {remainder}\n')

			for opt, arg in options:
				if remainder:
					arg = arg + ' ' + remainder[0]
				if arg:
					print(f'Arg = {arg}\n')
				if opt in ('-R', '--getRoutes'):
					my_org = arg
					get_global_routes(dashboard, config.apikey, my_org, orgs)

				elif opt in ('-T', '--topTalker'):
					my_network = arg
					get_top_talker(dashboard, config.apikey, my_network, orgs)

				elif opt in ('-S', '--getSignal'):
					my_network = arg
					get_wireless_signal(dashboard, config.apikey, my_network, orgs)

				else:
					print_usage()
		else:
			print('\nYou forgot to pass arguments!')
			print_usage()

	sys.exit(2)

if __name__ == '__main__':
	start_time = datetime.now()
	main()
	end_time = datetime.now()
	print(f'\nScript complete, total runtime {end_time - start_time}')




