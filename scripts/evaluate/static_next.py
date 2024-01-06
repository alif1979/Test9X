
import os
from collections import OrderedDict
from copy import deepcopy
from pprint import pprint
import pandas as pd
import json
from nettoolkit.nettoolkit_common import LST
from nettoolkit.nettoolkit_db import *
from nettoolkit.addressing import *
from .common.general import Initialize

# ===============================================================================================
# Support functions
# ===============================================================================================

def static_nh_routes(file):
	stt_df = pd.read_excel(file, sheet_name='static').fillna("")
	if 'next_hop' not in stt_df.columns:
		print(f'No next_hop column found in database for file {file}')
		return pd.DataFrame()
	stt_df = stt_df[ 
		(stt_df.next_hop != '') & (stt_df.next_hop != '9.0.64.1') &
		(stt_df.version == 4) &
		(stt_df.prefix != '0.0.0.0/0') & 
		(stt_df.prefix != '9.0.0.0')
	]
	return stt_df

def get_ipn(child, parent):
	return addressing(parent).ipn(child)


# ====================================================================================================


# ===============================================================================================

class StaticNexthop(Initialize):

	def __call__(self):
		print(f"Info: ~~~ START : {self.vrf} STATIC ROUTES RETRIVE ~~~")
		self.read_int_db()
		print(f"Info: ~~~ READING DATABASE FILES ~~~")
		self.read_cleanfiles()
		print(f"Info: ~~~ ADDING NEW NEXT HOPS ~~~")
		self.add_new_nh()
		print(f"Info: ~~~ WRITING OUT TO EXCEL ~~~")
		self.to_excel()
		print(f"Info: ~~~ COMPLETE : {self.vrf} STATIC ROUTES RETRIVE ~~~\n")


	def read_int_db(self):
		self.int_dfd = pd.read_excel(self.all_interfaces_file_new, sheet_name=None)
		self.int_dfd = { k: v.fillna('')  for k, v in self.int_dfd.items() }

	def read_cleanfiles(self):
		self.static_dev_dict = {}
		self.subset_dict = {}
		j = 0
		resos_not_in_int_dfd = set()
		for file in self.clean_files:
			# if not file.startswith('hke-vid'): continue
			hn = file.split("-clean")[0]
			file  = f"{self.capture_folder}/{file}"
			sttdf_filtered = static_nh_routes(file)
			if sttdf_filtered.empty: continue
			reso = hn.split("-")[0]
			if reso not in self.int_dfd: 
				resos_not_in_int_dfd.add(reso)
				continue
			#
			site_acc_subnets = set(self.int_dfd[reso].subnets)
			for i, row in sttdf_filtered.iterrows():
				for nh in row.next_hop.split("\n"):
					for site_acc_subnet in site_acc_subnets:
						if not isSubset(nh, site_acc_subnet):continue
						self.subset_dict[nh] = site_acc_subnet
						self.static_dev_dict[j] = {
							'hostname': hn,
							'pfx_vrf': row.pfx_vrf,
							'prefix': row.prefix,
							'next_hop': nh,
							'adminisrative_distance': row.adminisrative_distance,
							'tag_value': row.tag_value,
							'remark': row.remark,
							'nh_vlan_subnet_old': site_acc_subnet,
							'nh_vlan_subnet_new': self.get_new_subnet(reso, hn, site_acc_subnet),
						}
						j+=1
		print(f'    Resos  not defined in interfaces file {resos_not_in_int_dfd}')

	def add_new_nh(self):
		self.static_dev_df = pd.DataFrame.from_dict(self.static_dev_dict).fillna('').T
		self.static_dev_df['next_hop_new'] = self.static_dev_df.apply(lambda x: self.get_new_next_hop(x.next_hop, x.nh_vlan_subnet_new), axis=1)
		self.static_dev_df.drop( ['nh_vlan_subnet_old', 'nh_vlan_subnet_new'], axis=1, inplace=True)

	def get_new_next_hop(self, nh, new_subnet):
		return IPv4(new_subnet)[get_ipn(nh, self.subset_dict[nh])]

	def get_new_subnet(self, reso, hn, subnet):
		df = self.int_dfd[reso]
		minidf = df[(df.device==hn) & (df.subnets==subnet)]
		return minidf['new_subnets'][minidf.index[0]]

	def to_excel(self):
		self.static_dev_df.to_excel(self.static_route_changes_file, index=False)
		pass

# ====================================================================================================


