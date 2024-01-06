# --------------------------------------------
# IMPORTS
# --------------------------------------------
from pprint import pprint
from pathlib import *
import sys, os
import pandas as pd
pd.set_option('mode.chained_assignment', None)                               ## disable pandas warning msgs
#
from evaluate import *
# from evaluate.reso_directory import create_reso_to_device_types_map_file
# from evaluate.filter_gps_data import GpsDB
# from evaluate.filter_nb_data import NetbrainDB
# from evaluate.filter_poller_data import PollerDB
# from evaluate.common.general import Initialize, ClubDB
# from evaluate.common.other import update_missing_country_regions, update_unavailable_devices, update_make_model
# from evaluate.common.other import missing_neighbor_captures, get_all_neighbors, get_device_types_dict
# from evaluate.common.other import split_bpop_db
# from evaluate.vrf_intf import VrfInterfaces
# from evaluate.vrf_summary_n_assignment import SummaryNAssignments
# from evaluate.private_supernet import PrivateSupernet
# from evaluate.private_subnet import PrivateSubnet
# from evaluate.static_next import StaticNexthop
# from evaluate.config import DeltaGen
# from evaluate.dsrt import DSRT
# from evaluate.sdwan_se import EdgeRouter
# from evaluate.verify import Verify

# --------------------------------------------
#  INPUTS
# --------------------------------------------
vrf = 'acc.y1'                                                                ## vrf name
BEACON_SUBNET = '9.0.64.'                                                     ## to exclude interfaces with this
device_typs = {                                                               ## only consider these
  'eca', 'end', 'ecd', 'vsc', 'vid', 'vwd', 'vwb', 'vod', 'vdd', 'vea', 'vsd'
}
excluded_nbr_types = (                                                         ## exclude all these
  "", 'AP', 'VPB', 'VPR',  'SPA', 'NM', 'WLC', 'VUA', 'VSA', 'VIA', 'VDA', 
  'VBA', 'WC', 'VG', 'PA', 'VPA', 'BC', 'TS', 'SC', 'CD', 'VOA', 'EOA'
)
min_summary_size = 25                                                          ## /25 minimum advertisement
#
breakup = {                                                                    ## Pvt block assignment per region
	'ap':   '172.24.0.0',    # 24, 25, 26                                      ## only first block to mention
	'emea': '172.22.0.0',    # 22, 23,
	'la':   '172.21.0.0',    # 21
	'am':   '172.18.0.0',    # 18, 19, 20
}
#
sitetype_mask_map = {                                                          ## infra subnet type size mask
	'vsc': 25,
	'ecd': 25,
	'end': 27,
	'eca': 27, 
	"": 27,             # default /27 for undetected
}
blue_pop_reso_list = ('l3m', 'l3p', 'l3o', 'k5o', 'l8v', 'l3q', 'l3n', 'ie7', 'ie5', 'f1t')
#
# -- reso which are uplinked to other reso core devices.
reso_with_different_core = {
	'tuc': 'plt',
	'aus': 'bnt',
	'plr': 'rch',
	'rpl': 'rtp',  # no acc.y1
	'sjs': 'svl',  # no acc.y1
	'mdc': 'chq',
}


# --------------------------------------------
# path / folders
# --------------------------------------------
p = Path(".")
previous_path = p.resolve().parents[0]
sys.path.insert(len(sys.path), str(previous_path))
capture_folder = str(previous_path.joinpath('captures'))
database_folder = str(previous_path.joinpath('databases'))
vrf_folder = str(previous_path.joinpath(vrf))
vrf_input_db = str(previous_path.joinpath(vrf).joinpath('1.input_dbs'))
vrf_clubbed_db = str(previous_path.joinpath(vrf).joinpath('2.clubbed_dbs'))
vrf_other_db = str(previous_path.joinpath(vrf).joinpath('3.databases'))
vrf_other_folder = str(previous_path.joinpath(vrf).joinpath('4.others'))
vrf_other_cfg = str(previous_path.joinpath(vrf).joinpath('5.configs'))
output_folder = str(previous_path.joinpath(vrf).joinpath('6.delta_cfgs'))

