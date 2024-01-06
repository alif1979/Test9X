
import pandas as pd
from .common.general import *

# --------------------------------------------------------------------

class NetbrainDB(Initialize, Database):

	reso_dict = {}
	d = { 'region':[], 'country':[], 'reso':[], 'hostname':[], 'dev_type':[], 'ip':[]}
	list_of_ips = []

	def __call__(self):
		print(f"Info: ~~~ START : NETBRAIN DATABASE FILTERING ~~~")
		self.reso_list_values_to_lower()
		self.filter_db()
		self.update_data_dict()
		self.to_excel(self.nb_db_filtered_file)
		print(f"Info: ~~~ COMPLETE : NETBRAIN DATABASE FILTERING ~~~\n")

	def filter_db(self):
		df = pd.read_excel(self.nb_db_input_file).fillna("") 
		df = df[['Hostname', 'Mgmt IP']]                          ####  COLUMNS TO RETAIN
		self.df = df

	def update_data_dict(self):
		for hn, ip in zip(self.df['Hostname'], self.df['Mgmt IP']):
			self.add_to_dict(hn, ip, activity='NETBRAIN')

