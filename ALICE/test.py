import requests

# Use the TEST URL from your n8n Webhook node
test_url = "https://blx-ankush.app.n8n.cloud/webhook-test/alice-whatsapp-trigger"

headers = {
    "Alice-Token": "Ankush07@",  # Must match the Header Auth value you set
    "Content-Type": "application/json"
}

# The data Alice will send to the workflow
data = {
    "phone_number": "9066704247",
    "name": "Ankush",
    "message_content": "Hey! Alice here with a test message."
}

response = requests.post(test_url, json=data, headers=headers)
print(f"Status: {response.status_code}, Response: {response.text}")