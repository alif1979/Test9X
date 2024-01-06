

import pandas as pd
from nettoolkit.addressing import IPv4
from nettoolkit.nettoolkit_db import sort_dataframe_on_subnet, write_to_xl
from .common.general import Initialize


# ===============================================================================================
#  DSRT REQUEST FILE GENERATION CLASS
# ===============================================================================================

class DSRT(Initialize):

	def __call__(self):
		print(f"Info: ~~~ START: PREPARING FOR DSRT Sheet ~~~")
		self.read_dbs()
		self.initial_var_set()
		print(f"Info: ~~~ MAPPING RESO: REGIONS ~~~")
		self.map_reso_region()
		print(f"Info: ~~~ PREPARING CONTAINORS ~~~")
		self.get_containors_df()
		print(f"Info: ~~~ PREPARING SUBNETS ~~~")
		self.get_subnets_df()
		print(f"Info: ~~~ PREPARING DHCP SCOPES ~~~")
		self.get_dhcp_df()
		print(f"Info: ~~~ WRITING OUT TO EXCEL ~~~")
		self.to_excel()
		print(f"Info: ~~~ COMPLETE: PREPARING FOR DSRT Sheet ~~~\n")

	def read_dbs(self):
		self.intfs_dfd = pd.read_excel(self.all_interfaces_file_new, sheet_name=None)
		self.intfs_dfd = { k: v.fillna("") for k, v in self.intfs_dfd.items() }
		self.summary_df = pd.read_excel(self.summary_file_new).fillna("")
		self.campus_db_df = pd.read_excel(self.clubbed_db_file). fillna("")
		#
	def initial_var_set(self):
		self.resos = sorted(self.summary_df.columns)
		self.containors = {}
		self.subnet_add_dict = {}
		self.dhcp_dict = {}

	def map_reso_region(self):
		self.campus_db_df = self.campus_db_df[ (self.campus_db_df.Remark=="")]
		self.reso_region_map = {}
		for region, reso, country in zip(self.campus_db_df.region, self.campus_db_df.reso, self.campus_db_df.country):
			if reso in self.reso_region_map: 
				if region != self.reso_region_map[reso]['region']:			
					print(f"Region mapping error for {reso}: got {region}, have {self.reso_region_map[reso]['region']}")
				if country != self.reso_region_map[reso]['country']:			
					print(f"Country mapping error for {reso}: got {country}, have {self.reso_region_map[reso]['country']}")
				continue
			self.reso_region_map[reso] = {'region': region, 'country':country }


	def get_containors_df(self):
		n = 0
		# for reso in self.resos:
		for site, supernets in self.summary_df.T.iterrows():
			# if reso != site: continue
			for supernet in supernets:
				if not supernet: continue
				s = IPv4(supernet)
				container_row = {}
				container_row['Subnet Address'] = supernet
				container_row['subnet mask CIDR'] = s.binmask
				container_row['Reso Code'] = site
				container_row['Network type (Pick One)'] = 'Internet Guest'
				container_row['Owner Email'] = 'someone@ibm.com'
				container_row['Network Name'] = f"{self.reso_region_map[site]['region'].upper()}-{site.upper()}-Internet Guest-container"
				container_row['Action: Add or Delete'] = 'Add'
				container_row['Associated Domains'] = f"{self.reso_region_map[site]['country']}.IBMmobiledemo.net"
				self.containors[n] = container_row
				n+=1
		self.containors_df = pd.DataFrame.from_dict(self.containors).T
		self.containors_df = sort_dataframe_on_subnet(self.containors_df, 'Subnet Address')

	def get_subnets_df(self):
		n = 0
		already_assigned = set()
		for site, df in self.intfs_dfd.items():
			for i, row in df.iterrows():
				if row.new_subnets in already_assigned: continue
				already_assigned.add(row.new_subnets)
				int_number = row.interface  # vlan,loopback
				int_type = row.interface_type
				subnet = IPv4(row.new_subnets)
				infra_type = 'Infrastructure' if int_number < 1600 else 'User'
				gw_ip = subnet[1] if infra_type == "User" else ""
				if infra_type == 'Infrastructure': continue
				subnet_add_dict = {}
				subnet_add_dict['Subnet Address'] = row.new_subnets
				subnet_add_dict['subnet mask CIDR'] = subnet.binmask
				subnet_add_dict['Reso Code'] = site
				subnet_add_dict['Vlan'] = int_number
				subnet_add_dict['Network type (Pick One)'] = 'Internet Guest'
				subnet_add_dict['Owner Email'] = 'someone@ibm.com'
				subnet_add_dict['Network Name'] = f"{self.reso_region_map[site]['region'].upper()}-{site.upper()}-Internet Guest-{infra_type}"
				subnet_add_dict['Gateway / Router IP'] = gw_ip				
				subnet_add_dict['Action: Add or Delete'] = 'Add'
				subnet_add_dict['Associated Domains'] = f"{self.reso_region_map[site]['country']}.IBMmobiledemo.net"
				self.subnet_add_dict[n] = subnet_add_dict
				n+=1
		self.subnet_add_df = pd.DataFrame.from_dict(self.subnet_add_dict).T
		self.subnet_add_df = sort_dataframe_on_subnet(self.subnet_add_df, 'Subnet Address')

	def get_dhcp_df(self):
		n = 0
		already_assigned = set()
		for site, df in self.intfs_dfd.items():
			for i, row in df.iterrows():
				if row.new_subnets in already_assigned: continue
				already_assigned.add(row.new_subnets)
				int_number = row.interface  # vlan,loopback
				infra_type = 'Infrastructure' if int_number < 1600 else 'User'
				if infra_type == 'Infrastructure': continue
				subnet = IPv4(row.new_subnets)
				dhcp_dict = {}
				dhcp_dict['Subnet Address'] = row.new_subnets
				dhcp_dict['Starting address'] = subnet[11]
				dhcp_dict['Ending address'] = subnet[-1]
				dhcp_dict['Default Gateway'] = subnet[1]
				dhcp_dict['Lease time'] = '4 hours'
				dhcp_dict['DNS server IP'] = ''
				dhcp_dict['Domain name'] = f"{self.reso_region_map[site]['country']}.IBMmobiledemo.net"
				dhcp_dict['Scope Options'] = ''
				dhcp_dict['Action: Add or Delete'] = 'Add'
				dhcp_dict['RESO CODE'] = site
				dhcp_dict['VLAN'] = int_number
				self.dhcp_dict[n] = dhcp_dict
				n+=1
		self.dhcp_df = pd.DataFrame.from_dict(self.dhcp_dict).T
		self.dhcp_df = sort_dataframe_on_subnet(self.dhcp_df, 'Subnet Address')


	def to_excel(self):
		self.dfd = {'containers-add': self.containors_df, 
					'subnets-add': self.subnet_add_df, 
					'dhcp scope-add': self.dhcp_df}
		write_to_xl(self.dsrt_subnet_dhcp_request_file, self.dfd, index=False, overwrite=True)



