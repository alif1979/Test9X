
import os
from pprint import pprint
import pandas as pd
from nettoolkit.nettoolkit_common import LST
from nettoolkit.addressing import *
from collections import OrderedDict
from .common.general import Initialize


# ===============================================================================================
# Support functions
# ===============================================================================================

def print_subnet_distribution_summary(region_wise_size_wise_reso_dict):
	sqrs = [ 2**x for x in range(18)]
	for region, size_wise_reso_dict in region_wise_size_wise_reso_dict.items():
		print("-"*80)
		print(region)
		print("-"*80)
		for k in reversed(sorted(size_wise_reso_dict.keys())):
			if k in sqrs:
				print(f'{k} ip count is matched,', 
					f'subnet counts = {size_wise_reso_dict[k]["len"]},', 
					f'subnet sizes = {subnet_size_to_mask(k)},',  
					f'Resos = {size_wise_reso_dict[k]["resos"]}')
			else:
				for s in sqrs:
					if s > k:
						print(f'{k} nearest ip count {s},', 
							f'subnet counts = {size_wise_reso_dict[k]["len"]},', 
							f'subnet sizes = {subnet_size_to_mask(s)},',  
							f'Resos = {size_wise_reso_dict[k]["resos"]}')
						break

def get_updated_subnet_distribution_summary(region_wise_size_wise_reso_dict):
	updated_subnet_distribution_summary = {}
	sqrs = [ 2**x for x in range(18)]
	for region, size_wise_reso_dict in region_wise_size_wise_reso_dict.items():
		updated_subnet_distribution_summary[region] = {}
		for k in reversed(sorted(size_wise_reso_dict.keys())):
			if k in sqrs:
				if not updated_subnet_distribution_summary[region].get(k):
					updated_subnet_distribution_summary[region][k] = {'len': 0 }
				if not updated_subnet_distribution_summary[region][k].get('resos'):
					updated_subnet_distribution_summary[region][k]['resos'] = set()
				updated_subnet_distribution_summary[region][k]['resos'] = updated_subnet_distribution_summary[region][k]['resos'].union(size_wise_reso_dict[k]['resos'])
				updated_subnet_distribution_summary[region][k]['len'] += size_wise_reso_dict[k]['len']
			else:
				for s in sqrs:
					if s > k:
						if not updated_subnet_distribution_summary[region].get(s):
							updated_subnet_distribution_summary[region][s] = {'len': 0, 'resos': set() }
						updated_subnet_distribution_summary[region][s]['resos'] = updated_subnet_distribution_summary[region][s]['resos'].union(size_wise_reso_dict[k]['resos'])
						updated_subnet_distribution_summary[region][s]['len'] += size_wise_reso_dict[k]['len']
						break
	return updated_subnet_distribution_summary

# ===============================================================================================

class PrivateSupernet(Initialize):

	def __call__(self):
		if self.read_prev_allocation_db():
			quit()
		else:
			print(f"Info: ~~~ PREPARING FOR PRIVATE SUPERNETS ~~~")
			self.read_dbs()
			print(f"START: ~~~ ASSIGNING SUPERNETS TO REGIONS ~~~")
			self.assign_supernets_by_region()
			print(f"COMPLETE: ~~~ ASSIGNING SUPERNETS TO REGIONS ~~~")
			print(f"Info: ~~~ CONVERTING TO DF ~~~")
			self.convert_assignment_dict_to_df()
			print(f"Info: ~~~ WRITING OUT TO EXCEL ~~~")
			self.to_excel()
			print(f"Info: ~~~ TASKS COMPLETE - PRIVATE SUPERNETS PREPARATION ~~~\n")

	@property
	def breakup(self):
		return self._breakup

	@breakup.setter
	def breakup(self, d):
		self._breakup = d

	def read_prev_allocation_db(self):
		try:
			print(f"Info: ~~~ Checking for any Pre-Allocations ~~~")
			self.assignments_dict_df_load = pd.read_excel(self.summary_file_new).fillna("")
			print(f"Info: ~~~ Pre-Allocations Found, cannot overwrite ~~~")
			return True
		except:
			print(f"Info: ~~~ No Pre-Allocations Found ~~~")
			return False

	def read_dbs(self):
		self.summary_file_df = pd.read_excel(self.summary_file_current).fillna("")
		self.clubbed_db_filtered_df = pd.read_excel(self.clubbed_db_file).fillna("")
		self.clubbed_db_filtered_df = self.clubbed_db_filtered_df[(self.clubbed_db_filtered_df['Remark'] == '')]

	def assign_supernets_by_region(self):
		region_wise_size_wise_reso_dict = self.get_region_wise_size_wise_reso_dict()
		updated_subnet_distribution_summary = get_updated_subnet_distribution_summary(region_wise_size_wise_reso_dict)

		self.assignments_dict = {}
		self.allocation_orders = OrderedDict()
		for region, size_wise_dict in updated_subnet_distribution_summary.items():
			self.allocation_orders[region] = []
			regional_allocation_seq = self.allocation_orders[region]
			if self.detailed_display: print(f"  -- Allocating Region {region}")
			base_ip = self.breakup[region]
			A = Allocate(size_wise_dict, base_ip, what_list_dict_key='resos')
			A.start()
			for k, v in A.assignments.items():
				regional_allocation_seq.append(k)
				self.assignments_dict[k] = [v,]

	def convert_assignment_dict_to_df(self):
		self.assignments_dict_df = pd.DataFrame(dict([(key, pd.Series(value)) for key, value in self.assignments_dict.items()])).fillna("")

	def to_excel(self):
		self.assignments_dict_df.to_excel(self.summary_file_new, index=False)

	def get_region_wise_size_wise_reso_dict(self):
		regions = [x for x in set(self.clubbed_db_filtered_df['region']) if x]
		region_wise_resos_dict = { region: self.get_region_wise_resos(region) for region in regions}
		return {region: self.get_size_wise_reso_dict(resos) for region, resos in region_wise_resos_dict.items()}

	def get_region_wise_resos(self, region):
		if not region: return None
		return set(self.clubbed_db_filtered_df[(self.clubbed_db_filtered_df['region'] == region)]['reso'])

	def get_size_wise_reso_dict(self, resos):
		size_wise_reso_dict = {}
		for col in self.summary_file_df:
			if col.startswith('Unnamed'): continue
			if col not in resos: continue
			requires = sort_by_size(self.summary_file_df[col])
			require_size = 0
			for ip in self.summary_file_df[col]:
				if not ip: continue
				require_size += IPv4(ip).size
			if not size_wise_reso_dict.get(require_size):
				size_wise_reso_dict[require_size] = {'resos': set()}
			size_wise_reso_dict[require_size]['resos'].add(col)
		for s, v in size_wise_reso_dict.items():  v['len'] = len(v['resos'])
		return size_wise_reso_dict

	def club_for_different_core_uplinks(self):
		df = pd.read_excel(self.summary_file_new).fillna('')
		d = df.to_dict()
		for dl, ul in self.reso_with_different_core.items():
			if dl not in df.columns: continue
			for k, v in d[dl].items():
				d[ul][max(d[ul].keys()) + 1] = v
		#
		df = pd.DataFrame(d).fillna("")
		df.to_excel(self.summary_file_new, index=False)

	# ===============================================================================================
