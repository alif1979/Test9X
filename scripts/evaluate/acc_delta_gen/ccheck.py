

import json
from nettoolkit.addressing import *
from .check import ChkCommon

class CiscoChk(ChkCommon):

	# ------------------------------ INTERFACE RELATED ---------------------------------

	# capture: get `set interface prefix line string` for set line from interface type
	def get_intf(self, intf, int_type):
		if int_type.lower() == 'vlan':
			intf = 'interface vlan' + str(intf)
		if int_type.lower() == 'loopback':
			intf = 'interface loopback' + str(intf)
		if int_type.lower() == 'physical':
			minidf = self.clean_df_dict['physical'][(self.clean_df_dict['physical']['int_number'] == intf)]
			intf = minidf['interface'][minidf.index[0]].lower()
			intf = 'interface ' + str(intf)
		return intf

	# capture: get the join by character, "/" for description line, " " else
	@staticmethod
	def get_joinby_char(spl, line):
		joinby = " "
		if spl[0] == 'description':
			spl = line.strip().split("/")
			joinby = "/"
		return (spl, joinby)

	# capture: get specified interface configuration
	def get_cur_interface_conf(self, intf, int_type):
		if int(intf) == intf: 
			intf = int(intf)
			test = False
		else:
			test = True
		# if test: print(intf, int_type)
		intf = self.get_intf(intf, int_type)
		# if test: print(intf)
		int_conf_list, start = [], False
		for line in self.config_list:
			# if test: print(line)
			if line.lower().startswith(intf):
				start = True
			if not start: continue
			# if test: print(line)
			int_conf_list.append(line)
			if line[0] == "!" and len(line.strip()) == 1:
				break
		# if test: print(int_conf_list)
		return int_conf_list

	# Delete eligibles :  interface config
	def get_del_interface_conf(self, intf, int_type):
		if int(intf) == intf: 
			intf = int(intf)
		intf = self.get_intf(intf, int_type)
		if int_type.lower() in ('physical'):
			return ['default ' + intf, ]
		elif int_type.lower() in ('vlan', 'loopback'):
			return ['no ' + intf, ]
		else:
			return ['no ' + intf, ]

	# Add eligibles :  interface config.
	def get_proposed_interface_conf(self, old_subnet, new_subnet, cur_intf_conf_list):
		newipv4 = addressing(new_subnet)
		prop_intf_conf = []
		for line in cur_intf_conf_list:
			if line.strip() == "": continue			
			spl = line.strip().split()
			(spl, joinby) = self.get_joinby_char(spl, line)
			withmask = joinby != '/'
			newline = self.get_new_line(spl, joinby, old_subnet, newipv4, False)
			if not newline.startswith('interface ') and not newline.startswith("!"): newline = " " + newline
			prop_intf_conf.append(newline)
		return prop_intf_conf



	# ------------------------- BGP RELATED -------------------------- #

	# capture: bgp as number
	def get_bgp_as(self):
		bgp_campus_as = ""
		for line in self.config_list:
			if line.lower().startswith('router bgp '):
				bgp_campus_as = line.strip().split()[-1]
				break
		return bgp_campus_as

	# capture: acc.y1 address-family configurations
	def address_family_lines(self, vrf):
		bgp_start, af_start = False, False		
		af_lines = []
		for line in self.config_list:
			if not bgp_start and line.lower().startswith('router bgp '):
				bgp_start = True
				continue
			if bgp_start and line.strip().startswith(f"address-family ipv4 vrf {vrf}"):
				af_start = True
				continue
			if bgp_start and af_start and line.strip().startswith("exit-address-family"):
				break
			#
			if bgp_start and af_start: 
				af_lines.append(line)
		return af_lines

	# capture: router id command line(s)
	def get_bgp_router_id(self, af_lines):
		router_id_line = []
		for line in af_lines:
			if line.strip().startswith("bgp router-id "):
				router_id_line.append(line)
				break
		return router_id_line

	# capture: aggregate(s) command line(s)
	def get_existing_aggregates(self, af_lines):
		aggregate_list = []
		for line in af_lines:
			if line.strip().startswith("aggregate-address "):
				aggregate_list.append(line)
		return aggregate_list

	# capture: se-acc-xxxx all peers coammand line(s), & set of neighbors 
	def get_peer_group_nbrs(self, af_lines):
		peer_groups = ( 'se-acc', 'se-acc-dir', 'se-acc-lpp', 'se-acc-alt', 'se-acc-rr' )
		nbr_lines_list = []
		nbrs = set()
		se_acc_nbrs = set()
		for peer in peer_groups:
			for line in af_lines:
				if line.strip().endswith(f" peer-group {peer}"):
					nbr = line.strip().split()[1]
					nbrs.add(nbr)
					if peer == 'se-acc':
						se_acc_nbrs.add(nbr)
		#
		for line in af_lines:
			if line.strip().startswith(f"neighbor ") and line.strip().split()[1] in nbrs:
				nbr_lines_list.append(line)
		return (nbr_lines_list, nbrs, se_acc_nbrs)

	# Delete eligibles - club of aggregates; local-add, neghbor lines
	def get_del_bgp_config_list(self, dic, vrf):		
		del_bgp_config_list = []
		bgp_del_changes = []
		# bgp_del_changes.append(f'bgp router-id {dic["bgp_router_id"]}')    ## will overwrite
		bgp_del_changes.extend([ f"  no {line.strip()}" for line in dic["existing_aggregates"]])
		bgp_del_changes.extend([ f"  no neighbor {nbr}" for nbr in dic["peer_group_nbrs"]])
		if bgp_del_changes:
			del_bgp_config_list.extend([f'router bgp {dic["bgp_campus_as"]}', " !",
										f" address-family ipv4 vrf {vrf}", ])
			del_bgp_config_list.extend(bgp_del_changes)
			del_bgp_config_list.extend([f" exit-address-family", " !", "!"])
		return del_bgp_config_list

	# Add eligibles - BGP Configurations routerid, local-add, neighbor lines
	def update_bgp_cofig_list(self, bgp_config_list, vrf, old_summaries, new_summaries):
		new_list = []
		for line in bgp_config_list:
			line = line.strip()
			spl = line.split()
			for old_subnet, new_subnet in zip(old_summaries, new_summaries):
				updated_line = self.get_new_line(spl, " ", old_subnet, new_subnet, withmask=False)
				if updated_line != line:
					updated_line = "  " + updated_line.strip()
					break
				else:
					updated_line = ""
			new_list.append(updated_line)
		return new_list

	# Add eligibles - BGP Configurations aggregates
	def update_bgp_agg_list(self, vrf, new_supernet):
		return self.check_n_get_new_summaries(vrf, new_supernet, 'cisco')

	# Add eligibles - BGP Configurations router id
	def update_bgp_router_id_new(self, rid_lst, old_subnets, new_subnets):
		new_rid_lst = []
		for line in rid_lst:
			spl = line.strip().split()
			newline = self.get_new_line_for_subnets(spl, " ", old_subnets, new_subnets, withmask=False)
			if newline:
				new_rid_lst.append("  " + newline.strip())
				break
		return new_rid_lst

	# Add eligibles - club of routerid, aggregates, local-add, neghbor lines
	def get_add_bgp_config_list(self, dic, vrf):
		bgp_add_changes = []
		bgp_change_list = []
		if dic["new_bgp_router_id"]:
			bgp_change_list.extend(dic["new_bgp_router_id"])
		bgp_change_list.extend(dic["new_agg_lines_list"])
		bgp_change_list.extend(dic["new_nbr_lines_list"])
		if bgp_change_list:
			bgp_add_changes.extend([f'router bgp {dic["bgp_campus_as"]}', " !",
										f" address-family ipv4 vrf {vrf}"])
			bgp_add_changes.extend(bgp_change_list)
			bgp_add_changes.extend([f" exit-address-family", " !", "!"])
		return bgp_add_changes

	# ------------------------------- Statics ------------------------------ #

	# capture: static routes begin with 9.
	def get_static_routes_accy1_begin9(self):
		return [ line for line in self.config_list
			if line.lower().startswith('ip route vrf acc.y1 9.') ]

	#  Delete eligibles: All static routes begin with 9.
	def get_static_routes_accy1_begin9_del(self, routes):
		return [ f'no {line.strip()}' for line in routes ]

	#  Add eligibles: static Routes
	def get_static_routes_accy1_begin9_add(self, routes, se_acc_nbrs, old_subnets, new_subnets, old_supernet, new_supernet):
		new_list = []
		for line in routes:
			line = line.strip()
			spl = line.split()

			## -- summary subnet -- ##
			summarysubnet = False
			for i, item in enumerate(spl):
				try:
					s = addressing(item, spl[i+1])
				except:
					continue
				if str(s) == '9.0.0.0/8': 
					spl[i], spl[i+1] = '172.16.0.0', '255.240.0.0'
					dot9_idx = spl.index('name')+2
					if spl[dot9_idx] == '9.': spl[dot9_idx] = '172.16.'
					new_list.append(" ".join(spl))
					summarysubnet = True
					break
			if summarysubnet: continue

			## -- exact matched static routes -- ##
			newline  = self.check_n_get_old_new_for_exact_match(spl, old_subnets, new_subnets, 'cisco', withmask=True)
			if not newline: 
				newline = self.check_n_get_old_new_for_exact_match(spl, old_supernet, new_supernet, 'cisco',  withmask=True)
			if newline:
				new_list.append(newline)
				continue

			## -- BGP static routes -- ##
			newline = self.get_static_route_for_nbrs(line, spl, " ", old_supernet, new_supernet, False, se_acc_nbrs)
			if newline:
				new_list.extend(newline)

		return new_list

	#  Delete eligibles: static routes which has acc.y1 as next hop.
	def get_next_hop_changed_routes_del(self, static_df):
		new_list = []
		for i, row in static_df.iterrows():
			ip = IPv4(row.prefix)
			ad = f'name {row.adminisrative_distance} ' if row.adminisrative_distance else ""
			tag =  f'name {row.tag_value} ' if row.tag_value else ""
			name = f'name {row.remark} ' if row.remark else ""
			new_list.append(f'no ip route vrf {row.pfx_vrf} {ip.net} {ip.binmask} {row.next_hop}')
		return new_list

	#  Add eligibles: static routes which has acc.y1 as next hop.
	def get_next_hop_changed_routes_add(self, static_df):
		new_list = []
		for i, row in static_df.iterrows():
			ip = IPv4(row.prefix)
			ad = f'name {row.adminisrative_distance} ' if row.adminisrative_distance else ""
			tag =  f'name {row.tag_value} ' if row.tag_value else ""
			name = f'name {row.remark} ' if row.remark else ""
			new_list.append(f'ip route vrf {row.pfx_vrf} {ip.net} {ip.binmask} {row.next_hop_new} {ad}{tag}{name}')
		return new_list


	# ----------------------------- PL top level agg -------------------------- #

	# capture: top level aggregate prefix list and its application line
	def get_pl_top_lvl_agg_accy1_begin9(self):
		return [ line for line in self.config_list
			if (line.lower().startswith('ip prefix-list pl_agg_top_level_acc ')  and 
				line.strip().endswith('9.0.0.0/8'))]

	#  Delete eligibles: top level aggregate prefix list and its application line
	def get_pl_top_lvl_agg_accy1_begin9_del(self, lst):
		return [ f'no {line.strip()}' for line in lst ]

	#  Add eligibles: update top level aggregate prefix list and its application line
	def get_pl_top_lvl_agg_accy1_begin9_add(self, lst):
		new_list = []
		for line in lst:
			spl = line.split()
			new_list.append(" ".join(spl[:-1]) + " 172.16.0.0/12")
		return new_list

