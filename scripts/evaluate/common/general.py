
import pandas as pd
import json
from pprint import pprint

# ------------------------------------------------------------------------

class Initialize():

	def __init__(self, **kwargs):
		for k, v in kwargs.items():
			self.__dict__[k] = v


# ------------------------------------------------------------------------
class Database():

	def reso_list_values_to_lower(obj):
		obj.reso_df = pd.read_excel(obj.all_reso_file).fillna("")
		obj.reso_df = obj.reso_df[ ['RESO ID','Country', ] ]
		obj.reso_df['RESO ID'] = obj.reso_df['RESO ID'].apply(lambda x: str(x).lower())
		obj.reso_df['Country'] = obj.reso_df['Country'].apply(lambda x: str(x).lower())

		obj.reso_lady_df = pd.read_excel(obj.reso_list_file).fillna("")
		obj.reso_lady_df['Region'] = obj.reso_lady_df['Region'].apply(lambda x: x.lower())
		obj.reso_lady_df['Reso'] = obj.reso_lady_df['Reso'].apply(lambda x: str(x).lower())

	def get_region_reso_lady_df(obj, reso):
		try:
			minidf = obj.reso_lady_df[(obj.reso_lady_df['Reso'] == reso)]
			return minidf['Region'][minidf.index[0]]
		except:
			return ""

	def get_country_reso_df(obj, reso):
		try:
			minidf = obj.reso_df[(obj.reso_df['RESO ID'] == reso)]
			return minidf['Country'][minidf.index[0]]
		except:
			return ""

	def add_to_dict(self, hn, ip, activity):
		hn = hn.lower()
		hnspl = hn.split("-")
		if len(hnspl) > 1:
			reso = hnspl[0]
			dt = hnspl[1]
		else:
			print(f"Info: {activity} Data filter, skipped host - {hn}")
			return None
		#
		if dt not in self.device_typs: return None
		if not self.reso_dict.get(reso): self.reso_dict[reso] = {}
		if not self.reso_dict[reso].get(dt): self.reso_dict[reso][dt] = {'ips':[], 'hostnames':[]}
		self.reso_dict[reso][dt]['ips'].append(ip)
		self.reso_dict[reso][dt]['hostnames'].append(hn)
		self.list_of_ips.append(ip)
		#
		region = self.get_region_reso_lady_df(reso)
		country = self.get_country_reso_df(reso)
		self.d['hostname'].append(hn) 
		self.d['reso'].append(reso)
		self.d['ip'].append(ip)
		self.d['dev_type'].append(dt)
		self.d['region'].append(region)
		self.d['country'].append(country)

	def to_excel(self, file):
		self.df = pd.DataFrame(self.d).fillna("")
		self.df.to_excel(file, index=False)

# ------------------------------------------------------------------------