# ----------------------------------
# create missing output folders
# ----------------------------------
new_folders = (vrf_folder, 
	vrf_input_db, vrf_clubbed_db, vrf_other_db, vrf_other_folder,  vrf_other_cfg, output_folder
)
for folder in new_folders:
	if not os.path.exists(folder):
		print("Creating:", folder)
		os.makedirs(folder)
print("="*80)

# --------------------------------------------
# files (input/output)
# --------------------------------------------
#
# databases
all_reso_file                    = f'{database_folder}/all_reso_directory.xls'
reso_list_file                   = f'{database_folder}/resolist_poornima.xlsx'
gps_db_input_file                = f'{database_folder}/GPS_Enhanced_Search_Results.xlsx'
nb_db_input_file                 = f'{database_folder}/NB_Device_Report.xlsx'
poller_db_input_file             = f'{database_folder}/all_hosts_poller.txt'
#
gps_db_filtered_file             = f'{vrf_input_db}/gps_db.xlsx'
nb_db_filtered_file              = f'{vrf_input_db}/netbrain_db.xlsx'
poller_db_filtered_file          = f'{vrf_input_db}/poller_db.xlsx'
#
clubbed_db_file                  = f'{vrf_clubbed_db}/campus_devices_db.xlsx'
bpop_db_file                     = f'{vrf_clubbed_db}/bpop_devices_db.xlsx'
#
all_interfaces_file_current      = f'{vrf_other_db}/{vrf}_Reso_wise_subnets_current.xlsx'
all_interfaces_file_new          = f'{vrf_other_db}/{vrf}_Reso_wise_subnets_new.xlsx'
summary_file_current             = f'{vrf_other_db}/{vrf}_Reso_wise_summaries_current.xlsx'
summary_file_new                 = f'{vrf_other_db}/{vrf}_Reso_wise_summaries_new.xlsx'
region_wise_summary_file_current = f'{vrf_other_db}/{vrf}_Region_wise_summaries_current.xlsx'
summary_map_file                 = f'{vrf_other_db}/{vrf}_Reso_wise_summaries_map.xlsx'
#
sorted_interfaces_file_current   = f'{vrf_other_folder}/{vrf}_sorted_intfs_current.xlsx'
reso_to_device_types_map_file    = f'{vrf_other_folder}/{vrf}_reso_to_device_types_map.xlsx'
device_types_json_file           = f'{vrf_other_folder}/{vrf}_reso_to_device_types_map.json'
json_infra_file                  = f'{vrf_other_folder}/{vrf}_infra_summaries_new.json'
static_route_changes_file        = f'{vrf_other_folder}/{vrf}_static_route_changes.xlsx'
#
dsrt_subnet_dhcp_request_file    = f'{vrf_other_cfg}/{vrf}_Infoblox_update_DSRT_sheet.xlsx'
sdwan_router_changes_file        = f'{vrf_other_cfg}/{vrf}_SDWAN_EDGE_Router_change_sheet.xlsx'

# --------------------------------------------
#  global variables
# --------------------------------------------
clean_files =  [file.lower() for file in os.listdir(capture_folder) if file.endswith("-clean.xlsx")]
clean_files_hn =  [file.split("-clean")[0].lower() for file in clean_files]
dic = {
	#
	'vrf': vrf,
	#
	'capture_folder': capture_folder,
	'output_folder': output_folder,
	'vrf_folder': vrf_folder,
	#
	'all_reso_file': all_reso_file,
	'reso_list_file': reso_list_file,
	'gps_db_input_file': gps_db_input_file,
	'nb_db_input_file': nb_db_input_file,
	'poller_db_input_file': poller_db_input_file,
	#
	'gps_db_filtered_file': gps_db_filtered_file,
	'nb_db_filtered_file': nb_db_filtered_file,
	'poller_db_filtered_file': poller_db_filtered_file,	
	'clubbed_db_file': clubbed_db_file,    ## campus db
	'bpop_db_file': bpop_db_file,
	#
	'all_interfaces_file_current': all_interfaces_file_current,
	'all_interfaces_file_new': all_interfaces_file_new,
	'summary_file_current': summary_file_current,
	'summary_file_new': summary_file_new,
	'summary_map_file': summary_map_file,
	'sorted_interfaces_file_current': sorted_interfaces_file_current,
	'region_wise_summary_file_current': region_wise_summary_file_current,
	'static_route_changes_file': static_route_changes_file,
	'json_infra_file': json_infra_file,
	'dsrt_subnet_dhcp_request_file': dsrt_subnet_dhcp_request_file,
	'sdwan_router_changes_file': sdwan_router_changes_file,
	#
	'clean_files': clean_files,
	'clean_files_hn': clean_files_hn,
	#
	'reso_to_device_types_map_file': reso_to_device_types_map_file, 
	'device_typs': device_typs,
	'device_types_json_file': device_types_json_file,
	#
	'exceptional_subnet': BEACON_SUBNET,
	'reso_with_different_core': reso_with_different_core,
	'blue_pop_reso_list': blue_pop_reso_list,
	#
	'detailed_display': True,                                   # True: for More detailed display
}


