

import pandas as pd
from nettoolkit.addressing import IPv4
from nettoolkit.nettoolkit_db import sort_dataframe_on_subnet, write_to_xl
from .common.general import Initialize


# ===============================================================================================
#  DSRT REQUEST FILE GENERATION CLASS
# ===============================================================================================

class EdgeRouter(Initialize):

	def __call__(self):
		print(f"Info: ~~~ START: SDWAN EDGE ROUTER CHANGE SHEET PREPARATION ~~~")
		print(f"Info: ~~~ READING DATABASE ~~~")
		self.read_dbs()
		print(f"Info: ~~~ GET UPDATED IP DETAILS ~~~")
		self.update_all_sdwan_edge_routers()
		print(f"Info: ~~~ CONVERTING DATABSE TO DATAFRAME ~~~")
		self.convert_to_df()
		print(f"Info: ~~~ WRITING OUT TO EXCEL ~~~")
		self.to_excel()
		print(f"Info: ~~~ COMPLETE: SDWAN EDGE ROUTER CHANGE SHEET PREPARATION ~~~\n")

	def read_dbs(self):
		self.intfs_dfd = pd.read_excel(self.all_interfaces_file_new, sheet_name=None)
		self.intfs_dfd = { k: v.fillna("") for k, v in self.intfs_dfd.items() }

	def update_all_sdwan_edge_routers(self):
		self.all_routers = {} 
		for reso, df in self.intfs_dfd.items():
			if self.detailed_display: print(f"  -- Preparing for Reso {reso},")
			already_assigned = set()
			subnet_1131, subnet_1134, subnet_1131_new, subnet_1134_new, infra, infra_new = None, None, None, None, None, None
			for i, row in df.iterrows():
				if row.interface not in (1131, 1134, 21): continue
				if row.interface != 21 and row.interface in already_assigned: continue
				already_assigned.add(row.interface)
				#
				if row.interface == 1131: 
					subnet_1131 = IPv4(row.subnets)
					subnet_1131_new = IPv4(row.new_subnets)
				if row.interface == 1134: 
					subnet_1134 = IPv4(row.subnets)
					subnet_1134_new = IPv4(row.new_subnets)
				if row.interface == 21:   
					if row.device.endswith("b"):
						loopback = IPv4(row.subnets)
					else:
						loopback = IPv4(row.subnets)
						loopback_new = IPv4(row.new_subnets)
					infra = IPv4(loopback.expand(27))
					infra_new = IPv4(loopback_new.expand(27))
			self.all_routers[reso] = self.get_allocations(subnet_1131, subnet_1134,subnet_1131_new, subnet_1134_new, infra,infra_new)

	def get_allocations(self, subnet_1131, subnet_1134, subnet_1131_new, subnet_1134_new, infra,infra_new):
		if not subnet_1131: return {}
		sdwan_a = {
			'vpn210_lan_a_dir_ipv4': (3, subnet_1131, subnet_1131_new),
			'vpn210_lan_a_lo_ipv4': (21, infra, infra_new),
			'vpn210_lan_b_dir_ipv4': (4, subnet_1131, subnet_1131_new),
			'vpn210_lan_b_lo_ipv4': (22, infra, infra_new),
			'vpn210_se_lo210_ipv4': (17, infra, infra_new),
			'vpn210_se_service_ipv4': (1, subnet_1131, subnet_1131_new),
		}
		sdwan_b = {
			'vpn210_lan_a_dir_ipv4': (3, subnet_1134, subnet_1134_new),
			'vpn210_lan_a_lo_ipv4': (21, infra, infra_new),
			'vpn210_lan_b_dir_ipv4': (4, subnet_1134, subnet_1134_new),
			'vpn210_lan_b_lo_ipv4': (22, infra, infra_new),
			'vpn210_se_lo210_ipv4': (18, infra, infra_new),	
			'vpn210_se_service_ipv4': (1, subnet_1134, subnet_1134_new),
		}
		sdwan_s = {
			'vpn210_lan_dir_ipv4': (3, subnet_1131, subnet_1131_new),
			'vpn210_lan_lo_ipv4': (21, infra, infra_new),	    
			'vpn210_se_lo210_ipv4': (17, infra, infra_new),	
			'vpn210_se_service_ipv4': (1, subnet_1131, subnet_1131_new),
		}
		s = '-A'
		routers = {}
		if subnet_1134:
			routers['SE-B Router - Current'] = { k:v[1][v[0]] for k, v in sdwan_b.items()}
			routers['SE-B Router - new'] = { k:v[2][v[0]] for k, v in sdwan_b.items()}
		if subnet_1131 and not subnet_1134:
			sdwan_a = sdwan_s
			s = ""
		routers[f'SE{s} Router - Current'] = { k:v[1][v[0]] for k, v in sdwan_a.items()}
		routers[f'SE{s} Router - new'] = { k:v[2][v[0]] for k, v in sdwan_a.items()}
		return routers

	def convert_to_df(self):
		for reso, d in self.all_routers.items():
			self.all_routers[reso] = pd.DataFrame.from_dict(d)

	def to_excel(self):
		write_to_xl(self.sdwan_router_changes_file, self.all_routers, index=True, overwrite=True)

# ===============================================================================================
