from Node import Node, NodeType
from Action import Action
class State:
	def __init__(self, scene):
		# a dict save the nodes, key is the node's id and the value is the object
		self.nodes = {}
		# list of node's id for each level
		self.agent_list = []
		self.building_list = []
		self.floor_list = []
		self.room_list = []
		self.pose_list = []
		self.asset_list = []
		self.object_list = []
		self.objects_in_hand = []


		# save nodes
		self.nodes[scene['nodes']['agent'][0]['id']] = Node(scene['nodes']['agent'][0], NodeType.AGENT)
		self.agent_list = [scene['nodes']['agent'][0]['id']]
		if 'building' in scene['nodes']:
			for building in scene['nodes']['building']:
				self.nodes[building['id']] = Node(building, NodeType.BUILDING)
				self.building_list.append(building['id'])
		if 'floor' in scene['nodes']:
			for floor in scene['nodes']['floor']:
				self.nodes[floor['id']] = Node(floor, NodeType.FLOOR)
				self.floor_list.append(floor['id'])
		if 'room' in scene['nodes']:
			for room in scene['nodes']['room']:
				self.nodes[room['id']] = Node(room, NodeType.ROOM)
				self.room_list.append(room['id'])
		if 'pose' in scene['nodes']:
			for pose in scene['nodes']['pose']:
				self.nodes[pose['id']] = Node(pose, NodeType.POSE)
				self.pose_list.append(pose['id'])
		if 'asset' in scene['nodes']:
			for asset in scene['nodes']['asset']:
				self.nodes[asset['id']] = Node(asset, NodeType.ASSET)
				self.asset_list.append(asset['id'])
		if 'object' in scene['nodes']:
			for obj in scene['nodes']['object']:
				self.nodes[obj['id']] = Node(obj, NodeType.OBJECT)
				self.object_list.append(obj['id'])
		
		# save links
		for link in scene['links']:
			node1, node2 = link.split('↔')
			print(node1, node2)
			if self.nodes[node1].type == NodeType.ROOM or self.nodes[node1].type == NodeType.POSE:
				if self.nodes[node2].type == NodeType.POSE:
					self.nodes[node1].neighbors.append(node2)
					self.nodes[node2].neighbors.append(node1)
				# not save the link between room and agent or pose and agent, use agent’s location to get where is the agent
				elif self.nodes[node2].type != NodeType.AGENT:
					self.nodes[node1].children.append(node2)
			else:
				self.nodes[node1].children.append(node2)

	def __str__(self):
		return str(self.to_json())

	def to_json(self):
		res = {
			'nodes': {
				'building': [],
				'floor': [],
				'room': [],
				'pose': [],
				'agent': [],
				'asset': [],
				'object': []
			},
			'links': []
		}
		for building in self.building_list:
			res['nodes']['building'].append(self.nodes[building].full_info)
			for child in self.nodes[building].children:
				res['links'].append(building + '↔' + child)
		for floor in self.floor_list:
			res['nodes']['floor'].append(self.nodes[floor].full_info)
			for child in self.nodes[floor].children:
				res['links'].append(floor + '↔' + child)
		for room in self.room_list:
			res['nodes']['room'].append(self.nodes[room].full_info)
			for neighbor in self.nodes[room].neighbors:
				res['links'].append(room + '↔' + neighbor)
			for child in self.nodes[room].children:
				res['links'].append(room + '↔' + child)
		for pose in self.pose_list:
			res['nodes']['pose'].append(self.nodes[pose].full_info)
			for neighbor in self.nodes[pose].neighbors:
				# links only include like "pose1↔pose2", not "pose2↔pose1"
				if neighbor[:4] == 'pose' and int(pose[4:]) < int(neighbor[4:]):
					res['links'].append(pose + '↔' + neighbor)
		for agent in self.agent_list:
			res['nodes']['agent'].append(self.nodes[agent].full_info)
			# add links between agent and its location
			res['links'].append(self.nodes[agent].full_info['location']+ '↔' + agent)
		for asset in self.asset_list:
			res['nodes']['asset'].append(self.nodes[asset].full_info)
			for child in self.nodes[asset].children:
				res['links'].append(asset + '↔' + child)
		for obj in self.object_list:
			res['nodes']['object'].append(self.nodes[obj].full_info)
		
		if res['nodes']['building'] == []:
			res['nodes'].pop('building')
		if res['nodes']['floor'] == []:
			res['nodes'].pop('floor')
		if res['nodes']['pose'] == []:
			res['nodes'].pop('pose')
		if res['nodes']['asset'] == []:
			res['nodes'].pop('asset')
		if res['nodes']['object'] == []:
			res['nodes'].pop('object')
		return res

	def take_action(self, action):
		if action.action_type == 'goto':
			self.goto(action.action_arg)
		elif action.action_type == 'access':
			self.access(action.action_arg)
		elif action.action_type == 'pickup':
			self.pickup(action.action_arg)
		elif action.action_type == 'release':
			self.release(action.action_arg)
		elif action.action_type == 'turn_on':
			self.turn_on(action.action_arg)
		elif action.action_type == 'turn_off':
			self.turn_off(action.action_arg)
		elif action.action_type == 'open':
			self.open(action.action_arg)
		elif action.action_type == 'close':
			self.close(action.action_arg)
		elif action.action_type == 'done':
			self.done(action.action_arg)

	
	def goto(self, action_arg):
		agent_name = self.agent_list[0]
		self.nodes[agent_name].full_info['location'] = action_arg
	def access(self, action_arg):
		pass
	def pickup(self, action_arg):
		self.objects_in_hand.append(action_arg)
		# print(self.objects_in_hand)
	def release(self, action_arg):
		pass
	def turn_on(self, action_arg):
		pass
	def turn_off(self, action_arg):
		pass
	def open(self, action_arg):
		target_name = action_arg
		self.nodes[target_name].full_info['state'] = 'opened'
	def close(self, action_arg):
		target_name = action_arg
		self.nodes[target_name].full_info['state'] = 'closed'
	def done(self, action_arg):
		pass
