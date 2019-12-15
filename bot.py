from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from ruamel.yaml import YAML
import threading
from abn import Abn
from gsheets import Gsheet
from models import Transaction, Message, create_tables

yaml = YAML()


class Bot:

	def __init__(self, config):
		self.chat_id = config['telegram']['chat_id']
		self.bot = Updater(config['telegram']['token'])
		self.poll_time = config['poll_time']
		self.abn_config = config['abn']
		self.expense_categories = config['expense_categories']
		self.income_categories = config['income_categories']
		self.keywords = config['telegram']['keywords']

		self.g_sheet = Gsheet(config['gsheet'])

		self.bot.dispatcher.add_handler(CommandHandler('start', self.start))
		self.bot.dispatcher.add_handler(CallbackQueryHandler(self.button_pressed))
		self.bot.dispatcher.add_handler(CommandHandler('help', self.help))
		self.bot.dispatcher.add_handler(CommandHandler('previous', self.previous_transactions))
		self.bot.dispatcher.add_handler(CommandHandler('again', self.ask_transactions_again))
		self.bot.dispatcher.add_error_handler(self.error)

		# Start the Bot
		self.bot.start_polling()

		self.look_for_new_mutations()

		# Run the bot until the user presses Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT
		self.bot.idle()

	def look_for_new_mutations(self):
		Abn(self.abn_config).save_all_mutations()
		self.g_sheet.get_and_save_transactions()

		transactions = Transaction.select().where(
			(Transaction.asked == False) &
			(Transaction.in_drive == False) &
			(Transaction.ignored == False)
		)

		for transaction in transactions:
			self.ask(transaction)

		threading.Timer(interval=self.poll_time, function=self.look_for_new_mutations).start()

	def ask_transactions_again(self, _bot, update):
		self.g_sheet.get_and_save_transactions()
		Abn(self.abn_config).save_all_mutations()

		transactions = Transaction.select().where((Transaction.in_drive == False) & (Transaction.ignored == False))
		for transaction in transactions:
			if transaction.message is not None:
				self.try_delete_transaction_message(update.message.chat.id, transaction)
			self.ask(transaction)

	def ask(self, transaction: Transaction):
		keyboard = []

		categories = self.expense_categories if transaction.is_debit else self.income_categories

		for category_row in categories:
			row = []

			if isinstance(category_row, list):
				for category in category_row:
					category_name = category_short = category

					if isinstance(category, dict):
						category_name = list(category.keys())[0]
						category_short = list(category.values())[0]['short_name']

					row.append(InlineKeyboardButton(
						text=category_short,
						callback_data=category_name
					))

			else:
				row.append(InlineKeyboardButton(
					text=category_row,
					callback_data=category_row
				))
			keyboard.append(row)

		# Check if the last keyboard row has more than 4 buttons
		#  if it is, add a new keyboard row.
		if len(keyboard[-1]) >= 4:
			keyboard.append([])

		# Add the stop emoji button to the last row
		keyboard[-1].append(InlineKeyboardButton(
			"❌",
			callback_data=self.keywords['ignore']
		))

		reply_markup = InlineKeyboardMarkup(keyboard)

		print(transaction.message_text)

		telegram_message = self.bot.bot.send_message(
			chat_id=self.chat_id,
			text=transaction.message_text,
			reply_markup=reply_markup,
			parse_mode='Markdown'
		)

		Message.insert(
			id=telegram_message.message_id,
			transaction_id=transaction.id
		).on_conflict('replace').execute()

		transaction.asked = True
		transaction.save()

	def delete_transaction_message(self, chat_id: int, transaction: Transaction):
		try:
			if not self.bot.bot.delete_message(chat_id=chat_id, message_id=transaction.message.id):
				self.bot.bot.edit_message_text(
					text=transaction.message_text + '\n*Message over due*',
					chat_id=chat_id,
					message_id=transaction.message.id
				)
		except self.bot.bot.BadRequest:
			print(f'Message with id: {transaction.message.id} cannot be deleted')

	def try_delete_transaction_message(self, chat_id: int, transaction: Transaction):
		# In new thread as when it fails, it will block the entire process
		threading.Thread(target=Bot.delete_transaction_message, args=[self, chat_id, transaction]).start()

	@staticmethod
	def previous_transactions(_bot, _update):
		return ""

	def start(self, bot, update):
		update.message.reply_text('This bot will automatically notice you with new mutations. Enjoy :)')
		self.ask_transactions_again(bot, update)

	def button_pressed(self, bot, update):
		query = update.callback_query

		category: str = query.data

		message = Message.get_or_none(Message.id == query.message.message_id)

		inline_ignore_keyboard = InlineKeyboardMarkup([[
			InlineKeyboardButton(
				text='❌',
				callback_data=self.keywords['ask_again']
			),
			InlineKeyboardButton(
				text='❌&🔄󠀦󠀦',
				callback_data=self.keywords['ask_again_and_reload']
			),
		]])

		if message is not None:
			reload = category == self.keywords['ask_again_and_reload']
			ignore_message = category == self.keywords['ignore']
			ask_message_again = category == self.keywords['ask_again'] or reload
			spreadsheet_saving_success = False

			if message.transaction is not None:
				if not ignore_message:
					transaction = message.transaction

					spreadsheet_saving_success = self.g_sheet.add(
						amount=transaction.amount,
						description=transaction.description,
						category=category,
						time=transaction.time,
						is_debit=transaction.is_debit
					)
				elif ask_message_again:
					message.transaction.asked = False
					message.transaction.save()
				else:
					message.transaction.ignored = True
					message.transaction.save()

			if spreadsheet_saving_success or ignore_message or ask_message_again:
				message.delete_instance()
				if not bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id):
					query.edit_message_text(
						text=query.message.text + (
							f'\nChosen category: *{category}* ✔'
							if not ignore_message or ask_message_again else
							f'\n*❌ IGNORED ❌'
						),
						parse_mode='Markdown'
					)

				if reload:
					self.ask_transactions_again(bot, update)

			elif not spreadsheet_saving_success:
				query.edit_message_text(
					text=query.message.text + f'\n❌ *ERROR SAVING TO SPREADSHEET* ❌',
					parse_mode='Markdown',
					reply_markup=inline_ignore_keyboard
				)
		else:
			Message.insert(id=query.message.message_id, transaction_id=-1).execute()

			query.edit_message_text(
				text=query.message.text + f'\n❌ *ERROR: UNKNOWN MESSAGE* ❌',
				parse_mode='Markdown',
				reply_markup=inline_ignore_keyboard
			)

	@staticmethod
	def help(_bot, update):
		update.message.reply_text("Use /start to test this bot.")

	@staticmethod
	def error(_bot, update, error):
		"""Log Errors caused by Updates."""
		print('Update "%s" caused error "%s"', update, error)


if __name__ == '__main__':

	create_tables()

	with open('config.yaml', 'r', encoding="utf8") as yaml_config_file:
		Bot(yaml.load(yaml_config_file))
