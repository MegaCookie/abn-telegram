# ABN-Telegram
ABN telegram bot - Categorize your transactions through Telegram

Assuming personal payment information isn't that private, why not make use of the data
for your own budgetting scheme. This Telegram bot does exactly that. When a new transaction
is detected, this bot will ask to categorize the transaction, which then can be used in a 
spreadsheet. 
## Why? - Background information
Basically I wanted to track all my expenses and income and put that in a fancy spreadsheet. 
Therefore it must be easy to use and preferably on mobile. Making a native app is a safer
approach of course. However, as I consider payment info not that secure anymore as banks 
already have agreements with third parties and making this Telegram bot is way less complex
(and does not cost any money for an Apple Developer License). So as I'm fine storing 
my payment info on Google Drive, and an extra hop through Telegram does not bother me either.

## Installation
This makes use of the [abna Python library](https://github.com/djc/abna) to retrieve 
transactions.   
* `virtualenv venv`
* `. venv/bin/activate`
* `pip install -r requirements.txt`  
* `cp config-example.yaml config.yaml` and edit that to your preferences.  

Then enable the Google Sheets API on: https://console.developers.google.com/apis/library/sheets.googleapis.com  
* Make sure Oauth has access to (Oauth permission/ consent screen): `../auth/spreadsheets `
* Choose other (cause it's not an webapp)
* Download and save them as credentials.json in this folder
* Running not locally and need to confirm Oatuh? `ssh user@server -L 8080:localhost:8080` to map
your 8080 port to the 8080 port of the server.



### Finally
* `python bot.py` (with Python 3)

### Adding as a systemd service
* `sudo cp ./abn-telegram.service /etc/systemd/system`
* Edit the file: set the right folder and the user you want to run it as.
* `sudo systemctl enable /etc/systemd/system/abn-telegram.service`
* `sudo systemctl daemon-reload`
* `sudo systemctl start abn-telegram.service`

## Usage
T.B.C.