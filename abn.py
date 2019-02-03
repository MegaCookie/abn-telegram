import abna
import json
import time
import os.path


class Abn:

	def __init__(self, abn_config):
		self.iban_account = abn_config['iban_account']
		self.session = abna.Session(abn_config['iban_account'])
		self.pass_number = abn_config['pass_number']
		self.soft_token = abn_config['soft_token']

	def get_mutations(self):
		if os.path.isfile('mutations.json'):
			with open('mutations.json') as mutations_file:
				mutations = json.load(mutations_file)
				if 'lastUpdate' in mutations and time.time() - mutations['lastUpdate'] < 300:
					return mutations

		return self.update_mutations()

	def update_mutations(self):
		self.session.login(self.pass_number, self.soft_token)
		mutations = self.session.mutations(self.iban_account)
		mutations['lastUpdate'] = time.time()
		with open('mutations.json', 'w') as mutations_file:
			json.dump(mutations, mutations_file)

		return mutations
