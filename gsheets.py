import datetime
import yaml
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class Gsheet:

    def __init__(self, config):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('sheets', 'v4', credentials=creds)
        self.config = config

    def add(self, amount, description, category, time, is_debit):
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
