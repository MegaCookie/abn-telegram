import abna
import json
import time
import os.path
from datetime import datetime

from models import Transaction, Update


class Abn:

	def __init__(self, abn_config):
		self.iban_account = abn_config['iban_account']
		self.session = abna.Session(abn_config['iban_account'])
		self.pass_number = abn_config['pass_number']
		self.soft_token = abn_config['soft_token']

	def save_all_mutations(self):
		mutations = self.mutations

		update = Update.get_or_none(Update.id == 1)
		last_asked_transaction_timestamp = update.last_transaction if update is not None else 0
		print(last_asked_transaction_timestamp)
		last_timestamp = last_asked_transaction_timestamp

		for mutation in mutations['mutationsList']['mutations'][::-1]:
			mutation = mutation['mutation']

			# Trim the mutation time so we won't bother with microsecond comparisons
			mutation_time = datetime.strptime(mutation['transactionTimestamp'], '%Y%m%d%H%M%S%f').replace(microsecond=0)
			timestamp = mutation_time.timestamp()

			if timestamp > last_asked_transaction_timestamp:

				last_timestamp = last_timestamp if last_timestamp > timestamp else timestamp
				is_debit = mutation['amount'] < 0
				amount = "{0:.2f}".format(mutation['amount'] * -1 if is_debit else mutation['amount'])

				Transaction.insert(
					amount=amount,
					is_debit=is_debit,
					description=mutation['counterAccountName'],
					time=mutation_time
				).on_conflict('ignore').execute()

		if update is not None:
			update.update(last_transaction=last_timestamp).execute()
		else:
			Update.create(last_transaction=last_timestamp)

	@property
	def mutations(self) -> list:
		if os.path.isfile('mutations.json'):
			with open('mutations.json') as mutations_file:
				mutations = json.load(mutations_file)
				if 'lastUpdate' in mutations and time.time() - mutations['lastUpdate'] < 300:
					return mutations

		return self.update_mutations()

	def update_mutations(self) -> list:
		self.session.login(self.pass_number, self.soft_token)
		mutations = self.session.mutations(self.iban_account)
		mutations['lastUpdate'] = time.time()
		with open('mutations.json', 'w') as mutations_file:
			json.dump(mutations, mutations_file)

		return mutations
