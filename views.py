import requests
import re
import sys
import datetime
from django.shortcuts import render
from .forms import LookupForm

API_URL = 'http://db.grandsvc.mesh/api/v1/members/lookup/'
INSTALL_API_URL = 'http://db.grandsvc.mesh/api/v1/installs/'
DEVICE_API_BASE_URL = 'https://10.70.76.21/nms/api/v2.1/devices/onus?parentId='
STRIPE_CUSTOMER_API_URL = 'https://api.stripe.com/v1/customers/search'
STRIPE_SUBSCRIPTION_API_URL = 'https://api.stripe.com/v1/subscriptions'
MESHDB_API_KEY = ''
UISP_API_KEY = ''
STRIPE_API_KEY = ''

headers = {
    'accept': 'application/json',
    'Authorization': f'Token {MESHDB_API_KEY}'
}

ALLOWED_NETWORK_NUMBERS = [1932, 1933, 1934]
DEVICE_PARENT_IDS = {
    1932: 'a57ddde1-6fff-463a-bbee-cbe90258daa6',
    1933: '7e6d228f-2693-4ba2-9c0a-82811289f9f3',
    1934: '7ee45009-6bc2-4a26-9b83-a3b07c70a3f6'
}

def normalize_phone_number(phone):
    phone = phone.strip()
    if len(phone) == 10:
        return f"+1 {phone[:3]}-{phone[3:6]}-{phone[6:]}"
    return phone

def get_install_unit_and_network_number(install_number, headers):
    response = requests.get(f"{INSTALL_API_URL}{install_number}/", headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('unit', 'Unit info not available'), data.get('network_number', None)
    else:
        return None, None

def get_device_data(parent_id):
    headers = {
        'accept': 'application/json',
        'x-auth-token': f'{UISP_API_KEY}'
    }
    url = f"{DEVICE_API_BASE_URL}{parent_id}"
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        return None

def fetch_stripe_customer(email):
    response = requests.get(
        STRIPE_CUSTOMER_API_URL,
        headers={
            'Authorization': f'Bearer {STRIPE_API_KEY}',
            'Stripe-Version': '2024-06-20'
        },
        params={'query': f"email:'{email}'"}
    )
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            customer = data['data'][0]
            return customer['id'], customer['delinquent']
    return None, None

def fetch_stripe_subscription(customer_id):
    response = requests.get(
        STRIPE_SUBSCRIPTION_API_URL,
        headers={
            'Authorization': f'Bearer {STRIPE_API_KEY}',
            'Stripe-Version': '2024-06-20'
        },
        params={'customer': customer_id}
    )
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            subscription = data['data'][0]
            nickname = subscription['items']['data'][0]['price']['nickname']
            status = subscription['status']
            current_period_start = datetime.datetime.utcfromtimestamp(subscription['current_period_start']).strftime('%Y-%m-%d %H:%M:%S')
            current_period_end = datetime.datetime.utcfromtimestamp(subscription['current_period_end']).strftime('%Y-%m-%d %H:%M:%S')
            latest_invoice_id = subscription['latest_invoice']
            invoice_response = requests.get(f'https://api.stripe.com/v1/invoices/{latest_invoice_id}', headers={'Authorization': f'Bearer {STRIPE_API_KEY}'})
            invoice_data = invoice_response.json()
            last_paid = datetime.datetime.utcfromtimestamp(invoice_data['status_transitions']['paid_at']).strftime('%Y-%m-%d %H:%M:%S')
            return {
                'nickname': nickname,
                'status': status,
                'current_period_start': current_period_start,
                'current_period_end': current_period_end,
                'last_paid': last_paid
            }
    return None

def fetch_device_info(selected_member_info):
    install_number = selected_member_info['installs'][0]
    unit, network_number = get_install_unit_and_network_number(install_number, headers)
    
    device_info = None
    if unit:
        selected_member_info['unit'] = unit
        
        if network_number in DEVICE_PARENT_IDS:
            parent_id = DEVICE_PARENT_IDS[network_number]
            device_data = get_device_data(parent_id)
            
            if device_data:
                for d in device_data:
                    if unit in d['identification']['name']:
                        device_info = {
                            'name': d['identification']['name'],
                            'status': d['overview']['status'],
                            'signal': d['overview'].get('signal', 'N/A'),
                            'lastSeen': d['overview']['lastSeen'],
                            'model': d['identification'].get('model', 'N/A'),
                            'ssid1': next((iface['wireless']['ssid'] for iface in d['interfaces'] if iface['identification']['name'] == 'wlan0'), 'N/A'),
                            'ssid2': next((iface['wireless']['ssid'] for iface in d['interfaces'] if iface['identification']['name'] == 'wlan1'), 'N/A'),
                            'password1': next((iface['wireless']['key'] for iface in d['interfaces'] if iface['identification']['name'] == 'wlan0'), 'N/A'),
                            'password2': next((iface['wireless']['key'] for iface in d['interfaces'] if iface['identification']['name'] == 'wlan1'), 'N/A')
                        }
                        break
        
    # Use stripe_email_address if it exists; otherwise, fallback to primary_email_address
    stripe_email = selected_member_info.get('stripe_email_address')
    email = stripe_email if stripe_email else selected_member_info['primary_email_address']
    
    customer_id, delinquent = fetch_stripe_customer(email)
    selected_member_info['delinquent'] = delinquent
    
    subscription_info = None
    if customer_id:
        subscription_info = fetch_stripe_subscription(customer_id)
    
    return device_info, subscription_info

def index(request):
    results = None
    error_message = None
    selected_member_info = None
    device_info = None
    subscription_info = None

    if request.method == 'POST':
        form = LookupForm(request.POST, results=request.session.get('results', []))
        if form.is_valid():
            selected_member_id = form.cleaned_data.get('selected_member')
            if selected_member_id:
                selected_member_id = str(selected_member_id)
                results = request.session.get('results', [])
                selected_member_info = next((m for m in results if str(m['id']) == selected_member_id), None)
                
                if selected_member_info:
                    device_info, subscription_info = fetch_device_info(selected_member_info)
            else:
                query = form.cleaned_data['query']
                params = {}
                if re.match(r"^\d{10}$", query):
                    normalized_phone = normalize_phone_number(query)
                    params['phone_number'] = normalized_phone
                elif "@" in query:
                    params['email_address'] = query
                else:
                    params['name'] = query

                response = requests.get(API_URL, headers=headers, params=params)
                
                full_url = response.url
                print(f"Full URL: {full_url}", file=sys.stderr)
                
                if response.status_code == 200:
                    members = response.json().get('results', [])
                    valid_members = []
                    for member in members:
                        valid = False
                        for install_number in member['installs']:
                            unit, network_number = get_install_unit_and_network_number(install_number, headers)
                            if network_number in ALLOWED_NETWORK_NUMBERS:
                                valid = True
                                member['unit'] = unit
                                break
                        if valid:
                            valid_members.append(member)
                    results = valid_members
                    request.session['results'] = results
                    if len(results) == 1:
                        selected_member_info = results[0]
                        device_info, subscription_info = fetch_device_info(selected_member_info)
                    elif not results:
                        error_message = "No results found."
                else:
                    error_message = f"Error {response.status_code}: {response.text}"
    else:
        form = LookupForm()

    if results and len(results) > 1:
        form = LookupForm(results=results)

    return render(request, 'dashboard/lookup.html', {
        'form': form,
        'results': results,
        'error_message': error_message,
        'selected_member_info': selected_member_info,
        'device_info': device_info,
        'subscription_info': subscription_info
    })