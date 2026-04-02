# Forgot Password Functionality - Implementation Guide

## Overview
The forgot password system has been implemented with the following components:

### Current Implementation
- **Frontend**: Three new pages (forgot_password.html, reset_password.html) with intuitive UI
- **Backend**: Token-based password reset system with 30-minute expiration
- **Logic**: Secure token generation using `secrets` module

---

## Current Workflow

### 1. User Clicks "Forgot Password?"
- User on login page clicks "Forgot?" link next to password field
- Redirected to `/forgot-password` page

### 2. User Enters Username
- User enters their username
- System checks if user exists (without revealing existence for security)
- Generates a unique reset token valid for 30 minutes

### 3. User Gets Reset Link
- Currently: Link is displayed on the page (for testing)
- User can copy and paste the link to navigate to reset page
- Token validates: user exists AND token is not expired

### 4. User Sets New Password
- User enters new password and confirms it
- System validates:
  - Password is at least 6 characters
  - Passwords match
  - Token is still valid
- Password is hashed and updated in database
- Token is invalidated after use
- User redirected to login page

---

## Implementation Stages

### Stage 1: Current (Testing/Development)
**Status**: ✅ IMPLEMENTED

What works:
- All frontend pages created
- Token generation and validation
- Password update functionality
- Reset links displayed on page

```
User Flow:
Login Page → Forgot? → Enter Username → Get Link → Copy/Paste Link → Reset Password → Login
```

---

### Stage 2: Email Integration (Production Ready)
**Status**: ❌ NOT YET IMPLEMENTED

To send password reset links via email:

#### Step 1: Install Email Packages
```bash
pip install flask-mail
```

#### Step 2: Add Configuration to `app.py`
```python
# Add these imports
from flask_mail import Mail, Message

# Add email configuration after app initialization
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # or your email provider
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'  # Use App Password for Gmail
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@dentalopg.com'

mail = Mail(app)
```

#### Step 3: Create Email Helper Function
```python
def send_reset_email(user_email, username, reset_link):
    """Send password reset email to user"""
    msg = Message(
        subject='Password Reset Request - Dental OPG AI',
        recipients=[user_email],
        html=f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px;">
                    <h2>Password Reset Request</h2>
                    <p>Hello {username},</p>
                    <p>We received a request to reset your password. Click the link below to set a new password:</p>
                    <p>
                        <a href="{reset_link}" style="background-color: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </p>
                    <p>Or copy and paste this link: {reset_link}</p>
                    <p><strong>This link will expire in 30 minutes.</strong></p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">Do not reply to this email. This is an automated message.</p>
                </div>
            </body>
        </html>
        """
    )
    mail.send(msg)
```

#### Step 4: Update `forgot_password()` Route
Replace the TODO section:

```python
# Generate reset token
token = generate_reset_token(username)

# Send reset email
reset_link = url_for('reset_password', token=token, _external=True)

# Assuming User model has an email field
send_reset_email(user.email, user.username, reset_link)

return render_template('forgot_password.html',
                     success='Password reset link has been sent to your email. Check your inbox and spam folder.')
```

#### Step 5: Update User Model (if using email)
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Add this
    password = db.Column(db.String(255), nullable=False)
    scans = db.relationship('ScanHistory', backref='user', lazy=True, cascade='all, delete-orphan')
```

---

### Stage 3: Alternative - SMS/Phone Verification (Optional)
For SMS-based recovery, use Twilio:

```bash
pip install twilio
```

```python
from twilio.rest import Client

def send_reset_sms(phone_number, reset_link):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f'Reset your password: {reset_link}\nLink expires in 30 minutes.',
        from_=TWILIO_PHONE_NUMBER,
        to=phone_number
    )
    return message.sid
```

---

## Security Best Practices Implemented

✅ **Implemented:**
- Tokens use `secrets` module (cryptographically secure)
- Tokens are single-use (invalidated after password reset)
- 30-minute token expiration
- Passwords are hashed using `generate_password_hash()`
- Doesn't reveal if username exists on forgot page

⚠️ **Recommended for Production:**
- Use HTTPS/SSL (set `SESSION_COOKIE_SECURE=True`)
- Add rate limiting on forgot-password endpoint
- Log password reset attempts
- Send confirmation email after successful reset
- Require current password to reset if user is logged in
- Store tokens in database instead of memory (for multi-server deployments)

---

## Optional Enhancements

### 1. Add Security Questions
```python
class User(UserMixin, db.Model):
    # ... existing fields ...
    security_question = db.Column(db.String(255))
    security_answer = db.Column(db.String(255))  # hashed
```

### 2. Two-Factor Authentication
- Require email verification + SMS code
- Generated using `pyotp` package

### 3. Recovery Codes
- Generate backup codes during signup
- Allow password reset using recovery codes

### 4. Remember Device
- Store device fingerprints
- Skip 2FA on trusted devices

---

## Testing Checklist

### Development Testing
- [ ] Click "Forgot?" link on login page
- [ ] Enter valid username, get reset link
- [ ] Enter invalid username, confirm security message
- [ ] Copy reset link and paste in browser
- [ ] Verify token validation works
- [ ] Try expired token (wait 30+ minutes)
- [ ] Enter mismatched passwords
- [ ] Enter password < 6 characters
- [ ] Successfully reset password
- [ ] Login with new password

### Production Testing
- [ ] Email sending works
- [ ] Email contains clickable link
- [ ] Link works when clicked from email
- [ ] Rate limiting prevents abuse
- [ ] HTTPS/SSL enabled
- [ ] Confirmation email sent after reset
- [ ] Tokens only work once

---

## Database Migration (if adding email field)

```bash
# Using Flask-Migrate
flask db init
flask db migrate -m "Add email field to User model"
flask db upgrade
```

Or manually:
```python
# Run this in Python shell
from app import app, db, User

with app.app_context():
    # Add email column
    from sqlalchemy import String
    connection = db.engine.raw_connection()
    cursor = connection.cursor()
    cursor.execute('ALTER TABLE user ADD COLUMN email VARCHAR(120) UNIQUE')
    connection.commit()
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Token not working | Check if 30 minutes haven't passed; tokens stored in memory are cleared on app restart |
| Email not sending | Verify SMTP credentials, enable "Less secure apps" for Gmail, check spam folder |
| Reset link invalid | Ensure `_external=True` in `url_for()` and app is running on correct domain |
| Tokens lost on restart | Migrate token storage to database for production |

---

## Support for Alternative Recovery Methods

### Allow Password Reset by Email (without username)
```python
@app.route('/forgot-password-email', methods=['POST'])
def forgot_password_email():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    # ... similar logic ...
```

### Allow Unlock via Account Recovery Code
```python
class RecoveryCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    code = db.Column(db.String(8), unique=True)
    used = db.Column(db.Boolean, default=False)
```

---

## Summary

**Current Status**: Base functionality working ✅
- Frontend UI: Complete
- Token-based reset: Working
- Password update: Functional

**Next Step**: Integrate email sending or SMS for production use

For questions or issues, refer to Flask-Mail documentation or reach out to the development team.