class ClubDB(Initialize, Database):

	d = { 'region':[], 'country':[], 'reso':[], 'hostname':[], 'dev_type':[], 'ip':[], 'model':[]}

	def __call__(self):
		print(f"Info: ~~~ START :  DATABASE CLUBBING ~~~")
		self.read_filtered_dbs()
		self.club_db()
		self.to_excel(self.clubbed_db_file)
		print(f"Info: ~~~ COMPLETE :  DATABASE CLUBBING ~~~\n")

	def read_filtered_dbs(self):
		self.df1 = pd.read_excel(self.gps_db_filtered_file).fillna("")
		self.df2 = pd.read_excel(self.nb_db_filtered_file).fillna("")
		self.df3 = pd.read_excel(self.poller_db_filtered_file).fillna("")

	def club_db(self):
		for df in (self.df1, self.df2, self.df3):
			for i,  v in df.iterrows():
				if v.hostname in self.d['hostname']:
					hn_idx = self.d['hostname'].index(v.hostname)
					if not self.d['region'][hn_idx] and v.region:
						self.d['region'][hn_idx] = v.region
					if not self.d['country'][hn_idx] and v.country:
						self.d['country'][hn_idx] = v.country
					continue
				self.d['region'].append(v.region)
				self.d['country'].append(v.country)
				self.d['reso'].append(v.reso)
				self.d['dev_type'].append(v.dev_type)
				self.d['hostname'].append(v.hostname)
				self.d['ip'].append(v.ip)
				self.d['model'].append('')

	def get_device_types_dict(self, on_screen=False):
		self.get_ua_nbrs()
		df = pd.read_excel(self.clubbed_db_file).fillna('')
		df = df[(df.Remark == '')]
		device_types_dict = {}
		resos = set(df['reso'])
		for reso in resos:
			device_types_dict[reso] = {'device_types': sorted(set(df[(df['reso'] == reso)]['dev_type']))}
			device_types_dict[reso]['core_type'] = get_core_type(device_types_dict[reso]['device_types'])
			device_types_dict[reso]['count_of_vua'] = self.get_vua_counts(reso)
			device_types_dict[reso]['fixed_std_proposed_range'] = get_allocation(device_types_dict[reso]['core_type'], device_types_dict[reso]['count_of_vua'])

		for p, c in self.reso_with_different_core.items():
			device_types_dict[p]['core_type'] = device_types_dict[c]['core_type']
			device_types_dict[p]['fixed_std_proposed_range'] = get_allocation(device_types_dict[p]['core_type'], device_types_dict[p]['count_of_vua'])

		if on_screen:
			print("#"*80)
			print("# Reso: Device-Types")
			print("#"*80)
			pprint(device_types_dict)
			print("#"*80)
		else:
			with open(self.device_types_json_file, 'w') as f:
				json.dump(device_types_dict, f, indent=2)
			#
			self.dt_df = pd.DataFrame.from_dict(device_types_dict).fillna("").T
			self.dt_df.reset_index(inplace=True)
			self.dt_df = self.dt_df.rename(columns = {'index':'reso'})
			self.add_on_proposed_size()
			self.dt_df.to_excel(self.reso_to_device_types_map_file, index=True)


	def add_on_proposed_size(self):
		self.summary_file_df_new = pd.read_excel(self.summary_file_new).fillna('')
		self.dt_df['proposed_range_per_subnet_count'] = self.dt_df.reso.apply(lambda x: self.get_prp_range_per_subnet(x))
		self.dt_df['is_waste'] = (self.dt_df['proposed_range_per_subnet_count'] > self.dt_df['fixed_std_proposed_range'])
		self.dt_df['is_less'] = (self.dt_df['proposed_range_per_subnet_count'] < self.dt_df['fixed_std_proposed_range'])

	def get_prp_range_per_subnet(self, reso):
		try:
			return int(self.summary_file_df_new[reso][0].split('/')[-1])
		except:
			if reso in self.reso_with_different_core:
				if self.summary_file_df_new[self.reso_with_different_core[reso]][1]:
					return int(self.summary_file_df_new[self.reso_with_different_core[reso]][1].split('/')[-1])
			return 0

	def get_ua_nbrs(self):
		self.reso_ua_dict = {}
		for file in self.clean_files:
			reso = file.split("-")[0]
			if not self.reso_ua_dict.get(reso): self.reso_ua_dict[reso] = 0
			ph_df = pd.read_excel(f'{self.capture_folder}/{file}', sheet_name='physical').fillna("")
			vuas = len(ph_df['int_type'][(ph_df.int_type.str.lower() == 'vua')] )
			self.reso_ua_dict[reso] += vuas

	def get_vua_counts(self, reso):
		try:
			return self.reso_ua_dict[reso]
		except:
			return ""

# ---------------------------------------------------------------------------------------------------

def get_core_type(lst):
	core_device_typs = ('vsc', 'ecd', 'end', 'eca')
	for x in core_device_typs:
		if x in lst:
			return x
	return "" 

def get_allocation(site_core, vua_count):
	if isinstance(vua_count, str) and (
		site_core == '' or vua_count == ''
		):
		return ""
	alloc = {
		'eca': 23, 
		'end': 22 if vua_count < 7 else 21,
		'ecd': 20,
		'vsc': 19,
		'': "",
	}
	return alloc[site_core]

