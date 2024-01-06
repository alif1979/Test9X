
import pandas as pd
from .common.general import *

# --------------------------------------------------------------------

class PollerDB(Initialize, Database):

	reso_dict = {}
	d = { 'region':[], 'country':[], 'reso':[], 'hostname':[], 'dev_type':[], 'ip':[]}
	list_of_ips = []

	def __call__(self):
		print(f"Info: ~~~ START : POLLER DATABASE FILTERING ~~~")
		self.reso_list_values_to_lower()
		self.filter_db()
		self.update_data_dict()
		self.to_excel(self.poller_db_filtered_file)
		print(f"Info: ~~~ COMPLETE : POLLER DATABASE FILTERING ~~~\n")

	def filter_db(self):
		with open(self.poller_db_input_file, 'r') as f:
			self.lines = f.readlines()

	def update_data_dict(self):
		for line in self.lines:
			if line.startswith("#"): continue
			hash_spl = line.split("#")
			if len(hash_spl) < 2:
				print(f"INFO: VERY SMALL LINE DETCTED - {line}")
				continue
			remark = hash_spl[1].upper().replace("ICMPONLY", "").split(",")[-1].strip()
			iphn = hash_spl[0]
			ip_hn_spl = iphn.strip().split()
			ip = ip_hn_spl[0]
			hn = ip_hn_spl[1]
			self.add_to_dict(hn, ip, activity='POLLER')
