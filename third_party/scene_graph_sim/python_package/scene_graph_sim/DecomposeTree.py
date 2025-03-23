import json
import sys
sys.path.append('.')

from utils import remove_comments, semantic_search, call_LLM
from constants import PROMPT_DECOMPOSE_TASK, PROMPT_GET_REWARD_FOR_DECOMPOSE



def get_reward(message):
	user_input = 'Give me a review, here is the task decompose infomation:\n' + str(message)
	messages = [
		{'role': 'system', 'content': PROMPT_GET_REWARD_FOR_DECOMPOSE},
		{'role': 'user', 'content': user_input}]
	for i in range(5):
		gpt_reply = remove_comments(call_LLM(messages))
		# print('get_reward_reply:------------------------------\n',gpt_reply)
		try:
			gpt_reply_json = json.loads(gpt_reply)
		except Exception as e:
			print(e)
			if i == 4:
					raise Exception('get_reward failed' + str(e))
			continue
		return gpt_reply_json['result']
class TaskNode:
	def __init__(self, task_name, description="", is_leaf=False, formated_description=""):
		"""
		Initialize a TaskNode.

		:param task_name: Name or identifier of the task.
		:param description: A textual description of the task.
		:param is_leaf: True if the task is a leaf node (e.g., cannot be split further).
		"""
		self.task_name = task_name
		self.description = description
		self.formated_description=formated_description
		self.is_leaf = is_leaf
		self.children = []

	def add_child(self, child_node):
		"""
		Add a child node to the current node.

		:param child_node: An instance of TaskNode.
		"""
		self.children.append(child_node)

	def __repr__(self):
		return f"TaskNode({self.task_name}, description={self.description}, is_leaf={self.is_leaf})"
	


class TaskTree:
	def __init__(self, root_task="", root_description="", scene_graph="", generate_task_decompose_data=False, task_decompose_data_save_path=""):
		"""
		Initialize the TaskTree with a root task.

		:param root_task: Name or identifier of the root task.
		:param root_description: Description of the root task.
		"""
		self.root = TaskNode(root_task, description=root_description, is_leaf=False)
		self.scene_graph = scene_graph
		self.call_gpt_count = 0
		self.nodes = { self.root.task_name : self.root}
		self.generate_task_decompose_data = generate_task_decompose_data
		self.task_decompose_data_save_path = task_decompose_data_save_path
		self.history_messages = []    # the output data
		self.messages = []            # conversation history

	def process_messages(self, task_node, gpt_reply):
		task_name = task_node.task_name
		task_description = task_node.description
		if self.messages == []:
			self.messages = [
				{
					"content": PROMPT_DECOMPOSE_TASK+f'\n Here is the scene graph: \n{self.scene_graph} Here is the Task_name: {task_name}\nHere is the Task_description: {task_description}\n',
					"role": "user"
				},
				{
					"content": gpt_reply,
					"role": "assistant"
				}
			]
		else:
			self.messages.append({
				"content": f'Here is the Task_name: {task_name}\nHere is the Task_description: {task_description}\n',
				"role": "user"
			})
			self.messages.append({
				"content": gpt_reply,
				"role": "assistant"
			})
		label = get_reward(self.messages) == "True"
		self.history_messages.append(
			 {
				"messages": self.messages[:],
				"label": label
			}
		)
	def split_task(self, task_node):
		"""
		Split a task into subtasks and add them as children to the given task node.

		:param task_node: The TaskNode to split.
		"""
		task_name = task_node.task_name
		task_description = task_node.description
		messages = [{'role': 'system', 'content': PROMPT_DECOMPOSE_TASK}]
		user_input = f'Task_name: {task_name}\nTask_description: {task_description}\n3D Scene Graph: {self.scene_graph}'
		messages.append({'role': 'user', 'content': user_input})
		self.call_gpt_count += 1
		# Example split logic, modify this based on your actual task splitting rules
		for i in range(5):
			gpt_reply = call_LLM(messages)
			try:
				task_splits = json.loads(remove_comments(gpt_reply))
			except Exception as e:
				print(e)
				if i == 4:
					raise Exception('split faild' + str(e))
				continue
			break
		if self.generate_task_decompose_data == True:
			self.process_messages(task_node, gpt_reply)
		subtasks = task_splits.get('subtasks', [])
		for subtask in subtasks:
			is_leaf = not subtask['is_decomposable']
			if is_leaf:
				task_node.add_child(TaskNode(subtask['task_name'], subtask['description'], is_leaf, formated_description=subtask['formated_description']))
			else:
				task_node.add_child(TaskNode(subtask['task_name'], subtask['description'], is_leaf))

	def build_tree(self):
		"""
		Build the task tree using breadth-first traversal.
		"""
		queue = [self.root]

		while queue:
			if self.call_gpt_count > 100:
				raise Exception("Too many calls to GPT")
			current_node = queue.pop(0)
			if not current_node.is_leaf:
				self.split_task(current_node)
				queue.extend(current_node.children)
				for child in current_node.children:
					self.nodes[child.task_name] = child
		if self.generate_task_decompose_data == True:
			with open(self.task_decompose_data_save_path, 'w+') as f:
				json.dump(self.history_messages, f)

	def print_tree(self, node=None, level=0, plan=[]):
		"""
		Print the task tree structure.

		:param node: The starting node to print (default is root).
		:param level: The current level in the tree (used for indentation).
		"""
		if node is None:
			node = self.root
		print("    " * level + f"- {node.formated_description} | {node.task_name}: {node.description}")
		if node.is_leaf:
			plan.append(node.formated_description)
		for child in node.children:
			self.print_tree(child, level + 1, plan)
	
	def to_dict(self, node=None):
		"""
		Convert the task tree into a nested dictionary structure.

		:param node: The starting node to convert (default is root).
		:return: A dictionary representing the task tree.
		"""
		if node is None:
			node = self.root

		# Convert current node to a dictionary
		node_dict = {
			"task_name": node.task_name,
			"description": node.description,
			"formated_description": node.formated_description,
			"is_leaf": node.is_leaf,
			"children": [self.to_dict(child) for child in node.children],
		}
		return node_dict

	def save_tree(self, file_path):
		"""
		Save the task tree to a JSON file.

		:param file_path: The path of the file to save the task tree.
		"""
		# Convert the tree to a dictionary
		tree_dict = self.to_dict()
		tree_dict['scene_graph'] = self.scene_graph

		# Write the dictionary to a JSON file
		with open(file_path, "w+", encoding="utf-8") as f:
			json.dump(tree_dict, f, ensure_ascii=False, indent=4)
		print(f"Task tree saved to {file_path}")
	
	def load_tree(self, file_path):
		"""
		Load the task tree from a JSON file.

		:param file_path: The path of the file to load the task tree.
		"""
		with open(file_path, "r", encoding="utf-8") as f:
			tree_dict = json.load(f)
		
		# Load scene graph
		self.scene_graph = tree_dict.get('scene_graph', "")
		self.nodes = {}

		# Reconstruct the tree from the dictionary
		def build_node(node_data):
			node = TaskNode(
				task_name=node_data['task_name'],
				description=node_data['description'],
				formated_description=node_data['formated_description'],
				is_leaf=node_data['is_leaf']
			)
			self.nodes[node.task_name] = node
			for child_data in node_data.get('children', []):
				child_node = build_node(child_data)
				node.add_child(child_node)
			return node

		# Set the root node
		self.root = build_node(tree_dict)
		print(f"Task tree loaded from {file_path}")
	def get_node(self, task_name):
		return self.nodes.get(task_name, None)

	def generate_trajectory(self):
		"""
		Generate a trajectory from the start node to the end node.
		Start node is the original task which is going to be decomposed.
		End node is the leaf node which is the final task.
		Trajectory contains all subtasks child from the node to be decomposed.

		:param start_node: The start node of the trajectory.
		:param end_node: The end node of the trajectory.
		:return: A list of nodes representing the trajectory.
		"""
		start_node = self.root
		paths = []
		def dfs(node, path, paths):
			if node is None:
				return

			# 将当前节点的值加入路径
			path.append(node.task_name)
			paths.append(list(path))


			for child in node.children:
				dfs(child, path, paths)

			# 回溯，移除当前节点
			path.pop()
		dfs(start_node, [], paths)
		return paths

