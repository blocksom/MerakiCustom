#
# Author: Kyle T. Blocksom
# Title: Client URL List
# Date: May 12, 2020
#
# Objective: Iterate through list of Meraki Organizations, followed by Networks, then by clients
#            to print client | domain data (x5) to .csv file named after Network Name in Meraki Dashboard
#
# Notes: 
#   - 'pip install meraki==1.0.0b3' to runtime environment
#   - If Network Name file already exists on local client, file will be appended, not overwritten.
#

import meraki, csv, config, os, asyncio
from datetime import datetime

# Change 'apikey' variable to match Taco Bell Meraki Organization
apikey = config.apikey

def main(): 

    # Instantiate a Meraki dashboard API session
    dashboard = meraki.DashboardAPI(
        api_key=apikey,
        base_url='https://api.meraki.com/api/v1',
        output_log=False,
        print_console=False
    )

    # Get list of Organizations to which API key has access
    organizations = dashboard.organizations.getOrganizations()
    
    # Iterate through list of organizations
    for org in organizations:
        print(f'\nAnalyzing Organization {org["name"]}:\n')
        org_id = org['id']

        # Get list of networks in Organization
        try:
            networks = dashboard.organizations.getOrganizationNetworks(org_id)

        except meraki.APIError as e:
            print(f'Meraki API error: {e}')
            print(f'status code = {e.status}')
            print(f'reason = {e.reason}')
            print(f'error = {e.message}')
            continue

        except Exception as e:
            print(f'some other error: {e}')
            continue

        total = len(networks)
        counter = 1

        # Iterate through list of Networks
        for net in networks:
            print(f'\nFinding Clients in Network {net["name"]} ({counter} of {total})\n')
            try:
                # Get list of Clients on Network, filtering on timespan of last 14 days
                # def getNetworkClients(self, networkId: str, total_pages=1, direction='next', **kwargs):
                clients = dashboard.networks.getNetworkClients(net['id'], timespan=60*60*24*14, perPage=1000, total_pages='all')

            # Graceful failover
            except meraki.APIError as e:
                print(f'Meraki API error: {e}')
                print(f'status code = {e.status}')
                print(f'reason = {e.reason}')
                print(f'error = {e.message}')

            except Exception as e:
                print(f'some other error: {e}')

            else:
                # Define file to which we will write Client | Traffic data
                # Named after Network Name in Meraki Dashboard
                if os.path.exists(f'{net["name"]}.csv'):
                    os.remove(f'{net["name"]}.csv')
                
                file_name = f'{net["name"]}.csv'
                tracker = 1

                if clients:
                    total_client = len(clients)
                    # Iterate through Clients on Network
                    for client in clients:
                        print(f'\nAnalyzing Client {tracker}\'s traffic out of {len(clients)} total Clients:\n')

                        # Open file for appendment and set .csv field names to dictonary keys
                        output_file = open(f'{file_name}', mode='a', newline='\n')
                        
                        # field_names = traffic[0].keys()
                        field_names = ['Network Name', 'Network ID', 'id', 'mac', 'description', 'ip',  'ip6', 'ip6Local', 'user', \
                        'firstSeen', 'lastSeen', 'manufacturer', 'os', 'recentDeviceSerial', 'recentDeviceName', 'recentDeviceMac', \
                        'ssid', 'vlan', 'switchport', 'usage', 'status', 'notes', 'smInstalled', 'groupPolicy8021x', 'application', 'destination', \
                        'protocol', 'port', 'ts', 'recv', 'sent', 'numFlows', 'activeSeconds']
                        
                        network_dict = {'Network Name':net['name'], 'Network ID':net['id']}

                        # client-id, mac, description, ip,  ip6, ip6Local, user, firstSeen, lastSeen, manufacturer, os, recentDeviceSerial,
                        # recentDeviceName, recentDeviceMac, ssid, vlan, switchport, usage, status, notes, smInstalled, groupPolicy8021x)
                        csv_writer = csv.DictWriter(output_file, field_names, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)

                        if tracker == 1:
                            csv_writer.writeheader()

                        try:
                            # Get traffic history for each Client across each Network
                            # def getNetworkClientTrafficHistory(self, networkId: str, clientId: str, total_pages=1, direction='next', **kwargs):
                            # GET 'https://api.meraki.com/api/v1/networks/{networkId}/clients/{clientId}/trafficHistory'
                            traffic = dashboard.networks.getNetworkClientTrafficHistory(net['id'], client['id'])

                        # Graceful failover
                        except meraki.APIError as e:
                            print(f'Meraki API error: {e}')
                            print(f'status code = {e.status}')
                            print(f'reason = {e.reason}')
                            print(f'error = {e.message}')

                        except Exception as e:
                            print(f'some other error: {e}')

                        else:
                            if traffic:
                                traffic[0].update(clients[0])
                                index = 0
                                
                                while index < len(traffic) and tracker < len(clients):
                                    # Write traffic history to file
                                    traffic[index].update(network_dict)
                                    traffic[index].update(clients[tracker])
                                    csv_writer.writerow(traffic[index])

                                    index += 1

                        tracker += 1              

                output_file.close()
                counter += 1

# Script Driver to execute Client URL List project and calculate program runtime
if __name__ == '__main__':
    start_time = datetime.now()
    main()
    end_time = datetime.now()
    print(f'\nScript complete, total runtime {end_time - start_time}')