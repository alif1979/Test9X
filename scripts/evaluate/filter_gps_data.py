
import pandas as pd
from .common.general import *

# --------------------------------------------------------------------

class GpsDB(Initialize, Database):

	reso_dict = {}
	d = { 'region':[], 'country':[], 'reso':[], 'hostname':[], 'dev_type':[], 'ip':[]}
	list_of_ips = []

	def __call__(self):
		print(f"Info: ~~~ START : GPS DATABASE FILTERING ~~~")
		self.reso_list_values_to_lower()
		self.filter_db()
		self.update_data_dict()
		self.to_excel(self.gps_db_filtered_file)
		print(f"Info: ~~~ COMPLETE : GPS DATABASE FILTERING ~~~\n")

	def filter_db(self):
		df = pd.read_excel(self.gps_db_input_file).fillna("") 
		df = df[ ['Asset', 'IP', 'Device Type', 'Country'] ]      #### COLUMNS TO RETAIN 
		df = df[(df['Device Type'] == 'Data Switch')]             #### REMOVE DEVICES OTHER THAN SWITCHES
		nonips = {                                                #### NON-IP DEVICES IDENTIFIERS
			"DYNAMIC",
			"DHCP",
			"STACK",
			"NA",
			"n/a",
			"NOIP",
			"NOIP-STCK",
			"Not Applicable",
			"DYANAMIC",
			"DYNAMIC IPs",
			"NOIPSTCK",
			"NO-IP-STACK",
			"SPARE",
			"DYMANIC",
			"dinamic",
			"DYNAMIC IP",
			"NO",
		}
		for ni in nonips:	
			df = df[ ((df.IP != ni)) ]
		df = df[ (df['Asset'].str.lower().str[-4:] != '-kyn' )]       ##### REMOVE A FEW KYNDRYL DEVICES
		self.df = df

	def update_data_dict(self):
		for hn, ip in zip(self.df.Asset, self.df.IP):
			self.add_to_dict(hn, ip, activity='GPS')
