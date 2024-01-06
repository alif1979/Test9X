
# --------------------------------------------
# IMPORTS
# --------------------------------------------
from pathlib import *
import sys, os
import pandas as pd
import json
from collections import OrderedDict
from pprint import pprint
from nettoolkit.pyJuniper import *
from nettoolkit.addressing import *

from .ccheck import *
from .jcheck import *

# # --------------------------------------------
# # path / folder settings
# # --------------------------------------------
# p = Path(".")
# previous_path = p.resolve().parents[0]
# sys.path.insert(len(sys.path), str(previous_path))
# capture_folder = str(previous_path.joinpath('captures'))
# jinja_folder = str(previous_path.joinpath('jtemplates'))
# output_folder = str(previous_path.joinpath('outputs'))

# --------------------------------------------
# ------------------------------------------------------------------------------------------------------------
# SUPPORT FUNCTIONS ( ST~ING OPERATIONS )
# ------------------------------------------------------------------------------------------------------------
def get_remchar(devtype):
	if devtype == 'cisco_ios': return "!"
	return "#"

def header_what(what, remchar, headchar="*"):
	s = f"\n{remchar} {headchar*30} {remchar}\n"
	s += f"{remchar} {' '*40}[  {what}  ]{' '*65} {remchar}\n"
	s += f"{remchar} {headchar*30} {remchar}\n"
	return s

def header_dtype(what, remchar):
	s = f"{remchar}\n"
	s += f"{remchar} {' '*30} [ {what} ]\n"
	s += f"{remchar}\n"
	return s

def delta_interfaces(dic, dickey, what, remchar):
	s = ''
	s += header_dtype(what, remchar)
	for itype, ints in dic[dickey].items():
		for _int, config_list in ints.items():
			if config_list:
				s += "\n".join( config_list )
				s += "\n"
	return s

def delta_other(dic, dickey, what, remchar):
	s = ''
	if  dic[dickey]:
		s += f"{remchar} \n"
		s += f"{remchar} {' '*30}[ {what} ] \n"
		s += f"{remchar} \n"
		s += "\n".join( dic[dickey] )
		s += "\n"
	return s

def get_delta(dev, dev_dict, head_dict, func_dict, what, symbl):
	s = ""
	for device, dic in dev_dict.items():
		if device.lower() != dev.lower(): continue
		remchar = get_remchar(dic['dev_type'])
		s += header_what(what, remchar, symbl)
		#
		for key, w in head_dict.items(): 
			s += func_dict[key](dic, key, w, remchar)
		#
		s += f"{remchar}\n{remchar}\n"
		s += f"{remchar} {symbl*30} {remchar}\n\n\n"
	return s


