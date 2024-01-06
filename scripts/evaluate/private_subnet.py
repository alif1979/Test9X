
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

def get_size_wise_subnets(df, reso):
	size_wise_subnets = {}
	for subnet, intf in zip(df['subnets'], df['interface']):
		size = IPv4(subnet).size
		if not size_wise_subnets.get(size):
			size_wise_subnets[size] = {'subnets':[], 'intf':[],}
		size_wise_subnets[size]['subnets'].append(subnet)
		size_wise_subnets[size]['intf'].append(intf)
	return size_wise_subnets


def get_old_infra_summary(reso, old_summary_file_df, list_of_infra, infra_size):
	l = set()
	summaries = [x for x in old_summary_file_df[reso] if x]
	for infra in list_of_infra:
		for summary in summaries:
			if isSubset(infra, summary):
				smr = IPv4(infra)
				smr = IPv4(recapsulate(smr, infra_size))
				l.add(str(smr))
				break
	return l

def get_sb_dict(size_wise_reso_subnets, infra_size):
	sb_dict = {'intf':[], 'infra':[]}
	for k, v in size_wise_reso_subnets.items():
		try:
			int(infra_size)
		except:
			infra_size = 28
		if k <= 2**(32-infra_size):
			intf_type = 'infra'
		else:
			intf_type = 'intf'
		sb_dict[intf_type].extend(v['subnets'])
	return sb_dict

def list_to_dict_on_size(lst):
	subnet_size = {}
	for intf in lst:
		v4intf = IPv4(intf)
		size = v4intf.size
		if not subnet_size.get(size):
			subnet_size[size] = {'subnet':[] }
		subnet_size[size]['subnet'].append(intf)
	return subnet_size

def get_infra_assignment_dict(reso, assignments_dict):
	infra = assignments_dict['infra']
	assignments = assignments_dict['assignments']
	#
	infra_dict = {}
	for s in infra:
		for old, new in assignments.items():
			if not isSubset(s, old): continue
			s_ip = IPv4(s)
			sip = IPv4(s_ip+0+"/"+str(IPv4(old).mask))
			infra_dict[s] = IPv4(new)[sip.ip_number]+"/"+str(s_ip.mask)
			break
	return infra_dict

# ====================================================================================================


# ===============================================================================================

class PrivateSubnet(Initialize):

	def __call__(self):
		print(f"Info: ~~~ PREPARING FOR PRIVATE SUBNETS ~~~")
		self.read_dbs()
		print(f"START: ~~~ ASSIGNING SUBNETS TO RESOS ~~~")
		self.get_n_write_new_interface_subnet_details()
		print(f"Info: ~~~ WRITING OUT TO EXCEL ~~~")
		self.to_excel()
		print(f"Info: ~~~ WRITING OUT INFRA SUMMARY TO JSON ~~~")
		self.infra_summary_to_json()
		print(f"Info: ~~~ TASKS COMPLETE - PRIVATE SUBNETS PREPARATION ~~~\n")

	@property
	def sitetype_mask_map(self):
		return self._sitetype_mask_map

	@sitetype_mask_map.setter
	def sitetype_mask_map(self, d):
		self._sitetype_mask_map = d

	def read_dbs(self):
		self.clubbed_db_filtered_df = pd.read_excel(self.clubbed_db_file).fillna("")
		self.clubbed_db_filtered_df = self.clubbed_db_filtered_df[(self.clubbed_db_filtered_df['Remark'] == '')]
		self.old_summary_file_df = pd.read_excel(self.summary_file_current).fillna("")
		self.new_summary_file_df = pd.read_excel(self.summary_file_new).fillna("")
		self.old_intf_file_df = pd.read_excel(self.all_interfaces_file_current, sheet_name=None)
		self.old_intf_file_df = {k:v.fillna('') for k, v in self.old_intf_file_df.items()}
		self.new_intf_file_df = deepcopy(self.old_intf_file_df)

	def get_n_write_new_interface_subnet_details(self):
		# -----------------------------------------------------------------------
		size_wise_all_reso_subnets = self.get_size_wise_all_reso_subnets()
		new_summary_all_reso = self.get_new_summary_all_reso()
		self.infra_summaries = {}
		# -----------------------------------------------------------------------
		for reso in self.old_intf_file_df.keys():
			if self.detailed_display: print(f"  -- Allocating Reso {reso},")
			ad = self.get_assignment_dict(reso, size_wise_all_reso_subnets, new_summary_all_reso)
			iad = get_infra_assignment_dict(reso, ad)
			self.infra_summaries[reso] = { s: ad['assignments'][s] for s in ad['infra_summary'] }
			for x in ad['infra_summary']:
				del(ad['assignments'][x])
			ad['assignments'].update(iad)
			#
			self.new_intf_file_df[reso]['new_subnets'] =  self.new_intf_file_df[reso]['subnets'].apply(lambda x: self.get_assignment(x, ad) )

	def to_excel(self):
		# # -- write if_new.xlsx file.
		write_to_xl(self.all_interfaces_file_new, self.new_intf_file_df, index=False, overwrite=True)

	def infra_summary_to_json(self):
		# # -- write infra summary json  file.
		with open(self.json_infra_file, 'w') as f:
			json.dump(self.infra_summaries, f, indent=2)

	def get_size_wise_all_reso_subnets(self):
		return {reso: get_size_wise_subnets(df, reso) for reso, df in self.old_intf_file_df.items()}

	def get_new_summary_all_reso(self):
		return { reso:self.get_new_summary(reso) for reso in self.new_summary_file_df.columns }

	def get_assignment(self, x, ad):
		if x.startswith(self.exceptional_subnet): return x
		return ad['assignments'][x]

	def get_assignment_dict(self, reso, size_wise_all_reso_subnets, new_summary_all_reso):
		size_wise_reso_subnets = size_wise_all_reso_subnets[reso]
		new_summary = new_summary_all_reso[reso]
		infra_size = self.get_infra_size(reso)
		sb_dict = get_sb_dict(size_wise_reso_subnets, infra_size)
		set_of_infra_summary = get_old_infra_summary(reso, self.old_summary_file_df, sb_dict['infra'], infra_size)
		list_of_intfs = sorted_v4_addresses(set(sb_dict['intf']), ascending=True)
		infra_subnet_size = list_to_dict_on_size(set_of_infra_summary)
		intf_subnet_size = list_to_dict_on_size(list_of_intfs)
		base_ip=IPv4(new_summary[0]).net
		A = Allocate(infra_subnet_size, base_ip, what_list_dict_key='subnet')
		A.start()
		A.size_wise_dict = intf_subnet_size
		A.rearrange_size()
		A.start()
		return {'assignments': A.assignments, 'infra_summary': set_of_infra_summary, 'infra':sb_dict['infra'] }

	def get_infra_size(self, reso):

		df = self.clubbed_db_filtered_df[(self.clubbed_db_filtered_df['reso'] == reso)]
		devices = set(df.dev_type)
		dts = self.sitetype_mask_map.keys()      # ('vsc', 'ecd', 'end', 'eca')
		for dt in dts:
			if not dt: continue
			if dt in devices:
				return self.sitetype_mask_map[dt]
		print(f'WARN: site type not found for reso {reso}')
		return ""

	def get_new_summary(self, reso):
		base_subnets = self.new_summary_file_df[reso]
		return [x for x in base_subnets if x]


# ====================================================================================================



