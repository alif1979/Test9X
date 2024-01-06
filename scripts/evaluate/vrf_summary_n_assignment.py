
import os
import pandas as pd
from pprint import pprint
from nettoolkit.addressing import *
from .common.general import Initialize

# ===============================================================================================
# Support functions
# ===============================================================================================

def split_network(network):
	return network.split("/")[0].split(".")

def mask_network(network):
	return network.split("/")[-1]

def get_summary_region(region_subnets_dict):
	region_summaries_dict = {}
	for region, subnets in region_subnets_dict.items():
		print(f'Info:  -- Summarizing region {region}')
		region_summaries_dict[region] = get_summaries(*subnets)
	return region_summaries_dict

# ===============================================================================================
class SummaryNAssignments(Initialize):

	def __call__(self):
		self.read_prev_calc_summary_db()
		print(f"Info: ~~~ PREPARING FOR SUMMARY AND SORT  ~~~")
		self.read_db()
		self.set_defaults()
		#
		print(f"Info: ~~~ START : CALCULATING SUMMARY - {self.vrf}  ~~~")
		self.get_ndf()
		self.get_summary_df()
		self.summary_df_to_excel()
		print(f"Info: ~~~ COMPLETE : CALCULATING SUMMARY FOR VRF - {self.vrf}  ~~~")
		#
		print(f"Info: ~~~ START : SORTING SUBNETS FOR VRF - {self.vrf}  ~~~")
		self.get_sorted_assignments_df()
		self.sorted_assignments_to_excel()
		print(f"Info: ~~~ COMPLETE : SORTING SUBNETS FOR VRF - {self.vrf}  ~~~")
		#
		print(f"Info: ~~~ START : SUMMARY DISTRIBUTION ON REGION  ~~~")
		self.region_wise_summary_df()
		self.region_wise_summary_to_excel()
		print(f"Info: ~~~ COMPLETE : SUMMARY DISTRIBUTION ON REGION  ~~~\n")
		#
		print(f"Info: ~~~ DISPLAY SUMMARY  ~~~")
		self.current_used_second_octets()
		self.current_used_ips()

	def read_prev_calc_summary_db(self):
		try:
			print(f"Info: ~~~ Checking for any Summaries Pre-calculated ~~~")
			self.summary_df = pd.read_excel(self.summary_file_current).fillna("")
			print(f"Info: ~~~ Pre-calculated summary file Found, will be overwrite ~~~")
			return True
		except:
			print(f"Info: ~~~ No Pre-calculated summaries Found ~~~")
			return False

	def read_db(self):
		self.dfd = pd.read_excel(self.all_interfaces_file_current, sheet_name=None)
		self.clubbed_db_df = pd.read_excel(self.clubbed_db_file).fillna("")

	@property
	def min_summary_size(self):
		return self._min_summary_size

	@min_summary_size.setter
	def min_summary_size(self, n):
		self._min_summary_size = n

	def set_defaults(self):
		try:
			self.min_subnet_size = self.min_summary_size
			print(f"Info: ~~~ STATIC : MININUM SUBNET SIZE FOR - {self.vrf} - {self.min_subnet_size}  ~~~")
		except:
			raise Exception(f"Error: Unidentified VRF {self.vrf}, First set default minimum subnet size in SummaryNAssignments")

	def get_ndf(self):
		self.ndf = {}
		for k, v in self.dfd.items():
			self.dfd[k] = v.fillna("")
			self.ndf[k] = None
		#
		for k, v in self.dfd.items():
			if self.detailed_display: print(f"Info:  -- Preparing summary for {k}")
			summary_set = set()
			sumries = calc_summmaries(self.min_subnet_size, *v.subnets)
			for x in sumries:
				if x.startswith(self.exceptional_subnet): continue
				summary_set.add(x)
			self.ndf[k] = summary_set
		return self.ndf

	def get_summary_df(self):
		self.summary_df = pd.DataFrame.from_dict(self.ndf, orient='index').fillna("").T

	def summary_df_to_excel(self):
		self.summary_df.to_excel(self.summary_file_current, index=False)

	def get_sorted_assignments_df(self):
		self.sorted_df = pd.DataFrame.from_dict(self.ndf, orient='index').fillna("")
		nbs = {1:[], 2:[], 3:[], 4:[], 'network':[], 'reso':[]}
		for col in self.sorted_df.columns:
			for i, network in enumerate(self.sorted_df[col]):
				if not network: continue
				sn = split_network(network)
				if not sn: continue
				nbs['network'].append(network)
				nbs['reso'].append(self.sorted_df.index[i])
				for _ in range(1,5):
					nbs[_].append(sn[_-1])
		#
		self.sorted_df = pd.DataFrame(nbs)
		for x in range(1, 5):
			self.sorted_df[x] = pd.to_numeric(self.sorted_df[x], errors='coerce')
		self.sorted_df.sort_values([1,2,3,4], inplace=True, ascending=True)
		self.sorted_df.drop([1,2,3,4], axis=1, inplace=True)

	def sorted_assignments_to_excel(self):
		self.sorted_df.to_excel(self.sorted_interfaces_file_current, index=False)

	# ===============================================================================================

	def region_wise_summary_df(self):
		self.clubbed_db_df = self.clubbed_db_df[ (self.clubbed_db_df.Remark == '') ]
		regions = set(self.clubbed_db_df.region)
		region_dict = {r:self.clubbed_db_df[(self.clubbed_db_df.region == r)] for r in regions}
		countries = set(self.clubbed_db_df.country)
		# country_dict = {c:self.clubbed_db_df[(self.clubbed_db_df.country == c)] for c in countries}
		regeion_reso_dict = { region: set(region_df.reso) for region, region_df in region_dict.items() }
		region_subnets_dict = self.get_region_subnets_dict(regeion_reso_dict)
		summary_region = get_summary_region(region_subnets_dict)
		self.summary_region_wise_df = pd.DataFrame(
			dict([(key, pd.Series(value)) for key, value in summary_region.items()])
		).fillna("")
		self.summary_region_wise_df = self.summary_region_wise_df[['ap','emea','la','am']]

	def get_region_subnets_dict(self, regeion_reso_dict):
		region_subnets_dict = {}
		for region, resos in regeion_reso_dict.items():
			region_subnets_dict[region] = set()
			for reso in resos:
				try:
					sdfset = set(self.summary_df[reso])
				except: 
					if not self.reso_with_different_core.keys():
						print(f"WARN: Missing reso in {self.vrf} summary file - {reso}")
					sdfset = set()
				region_subnets_dict[region] = region_subnets_dict[region].union(sdfset)
		#
		for region, subnets in region_subnets_dict.items():
			region_subnets_dict[region] = LST.remove_empty_members(subnets)
		return region_subnets_dict


	def region_wise_summary_to_excel(self):
		self.summary_region_wise_df.to_excel(self.region_wise_summary_file_current)

	# ===============================================================================================

	def current_used_second_octets(self):
		used_second_octets = set()
		for col in self.summary_region_wise_df.columns:
			for subnet in self.summary_region_wise_df[col]:
				if not subnet: continue
				used_second_octets.add(ipv4_octets(subnet)['octets'][1])
		suso = sorted(used_second_octets)
		print(f'Current used second octets :\n{suso}')
		return suso

	def current_used_ips(self):
		print(f'Current used scope :')
		for col in self.summary_region_wise_df.columns:
			ips = 0
			for subnet in self.summary_region_wise_df[col]:
				if not subnet: continue
				mask = subnet.split("/")[-1]    
				ips += 2**(32-int(mask))
			print(f'{col} - {ips}')

	# ===============================================================================================
