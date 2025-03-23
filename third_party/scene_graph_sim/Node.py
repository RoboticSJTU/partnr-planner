from enum import Enum
class NodeType(Enum):
	AGENT = 0
	BUILDING = 1
	FLOOR = 2
	ROOM = 3
	POSE = 4
	ASSET = 5
	OBJECT = 6

class Node:
	def __init__(self, node, node_type):
		self.name = node['id']
		self.type = node_type
		self.children = []
		self.neighbors = []
		self.full_info = node