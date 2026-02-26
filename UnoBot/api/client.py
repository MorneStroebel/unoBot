import requests
from config.settings import API_BASE_URL, MAC_ADDRESS, DEBUG_MODE

HEADERS = {
    "Content-Type": "application/json",
    "X-MAC-Address": MAC_ADDRESS
}

def debug_print(method, url, payload=None):
    if DEBUG_MODE:
        print("\n--- HTTP REQUEST ---")
        print("Method:", method)
        print("URL:", url)
        print("Headers:", HEADERS)
        if payload:
            print("Payload:", payload)
        print("-------------------\n")

def get(endpoint):
    url = f"{API_BASE_URL}{endpoint}"
    debug_print("GET", url)
    return requests.get(url, headers=HEADERS)

def post(endpoint, payload):
    url = f"{API_BASE_URL}{endpoint}"
    debug_print("POST", url, payload)
    return requests.post(url, headers=HEADERS, json=payload)