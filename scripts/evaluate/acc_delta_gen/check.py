
import pandas as pd
import json
from nettoolkit.addressing import *

class ChkCommon():

	def __init__(self, config_list, clean_df_dict):
		self.config_list = config_list
		self.clean_df_dict = clean_df_dict

	# get corresponding `new ip` address with/without mask. if old ip is in old_subnet. (old_subnet: is a singular entry)
	# None else.
	def get_new_ip(self, old_ip, old_subnet, new_subnet, withmask=False):
		try:
			try:
				_v4 = IPv4(old_ip)
			except:
				_v4 = addressing(old_ip)
			oldv4 = addressing(old_subnet)
			if not isSubset(_v4, oldv4): return None
			schema_v4 = IPv4(f'{_v4.net}/{oldv4.mask}')
			ip_n = schema_v4.ip_number
			#
			newv4 = addressing(new_subnet)
			new_ip = newv4.n_thIP(ip_n, withMask=withmask)
			return new_ip
		except:
			return None

	# get corresponding `new ip` address with/without mask. if `s` ip is in any of old subnets (old: list of subnets)
	# None else.
	def check_n_get_old_new_ip(self, s, old, new, withmask=False):
		for o, n in zip(old, new):
			if o and n and isSubset(s, o):
				return self.get_new_ip(s.net, o, n, withmask)
		return None

	# get corresponding `new subnet` address with/without mask. if subnet `s` is in any of old subnet(s) (old: singular or list of subnets)
	# None else.
	def check_n_get_old_new_network(self, s, old, new, withmask=True):
		if not isinstance(old, (list, set, tuple, pd.Series)):
			old, new = [old, ], [new, ]
		for o, n in zip(old, new):
			try:
				_o = IPv4(o)
			except:
				_o = addressing(o)
			try:
				_s = IPv4(s)
			except:
				_s = addressing(s)

			if isSubset(_s, _o):
				return self.get_new_ip(s, o, n, withmask)
		return None

	# get corresponding `new supernet` summary address with/without mask. if subnet `s` exactly matches with old subnet (old: singular entry)
	# None else.
	def check_n_get_old_new_for_exact_match(self, spl, old, new, make, withmask=True):
		replace, new_line = False, ''
		for i, item in enumerate(spl):
			try:
				if make == 'cisco':
					s = addressing(item, spl[i+1])
				elif make == 'juniper':
					s = addressing(item)
			except:
				continue
			new_item = self.check_n_get_old_new_for_exact_match_network(s, old, new)
			# new_item = new if str(s) == str(old) else None
			if new_item:
				new_item = IPv4(new_item) 				
				replace = True
				if make == 'cisco':
					spl[i], spl[i+1] = new_item.net, new_item.binmask
					break
				elif make == 'juniper':
					spl[i] = str(new_item)
					break
		if replace:
			new_line = " ".join(spl)
			if make == 'cisco': new_line = new_line 
		if new_line: return new_line
		return None

	def check_n_get_old_new_for_exact_match_network(self, s, old, new):
		if isinstance(old, str): 
			old, new = [old, ], [new, ]
		for o, n in zip(old, new):
			if not o or not n: continue
			if str(s) == str(o):
				return n
		return None

	def check_n_get_new_summaries(self, vrf, new, make):
		new_lines = []
		if isinstance(new, str):
			if not new: return []
			new = IPv4(new) 
			if make == 'cisco':
				net, net_mask = new.net, new.binmask
				new_lines.append(f'  aggregate-address {net} {net_mask} summary-only attribute-map rm_site_summary_{vrf}')
			elif make == 'juniper':
				new_lines.append(f'set routing-instances {vrf} routing-options aggregate route {new}')
		elif isinstance(new, (pd.core.series.Series, list, set, tuple)):
			for n in new:
				new_lines.extend(self.check_n_get_new_summaries(vrf, n, make))
		#
		return new_lines


	# supportive  : updated line for input (splitted line - spl) - singular subnets
	def get_new_line(self, spl, joinby, old_subnet, new_subnet, withmask):
		for i, item in enumerate(spl):
			new_ip = self.get_new_ip(item, old_subnet, str(new_subnet), withmask=withmask)
			if new_ip:
				spl[i] = new_ip
		return joinby.join(spl)


	# supportive  : updated line for input (splitted line - spl) - list of subnets
	def get_new_line_for_subnets(self, spl, joinby, old_subnets, new_subnets, withmask):
		for i, item in enumerate(spl):
			for old_subnet, new_subnet in zip(old_subnets, new_subnets):
				if not old_subnet or not new_subnet: continue
				new_ip = self.get_new_ip(item, old_subnet, new_subnet, withmask=withmask)
				if new_ip:
					spl[i] = new_ip
					break
		return joinby.join(spl)

	# supportive  : updated line for input (splitted line - spl) - singular subnets
	def get_static_route_for_nbr(self, spl, joinby, old_subnet, new_subnet, withmask, nbrs, hostmask):
		came = False
		for i, item in enumerate(spl):
			if item.split("/")[0] not in nbrs: 
				came = True
				continue
			new_ip = self.get_new_ip(item, old_subnet, str(new_subnet), withmask=withmask)
			if new_ip and hostmask is True and not new_ip.endswith('/32'):
				new_ip = new_ip + "/32" 
			if new_ip:
				spl[i] = new_ip
		if came: return joinby.join(spl)


	# supportive  : updated line for input (splitted line - spl) - list of subnets
	def get_static_route_for_nbrs(self, line, spl, joinby, old_subnets, new_subnets, withmask, nbrs, hostmask=False):
		new_lines = []
		if not nbrs: return new_lines
		for old_subnet, new_subnet in zip(old_subnets, new_subnets):
			if not old_subnet or not new_subnet: continue
			newline = self.get_static_route_for_nbr(spl, joinby, old_subnet, new_subnet, withmask, nbrs, hostmask)
			if newline != line:
				newlines = self.static_annotate(newline)
				new_lines.extend(newlines)
				break
		return new_lines

	def static_annotate(self, line):
		lines = []
		spl = line.split(" ## comment: ")
		lines.append(spl[0])
		if len(spl) <= 1: return lines
		comment = spl[1]
		cmd = " ".join(spl[0].split()[1:-1])
		annotated_line = f'annotate {cmd} "{comment}"'
		lines.append(annotated_line)
		return lines

