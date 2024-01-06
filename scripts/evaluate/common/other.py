
import pandas as pd
import os
from pprint import pprint
import json

# ------------------------------------------------------------------------
def update_missing_country_regions(df, capture_folder, clubbed_db_file):
	df['Remark'] = df.ip.apply(lambda x: "")
	for i, row in df.iterrows():
		if row.Remark: continue
		if row.region and row.country: continue
		#
		cl_file = f'{capture_folder}/{row.hostname}-clean.xlsx'
		try:
			clf_df = pd.read_excel(cl_file, sheet_name='var').fillna("")
		except:
			print(f"WARN: capture file unavailable for {row.hostname}")
		clf_df_reg = clf_df[clf_df['var'] == 'region']
		clf_df_cnt = clf_df[clf_df['var'] == 'country']
		region = clf_df_reg['default'][clf_df_reg.index[0]].lower()
		country = clf_df_cnt['default'][clf_df_cnt.index[0]].lower()
		#
		if not row.region:   df.at[i, 'region' ] = region
		if not row.country:  df.at[i, 'country'] = country
		#
	df.to_excel(clubbed_db_file)

# ------------------------------------------------------------------------
def update_make_model(df, capture_folder, clubbed_db_file):
	df['Remark'] = df.ip.apply(lambda x: "")
	for i, row in df.iterrows():
		if row.Remark: continue
		#
		cl_file = f'{capture_folder}/{row.hostname}-clean.xlsx'
		try:
			clf_df = pd.read_excel(cl_file, sheet_name='var').fillna("")
		except:
			print(f"WARN: capture file unavailable for {row.hostname}")
		clf_df_model = clf_df[clf_df['var'] == 'model']
		model = clf_df_model['default'][clf_df_model.index[0]].lower()
		#
		if not row.model:   df.at[i, 'model' ] = model
		#
	df.to_excel(clubbed_db_file)

# ------------------------------------------------------------------------
def missing_capture_hosts(df, capture_folder, clean_files_hn):
	not_available = []
	for i, row in df.iterrows():
		if row.Remark != '' : continue
		if row.hostname not in clean_files_hn:
			not_available.append(row.hostname)
	return not_available

def update_unavailable_devices(df, capture_folder, clubbed_db_file, clean_files_hn):
	missing_captures = missing_capture_hosts(df, capture_folder, clean_files_hn)
	for i, row in df.iterrows():
		if row.Remark: continue
		if row.hostname in missing_captures:
			df.at[i, 'Remark'] = "Capture-Not-Available"
	df.to_excel(clubbed_db_file)


# ------------------------------------------------------------------------------
#  Split Blue Pop devices from campus devices
# ------------------------------------------------------------------------------

def split_bpop_db(clubbed_db_file, bpop_db_file, blue_pop_reso_list):
	print(f"Info: Splitting the devices bluepop v/s campus.")
	df = pd.read_excel(clubbed_db_file).fillna('')
	bpop_df = df[df.reso.isin(blue_pop_reso_list)]
	campus_df = df[~df.reso.isin(blue_pop_reso_list)]
	bpop_df.to_excel(bpop_db_file, index=False)
	campus_df.to_excel(clubbed_db_file, index=False)


# ------------------------------------------------------------------------------
# optional verification function
# ------------------------------------------------------------------------------

def get_all_neighbors(capture_folder, excluded_nbr_types, clean_files):
	all_nbrs = {}
	for file in clean_files:
		reso = file.split("-")[0].lower()
		df = pd.read_excel(f'{capture_folder}/{file}', sheet_name='physical').fillna('')
		for ex_nbr_type in excluded_nbr_types: 
			df.drop(df[(df.nbr_dev_type.str.upper() == ex_nbr_type)].index, axis=0, inplace=True)
		if df.empty:
			continue
		nbr_host_names = set(df.nbr_hostname)
		if not all_nbrs.get(reso):
			all_nbrs[reso] = set()
		all_nbrs[reso] = all_nbrs[reso].union(nbr_host_names)
	return all_nbrs

def missing_neighbor_captures(all_nbrs, excluded_nbr_types, clean_files_hn):
	file_missing_nbrs = {}
	for reso, nbrs in all_nbrs.items():
		for nbr in nbrs:
			if not nbr: continue
			if nbr.lower() in clean_files_hn: continue
			if nbr.find("-") > 1 :
				if nbr.split("-")[1].lower() == reso: continue               # P9 SD wan Router
				if nbr.split("-")[1].upper() in excluded_nbr_types: continue # excluded neighbors list
			else:
				continue
			if not file_missing_nbrs.get(reso):
				file_missing_nbrs[reso] = set()
			file_missing_nbrs[reso].add(nbr)
	print("#"*80)
	print("# Missing Captures for below devices (verify and recapture)")
	print("#"*80)
	pprint(file_missing_nbrs)
	print("#"*80)
	return file_missing_nbrs

# ------------------------------------------------------------------------------

# def get_device_types_dict(clubbed_db_file, to_file=None):
# 	df = pd.read_excel(clubbed_db_file).fillna('')
# 	df = df[(df.Remark == '')]
# 	device_types_dict = {}
# 	resos = set(df['reso'])
# 	for reso in resos:
# 		device_types_dict[reso] = sorted(set(df[(df['reso'] == reso)]['dev_type']))
# 	if not to_file:
# 		print("#"*80)
# 		print("# Reso: Device-Types")
# 		print("#"*80)
# 		pprint(device_types_dict)
# 		print("#"*80)
# 	else:
# 		with open(to_file, 'w') as f:
# 			json.dump(device_types_dict, f, indent=2)
# 	return device_types_dict

# # ------------------------------------------------------------------------------
