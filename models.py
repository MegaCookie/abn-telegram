from peewee import *
from datetime import datetime

db = SqliteDatabase('abn-telegram.db')


def create_tables():
	with db:
		db.create_tables([Transaction, Message, Update])


class BaseModel(Model):
	class Meta:
		database = db


class Transaction(BaseModel):
	amount = FloatField()
	is_debit = BooleanField()
	description = CharField()
	time = DateTimeField()
	asked = BooleanField(default=False)
	in_drive = BooleanField(default=False)
	ignored = BooleanField(default=False)

	class Meta:
		indexes = (
			# create a unique on amount/ time
			(('amount', 'time'), True),
		)

	@property
	def message(self):
		try:
			return self.messages.get()
		except DoesNotExist:
			return None

	@property
	def time_human(self):
		return self.time.strftime('%d %b. %Y %H:%M')

	@property
	def amount_human(self):
		return "{0:.2f}".format(self.amount)

	@property
	def message_text(self):
		return (
			f'{self.time_human}\n'
			f'*{self.description}*\n'
			f'*➖ €{self.amount_human}* 💸'
		) if self.is_debit else (
			f'{self.time_human}\n'
			f'*{self.description}*\n'
			f'*➕ €{self.amount_human} 💰*'
		)


class Message(BaseModel):
	id = IntegerField(unique=True)
	transaction = ForeignKeyField(Transaction, backref='messages', unique=True, null=True)


class Update(BaseModel):
	last_transaction = DateTimeField()

	def get_last_transaction_time(self):
		self.first()


if __name__ == '__main__':

	create_tables()
