import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
from models import Transaction

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class Gsheet:

	def __init__(self, config):
		credentials = None
		if os.path.exists('token.pickle'):
			with open('token.pickle', 'rb') as token:
				credentials = pickle.load(token)
		# If there are no (valid) credentials available, let the user log in.
		if not credentials or not credentials.valid:
			if credentials and credentials.expired and credentials.refresh_token:
				credentials.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(
					'credentials.json', SCOPES)
				credentials = flow.run_local_server()
			# Save the credentials for the next run
			with open('token.pickle', 'wb') as token:
				pickle.dump(credentials, token)

		self.service = build('sheets', 'v4', credentials=credentials)
		self.config = config

	def add(self, amount: float, description: str, category: str, time: datetime, is_debit: bool) -> bool:
		sheet_range = self.config['expenses_range'] if is_debit else self.config['income_range']
		values = [
			time.strftime(self.config['date_format']),
			description,
			category,
			str(amount).replace('.', ',') if self.config['use_comma'] else str(amount)
		]
		result = self.service.spreadsheets().values().append(
			spreadsheetId=self.config['id'],
			range=sheet_range,
			valueInputOption='USER_ENTERED',
			body={'values': [values]}
		).execute()
		return result['updates']['updatedCells'] > 0

	def get_and_save_transactions(self):

		for is_debit in [True, False]:

			result = self.service.spreadsheets().values().get(
				spreadsheetId=self.config['id'],
				range=self.config['expenses_range'] if is_debit else self.config['income_range']
			).execute()

			for transaction in result['values']:
				time = datetime.strptime(transaction[0], self.config['date_format'])
				description = transaction[1]
				amount = float(transaction[3].replace(',', '.') if self.config['use_comma'] else transaction[3])

				Transaction.insert(
					time=time,
					description=description,
					amount=amount,
					is_debit=is_debit,
					asked=True,
					in_drive=True
				).on_conflict('replace').execute()  # Using insert as we do not need the model
