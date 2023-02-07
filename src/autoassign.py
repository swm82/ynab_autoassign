import os
import sys
import csv
import requests
from datetime import date
from constants.constants import CSV_HEADER_AMT, CSV_HEADER_ID, CSV_HEADER_NAME, ID_KEY, AMOUNT_KEY, BASE_URL, CATEGORY_ENDPOINT, CATEGORY_FIELD, CATEGORY_UPDATE_PAYLOAD, DATA_FIELD, BUDGETED_AMT_FIELD
from util import convert_milliunits_to_str, convert_str_to_milliunits

def read_credentials(filename):
    with open(filename) as f:
        return f.readline().split(',')

def read_input(filename):
    with open(filename, newline='') as csvfile:
        data  = {}
        reader = csv.DictReader(csvfile)
        for row in reader:
            data[row[CSV_HEADER_NAME]] = {ID_KEY: row[CSV_HEADER_ID], AMOUNT_KEY: convert_str_to_milliunits(row[CSV_HEADER_AMT])}
        return data

def calculate_total_update_amount(data):
    curr_sum = 0
    for _, fields in data.items():
        curr_sum += fields[AMOUNT_KEY]
    return curr_sum

def get_ready_to_assign_amt(budget_id):
    headers = {'Authorization': 'Bearer {token}'.format(token=token), 'accept': 'application/json', 'Content-Type': 'application/json'}
    url = BASE_URL + '/budgets/{budget_id}/months'.format(budget_id=budget_id)
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print('Received a {status_code} response [{response}] when getting Ready To Assign amount'.format(status_code=response.status_code, response=response.json()))
    
    today = date.today().replace(day=1)
    for month in response.json()[DATA_FIELD]['months']:
        if str(today) == month['month']:
            return month['to_be_budgeted']
    # TODO: Throw something
    return None
    

def verify_sufficient_funds(data, budget_id):
    return get_ready_to_assign_amt(budget_id) >= calculate_total_update_amount(data)

def update_categories(data, budget_id):
    if not verify_sufficient_funds(data, budget_id):
        print('Auto Assign Failed: Insufficient funds to execute auto assign')
        return
    headers = {'Authorization': 'Bearer {token}'.format(token=token), 'accept': 'application/json', 'Content-Type': 'application/json'}
    for category_name, category_fields in data.items():
        url = BASE_URL + CATEGORY_ENDPOINT.format(budget_id=budget_id, category_id=category_fields[ID_KEY])
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print('Received a {status_code} response [{response}] when getting category data'.format(status_code=response.status_code, response=response.json()))
            continue
        currAmt = get_budgeted_amt(response)
        newAmt = currAmt + category_fields[AMOUNT_KEY]
        print('Updating category [{category}], Current amount [{amt}], New amount [{newAmt}]'.format(category=category_name, amt=convert_milliunits_to_str(currAmt), newAmt=convert_milliunits_to_str(newAmt)))
        response = requests.patch(url, headers=headers, data=CATEGORY_UPDATE_PAYLOAD.format(amt=newAmt))
        if response.status_code != 200:
            print('Received a {status_code} response [{response}] when updating category'.format(status_code=response.status_code, response=response.json()))

def get_budgeted_amt(json_data):
    return int(json_data.json()[DATA_FIELD][CATEGORY_FIELD][BUDGETED_AMT_FIELD])

def undo_update(data, budget_id):
    flipped = { cat: {ID_KEY: fields[ID_KEY], AMOUNT_KEY: -fields[AMOUNT_KEY]} for cat, fields in data.items()}
    update_categories(flipped, budget_id)

print('Starting process...')

isUndo = False
args = sys.argv[1:]
if len(args) >= 1:
    if args[0] == '-u':
        print('Running UNDO process..')
        isUndo = True

# Get the secrets
token = os.environ.get('API_KEY')
# TODO: Get the budget id's from the token, ask user which to update
budget_id = os.environ.get('BUDGET_ID')

data = read_input('input/' + budget_id)

# Verify that we're updating the correct account
headers = {'Authorization': 'Bearer {token}'.format(token=token), 'accept': 'application/json', 'Content-Type': 'application/json'}
url = BASE_URL + '/budgets/{budget_id}'.format(budget_id=budget_id)
response = requests.get(url, headers=headers)
update = input('Update Budget "{budget_name}" (Y/N)?: '.format(budget_name=response.json()['data']['budget']['name']))

# Confirm
if update in ['y', 'Y']:
    if isUndo:
        undo_update(data, budget_id)
    else:
        update_categories(data, budget_id)
    print('Update complete..\nRemaining unbudgeted balance: {unbudgeted_amount}'.format(unbudgeted_amount=convert_milliunits_to_str(get_ready_to_assign_amt(budget_id))))
else:
    print('Aborting update..')