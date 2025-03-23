from enum import Enum
ACTIONTYPE = ['goto', 'open', 'close']

class Action:
	def __init__(self, action_type=None, action_arg=None, action_str=None):
		if action_str:
			self.action_type = action_str.split('(')[0]
			self.action_arg = action_str.split('(')[1].split(')')[0]
		else:
			self.action_type = action_type
			self.action_arg = action_arg
	
	
	def __str__(self):
		return f"{self.action_type}({self.action_arg})"
	
	def __repr__(self):
		return f"{self.action_type}({self.action_arg})"
	def __eq__(self, other):
		return self.action_type == other.action_type and self.action_arg == other.action_arg