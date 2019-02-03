from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from ruamel.yaml import YAML
import threading
from abn import Abn
from gsheets import Gsheet
import json
from datetime import datetime
import shelve

yaml = YAML()


class Bot:

    def __init__(self, config):
        self.chat_id = config['telegram']['chat_id']
        self.bot = Updater(config['telegram']['token'])
        self.poll_time = config['poll_time']
        self.abn_config = config['abn']
        self.categories = config['categories']

        self.g_sheet = Gsheet(config['gsheet'])

        self.bot.dispatcher.add_handler(CommandHandler('start', self.start))
        self.bot.dispatcher.add_handler(CallbackQueryHandler(self.button_pressed))
        self.bot.dispatcher.add_handler(CommandHandler('help', self.help))
        self.bot.dispatcher.add_error_handler(self.error)

        # Start the Bot
        self.bot.start_polling()

        self.look_for_new_mutations()

        # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT
        self.bot.idle()

    def look_for_new_mutations(self):
        abn = Abn(self.abn_config)
        mutations = abn.get_mutations()
        # print(json.dumps(mutations, indent=2))

        with open('last_transaction.yaml', 'r+') as yaml_file:
            yaml_dict = yaml.load(yaml_file.read())
            last_asked_transaction_timestamp = yaml_dict['timestamp'] if yaml_dict is not None and 'timestamp' in yaml_dict else 0
            last_timestamp = last_asked_transaction_timestamp

            for mutation in mutations['mutationsList']['mutations'][::-1]:
                mutation = mutation['mutation']

                time = datetime.strptime(mutation['transactionTimestamp'], '%Y%m%d%H%M%S%f')
                timestamp = time.timestamp()

                if timestamp > last_asked_transaction_timestamp:
                    last_timestamp = last_timestamp if last_timestamp > timestamp else timestamp
                    is_debit = mutation['amount'] < 0
                    amount = "{0:.2f}".format(mutation['amount'] * -1 if is_debit else mutation['amount'])
                    self.ask(mutation['counterAccountName'], amount, time, is_debit)
                    # print(json.dumps(mutation, indent=2))

        with open('last_transaction.yaml', 'w+') as yaml_file:
            yaml.dump({'timestamp': last_timestamp}, yaml_file)

        abn_poll_thread = threading.Timer(self.poll_time, self.look_for_new_mutations)
        abn_poll_thread.start()

    def ask(self, description, amount, time, is_debit):
        keyboard = []

        for category_row in self.categories:
            row = []

            if isinstance(category_row, list):
                for category in category_row:
                    category_name = category_short = category

                    if isinstance(category, dict):
                        category_name = list(category.keys())[0]
                        category_short = list(category.values())[0]['short_name']

                    row.append(InlineKeyboardButton(
                        category_short,
                        callback_data=category_name
                    ))

            else:
                row.append(InlineKeyboardButton(
                        category_row,
                        callback_data=category_row
                ))
            keyboard.append(row)

        keyboard[-1].append(InlineKeyboardButton(
                    "❌",
                    callback_data=json.dumps({'stop': 'true'})
        ))

        reply_markup = InlineKeyboardMarkup(keyboard)

        time_human = time.strftime('%d %b. %Y %H:%M')
        message = self.bot.bot.send_message(
                                            chat_id=self.chat_id,
                                            text=f'{time_human}\n{description}\n€{amount}',
                                            reply_markup=reply_markup
                                            )

        with shelve.open('telegram_messages.shelve') as tm:
            tm[str(message.message_id)] = {
                    'amount': amount,
                    'description': description,
                    'time': time,
                    'is_debit': is_debit
                    }

    @staticmethod
    def start(_bot, update):
        update.message.reply_text('This bot will automatically notice you with new mutations. Enjoy :)')

    def button_pressed(self, bot, update):
        query = update.callback_query

        category = query.data

        with shelve.open('telegram_messages.shelve') as tm:
            info = tm[str(query.message.message_id)]
            success = self.g_sheet.add(info['amount'], info['description'], category, info['time'], info['is_debit'])

            if success:
                del info
                bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

    @staticmethod
    def help(_bot, update):
        update.message.reply_text("Use /start to test this bot.")

    @staticmethod
    def error(_bot, update, error):
        """Log Errors caused by Updates."""
        print('Update "%s" caused error "%s"', update, error)


if __name__ == '__main__':
    with open('config.yaml', 'r', encoding="utf8") as yaml_config_file:
        Bot(yaml.load(yaml_config_file))
