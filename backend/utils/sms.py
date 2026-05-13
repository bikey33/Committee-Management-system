# utils/sms.py

def send_sms(phone_number, message):
    # Replace this with your SMS provider integration
    print(f"Sending SMS to {phone_number}: {message}")
    # For example, use Twilio, Nexmo, etc.
    # Example Twilio usage (pseudocode):
    # client.messages.create(to=phone_number, from_=YOUR_TWILIO_NUMBER, body=message)
