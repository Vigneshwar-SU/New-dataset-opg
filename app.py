import os
import numpy as np
import secrets
import time
from datetime import datetime, timedelta
from io import BytesIO
from flask import Flask, render_template, request, send_from_directory, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from tensorflow.keras.preprocessing import image
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib import colors

# Suppress TF warnings BEFORE importing model_loader
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Load environment variables from .env file
load_dotenv()

# Import model_loader which applies patches
from model_loader import load_model

# ----------------Flask App ----------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key_change_this'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath("users.db")}'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ----------------Database ----------------
db = SQLAlchemy(app)

# ----------------User Model ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    mobile = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    scans = db.relationship('ScanHistory', backref='user', lazy=True, cascade='all, delete-orphan')

# ----------------ScanHistory Model ----------------
class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    prediction = db.Column(db.String(80), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    image_path = db.Column(db.String(255), nullable=False)
    # Store probabilities as JSON string
    caries_prob = db.Column(db.Float, default=0.0)
    decayed_prob = db.Column(db.Float, default=0.0)
    ectopic_prob = db.Column(db.Float, default=0.0)
    healthy_prob = db.Column(db.Float, default=0.0)

# ----------------Login Manager ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------OTP and Password Reset Storage ----------------
# Stores OTP with format: {username: {'otp': otp_code, 'mobile': mobile_number, 'expiration': expiration_time}}
otp_storage = {}
# Stores password reset tokens with format: {token: {'username': username, 'expiration': expiration_time}}
password_reset_tokens = {}
OTP_EXPIRATION_MINUTES = 10  # OTP expires in 10 minutes
TOKEN_EXPIRATION_MINUTES = 30  # Token expires in 30 minutes

def validate_username_format(username):
    """
    Validate username follows DOCT format:
    - Starts with 'DOCT'
    - Followed by exactly 8 digits
    - Example: DOCT12345678
    """
    import re
    pattern = r'^DOCT\d{8}$'
    return re.match(pattern, str(username)) is not None

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(secrets.randbelow(999999)).zfill(6)

def format_phone_number(phone_number):
    """
    Format phone number to E.164 format required by Twilio Verify API.
    E.164 format: +<country_code><number> (e.g., +918248564527)
    
    If phone number doesn't start with +, assume it's Indian (+91)
    """
    # Remove any spaces, dashes, or special characters
    cleaned = ''.join(c for c in str(phone_number) if c.isdigit() or c == '+')
    
    # If already starts with +, assume it's correctly formatted
    if cleaned.startswith('+'):
        return cleaned
    
    # If it starts with country code (91 for India), add +
    if cleaned.startswith('91') and len(cleaned) >= 12:
        return '+' + cleaned
    
    # If it's 10 digits (Indian local format), prepend +91
    if len(cleaned) == 10:
        return '+91' + cleaned
    
    # Otherwise, return as-is with + prefix (caller may need to verify)
    return '+' + cleaned

def send_otp_sms(mobile_number, otp):
    """
    Send OTP via SMS using Twilio Verify API
    
    Twilio Verify handles OTP generation and delivery.
    Requires environment variables:
    - TWILIO_ACCOUNT_SID
    - TWILIO_AUTH_TOKEN
    - TWILIO_VERIFY_SERVICE_ID
    
    Returns: True if sent successfully, False otherwise
    """
    # Format phone number to E.164 format (required by Twilio)
    formatted_mobile = format_phone_number(mobile_number)
    
    # Get Twilio credentials from environment variables
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    TWILIO_VERIFY_SERVICE_ID = os.environ.get('TWILIO_VERIFY_SERVICE_ID', '').strip()
    
    # Check if credentials are configured
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_ID:
        # Development mode: print to console
        print(f"\n{'='*70}")
        print(f"[DEV MODE] OTP SENT TO: {mobile_number} (formatted: {formatted_mobile})")
        print(f"[DEV MODE] OTP CODE: {otp}")
        print(f"[DEV MODE] Valid for 10 minutes")
        print(f"{'='*70}\n")
        
        # Still log that credentials are missing
        print(f"⚠️  NOTE: To send real SMS, configure .env file with Twilio Verify credentials")
        print(f"   See .env.example for setup instructions\n")
        
        return True
    
    # Production mode: Send via Twilio Verify API
    try:
        from twilio.rest import Client
        
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send OTP via Twilio Verify API with formatted phone number
        verification = client.verify.v2.services(TWILIO_VERIFY_SERVICE_ID).verifications.create(
            to=formatted_mobile,
            channel='sms'
        )
        
        # Store verification SID for later verification
        otp_storage[mobile_number] = {
            'verification_sid': verification.sid,
            'expiration': time.time() + (OTP_EXPIRATION_MINUTES * 60)
        }
        
        print(f"✓ SMS OTP sent successfully to {formatted_mobile}")
        print(f"  Verification SID: {verification.sid}")
        print(f"  Status: {verification.status}")
        return True
        
    except ImportError:
        print(f"✗ ERROR: Twilio module not found")
        print(f"  Install with: pip install twilio")
        return False
        
    except Exception as e:
        print(f"✗ ERROR sending OTP via Twilio Verify: {str(e)}")
        return False

def store_otp(username, mobile_number):
    """Store mobile number for OTP verification"""
    # For Twilio Verify, we don't need to generate OTP ourselves
    # Twilio handles it. We just store the mobile number.
    otp_storage[username] = {
        'mobile': mobile_number,
        'expiration': time.time() + (OTP_EXPIRATION_MINUTES * 60)
    }
    return None  # Twilio generates the OTP

def check_otp(username, otp_entered):
    """Verify OTP against Twilio Verify API"""
    if username not in otp_storage:
        return False, "No OTP request found"
    
    otp_data = otp_storage[username]
    
    if time.time() > otp_data['expiration']:
        del otp_storage[username]
        return False, "OTP expired. Please request a new one."
    
    # Get Twilio credentials
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '').strip()
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '').strip()
    TWILIO_VERIFY_SERVICE_ID = os.environ.get('TWILIO_VERIFY_SERVICE_ID', '').strip()
    
    # Development mode: simple verification
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_VERIFY_SERVICE_ID:
        # In dev mode, accept any 6-digit code
        if len(str(otp_entered)) == 6 and str(otp_entered).isdigit():
            return True, "OTP verified successfully (DEV MODE)"
        else:
            return False, "Invalid OTP format. Please enter 6 digits."
    
    # Production mode: verify against Twilio
    try:
        from twilio.rest import Client
        
        mobile = otp_data['mobile']
        formatted_mobile = format_phone_number(mobile)
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Verify the code with Twilio using formatted number
        verification_check = client.verify.v2.services(TWILIO_VERIFY_SERVICE_ID).verification_checks.create(
            to=formatted_mobile,
            code=str(otp_entered)
        )
        
        if verification_check.status == 'approved':
            print(f"✓ OTP verified successfully for {formatted_mobile}")
            del otp_storage[username]
            return True, "OTP verified successfully"
        else:
            return False, f"OTP verification failed: {verification_check.status}"
            
    except Exception as e:
        print(f"✗ ERROR verifying OTP with Twilio: {str(e)}")
        return False, f"Verification error: {str(e)}"

