
import pandas as pd
from nettoolkit.nettoolkit_db import *
from .common.general import Initialize

# ===============================================================================================
# Support functions
# ===============================================================================================

def get_subnets(df, vrf):
	try:
		v = list(df[df.intvrf==vrf]['int_number'])
		s = list(df[df.intvrf==vrf]['subnet'])
		return {_v: _s for _v,_s in zip(v, s)}
	except:
		pass

def get_subnets_status(df, vrf):
	try:
		v = list(df[df.intvrf==vrf]['int_number'])
		s = list(df[df.intvrf==vrf]['link_status'])
		return {_v: _s for _v,_s in zip(v, s)}
	except:
		pass

def get_df_dict(df_dict, reso):
	if reso in df_dict:
		d = df_dict[reso]
	else:
		d = {'interface': [], 'subnets':[], 'device':[], 'interface_type':[], 'status':[]}
	return d

def update_x_nets(hn, x_net, df_dict, reso, skip_b, what, x_stats):
	for v, subnet in x_net.items():
		if skip_b and v in df_dict['interface']: continue
		if not subnet: continue
		df_dict['interface_type'].append(what)
		df_dict['interface'].append(v)
		df_dict['subnets'].append(subnet)
		df_dict['device'].append(hn)
		status = 'up' if x_stats[v] not in ('disabled', 'administratively down') else 'down'
		df_dict['status'].append(status)
	return df_dict

def merge_dicts(d1, d2):
	for reso, vd in d1.items():
		for k, v in vd.items():
			try:
				v.extend(d2[reso][k])
			except KeyError:
				pass
	return d1



# ===============================================================================================
class VrfInterfaces(Initialize):

	def __call__(self):
		self.read_prev_calc_summary_db()
		print(f"Info: ~~~ START : COLLECTING {self.vrf} INSTANCE INTERFACES DATA ~~~")
		self.read_dbs()
		self.merge_intf_dicts()
		self.convert_to_df()
		self.to_excel()
		print(f"Info: ~~~ COMPLETE : COLLECTING {self.vrf} INSTANCE INTERFACES DATA ~~~\n")

	def read_prev_calc_summary_db(self):
		try:
			print(f"Info: ~~~ Checking for a Previous Interface files ~~~")
			self.df_dict_loaded = pd.read_excel(self.all_interfaces_file_current, sheet_name=None)
			print(f"Info: ~~~ An existing interface file found, it will be overwrited ~~~")
			return True
		except:
			print(f"Info: ~~~ No existing interface file Found ~~~")
			return False

	def read_dbs(self):
		if len(self.clean_files) == 0:
			print(f'Critical: ~~~ Excel clean files not found, Please capture log and provide clean files first ~~~')
			quit()
		df = pd.read_excel(self.clubbed_db_file).fillna('')
		self.valid_hosts = list(sorted(df[(df.Remark == '')].hostname))
		self.df_dict_vlans = self.get_df_dict_frames(skip_b=False, what='vlan')
		self.df_dict_lpbks = self.get_df_dict_frames(skip_b=False, what='loopback')
		self.df_dict_physc = self.get_df_dict_frames(skip_b=False, what='physical')

	def merge_intf_dicts(self):
		print(f"Info: ~~~ START : MERGING INTERFACES (vlans, physicals, loopbacks) ~~~")
		self.df_dict = merge_dicts(self.df_dict_vlans, self.df_dict_lpbks)
		self.df_dict = merge_dicts(self.df_dict, self.df_dict_physc)
		print(f"Info: ~~~ COMPLETE : MERGING INTERFACES (vlans, physicals, loopbacks) ~~~")

	def convert_to_df(self):
		print(f"Info: ~~~ START : CONVERT TO DF OBJECT ~~~")
		for reso, vls in self.df_dict.items():
			self.df_dict[reso] = pd.DataFrame(vls)
		print(f"Info: ~~~ COMPLETE : CONVERT TO DF OBJECT ~~~")

	def to_excel(self):
		print(f"Info: ~~~ START : WRITING OUT ~~~")
		write_to_xl(self.all_interfaces_file_current, self.df_dict, index=False, overwrite=True, index_label="")
		print(f"Info: ~~~ COMPLETE : WRITING OUT ~~~")


	def get_df_dict_frames(self, skip_b, what):
		df_dict_item = {}
		for file in self.clean_files:
			if self.detailed_display: print(f"Info:      WORKING ON {file}")
			hn = file.split('-clean')[0]
			reso = hn.split("-")[0].lower()
			if hn not in self.valid_hosts: 
				print("           -- Not listed in database, skipped")
				continue
			#
			file = f"{self.capture_folder}/{file}"
			df = pd.read_excel(file, sheet_name=what).fillna("")
			_nets = get_subnets(df, self.vrf)
			_stats = get_subnets_status(df, self.vrf)
			if not _nets:
				continue
			vd = get_df_dict(df_dict_item, reso)
			vd = update_x_nets(hn, _nets, vd, reso, skip_b, what, _stats)
			df_dict_item[reso] = vd
		return df_dict_item


# ===============================================================================================
