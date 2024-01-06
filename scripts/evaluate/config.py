
import json
import pandas as pd
from pprint import pprint
from nettoolkit.pyJuniper import *
from nettoolkit.addressing import *
from .common.general import Initialize

from .acc_delta_gen.clean import RDD

# =====================================================================================

class DeltaGen(Initialize):


	def __call__(self):
		print(f"Info: ~~~ START: DELTA CONFIG GENERATION  ~~~")
		self.read_dbs()
		print(f"Info: ~~~ DATA READY ~~~")


	def read_dbs(self):
		try:
			with open(self.json_infra_file, 'r') as f:
				self.infra_summ_json = json.load(f)
		except:
			print(f"Critical: ~~~ Missing Infra Summary json file, please provide ~~~")
			quit()
		self.old_summary_file_df = pd.read_excel(self.summary_file_current).fillna("")
		self.new_summary_file_df = pd.read_excel(self.summary_file_new).fillna("")
		self.new_intf_file_df = pd.read_excel(self.all_interfaces_file_new, sheet_name=None)

	def start_delta_preparations(self, reso):
		if self.detailed_display: print(f"  -- Working on Reso {reso},")
		rdd = RDD(self.capture_folder, 
			self.all_interfaces_file_new, 
			self.summary_file_current, 
			self.summary_file_new, 
			reso, 
			self.vrf, 
			self.infra_summ_json[reso],
			self.static_route_changes_file,
		)
		rdd()
		for k, v in rdd.dev_dict.items():
			self.to_cfg(k, rdd)

	def delta_generation(self, reso=None):
		if not reso:
			for reso in self.new_intf_file_df.keys():
				self.start_delta_preparations(reso)
		elif isinstance(reso, str):
			self.start_delta_preparations(reso)
		elif isinstance(reso, (list, set, tuple)):
			for _reso in reso:
				self.start_delta_preparations(_reso)
		print(f"Info: ~~~ COMPLETE: DELTA CONFIG GENERATION ~~~\n")


	def to_cfg(self, k, rdd):

		with open(f'{self.output_folder}/{k}.cfg', 'w') as f:
			f.write(rdd.banner(k))

		with open(f'{self.output_folder}/{k}.cfg', 'a') as f:
			f.write(rdd.del_delta(k))

		with open(f'{self.output_folder}/{k}.cfg', 'a') as f:
			f.write(rdd.add_delta(k))
