import pandas as pd
import os


def getreso(reso, sites):
	if sites.get(str(reso).lower()):

		sr = sites[str(reso).lower()]		
		del sites[str(reso).lower()]
		return sr
	else:
		return ""

def get_sites_dict(files):
	sites = {}
	for file in files:
		spl = file.split("-")
		reso = spl[0].lower()
		dt = spl[1].lower()
		if not sites.get(reso):
			sites[reso] = set()
		sites[reso].add(dt)
	return sites

def create_reso_to_device_types_map_file(reso_list_file, capture_folder, reso_to_device_types_map_file):
	df = pd.read_excel(reso_list_file).fillna("") 
	files = [file for file in os.listdir(capture_folder) if file.endswith(".xlsx")]
	sites = get_sites_dict(files)
	df['device_types'] = df.Reso.apply(lambda x: getreso(x, sites) )
	df.to_excel(reso_to_device_types_map_file)