def generate_reset_token(username):
    """Generate a unique reset token for password recovery"""
    token = secrets.token_urlsafe(32)
    expiration = time.time() + (TOKEN_EXPIRATION_MINUTES * 60)
    password_reset_tokens[token] = {
        'username': username,
        'expiration': expiration
    }
    return token

def verify_reset_token(token):
    """Verify if a reset token is valid and not expired"""
    if token not in password_reset_tokens:
        return None
    
    token_data = password_reset_tokens[token]
    if time.time() > token_data['expiration']:
        # Token expired, remove it
        del password_reset_tokens[token]
        return None
    
    return token_data['username']

# ----------------Initialize Database ----------------
with app.app_context():
    db.create_all()

# ----------------Load Model ----------------
print("Loading model...")
model = load_model('hypervision_OPG_model.h5')
print("Model loaded successfully!")

# ---------------- Model Settings ----------------
img_size = (299, 299)

class_dict = {
    0: 'Caries',
    1: 'Decayed Tooth',
    2: 'Ectopic',
    3: 'Healthy Teeth'
}

classes = list(class_dict.values())

# ---------------- Serve Uploaded Images ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ----------------Login Route ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

# ----------------Signup Route ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not mobile or not password or not confirm_password:
            return render_template('signup.html', error='All fields are required')
        
        if not validate_username_format(username):
            return render_template('signup.html', error='Username must follow format: DOCT + 8 digits (e.g., DOCT12345678)')
        
        if len(mobile) < 10:
            return render_template('signup.html', error='Please enter a valid mobile number')
        
        if len(password) < 6:
            return render_template('signup.html', error='Password must be at least 6 characters')
        
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('signup.html', error='Username already exists')
        
        # Check if mobile already exists
        existing_mobile = User.query.filter_by(mobile=mobile).first()
        if existing_mobile:
            return render_template('signup.html', error='This mobile number is already registered')
        
        # Create new user
        new_user = User(username=username, mobile=mobile, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# ----------------Forgot Password Route (OTP Based) ----------------
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        mobile = request.form.get('mobile')
        
        # Check if user exists
        user = User.query.filter_by(username=username).first()
        
        if not user:
            # For security, don't reveal if username exists
            return render_template('forgot_password.html', 
                                 error='Username or mobile number not found')
        
        # Verify mobile number matches
        if user.mobile != mobile:
            return render_template('forgot_password.html',
                                 error='Mobile number does not match the registered number')
        
        # Store OTP data and send OTP via Twilio Verify
        store_otp(username, mobile)
        otp_sent = send_otp_sms(mobile, None)
        
        if not otp_sent:
            return render_template('forgot_password.html',
                                 error='Failed to send OTP. Please try again.')
        
        # Redirect to OTP verification page
        return redirect(url_for('verify_otp', username=username))
    
    return render_template('forgot_password.html')

# ----------------OTP Verification Route ----------------
@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    username = request.args.get('username') or request.form.get('username')
    
    if not username:
        return render_template('forgot_password.html', error='Invalid request. Please start over.')
    
    if request.method == 'POST':
        otp_entered = request.form.get('otp')
        
        if not otp_entered:
            return render_template('otp_verification.html',
                                 username=username,
                                 error='Please enter the OTP')
        
        # Verify OTP
        is_valid, message = check_otp(username, otp_entered)
        
        if not is_valid:
            return render_template('otp_verification.html',
                                 username=username,
                                 error=message)
        
        # OTP verified, generate reset token and redirect to password reset
        token = generate_reset_token(username)
        return redirect(url_for('reset_password', token=token))
    
    return render_template('otp_verification.html', username=username)

# ----------------Reset Password Route ----------------
@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token') or request.form.get('token')
    
    if not token:
        return render_template('forgot_password.html', error='No token provided. Request a new password reset.')
    
    username = verify_reset_token(token)
    
    if not username:
        return render_template('forgot_password.html', error='Invalid or expired token. Please request a new password reset.')
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not new_password or not confirm_password:
            return render_template('reset_password.html', 
                                 token=token,
                                 error='All fields are required')
        
        if len(new_password) < 6:
            return render_template('reset_password.html',
                                 token=token,
                                 error='Password must be at least 6 characters')
        
        if new_password != confirm_password:
            return render_template('reset_password.html',
                                 token=token,
                                 error='Passwords do not match')
        
        # Get user to check old password
        user = User.query.filter_by(username=username).first()
        if user:
            # Check if new password is the same as old password
            if check_password_hash(user.password, new_password):
                return render_template('reset_password.html',
                                     token=token,
                                     error='New password cannot be the same as your old password. Please create a different password.')
            
            # Update user password
            user.password = generate_password_hash(new_password)
            db.session.commit()
            
            # Remove used token
            if token in password_reset_tokens:
                del password_reset_tokens[token]
            
            return redirect(url_for('login'))
    
    
    return render_template('reset_password.html', token=token)

# ----------------Logout Route ----------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ----------------Main Route ----------------
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    prediction_label = None
    class_prob_pairs = None
    image_path = None

    if request.method == 'POST':
        file = request.files.get('image')

        if file and file.filename != '':
            filename = file.filename
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            # ----- Image Preprocessing -----
            img = image.load_img(save_path, target_size=img_size)
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = img_array / 255.0

            # ----- Prediction -----
            preds = model.predict(img_array)
            class_index = np.argmax(preds, axis=1)[0]
            prediction_label = classes[class_index]

            class_prob_pairs = list(zip(classes, preds[0]))

            # IMPORTANT: browser-accessible URL
            image_path = f"/uploads/{filename}"
            
            # Save to scan history with probabilities
            scan = ScanHistory(
                user_id=current_user.id,
                filename=filename,
                prediction=prediction_label,
                image_path=image_path,
                caries_prob=float(preds[0][0]) * 100,
                decayed_prob=float(preds[0][1]) * 100,
                ectopic_prob=float(preds[0][2]) * 100,
                healthy_prob=float(preds[0][3]) * 100
            )
            db.session.add(scan)
            db.session.commit()

    return render_template(
        'index.html',
        prediction=prediction_label,
        class_prob_pairs=class_prob_pairs,
        image_path=image_path
    )

# ----------------Scan History Route ----------------
@app.route('/scan-history')
@login_required
def scan_history():
    scans = ScanHistory.query.filter_by(user_id=current_user.id).order_by(ScanHistory.timestamp.desc()).all()
    return render_template('scan_history.html', scans=scans)

# ----------------Download Scan Report as PDF ----------------
@app.route('/download-report/<int:scan_id>')
@login_required
def download_report(scan_id):
    scan = ScanHistory.query.get_or_404(scan_id)
    
    # Check if user owns this scan
    if scan.user_id != current_user.id:
        return redirect(url_for('scan_history'))
    
    # Create PDF
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#3b82f6'),
        spaceAfter=12,
        alignment=1  # Center alignment
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a202c'),
        spaceAfter=10,
        spaceBefore=10
    )
    
    # Elements
    elements = []
    
    # Title
    elements.append(Paragraph("Dental OPG AI Diagnostic Report", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Report Info
    report_info = [
        ['Patient ID:', current_user.username],
        ['Scan Date:', scan.timestamp.strftime('%B %d, %Y')],
        ['Scan Time:', scan.timestamp.strftime('%I:%M %p')],
        ['Report Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')]
    ]
    
    info_table = Table(report_info, colWidths=[1.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f4ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Add Scan Image
    elements.append(Paragraph("OPG X-Ray Scan", heading_style))
    
    try:
        # Get the image file path
        image_filename = scan.image_path.split('/')[-1]
        full_image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        
        if os.path.exists(full_image_path):
            img = RLImage(full_image_path, width=4*inch, height=3*inch)
            elements.append(img)
            elements.append(Spacer(1, 0.2*inch))
    except:
        pass
    
    # Prediction Result
    elements.append(Paragraph("Analysis Results", heading_style))
    
    result_table = [
        ['Predicted Classification:', scan.prediction],
        ['Filename:', scan.filename]
    ]
    
    result_table_obj = Table(result_table, colWidths=[2*inch, 4*inch])
    result_table_obj.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
    ]))
    
    elements.append(result_table_obj)
    elements.append(Spacer(1, 0.3*inch))
    
    # Confidence Scores
    elements.append(Paragraph("Confidence Scores", heading_style))
    
    confidence_data = [
        ['Classification', 'Confidence'],
        ['Caries', f'{scan.caries_prob:.1f}%'],
        ['Decayed Tooth', f'{scan.decayed_prob:.1f}%'],
        ['Ectopic', f'{scan.ectopic_prob:.1f}%'],
        ['Healthy Teeth', f'{scan.healthy_prob:.1f}%']
    ]
    
    conf_table = Table(confidence_data, colWidths=[2.5*inch, 2*inch])
    conf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')])
    ]))
    
    elements.append(conf_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Classification Legend
    elements.append(Paragraph("Classification Categories", heading_style))
    
    legend_text = """
    <b>Caries:</b> Tooth decay and cavity formation<br/>
    <b>Decayed Tooth:</b> Severely decayed or damaged teeth<br/>
    <b>Ectopic:</b> Abnormally positioned teeth<br/>
    <b>Healthy Teeth:</b> Normal, healthy tooth structures<br/>
    """
    elements.append(Paragraph(legend_text, styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Disclaimer
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#7c3aed'),
        alignment=0
    )
    
    disclaimer_text = """
    <b>DISCLAIMER:</b> This AI diagnostic tool is intended for educational and research purposes only. 
    It should not be used as a substitute for professional dental diagnosis or treatment. 
    All results should be reviewed by a qualified dental professional before clinical use.
    """
    elements.append(Paragraph(disclaimer_text, disclaimer_style))
    
    # Build PDF
    doc.build(elements)
    pdf_buffer.seek(0)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'dental_report_{scan.user.username}_{scan.timestamp.strftime("%Y%m%d_%H%M%S")}.pdf'
    )

# ---------------- Run App ----------------
if __name__ == '__main__':
    app.run(debug=True)
