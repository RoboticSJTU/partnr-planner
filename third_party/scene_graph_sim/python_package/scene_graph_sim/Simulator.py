import json
import copy
from .Node import NodeType
from .State import State
from .Action import Action

class Simulator:
	def __init__(self):
		self.full_graph = None
		self.sub_graph = None
		self.legal_actions = ['goto', 'access', 'open', 'close', 'pickup', 'pick', 'pick up', 'release', 'turn_on', 'turn_off', 'flush', 'water', 'clean', 'wash', 'wipe', 'organize' 'done']
		# self.state_space = ['closed', 'opened']

	def load_scene(self, scene_file_path):
		with open(scene_file_path, 'r') as scene_file:
			scene = json.load(scene_file)
		self.full_graph = State(scene)
	
	def collapse(self):
		graph = copy.deepcopy(self.full_graph)
		graph.asset_list = []
		graph.object_list = []
		graph.nodes = {k:v for k, v in graph.nodes.items() if v.type != NodeType.ASSET and v.type != NodeType.OBJECT}
		for key, value in graph.nodes.items():
			if value.type == NodeType.ROOM:
				value.children = []
		self.sub_graph = graph
		return self.sub_graph
	
	def expand_all(self):
		graph = copy.deepcopy(self.full_graph)
		self.sub_graph = graph
		return self.sub_graph

	def expand(self, node_name):
		self.sub_graph.nodes[node_name].children = self.full_graph.nodes[node_name].children
		# Add asset add object nodes who belong to the expanded node
		for child in self.sub_graph.nodes[node_name].children:
			self.sub_graph.nodes[child] = self.full_graph.nodes[child]
			if self.sub_graph.nodes[child].type == NodeType.ASSET:
				self.sub_graph.asset_list.append(child)
				for obj in self.sub_graph.nodes[child].children:
					self.sub_graph.nodes[obj] = self.full_graph.nodes[obj]
					self.sub_graph.object_list.append(obj)
			elif self.sub_graph.nodes[child].type == NodeType.OBJECT:
				self.sub_graph.object_list.append(child)
			
		return self.sub_graph


	def contract(self, node_name):
		for child in self.sub_graph.nodes[node_name].children:
			if self.sub_graph.nodes[child].type == NodeType.ASSET:
				for obj in self.sub_graph.nodes[child].children:
					self.sub_graph.nodes.pop(obj)
					self.sub_graph.object_list.remove(obj)
				self.sub_graph.nodes.pop(child)
				self.sub_graph.asset_list.remove(child)
			elif self.sub_graph.nodes[child].type == NodeType.OBJECT:
				self.sub_graph.nodes.pop(child)
				self.sub_graph.object_list.remove(child)
		self.sub_graph.nodes[node_name].children = []
		return self.sub_graph

	def get_legal_actions(self):
		legal_actions = ["done()"]
		agent_name = self.sub_graph.agent_list[0]
		agent_location = self.sub_graph.nodes[self.sub_graph.nodes[agent_name].full_info['location']]
		
		# goto action for all the rooms
		for room in self.sub_graph.room_list:
			legal_actions.append(Action('goto', room))
		
		# action from asset and object
		if agent_location.type == NodeType.ROOM:
			for obj in self.sub_graph.objects_in_hand:
				legal_actions.append(Action('release', obj))
			for child in agent_location.children:
				if self.sub_graph.nodes[child].type == NodeType.ASSET:
					for act in self.sub_graph.nodes[child].full_info['affordances']:
						if act in self.legal_actions:
							legal_actions.append(Action(act, child))
					for obj_str in self.sub_graph.nodes[child].children:
						for act in self.sub_graph.nodes[obj_str].full_info['affordances']:
							if act in self.legal_actions:
								legal_actions.append(Action(act, obj_str))
				elif self.sub_graph.nodes[child].type == NodeType.OBJECT:
					for act in self.sub_graph.nodes[child].full_info['affordances']:
						if act in self.legal_actions:
							legal_actions.append(Action(act, child))
		return [str(action) for action in legal_actions]
	
	def take_action(self, action):
		self.sub_graph.take_action(action)
	
	def get_room_list(self):
		return self.sub_graph.room_list

	def get_pose_list(self):
		return self.sub_graph.pose_list



if __name__ == '__main__':
	sim = Simulator()
	sim.load_scene('./data/3DSceneGraph_Gibson/merge_graph/3DSceneGraph_Allensville.json')
	sim.collapse()
	sim.expand('bathroom1')
	# sim.expand('storage_room')
	action_sequence = [
		"goto(bathroom1)",
        "pickup(vase1)",
      "done()"]
	for action_str in action_sequence:
		if action_str == 'done()':
			break
		legal_actions = sim.get_legal_actions()
		print('legal_actions:', legal_actions)
		print(f'take action:{action_str}')
		sim.take_action(action = Action(action_str=action_str))