# Twilio SMS Setup Guide

## Quick Start (5 minutes)

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/
2. Click "Sign Up"
3. Fill in your details and verify your email
4. You get **$15 free credits** (~2000 SMS messages)

### Step 2: Get Your Credentials
After login, go to **Twilio Console**:

1. **Account SID**: Visible on dashboard (looks like: `ACxxxxxxxxxxxxxxxxxxxxxxxxxx`)
2. **Auth Token**: Visible on dashboard (click "Show" to reveal)
3. **Phone Number**: 
   - Go to **Phone Numbers** → **Manage Numbers** → **Active Numbers**
   - Or get a trial number (free for 30 days)
   - Format: `+1234567890`

### Step 3: Configure .env File
Create `.env` file in project root with:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

**DO NOT share these credentials!** Add `.env` to `.gitignore`:
```
echo ".env" >> .gitignore
```

### Step 4: Restart Flask
```bash
# Stop Flask (Ctrl+C)
# Then restart:
.\env\Scripts\python.exe app.py
```

### Step 5: Test 
1. Go to http://127.0.0.1:5000/signup
2. Create account with your real mobile number
3. Click "Forgot Password"
4. Enter username and mobile
5. **Real SMS** will be sent to your phone! 📱

---

## Getting Trial Phone Number (Optional)

If you don't have a Twilio phone number yet:

1. In **Twilio Console** → **Phone Numbers** → **Get Started**
2. Click **Get your first Twilio phone number**
3. Accept the default US number offered
4. Copy the number (e.g., `+1234567890`)
5. Add to `.env` file

---

## Understanding Twilio Pricing

| Item | Cost |
|------|------|
| SMS in US/Canada | $0.0075/SMS |
| International SMS | $0.01-0.15/SMS varies |
| Free Trial Credit | $15 |
| Estimated SMS with $15 | ~2000 messages |

**Note**: First time setup may require upgrading account to send SMS internationally.

---

## Troubleshooting

### SMS not sending?

**Check 1: Credentials in .env**
```bash
# Verify file exists:
dir .env
# Content should NOT be empty
```

**Check 2: Flask console output**
When you send OTP, Flask should print:
```
✓ SMS sent successfully to +1234567890
  Message SID: SM1234567890abcdef
```

NOT this:
```
[DEV MODE] OTP SENT TO: +1234567890
```

**Check 3: Restart Flask**
```bash
# Stop with Ctrl+C
# Then:
.\env\Scripts\python.exe app.py
```

**Check 4: Twilio Account Status**
- Check if account is verified
- Check if you have phone credits
- Check if phone number is active

### Phone number not receiving SMS?

1. Make sure number format is correct: `+1234567890` (with country code)
2. Check Twilio **Message Logs** in console
3. Ensure it's not going to spam folder
4. Try a different phone number

### "Auth Token Invalid" error?

- Copy auth token again from Twilio console (click "Show")
- Make sure you copied the full token
- Restart Flask after updating .env

---

## Production Best Practices

### 1. Environment Variables (Don't use .env in production)
Use system environment variables instead:

**Windows:**
```bash
setx TWILIO_ACCOUNT_SID "ACxxxxxxx"
setx TWILIO_AUTH_TOKEN "xxxxxx"
setx TWILIO_PHONE_NUMBER "+1234567890"
```

**Linux/Mac:**
```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxx"
export TWILIO_AUTH_TOKEN="xxxxxx"
export TWILIO_PHONE_NUMBER="+1234567890"
```

### 2. Protect Credentials
- **Never** commit `.env` to git
- Add to `.gitignore`: `echo ".env" >> .gitignore`
- Don't log credentials in code

### 3. Add Rate Limiting
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per minute")
def forgot_password():
    # Prevents brute force OTP requests
```

### 4. Monitor SMS Costs
- Check Twilio dashboard regularly
- Set up billing alerts
- Consider monthly budget limits

---

## Verifying Setup

### Test 1: Check Environment Variables are Loaded
In Flask app, they should be loaded:
```python
from dotenv import load_dotenv
import os

load_dotenv()  # Load from .env

print(os.environ.get('TWILIO_ACCOUNT_SID'))  # Should print your SID
```

### Test 2: Send Test SMS from Console
```python
from twilio.rest import Client
import os

account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
phone = os.environ.get('TWILIO_PHONE_NUMBER')

client = Client(account_sid, auth_token)
message = client.messages.create(
    body="Test SMS from Python",
    from_=phone,
    to="+your_number_here"
)
print(message.sid)
```

---

## Next Steps

1. ✅ Create Twilio account
2. ✅ Get credentials  
3. ✅ Create `.env` file
4. ✅ Restart Flask
5. ✅ Test with real SMS
6. 🎉 Enjoy working OTP system!

---

## Support

- **Twilio Docs**: https://www.twilio.com/docs/sms
- **Twilio Python**: https://www.twilio.com/docs/libraries/python
- **Troubleshooting**: https://www.twilio.com/docs/sms/troubleshooting

