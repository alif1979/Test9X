
import os
import json
import pandas as pd
from nettoolkit.pyJuniper import convert_to_set_from_captures
from nettoolkit.addressing import addressing
from pprint import pprint

from .common.general import Initialize

# =====================================================================================

class Verify(Initialize):


	def __call__(self):
		print(f" ~~~ SUMMARY  ~~~")
		# self.read_dbs()
		# self.is_any_missing()
		# self.verify_bgp_router_ids()
		# self.add_old_summary_to_new_summary_mappings()
		print(f"\n")
		self.get_ua_nbrs()

	def temp_check(self):
		#  NOT IN USE, RND only
		dfd = pd.read_excel(self.dsrt_subnet_dhcp_request_file, sheet_name=None)
		cont_df = dfd['containers-add']
		subnet_df = dfd['subnets-add']
		dhcp_df = dfd['dhcp scope-add']

		cont_resos = set(cont_df['Reso Code'])
		subnet_resos = set(subnet_df['Reso Code'])
		dhcp_resos = set(dhcp_df['RESO CODE'])

		uresos =  {'pok', 'imr1', 'j8v', 'h5y', '423', 'smb', 'j0a', 'a20', '871', 'ci0', 'i9g', 'rpl', 'h8p', 'c1u', '755', 'l9e', 'bol', 'g6e', 'atch', 'ft7', '4ws', 'bld', 'im9d', 'sjs', 'h6i', 'mlg', 'h8z', 'bcy', 'mdc', 'g9z', 'pll', 'k0q', 'g7i', 'er4', 'k4a', 'hgh', 'imr2', '5u5', '0am', 'g4l', 'j0k', 'e2y', 'e1j'}

		print(len(cont_resos), len(subnet_resos), len(dhcp_resos))
		print(cont_resos.difference(subnet_resos))
		print(cont_resos.difference(dhcp_resos))
		print(subnet_resos.difference(dhcp_resos))

		print(len(uresos))
		print(cont_resos.difference(subnet_resos).difference(uresos)   )






	def read_dbs(self):
		self.clubbed_db_df = pd.read_excel(self.clubbed_db_file).fillna('')		
		self.reso_list_df = pd.read_excel(self.reso_list_file).fillna('')		
		self.reso_to_device_types_map_df = pd.read_excel(self.reso_to_device_types_map_file).fillna('')		
		self.old_interfaces_dfd = pd.read_excel(self.all_interfaces_file_current, sheet_name=None)	
		self.old_interfaces_dfd = { k:v.fillna('') for k, v in self.old_interfaces_dfd.items()}
		self.new_interfaces_dfd = pd.read_excel(self.all_interfaces_file_new, sheet_name=None)	
		self.new_interfaces_dfd = { k:v.fillna('') for k, v in self.new_interfaces_dfd.items()}
		self.old_summary_df = pd.read_excel(self.summary_file_current).fillna('')		
		self.new_summary_df = pd.read_excel(self.summary_file_new).fillna('')		
		self.old_region_wise_summary_df = pd.read_excel(self.region_wise_summary_file_current).fillna('')		
		with open(self.device_types_json_file) as f:
			self.device_types = json.load(f)
		with open(self.json_infra_file) as f:
			self.infra = json.load(f)


	def is_any_missing(self):
		config_files = set([file.split(".")[0].lower() for file in os.listdir(self.output_folder) if file.endswith('.cfg')])
		clean_files = [x.lower() for x in set(self.clean_files_hn)]
		#
		devices_with_vrf_int = set()
		for reso, df in self.old_interfaces_dfd.items():
			devices_with_vrf_int = devices_with_vrf_int.union(set(df.device))
		devices_with_vrf_int = set([x.lower() for x in devices_with_vrf_int])
		# #

		old_summarized_sites = self.old_summary_df.columns
		new_summarized_sites = self.new_summary_df.columns
		#
		old_intfs_sites = self.old_interfaces_dfd.keys()
		new_intfs_sites = self.new_interfaces_dfd.keys()
		#
		dt_sites = set(self.device_types.keys())
		infra_assigned_sites = set(self.infra.keys())
		#
		clubbed_db_w = self.clubbed_db_df[(self.clubbed_db_df.Remark == '')]
		clubbed_db_wo = self.clubbed_db_df[(self.clubbed_db_df.Remark != '')]
		junipers_staring = ('me-3600x-24fs-m', 'mx240', 'qfx5100-48s-6q')
		clubbed_db_w_vrf = clubbed_db_w[clubbed_db_w.hostname.isin(list(devices_with_vrf_int))] 
		clubbed_db_w_juniper = clubbed_db_w_vrf[clubbed_db_w_vrf.model.isin(list(junipers_staring))]
		clubbed_db_w_cisco = clubbed_db_w_vrf[~clubbed_db_w_vrf.model.isin(list(junipers_staring))]
		
		print("-"*80)
		print(f"Info: Listed Resos in campus-db {len(set(self.clubbed_db_df.reso))}")
		print(f"\t in device type json file: {len(dt_sites)}")
		print(f"\t in infra alloc json file: {len(infra_assigned_sites)}")
		print(f"\t in old interfaces file: {len(old_intfs_sites)}")
		print(f"\t in new interfaces file: {len(new_intfs_sites)}")
		print(f"\t in old Summaries: {len(old_summarized_sites)}")
		print(f"\t in new Summaries: {len(new_summarized_sites)}")
		print(f"Resos missed from process = {dt_sites.difference(infra_assigned_sites).difference(self.blue_pop_reso_list)}")
		print("-"*80)
		#
		print(f"Info: Listed Devices in Database {len(set(self.clubbed_db_df.hostname))}")
		print(f"\t captures available: {len(clubbed_db_w)}")
		print(f"\t captures unavailable: {len(clubbed_db_wo)}")
		print(f"Info: Clean files: {len(clean_files)}")
		print(f"\t Devices found with {self.vrf} instance: {len(devices_with_vrf_int)}")
		print(f"\t Configuration Delta found for Devices: {len(config_files)}")
		print(f"Missing Configurations = {devices_with_vrf_int.difference(config_files)}")
		print("-"*80)
		#
		print(f"Info: Hardware Types {len(set(clubbed_db_w_vrf.model))}")
		for model in sorted(set(clubbed_db_w_vrf.model)):
			print(f"\t {model}:  {len(clubbed_db_w_vrf[(clubbed_db_w_vrf.model == model)].model)}")
		print("-"*80)
		#
		print(f"Info: Device Types {len(set(clubbed_db_w_vrf.dev_type))}")
		print(f"\t Device Type:\ttotal\tjuniper\tcisco")
		t, j, c = 0,0,0
		self.dtm = {}
		for dev_type in sorted(set(clubbed_db_w_vrf.dev_type)):
			self.dtm[dev_type] = {}
			total = len(clubbed_db_w_vrf[(clubbed_db_w_vrf.dev_type == dev_type)].dev_type)
			junipers = clubbed_db_w_juniper[(clubbed_db_w_juniper.dev_type == dev_type)].hostname
			ciscos = clubbed_db_w_cisco[(clubbed_db_w_cisco.dev_type == dev_type)].hostname
			self.dtm[dev_type]['juniper'] = list(junipers)
			self.dtm[dev_type]['cisco'] = list(ciscos)
			junipers = len(junipers)
			ciscos = len(ciscos)
			print(f"\t {dev_type}:\t\t\t{total}\t\t{junipers}\t\t{ciscos}")
			t += total
			j += junipers
			c += ciscos
		print(f"\t Total:\t\t\t{t}\t\t{j}\t\t{c}")
		print("-"*80)
		#
		# pprint(self.dtm)


	def verify_bgp_router_ids(self):
		config_files = set([file for file in os.listdir(self.output_folder) if file.endswith('.cfg')])
		rid_dict = {}
		rid_found_in_devices = set()
		all_devices = set()
		for file in config_files:
			hn = file.split(".")[0]
			all_devices.add(hn)
			with open(f"{self.output_folder}/{file}", 'r') as f:
				lns = f.readlines()
			for ln in lns:
				if (ln.startswith('  bgp router-id ') or 
					ln.startswith('set routing-instances acc.y1 routing-options router-id ')):
					rid = ln.strip().split()[-1]
					if not rid_dict.get(rid): rid_dict[rid] = set()
					rid_dict[rid].add(hn) 
					rid_found_in_devices.add(hn)
					break
		# pprint(f"Devices which are not configured with router-id are: {sorted(all_devices.difference(rid_found_in_devices))}")
		print(f"# {'='*95} #")
		print(f"# VERY IMPORTANT MESSAGE")
		print(f"# {'='*95} #")
		for rid, devices in rid_dict.items():
			if len(devices) == 1: continue
			print(f"WARN: Multiple devices found with same router-id: {rid} - {devices}")
		print(f"# {'='*95} #")


	def add_old_summary_to_new_summary_mappings(self):
		hostnames = set([file.split(".")[0] for file in os.listdir(self.output_folder) if file.endswith('.cfg')])
		mappings = {}
		for hn in hostnames:
			reso = hn.split("-")[0]
			mappings[reso] = {'new': set(), 'current': set()}
		for hn in hostnames:
			reso = hn.split("-")[0]
			# if reso != 'cny': continue
			conf_file = f"{self.output_folder}/{hn}.cfg"
			with open(conf_file, 'r') as f:
				conf_lns = f.readlines()
			new, current = get_acc_summaries(conf_lns)
			mappings[reso]['current'] = mappings[reso]['current'].union(current)
			mappings[reso]['new'] = mappings[reso]['new'].union(new)

		df = pd.DataFrame(mappings).fillna("").T
		df = df[['current', 'new']]
		df.to_excel(self.summary_map_file)

	def get_ua_nbrs(self):
		reso_ua_dict = {}
		for file in self.clean_files:
			reso = file.split("-")[0]
			if not reso_ua_dict.get(reso): reso_ua_dict[reso] = 0
			ph_df = pd.read_excel(f'{self.capture_folder}/{file}', sheet_name='physical').fillna("")
			vuas = len(ph_df['int_type'][(ph_df.int_type.str.lower() == 'vua')] )
			reso_ua_dict[reso] += vuas

		df = pd.read_excel(self.reso_to_device_types_map_file).fillna("")
		df['site_core'] = df.apply(lambda x: get_core_type(x.Reso, x.device_types, self.reso_with_different_core), axis=1)
		df['count_of_vua'] = df.Reso.apply(lambda x: get_vua_counts(x, reso_ua_dict))
		df['proposed_range'] = df.apply(lambda x: get_allocation(x.site_core, x.count_of_vua), axis=1)
		parent_cores = get_parent_core(df, self.reso_with_different_core)
		df['site_core'] = df.apply(lambda x: update_core_type(x, parent_cores), axis=1)

		df.to_excel(self.reso_to_device_types_map_file)


