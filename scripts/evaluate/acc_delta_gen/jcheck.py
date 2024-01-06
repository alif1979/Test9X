
import json
from nettoolkit.pyJuniper import *
from nettoolkit.addressing import *
from .check import ChkCommon


TOP_LVL_AGG_PL_NAME = 'pl_net_172_16'


# convert set command line to delete command line
def set_to_del(line):
	return "del "+" ".join(line.strip().split()[1:])


class JuniperChk(ChkCommon):

	# ------------------------------ INTERFACE RELATED ---------------------------------

	# capture: get `set interface prefix line string` for set line from interface type
	def get_intf(self, intf, int_type):
		if int_type.lower() == 'vlan':
			intf = 'set interfaces irb unit ' + str(intf)
		if int_type.lower() == 'loopback':
			intf = 'set interfaces lo0 unit ' + str(intf)
		if int_type.lower() == 'physical':
			intf = 'set interfaces ' + str(intf)
		return intf

	# capture: get the join by character, "/" for description line, " " else
	@staticmethod
	def get_joinby_char(spl, line):
		joinby = " "
		if 'description' in spl:
			spl = line.split("/")
			joinby = "/"
		return (spl, joinby)

	# capture: get specified interface configuration
	def get_cur_interface_conf(self, intf, int_type):
		intf = self.get_intf(intf, int_type)
		int_conf_list = [line 
				for line in self.config_list
				if line.lower().startswith(intf)]
		int_conf_list.append("#")
		return int_conf_list


	# Delete eligibles :  interface config
	def get_del_interface_conf(self, intf, int_type):
		intf = self.get_intf(intf, int_type)
		return ['del ' + intf[4:], ]

	# Add eligibles :  interface config.
	def get_proposed_interface_conf(self, old_subnet, new_subnet, cur_intf_conf_list):
		newipv4 = addressing(new_subnet)
		prop_intf_conf = []
		for line in cur_intf_conf_list:
			if line.strip() == "": continue			
			spl = line.strip().split()
			(spl, joinby) = self.get_joinby_char(spl, line)
			withmask = joinby != '/'
			newline = self.get_new_line(spl, joinby, old_subnet, newipv4, withmask)
			if newline.find("virtual-address") > 0: newline = newline[:-3]
			prop_intf_conf.append(newline)
		return prop_intf_conf



	# ------------------------- BGP RELATED -------------------------- #

	# capture: bgp as number
	def get_bgp_as(self):
		bgp_campus_as_line = []
		for line in self.config_list:
			if line.lower().startswith('set routing-options autonomous-system '):
				bgp_campus_as_line.append(line)
				break
		return bgp_campus_as_line

	# capture: acc.y1 se-acc bgp group command lines
	def address_family_lines(self, vrf):
		af_lines = []
		for line in self.config_list:
			if not line.lower().startswith('set routing-instances acc.y1 protocols bgp group se-acc'): continue
			spl = line.strip().split()
			if "local-address" in spl or "neighbor" in spl:
				af_lines.append(line)
		return af_lines

	# capture: router id command line(s)
	def get_bgp_router_id(self, af_lines):
		router_id_line = []
		for line in self.config_list:
			if not line.lower().startswith('set routing-instances acc.y1 routing-options router-id '): continue
			router_id_line.append(line)
			break
		return router_id_line

	# capture: aggregate(s) command line(s)
	def get_existing_aggregates(self, af_lines):
		aggregate_list = []
		for line in self.config_list:
			if not line.lower().startswith('set routing-instances acc.y1 routing-options aggregate route '): continue
			aggregate_list.append(line)
		return aggregate_list

	# capture: se-acc-xxxx all peers coammand line(s), & set of neighbors 
	def get_peer_group_nbrs(self, af_lines):
		nbr_lines_list = []
		nbrs = set()
		se_acc_nbrs = set()
		peer_groups = ( 'se-acc', 'se-acc-dir', 'se-acc-lpp', 'se-acc-alt' )
		for line in self.config_list:
			if not line.lower().startswith('set routing-instances acc.y1 protocols bgp group se-acc'): continue
			spl = line.strip().split()
			if "local-address" in spl or "neighbor" in spl:
				nbr_lines_list.append(line)
				nbrs.add(spl[8])
			if ("neighbor" in spl
				and line.lower().startswith('set routing-instances acc.y1 protocols bgp group se-acc ')):
					se_acc_nbrs.add(spl[8])
		return (nbr_lines_list, nbrs, se_acc_nbrs)

	# Delete eligibles - club of routerid; aggregates; local-add, neghbor lines
	def get_del_bgp_config_list(self, dic, vrf):		
		bgp_del_changes = []
		bgp_del_changes.extend([ set_to_del(line) for line in dic["bgp_router_id"]])
		bgp_del_changes.extend([ set_to_del(line) for line in dic["existing_aggregates"]])
		bgp_del_changes.extend([ set_to_del(line.split("description")[0]) for line in dic["existing_nbr_lines_list"]])
		return bgp_del_changes

	# Add eligibles - BGP Configurations routerid, local-add, neighbor lines
	def update_bgp_cofig_list(self, bgp_config_list, vrf, old_summaries, new_summaries):
		new_list = []
		for line in bgp_config_list:
			spl = line.split()
			for old_subnet, new_subnet in zip(old_summaries, new_summaries):
				updated_line = self.get_new_line(spl, " ", old_subnet, new_subnet, withmask=False)
				if updated_line != line:
					break
				else:
					updated_line = ""
			new_list.append(updated_line)
		return new_list

	# Add eligibles - BGP Configurations aggregates
	def update_bgp_agg_list(self, vrf, new_supernet):
		return self.check_n_get_new_summaries(vrf, new_supernet, 'juniper')

	# Add eligibles - BGP Configurations router id
	def update_bgp_router_id_new(self, rid_lst, old_subnets, new_subnets):
		new_rid_lst = []
		for line in rid_lst:
			spl = line.strip().split()
			newline = self.get_new_line_for_subnets(spl, " ", old_subnets, new_subnets, withmask=False)
			if newline:
				new_rid_lst.append(newline)
				break
		return new_rid_lst

	# Add eligibles - club of routerid, aggregates, local-add, neghbor lines
	def get_add_bgp_config_list(self, dic, vrf):
		bgp_add_changes = []
		bgp_add_changes.extend([ line for line in dic["new_bgp_router_id"]])
		bgp_add_changes.extend([ line for line in dic["new_agg_lines_list"]])
		bgp_add_changes.extend([ line for line in dic["new_nbr_lines_list"]])
		return bgp_add_changes

	# ------------------------------- STATIC ROUTE RELATED ------------------------------ #

	# capture: static routes begin with 9.
	def get_static_routes_accy1_begin9(self):
		return [ line
			for line in self.config_list
			if line.startswith("set routing-instances acc.y1 routing-options static route 9.") ] 

	#  Delete eligibles: All static routes begin with 9.
	def get_static_routes_accy1_begin9_del(self, routes):
		return sorted(set([ " ".join(set_to_del(line).split()[:7])  for line in routes ]))

	#  Add eligibles: static Routes
	def get_static_routes_accy1_begin9_add(self, routes, se_acc_nbrs, old_subnets, new_subnets, old_supernet, new_supernet):
		new_list = []
		for line in routes:
			spl = line.split()

			## -- summary subnet -- ##
			summarysubnet = False
			for i, item in enumerate(spl):
				if item == '9.0.0.0/8':
					spl[i] = '172.16.0.0/12'
					newline = " ".join(spl)
					newlines = self.static_annotate(newline)
					new_list.extend(newlines)
					summarysubnet = True
					break
			if summarysubnet: continue

			## -- exact matched static routes -- ##
			newline  = self.check_n_get_old_new_for_exact_match(spl, old_subnets, new_subnets, 'juniper', withmask=True)
			if not newline: 
				newline = self.check_n_get_old_new_for_exact_match(spl, old_supernet, new_supernet, 'juniper',  withmask=True)
			if newline:
				newlines = self.static_annotate(newline)
				new_list.extend(newlines)
				continue

			## -- BGP static routes -- ##
			for old_nbr in se_acc_nbrs:
				if f'{old_nbr}/32' in spl:
					newline = self.get_static_route_for_nbrs(line, spl, " ", old_supernet, new_supernet, False, se_acc_nbrs, hostmask=True)
					if newline:
						new_list.extend(newline)
						break
		return new_list

	#  Delete eligibles: static routes which has acc.y1 as next hop.
	def get_next_hop_changed_routes_del(self, static_df):
		new_list = []
		for i, row in static_df.iterrows():
			new_list.append(f'del routing-instances {row.pfx_vrf} routing-options static route {row.prefix}')
		return new_list

	#  Add eligibles: static routes which has acc.y1 as next hop.
	def get_next_hop_changed_routes_add(self, static_df):
		new_list = []
		for i, row in static_df.iterrows():
			ad = f' preference {row.adminisrative_distance}' if row.adminisrative_distance else ""
			tag =  f' tag {row.tag_value}' if row.tag_value else ""
			name = f' {row.remark}' if row.remark else ""
			next_hop = f' next-hop {row.next_hop_new}' if row.remark else ""
			new_list.append(f'set routing-instances {row.pfx_vrf} routing-options static route {row.pfx_vrf} retain')
			for item in (next_hop, tag, ad):
				if not item: continue
				new_list.append(f'set routing-instances {row.pfx_vrf} routing-options static route {row.pfx_vrf}{item}')
			if name:
				new_list.append(f'annotate routing-instances {row.pfx_vrf} routing-options static route {row.pfx_vrf}{name}')
		return new_list

	# ----------------------------- PL top level agg -------------------------- #

	# capture: top level aggregate prefix list and its application line
	def get_pl_top_lvl_agg_accy1_begin9(self):
		return [ line
			for line in self.config_list
			if 'pl_net_9' in line.split() and 'rm_from_se_acc' in line.split() ] 

	#  Delete eligibles: top level aggregate prefix list and its application line
	def get_pl_top_lvl_agg_accy1_begin9_del(self, lst):
		return sorted([set_to_del(line)  for line in lst ])

	#  Add eligibles: update top level aggregate prefix list and its application line
	def get_pl_top_lvl_agg_accy1_begin9_add(self, lst):
		s, d, tlagg = 'pl_net_9', TOP_LVL_AGG_PL_NAME, []
		if lst:
			tlagg.extend([f'set policy-options prefix-list {d} 172.16.0.0/12'])
			tlagg.extend([line.replace(s, d)  for line in lst ])
		return tlagg