def generate_data_1():
	tree_from_load =  TaskTree()
	tree_from_load.load_tree('data/tasks/task_decompose/office/A delegation of project partners is arriving soon. We want to serve them snacks and non-alcoholic drinks. Prepare everything in the largest meeting room. Use items found in the supplies room only..xml')
	tree_from_load.print_tree()
	trajectorys =  tree_from_load.generate_trajectory()
	data_json = []
	for traj in trajectorys:
		traj_data = ''
		for node in traj:
			tree_node = tree_from_load.get_node(node)
			traj_data += f'Decompose: {tree_node.task_name if tree_node.task_name != "original_task" else tree_node.description} '
			for i, child in enumerate(tree_node.children):
				traj_data += f'Subtask{i+1}: {child.task_name} Description: {child.description} Decomposable: {"No" if child.is_leaf else "Yes"} Formated_description: {child.formated_description}'
		
		data = {
			"messages": [
				{
					"content": f'Given the scene graph and task, help me to decompose the task into subtasks. Here are the task:',
					"role": "user"
				},
				{
					"content": traj_data,
					"role": "assistant"
				}
			],
			"label": True
		}
		data_json.append(data)

	with open('./save_test.json', 'w+') as f:
		json.dump(data_json, f)

# Example Usage
if __name__ == "__main__":
	# Create a task tree
	task_name = "root"
	task_description = "I want to make a sandwich. Place all the ingredients on the lunch table."
	scene_graph_path = './data/scenegraphs/scene_from_paper_office.json'
	searched_graph = ''
	try:
		searched_graph, _, _ = semantic_search(scene_graph_path, task_description)
	except Exception as e:
		print(e)
	task_tree = TaskTree(task_name, task_description, searched_graph, True, './data/test_generate_with_split.json')
	# Build the tree
	task_tree.build_tree()

	plan = []
	# # Print the tree
	task_tree.print_tree(plan=plan)
	print('plan:\n', plan)
	# task_tree.save_tree(f'.{task_description}.xml')

	# tree_from_load =  TaskTree()
	# tree_from_load.load_tree('data/tasks/task_decompose/office/A delegation of project partners is arriving soon. We want to serve them snacks and non-alcoholic drinks. Prepare everything in the largest meeting room. Use items found in the supplies room only..xml')
	# tree_from_load.print_tree()
