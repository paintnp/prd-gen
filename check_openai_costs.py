import requests
import os
from datetime import datetime, timedelta

# Get API key from environment variables
api_key = os.environ.get('OPENAI_API_KEY')

if not api_key:
    print('Error: OPENAI_API_KEY environment variable not found')
    exit(1)

# Calculate last month's date range
today = datetime.now()
first_day_of_current_month = datetime(today.year, today.month, 1)
last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
first_day_of_previous_month = datetime(last_day_of_previous_month.year, last_day_of_previous_month.month, 1)

start_date = first_day_of_previous_month.strftime('%Y-%m-%d')
end_date = last_day_of_previous_month.strftime('%Y-%m-%d')

print(f'Fetching OpenAI API costs from {start_date} to {end_date}...')

# Make API request
headers = {
    'Authorization': f'Bearer {api_key}'
}

response = requests.get(
    f'https://api.openai.com/v1/dashboard/billing/usage?start_date={start_date}&end_date={end_date}',
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    # The total_usage value is in hundredths of cents, so divide by 100 to get dollars
    total_cost = data.get('total_usage', 0) / 100
    print(f'Total OpenAI API cost for last month: ${total_cost:.2f}')
else:
    print(f'Error: {response.status_code}')
    print(response.text) 