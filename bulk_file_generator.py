#
# Author: Kyle T. Blocksom
# Title: Bulk File Generator
# Date: June 25, 2020
#
# Objective: Create CSV file with iterations of store names, each with 3 device SNs attached for claiming
#
#
# Usage: python3 bulk_file_generator.py <file_name>
#

import sys, csv, os, time
from datetime import datetime

###########################################################################################################################################
#
# print_usage() - Print out possible commands for CLI usage
#
###########################################################################################################################################
def print_usage():
	print ();
	print ("Usage examples:")
	print ("\tpython3 bulk_file_generator.py <file_name>         [Create CSV file wiht name <file_name>.csv]")


###########################################################################################################################################
#
# main() - Driver for Bulk File Generator
#
###########################################################################################################################################
def main():

	# Grab and process the command line options
	try:
		file_name = sys.argv[1]
		file_name += '.csv'
		print(f'\nfile_name = {file_name}')

	except getopt.GetoptError as err:
		# Print help information and exit:
		print (err)  # Will print something like "option -a not recognized"
		print_usage()
		sys.exit(2)

	# Remove file <file_name> if already existing
	if os.path.exists(f'{file_name}'):
		os.remove(f'{file_name}')

	# Open file <file_name> for write
	with open(file_name, 'w', newline='') as csvfile:
		fieldnames = ['Network Name', 'Serial Number']
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

		writer.writeheader()

		store_num = 1
		store_total = 30
		row = 0
		num_rows = 3

		# Write three rows for each Network Name, Serial Numbers currently = Empty String
		while store_num < store_total:
			row = 0
			while row < num_rows:
				store_name = 'Test-' + str(store_num)
				writer.writerow({'Network Name': store_name, 'Serial Number': ''})
				row += 1

			store_num += 1

if __name__ == '__main__':
	start_time = datetime.now()
	main()
	end_time = datetime.now()
	print(f'\nScript complete, total runtime {end_time - start_time}')