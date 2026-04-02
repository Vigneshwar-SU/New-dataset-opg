# Mobile OTP-Based Password Reset - Implementation Guide

## Overview
A secure password recovery system using SMS-based One-Time Password (OTP) verification. Users must provide their registered mobile number and verify the OTP sent to their mobile before resetting the password.

## Architecture

```
User Signup
    ↓
Enter: Username + Mobile + Password
    ↓
Account Created (Mobile stored in DB)
    ↓
Forgot Password
    ↓
Enter: Username + Mobile
    ↓
System verifies mobile matches
    ↓
Generate & Send 6-digit OTP (10 min validity)
    ↓
User enters OTP
    ↓
OTP Verified
    ↓
Create New Password
    ↓
Password Updated → Redirect to Login
```

---

## What's Implemented ✅

### Database Changes
- **User Model** now includes `mobile` field (unique)
- Mobile number is mandatory during signup
- Mobile is verified during password reset

### Frontend
1. **signup.html** - Added mobile number input field
2. **forgot_password.html** - Added mobile number verification field
3. **otp_verification.html** - NEW page with:
   - 6-digit OTP input
   - 10-minute countdown timer
   - Automatic warning when time running low
   - Resend OTP option

### Backend (app.py)
1. **OTP Generation** - Secure 6-digit codes using `secrets` module
2. **OTP Storage** - In-memory storage with timestamp validation
3. **OTP SMS Handler** - Ready for Twilio integration
4. **New Routes**:
   - `/forgot-password` - Now asks for mobile + username
   - `/verify-otp` - OTP verification page
   - `/reset-password` - Password reset (unchanged)

---

## Setting Up SMS/OTP with Twilio

### Step 1: Create Twilio Account
1. Go to https://www.twilio.com/
2. Sign up for free account (~$15 free credits)
3. Get your credentials:
   - Account SID
   - Auth Token
   - Phone Number (assigned to your account)

### Step 2: Install Twilio Package
```bash
pip install twilio
```

### Step 3: Set Environment Variables
Create a `.env` file in your project root:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
```

Or set them in your system environment.

### Step 4: Update app.py Configuration
The OTP sending function already has Twilio integrated! It auto-detects if credentials are set:

```python
# In send_otp_sms function (already in app.py)
if TWILIO_ACCOUNT_SID == 'your_account_sid':
    # Development mode: OTP printed to console
    print(f"[DEV MODE] OTP for {mobile_number}: {otp}")
else:
    # Production: SMS sent via Twilio
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(...)
```

### Step 5: Test OTP Flow

#### Development Mode (without Twilio credentials)
```
1. Signup with any username and mobile (e.g., +1234567890)
2. Go to Forgot Password
3. Enter username and mobile
4. Check Flask console output - OTP will be displayed there
5. Copy OTP and enter in verification form
```

#### Production Mode (with Twilio credentials)
```
1. Set environment variables with Twilio credentials
2. Signup with real mobile number
3. Go to Forgot Password
4. Enter username and mobile
5. SMS will be sent to the mobile number
6. User receives OTP and enters it
```

---

## Development vs Production

### Development (Current)
- OTP printed to console
- No SMS actually sent
- Perfect for testing
- No Twilio account needed

### Production
- Requires `.env` file with Twilio credentials
- Real SMS messages sent
- Costs ~$0.0075 per SMS
- Can cover ~2000 OTPs with $15 credit

---

## Alternative SMS Providers

### Option 1: AWS SNS (Amazon)
```python
import boto3

def send_otp_aws(phone_number, otp):
    client = boto3.client('sns')
    message = f'Your OTP is: {otp}\nValid for 10 minutes.'
    client.publish(
        PhoneNumber=phone_number,
        Message=message
    )
```

### Option 2: Firebase (Google)
```python
# Uses Firebase Cloud Messaging
# Requires Firebase project setup
```

### Option 3: Exotel (India-based)
```python
import requests

def send_otp_exotel(phone_number, otp):
    auth = ('exotel_sid', 'exotel_token')
    data = {
        'From': 'your_phone_number',
        'To': phone_number,
        'Body': f'Your OTP: {otp}'
    }
    requests.post('https://api.exotel.com/v1/sms/send', 
                  auth=auth, data=data)
```

---

## Security Features Implemented ✅

1. **OTP Expiration** - 10 minutes validity
2. **Single Use** - Token deleted after successful verification
3. **Rate Limiting** - (Recommended to add)
4. **Mobile Verification** - Must match registered number
5. **Secure Generation** - Uses `secrets` module
6. **No Replay Attacks** - Each request generates new OTP
7. **Username+Mobile** - Dual verification required

---

## Recommended Enhancements

### 1. Rate Limiting (Prevent Brute Force)
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/forgot-password', methods=['POST'])
@limiter.limit("5 per minute")
def forgot_password():
    # ... existing code ...
```

