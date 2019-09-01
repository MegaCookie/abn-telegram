from pyparsing import Word, alphas


class Rules:
	def __init__(self):
		self.kaas = "kaas"
		self.rules = []


	def load_rules(self):
		with open('rules') as rule_file:
			self.rules = rule_file.read()