# ================================================================================
#  Database/ inventory
# ================================================================================
class Inventory(Initialize):

	def start_database_prep(self):
		create_reso_to_device_types_map_file(self.reso_list_file, self.capture_folder, self.reso_to_device_types_map_file)

		## Gather All 3 Databases		
		GpsDB(**dic)()
		NetbrainDB(**dic)()
		PollerDB(**dic)()

		## Put them together in a single DB
		self.CLUB = ClubDB(**dic)
		self.CLUB()
		update_missing_country_regions(self.CLUB.df, capture_folder, clubbed_db_file)
		update_make_model(self.CLUB.df, capture_folder, clubbed_db_file)
		update_unavailable_devices(self.CLUB.df, capture_folder, clubbed_db_file, self.clean_files_hn)
		# self.CLUB.get_device_types_dict()
		# get_device_types_dict(clubbed_db_file, to_file=device_types_json_file)

		# ## split out bpop devices
		split_bpop_db(clubbed_db_file, bpop_db_file, blue_pop_reso_list)



# ================================================================================
#  Data Evaluation
# ================================================================================
class Evaluate(Initialize):

	# --------------- ADDRESSING ------------------
	def start_subnetting(self):

		# vrf interfaces and subnets
		VrfInterfaces(**dic)()

		## current summary and assignments
		SumNAss = SummaryNAssignments(**dic)
		SumNAss.min_summary_size = min_summary_size
		SumNAss()

		## private supernet allocations
		PvtSuper = PrivateSupernet(**dic)
		PvtSuper.breakup = breakup
		PvtSuper()

		# ## private subnet allocations
		PrvSub = PrivateSubnet(**dic)
		PrvSub.sitetype_mask_map = sitetype_mask_map
		PrvSub()

		## club private supernet for reso, which are uplinked to other reso core devices.
		PvtSuper.club_for_different_core_uplinks()

	# --------------- STATIC ------------------
	## capture acc.y1 next-hop static route 
	def static_route_add(self):
		StaticNexthop(**dic)()

		
# ================================================================================



# ================================================================================
#  Main 
# ================================================================================
if __name__ == "__main__":
	pass

	####### DATABASE PREP ######## 
	Inv = Inventory(**dic)
	Inv.start_database_prep()

	######## EVALUATE ########
	Eve = Evaluate(**dic)
	Eve.start_subnetting()
	Eve.static_route_add()

	######## DELTA CONFIG PREP ########
	DCG = DeltaGen(**dic)
	DCG()
	DCG.delta_generation()  					# reso='d4t'; single = str , multi = list , all (reso=None)


	######## DSRT - INFOBLOX UPDATE SHEET PREP ########
	DSRT(**dic)()

	######## SDWAN EDGE WAN ROUTERS CHANGE SHEET PREP ########
	EdgeRouter(**dic)()

	######## VERIFICATION & REPORT ########
	Verify(**dic)()

	Inv.CLUB.get_device_types_dict()

	# ================================================================================

	



	

	# # ======================================================================================================== 
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~
	#  Other Visual summaries
	# ~~~~~~~~~~~~~~~~~~~~~~~~~~

	# ======================================================================================================== 
	## Missing Capture Verifications ##
	# missing_neighbor_captures( 
	# 	get_all_neighbors(capture_folder, excluded_nbr_types, clean_files), excluded_nbr_types, clean_files_hn 
	# )
	# ======================================================================================================== 

	# # ======================================================================================================== 
	# ## Device types dictionary ##
	# get_device_types_dict(
	# 	clubbed_db_file,
	# )
	# # ======================================================================================================== 
	# # ======================================================================================================== 