# =====================================================================================

def get_vua_counts(reso, reso_ua_dict):
	try:
		return reso_ua_dict[reso.lower()]
	except:
		return "Unavailable"

def get_parent_core(df, reso_with_different_core):
	parent_cores = {}
	for i, row in df.iterrows():
		if str(row.Reso).lower() not in reso_with_different_core.values(): continue
		for k, v in reso_with_different_core.items():
			if str(row.Reso).lower() == v:
				parent_cores[k] = row.site_core
				break
	return parent_cores

def update_core_type(df, parent_cores):
	if parent_cores.get(str(df.Reso).lower()):
		return parent_cores[str(df.Reso).lower()]
	return df.site_core

def get_core_type(reso, dt, reso_with_different_core):
	core_device_typs = ('vsc', 'ecd', 'end', 'eca')
	# if str(reso).lower() in reso_with_different_core:
	# 	return "later"
	for cdt in core_device_typs:
		if cdt in dt:
			return cdt
	return "Unavailable" 

def get_allocation(site_core, vua_count):
	if isinstance(vua_count, str) and (
		site_core == 'Unavailable' or vua_count == 'Unavailable'
		):
		return "Unavailable"
	alloc = {
		'eca': "/23", 
		'end': "/22" if vua_count < 7 else "/21",
		'ecd': "/20",
		'vsc': "/19",
		'Unavailable': "Unavailable",
	}
	return alloc[site_core]


def get_acc_summaries(conf_lst):
	add_summaries, del_summaries = set(), set()
	for ln in conf_lst:
		if ln.startswith('set routing-instances acc.y1 routing-options aggregate route '):
			add_summaries.add(ln.strip().split()[-1])
		elif ln.startswith("  aggregate-address "):
			spl_ln = ln.strip().split()					
			add_summaries.add(str(addressing(spl_ln[1], spl_ln[2])))
		#		
		elif ln.startswith('del routing-instances acc.y1 routing-options aggregate route '):
			del_summaries.add(ln.strip().split()[-1])
		elif ln.startswith("  no aggregate-address "):
			spl_ln = ln.strip().split()					
			del_summaries.add(str(addressing(spl_ln[2], spl_ln[3])))
	return (add_summaries, del_summaries)				
