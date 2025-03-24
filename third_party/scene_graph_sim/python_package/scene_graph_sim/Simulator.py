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
	
	def check_the_plan(self, plan):
		# 用于记录当前是否已经拿起物品
		holding_item = None

		for action in plan:
			# 检查是否是 Pick 动作
			if action.startswith("Pick["):
				# 如果已经拿着物品，则提示错误
				if holding_item is not None:
					return "Error: you only can pick one thing at one time, you must place the object in hand brefore you pick another."
				holding_item = action
			
			# 检查是否是 Place 动作
			elif action.startswith("Place["):
				# 如果放下物品，则清空当前拿起的物品
				holding_item = None

		near_cabinet = False
		cabinet_opened = False

		for action in plan:
			# 检查是否是 Navigate 到 cabinet
			if action.startswith("Navigate[cabinet_"):
				near_cabinet = True
				cabinet_opened = False  # 重置打开状态，因为导航到新的 cabinet 需要重新打开

			# 检查是否是 Open cabinet
			elif action.startswith("Open[cabinet_"):
				if not near_cabinet:
					return f"Error: you can not {action}, because you have not navigate to the canibet"
				cabinet_opened = True

			# 检查是否是 Pick 动作
			elif action.startswith("Pick["):
				if near_cabinet and not cabinet_opened:
					return f"Error：you can not{action}, because you have not to open the cabinet"

			# 如果离开 cabinet 区域，重置状态
			elif action.startswith("Navigate[") and not action.startswith("Navigate[cabinet_"):
				near_cabinet = False
				cabinet_opened = False

    
		return True

			



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