Installation:
```bash
pip install Flask-Limiter
```

### 2. Database-Backed Token Storage (Multi-server)
```python
class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    expiration = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

# Replace token storage with database queries
```

### 3. OTP Database Table
```python
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    expiration = db.Column(db.DateTime, nullable=False)
    attempts = db.Column(db.Integer, default=0)
    max_attempts = 5  # Lock after 5 attempts
    used = db.Column(db.Boolean, default=False)
```

### 4. Logging & Audit Trail
```python
import logging

logger = logging.getLogger(__name__)

def log_reset_attempt(username, mobile, success):
    logger.info(f"Password reset attempt - User: {username}, Mobile: {mobile}, Status: {success}")

# Call in forgot_password and verify_otp
```

### 5. Email Confirmation After Reset
```python
def send_reset_confirmation_email(email, username):
    msg = Message(
        subject='Password Reset Confirmation',
        recipients=[email],
        body=f'Your password was successfully reset. If this wasn\'t you, contact support.'
    )
    mail.send(msg)

# Call after successful password reset
```

---

## Testing Checklist

### Signup Flow
- [ ] Mobile number field appears in signup form
- [ ] Validation: Requires minimum 10 characters
- [ ] Validation: Prevents duplicate mobile numbers
- [ ] Account creates with mobile stored

### Forgot Password Flow
- [ ] Both username AND mobile required
- [ ] Validation: Mobile must match registered number
- [ ] OTP generated and stored
- [ ] OTP appears in console (dev mode) or SMS sent (prod)

### OTP Verification
- [ ] 6-digit code input field
- [ ] Countdown timer displays correctly
- [ ] Timer goes red when < 2 minutes remain
- [ ] Failed OTP shows error message
- [ ] Correct OTP proceeds to password reset

### Password Reset
- [ ] Only after OTP verified
- [ ] Can update to new password
- [ ] Token invalidated after reset
- [ ] Redirects to login page

---

## Deployment Checklist for Production

- [ ] Install Twilio package: `pip install twilio`
- [ ] Create Twilio account with credits
- [ ] Set environment variables (TWILIO_ACCOUNT_SID, etc.)
- [ ] Enable HTTPS/SSL: `SESSION_COOKIE_SECURE = True`
- [ ] Add rate limiting to prevent abuse
- [ ] Test SMS delivery with real phone
- [ ] Monitor SMS costs
- [ ] Set up logging for audit trail
- [ ] Implement email confirmation after reset
- [ ] Add "Report suspicious activity" link

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OTP not appearing in console | Flask app might not be in DEBUG mode. Check terminal output. |
| SMS not sending | Verify Twilio credentials in environment variables. Check account has credits. |
| OTP expired before user enters it | Increase `OTP_EXPIRATION_MINUTES` if needed (currently 10 min) |
| Mobile number mismatch error | Ensure signup mobile matches forgot password mobile (formatting matters) |
| Timer not counting down | Check browser console for JS errors. Ensure JavaScript enabled. |
| Multiple OTP requests | Implement rate limiting as shown above |
| OTP working in dev but not prod | Verify environment variables are set correctly: `echo $TWILIO_ACCOUNT_SID` |

---

## Code Files Modified

1. **app.py**
   - Added `mobile` field to User model
   - OTP generation & storage functions
   - Updated `/signup` route
   - Replaced `/forgot-password` route with OTP flow
   - Added `/verify-otp` route
   - Updated `/reset-password` route

2. **templates/signup.html**
   - Added mobile number input field

3. **templates/forgot_password.html**
   - Added mobile number input field
   - Updated button to "Send OTP"
   - Updated info text

4. **templates/otp_verification.html** (NEW)
   - OTP input form
   - Countdown timer with warning
   - Resend option

---

## Code Example: Custom Implementation

If you want to use a different SMS provider, update this function in `send_otp_sms`:

```python
def send_otp_sms(mobile_number, otp):
    """Send OTP via SMS using your provider"""
    try:
        # Your SMS provider API call here
        # Example: requests.post(url, data={...})
        
        print(f"[DEV] OTP sent to {mobile_number}: {otp}")
        return True
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False
```

---

## Support & Documentation

- **Twilio Docs**: https://www.twilio.com/docs/sms
- **Twilio Python**: https://www.twilio.com/docs/libraries/python
- **SMS Best Practices**: https://www.twilio.com/blog/
- **Flask-Login**: https://flask-login.readthedocs.io/

---

## Summary

✅ **Current Status**: 
- OTP system fully functional
- SMS integration ready
- Development mode works without Twilio
- Production ready with Twilio credentials

**Next Step**: Set up Twilio account and add credentials for production SMS sending.

For questions or issues, refer to the code comments in `app.py` or Twilio documentation.