# ------------------------------------------------------------------------------------------------------------
# RDD Class ( REPLACE DEVICE DATABASE )
# ------------------------------------------------------------------------------------------------------------
class RDD():

	def __init__(self, 
		capture_folder, 
		file, 
		summary_file, new_summary_file, 
		reso, 
		vrf,
		infra_summ_json,
		static_next_hop_file,
		):
		self.capture_folder = capture_folder
		self.file = file
		self.summary_file = summary_file
		self.new_summary_file = new_summary_file
		self.reso = reso
		self.vrf = vrf
		self.infra_summ_json = infra_summ_json
		self.static_next_hop_file = static_next_hop_file

	def __call__(self):

		self.readers_digest()
		self.add_details_to_digest()
		#
		self.exec_interfaces()
		self.exec_bgp()
		self.exec_statics()
		self.exec_top_lvl_agg()

	# ---------------------------------------------------------------------------------------------------- #

	def readers_digest(self):
		self.read_db()
		self.devices = self.get_devices()
		self.dev_dict = self.get_device_dict()
		self.get_infra_summary_lists()

	def add_details_to_digest(self):
		self.add_device_log_list_to_dev_dict()
		self.add_all_config_list_to_dev_dict()
		self.get_device_types()
		self.get_check_object()
		self.get_device_func_type()

	# ---------------------------------------------------------------------------------------------------- #

	def read_db(self):
		self.df = pd.read_excel(self.file, sheet_name=self.reso).fillna("")
		self.summary_fd = pd.read_excel(self.summary_file).fillna("")[self.reso]
		self.new_summary_fd = pd.read_excel(self.new_summary_file).fillna("")[self.reso]
		self.remove_beacon_interfaces()
		self.static_nh_df = pd.read_excel(self.static_next_hop_file).fillna("")

	def remove_beacon_interfaces(self):
		minidf = self.df[ ((self.df.interface == 219) & (self.df.interface_type == 'loopback') ) ]
		self.df.drop(list(minidf.index), axis=0, inplace=True)

	def get_devices(self):
		devices = set(self.df.device)
		for device in devices:
			if device.endswith('a') and f"{device[:-1]}b" not in devices:
				if device[-3:].lower() in ('eca', 'end'): continue						## single leg device
				if device.find('-vwb-hp') > 1 or  device.find('-vwb-hr') > 1: continue  ## vwb devices
				print(f"WARN: b device missing for {device}")
		return devices

	def get_device_dict(self):
		dev_dict = {}
		for device in self.devices:
			dev_df = self.df[self.df.device == device]
			if dev_df.empty:
				print(f"Error: No DataFrame found for device {device}")
				dev_dict[device] = {'dev_df': pd.DataFrame()}
				continue
			dev_df.drop('device', axis=1, inplace=True)
			# dev_df = dev_df.dropna()
			dev_dict[device] = {'dev_df': dev_df}
		return dev_dict

	def get_infra_summary_lists(self):
		self.old_infra_summaries = []
		self.new_infra_summaries = []
		for old, new in self.infra_summ_json.items():
			self.old_infra_summaries.append(old)
			self.new_infra_summaries.append(new)

	# ---------------------------------------------------------------------------------------------------- #

	def add_device_log_list_to_dev_dict(self):
		for device, dic in self.dev_dict.items():
			file = f'{self.capture_folder}/{device}.log'
			clean_file = f'{self.capture_folder}/{device}-clean.xlsx'
			try:
				with open(file, 'r') as f:
					lns = f.readlines()
				dic['fullloglist'] = lns 	
				dic['capture_file'] = file
				dic['clean_df'] = pd.read_excel(clean_file, sheet_name=None)
				dic['clean_df'] = { k:v.fillna("") for k, v in dic['clean_df'].items()}
				dic['cur_template'] = self.get_template(dic['clean_df']['var'])
			except FileNotFoundError:
				print(f"Error: No Capture Log found {file}")

	def add_all_config_list_to_dev_dict(self):
		for device, dic in self.dev_dict.items():
			dic['config_list'] = self.get_config_list(device)

	def get_config_list(self, device):
		try:
			fullloglist = self.dev_dict[device]['fullloglist']
		except KeyError as e:
			print(f"No capture list found for device {device} - {e}")
			return []
		config_start = False
		config_list = []
		for line in fullloglist:
			if config_start and line[1:].startswith(' output for command: '):
				break
			if not config_start and (
				line[1:].startswith(' output for command: show configuration')
				or line[1:].startswith(' output for command: show run')
				):
				config_start = True
				continue
			if not config_start: continue
			config_list.append(line)
		return config_list

	def get_device_types(self):
		for device, dic in self.dev_dict.items():
			dtype = ''
			if dic.get('fullloglist'):
				for line in dic['fullloglist']:
					if line.startswith("#"):
						dtype = 'juniper_junos'
						break
					elif line.startswith("!"):
						dtype = 'cisco_ios'
						break
			dic['dev_type'] = dtype

	def get_check_object(self):
		for device, dic in self.dev_dict.items():
			if dic['dev_type'] == 'juniper_junos':
				setconfig = convert_to_set_from_captures(conf_file=dic['capture_file'])
				dic['config'] = setconfig
				dic['dev_chk'] = JuniperChk(dic['config'], dic['clean_df'])
			elif dic['dev_type'] == 'cisco_ios':
				dic['config'] = dic['config_list']
				dic['dev_chk'] = CiscoChk(dic['config'], dic['clean_df'])
			else:
				dic['config'] = []
				dic['dev_chk'] = None

	def get_device_func_type(self):
		for device, dic in self.dev_dict.items():
			dic['dev_func_type'] = dic['capture_file'].split("/")[-1].split('-')[1].split(".")[0]

	def get_template(self, df):
		minidf = df[(df['var']=='banner')]
		return minidf['default'][minidf.index[0]]



	# ---------------------------------------------------------------------------------------------------- #

	def exec_interfaces(self):
		self.get_device_interfaces()
		self.get_int_configs()
		self.update_int_configs()
		self.update_int_configs_removals()


	def get_device_interfaces(self):
		for device, dic in self.dev_dict.items():
			df = dic['dev_df']
			itypes = set(df.interface_type)
			dic['interfaces'] = {}
			for itype in itypes:
				intfs = list(df[df.interface_type == itype]['interface'])
				dic['interfaces'][itype] = intfs

	def get_int_configs(self):
		for device, dic in self.dev_dict.items():
			intfs = dic['interfaces']
			dic['interfaces_config'] = {}
			dicic = dic['interfaces_config']
			for itype, ints in intfs.items():
				dicic[itype] = {}
				dicicit = dicic[itype]
				for _int in ints:
					if dic['dev_chk'] is not None:
						dicicit[_int] = dic['dev_chk'].get_cur_interface_conf(_int, itype)

	def update_int_configs_removals(self):
		for device, dic in self.dev_dict.items():
			intfs = dic['interfaces']
			dic['del_interfaces_config'] = {}
			dicic = dic['del_interfaces_config']
			for itype, ints in intfs.items():
				dicic[itype] = {}
				dicicit = dicic[itype]
				for _int in ints:
					if dic['dev_chk'] is not None:
						dicicit[_int] = dic['dev_chk'].get_del_interface_conf(_int, itype)

	def update_int_configs(self):
		i_type_seq = ('loopback', 'physical', 'vlan')
		for device, dic in self.dev_dict.items():
			dev_df = dic['dev_df']
			intfs = dic['interfaces']
			dic['proposed_interfaces_config'] = {}
			dicic = dic['proposed_interfaces_config']
			old_dicic = dic['interfaces_config']
			#
			for i_type in i_type_seq:
				for itype, ints in intfs.items():
					if itype != i_type: continue
					dicic[itype] = {}
					dicicit = dicic[itype]
					old_dicicit = old_dicic[itype]
					for _int in ints:
						if dic['dev_chk'] is not None:
							row_series = dev_df[(dev_df.interface_type == itype) & (dev_df.interface == _int)]
							subnets = row_series.subnets
							old_subnet = subnets[subnets.index[0]]
							new_subnets = row_series.new_subnets
							new_subnet = new_subnets[new_subnets.index[0]]
							dicicit[_int] = dic['dev_chk'].get_proposed_interface_conf(old_subnet, new_subnet, old_dicicit[_int])

	# ---------------------------------------------------------------------------------------------------- #

	def exec_bgp(self):
		self.add_device_bgp_lists_to_dev_dict()
		self.get_device_bgp_config_removals()
		self.get_device_bgp_config_additions()

	def add_device_bgp_lists_to_dev_dict(self):
		for device, dic in self.dev_dict.items():
			dtype = device.split('-')
			file = f'{self.capture_folder}/{device}.log'
			dic['bgp_campus_as'] = dic['dev_chk'].get_bgp_as()
			dic['af_lines'] = dic['dev_chk'].address_family_lines(self.vrf)
			dic['bgp_router_id'] = dic['dev_chk'].get_bgp_router_id(dic['af_lines'])
			dic['existing_aggregates'] = dic['dev_chk'].get_existing_aggregates(dic['af_lines'])
			dic['existing_nbr_lines_list'], dic['peer_group_nbrs'], dic['se_acc_nbrs'] = dic['dev_chk'].get_peer_group_nbrs(dic['af_lines'])

	def get_device_bgp_config_removals(self):
		for device, dic in self.dev_dict.items():
			dtype = device.split('-')
			if dic['dev_chk'] is not None:
				dic['del_bgp_config_list'] = dic['dev_chk'].get_del_bgp_config_list(dic, self.vrf)

	def get_device_bgp_config_additions(self):
		for device, dic in self.dev_dict.items():
			dtype = device.split('-')
			dev_df = dic['dev_df']
			if dic['dev_chk'] is not None:
				# ----------------------- aggregation only on core --------------------------------
				if dic['dev_func_type'].lower() in ('vsc', 'ecd', 'end', 'eca'):
					dic['new_agg_lines_list'] = dic['dev_chk'].update_bgp_agg_list(self.vrf, self.new_summary_fd)
				else:
					dic['new_agg_lines_list'] = []
				
				# ----------------------- rest of bgp config ------------------------
				old_summaries = self.old_infra_summaries
				new_summaries = self.new_infra_summaries
				dic['new_nbr_lines_list'] = dic['dev_chk'].update_bgp_cofig_list(dic['existing_nbr_lines_list'], self.vrf, old_summaries, new_summaries)
				dic['new_bgp_router_id'] = dic['dev_chk'].update_bgp_router_id_new(dic['bgp_router_id'], old_summaries, new_summaries)
				dic['proposed_bgp_config'] = dic['dev_chk'].get_add_bgp_config_list(dic, self.vrf)			


	# ---------------------------------------------------------------------------------------------------- #

	def exec_statics(self):
		for device, dic in self.dev_dict.items():
			dtype = device.split('-')
			file = f'{self.capture_folder}/{device}.log'
			old_subnets = dic['dev_df'].subnets
			new_subnets = dic['dev_df'].new_subnets
			old_supernets = self.old_infra_summaries
			new_supernets = self.new_infra_summaries
			#
			dic['current_static_9'] = dic['dev_chk'].get_static_routes_accy1_begin9()
			dic['del_static_9_list'] = dic['dev_chk'].get_static_routes_accy1_begin9_del(dic['current_static_9'])
			dic['add_static_9_list'] = dic['dev_chk'].get_static_routes_accy1_begin9_add(dic['current_static_9'], dic['peer_group_nbrs'], old_subnets, new_subnets, old_supernets, new_supernets)
			#
			filtered_static_df = self.static_nh_df[(self.static_nh_df.hostname == device)]
			dic['del_next_hop_changed'] = dic['dev_chk'].get_next_hop_changed_routes_del(filtered_static_df)
			dic['add_next_hop_changed'] = dic['dev_chk'].get_next_hop_changed_routes_add(filtered_static_df)

	# ---------------------------------------------------------------------------------------------------- #

	def exec_top_lvl_agg(self):
		for device, dic in self.dev_dict.items():
			file = f'{self.capture_folder}/{device}.log'
			dic['current_pl_top_lvl_agg'] = dic['dev_chk'].get_pl_top_lvl_agg_accy1_begin9()
			dic['del_pl_top_lvl_agg_list'] = dic['dev_chk'].get_pl_top_lvl_agg_accy1_begin9_del(dic['current_pl_top_lvl_agg'])
			dic['add_pl_top_lvl_agg_list'] = dic['dev_chk'].get_pl_top_lvl_agg_accy1_begin9_add(dic['current_pl_top_lvl_agg'])


	# ---------------------------------------------------------------------------------------------------- #


	def add_delta(self, dev):
		what, symbl = 'ADDITIONS', "++++"
		head_dict = OrderedDict([
			('proposed_interfaces_config', f'INTERFACE DELTA - {what}'),
			('proposed_bgp_config', f'BGP DELTA - {what}'),
			('add_static_9_list', f'STATIC ROUTES DELTA - {what}'),
			('add_next_hop_changed', f'STATIC - NEXT HOPS XOVER - {what}'),
			('add_pl_top_lvl_agg_list', f'PL TOP LVL AGG DELTA - {what}'),
		])
		func_dict = OrderedDict([
			('proposed_interfaces_config', delta_interfaces),
			('proposed_bgp_config', delta_other),
			('add_static_9_list', delta_other),
			('add_next_hop_changed', delta_other),
			('add_pl_top_lvl_agg_list', delta_other),
		])
		#
		return get_delta(dev, self.dev_dict, head_dict, func_dict, what, symbl)


	def del_delta(self, dev):
		what, symbl = 'DELETIONS', "----"
		head_dict = OrderedDict([
			('del_interfaces_config', f'INTERFACE DELTA - {what}'),
			('del_bgp_config_list', f'BGP DELTA - {what}'),
			('del_static_9_list', f'STATIC ROUTES DELTA - {what}'),
			('del_next_hop_changed', f'STATIC - NEXT HOPS XOVER - {what}'),
			('del_pl_top_lvl_agg_list', f'PL TOP LVL AGG DELTA - {what}'),
		])
		func_dict = OrderedDict([
			('del_interfaces_config', delta_interfaces),
			('del_bgp_config_list', delta_other),
			('del_static_9_list', delta_other),
			('del_next_hop_changed', delta_other),
			('del_pl_top_lvl_agg_list', delta_other),
		])
		return get_delta(dev, self.dev_dict, head_dict, func_dict, what, symbl)

	def banner(self, dev):
		return f'\n{" "*10}{self.dev_dict[dev.lower()]["cur_template"]}\n'

	# ---------------------------------------------------------------------------------------------------- #


# --------------------------------------------------------------------------------------------------------- #
