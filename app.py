from flask import Flask, redirect, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from flask import session
from functools import wraps
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mail import Mail, Message
import random, string
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import os
from dotenv import load_dotenv

load_dotenv()

def generate_ref_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))








# -------------------
# App config
# -------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)

db = SQLAlchemy(app)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_port=1
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",  # if cross-domain
    SESSION_COOKIE_SECURE=True,      # only if HTTPS
    PERMANENT_SESSION_LIFETIME=86400
)




# -------------------
# Database models
# -------------------


class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    crypto = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_id = db.Column(db.String(64), unique=True, nullable=True)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.now())



class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    plan_id = db.Column(db.Integer, nullable=False)
    amount_usd = db.Column(db.Float, nullable=False)
    crypto = db.Column(db.String(10), nullable=False)
    crypto_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=db.func.now())
    last_payout_at = db.Column(db.DateTime, nullable=True)


class Deposit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    crypto = db.Column(db.String(10), nullable=False, default='usdt')
    tx_id = db.Column(db.String(64), unique=True, nullable=False)
    status = db.Column(db.String(20), default="completed")
    created_at = db.Column(db.DateTime, default=db.func.now())
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # allow admin without email
    fullname = db.Column(db.String(100), nullable=True)
    withdrawal_frozen = db.Column(db.Boolean, default=False)
 
    btc_balance = db.Column(db.Float, default=0.0)
    eth_balance = db.Column(db.Float, default=0.0)
    usdt_balance = db.Column(db.Float, default=0.0)
    bnb_balance = db.Column(db.Float, default=0.0)

    # Wallet Addresses
    btc_address = db.Column(db.String(100), nullable=True)
    eth_address = db.Column(db.String(100), nullable=True)
    usdt_address = db.Column(db.String(100), nullable=True)
    bnb_address = db.Column(db.String(100), nullable=True)

    is_admin = db.Column(db.Boolean, default=False)
    referral_code = db.Column(db.String(20), unique=True)
    referred_by = db.Column(db.String(20), nullable=True)
    referral_earnings = db.Column(db.Float, default=0.0)
    
    # Password recovery fields
    recovery_code = db.Column(db.String(6), nullable=True)
    recovery_code_expires = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=db.func.now())


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def set_mpassword(self, mpassword):
        self.mpassword_hash = generate_password_hash(mpassword)

    def check_mpassword(self, mpassword):
        if not self.mpassword_hash:
            return False
        return check_password_hash(self.mpassword_hash, mpassword)
    def send_email(to, subject, body):
     try:
        msg = Message(subject, recipients=[to])
        msg.body = body
        mail.send(msg)
     except Exception as e:
        print("EMAIL ERROR:", e)

with app.app_context():
    db.create_all()
with app.app_context():
    if not User.query.filter_by(username="Achor").first():
        admin = User(
            username="Achor",
            is_admin=True
        )
        admin.set_password("Achokaka222")
        db.session.add(admin)
        db.session.commit()

def send_welcome_email(email, username):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Welcome to Global Energy</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,

            <p>We’re excited to welcome you to <b>Global Energy</b>.  
            Your account has been successfully created and you can now access your dashboard.</p>

            <p>If you need any assistance, our support team is available 24/7.</p>

            <p>Best regards,<br>
            <b>Global Energy Team</b><br>
            https://globalenergy.trade</p>

        </div>
        </body>
        </html>
        """

        msg = Message(
            subject="Welcome to Global Energy",
            recipients=[email],
        )
        msg.html = html_body
        mail.send(msg)

        print("Welcome email sent to:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

def send_referral_signup_email(referrer_email, referrer_username, new_username, new_email):
    """Send email to referrer when someone signs up using their referral link"""
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">🎉 New Referral Signup!</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{referrer_username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Great news! Someone just signed up using your referral link! 🎊
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">New User:</p>
                <p style="color:#00ff88;font-size:15px;font-weight:600;margin:0 0 10px 0;">
                    {new_username}
                </p>
                
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Email:</p>
                <p style="color:#fff;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                    {new_email}
                </p>
            </div>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                When they make their first deposit, you'll receive <b style="color:#00ff88;">5% commission</b> automatically! 💰
            </p>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">✓ Active Referral</span></p>
            </div>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                Keep referring users to earn more commissions!<br>
                <b>Global Energy Team</b><br>
                https://globalenergy.trade
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message(
            subject="🎉 New Referral Signup - Global Energy",
            recipients=[referrer_email],
        )
        msg.html = html_body
        mail.send(msg)

        print(f"[REFERRAL] Signup notification sent to {referrer_username} ({referrer_email}) for new user {new_username}")

    except Exception as e:
        print(f"[REFERRAL] EMAIL ERROR sending signup notification: {e}")

def send_credit_email(email, username, coin, amount, user_wallet_address, company_wallet_address, tx_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Hello {username},</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                You successfully received <b style="color:#00ff88;">${amount:.2f}</b> in your <b>{coin.upper()}</b> wallet.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Transaction ID:</p>
                <p style="color:#00ff88;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                    {tx_id if tx_id else 'N/A'}
                </p>
            </div>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">From (Company Wallet):</p>
                <p style="color:#fff;font-size:12px;word-break:break-all;margin:0 0 15px 0;font-family:monospace;">
                    {company_wallet_address}
                </p>
                
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">To (Your Wallet):</p>
                <p style="color:#fff;font-size:12px;word-break:break-all;margin:0;font-family:monospace;">
                    {user_wallet_address}
                </p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">Completed</span></p>
            </div>

                <p style="color:#888;font-size:13px;margin-top:25px;">
                    Thanks for choosing us.
                </p>

        </div>
        </body>
        </html>
        """

        msg = Message(
            subject="Credit Alert - Global Energy",
            recipients=[email],
        )
        msg.html = html_body
        mail.send(msg)

        print("Credit alert sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)
def send_referral_commission_email(email, username, coin, amount, user_wallet_address, company_wallet_address, tx_id=None):
        try:
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
            <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
                <div style="text-align:center;margin-bottom:20px;">
                    <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
                </div>

                <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Referral Commission Received</p>

                <p style="color:#eee;font-size:15px;line-height:1.6;">
                    Hello <b style="color:#00ff88;">{username}</b>,
                </p>

                <p style="color:#eee;font-size:15px;line-height:1.6;">
                    You just received a referral commission of <b style="color:#00ff88;">${amount:.2f}</b> ({coin.upper()}) from a referred user's deposit.
                </p>

                <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                    <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Transaction ID:</p>
                    <p style="color:#00ff88;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                        {tx_id if tx_id else 'N/A'}
                    </p>
                </div>

                <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                    <p style="color:#888;font-size:12px;margin:0 0 5px 0;">From (Company Wallet):</p>
                    <p style="color:#fff;font-size:12px;word-break:break-all;margin:0 0 15px 0;font-family:monospace;">
                        {company_wallet_address}
                    </p>
                
                    <p style="color:#888;font-size:12px;margin:0 0 5px 0;">To (Your Wallet):</p>
                    <p style="color:#fff;font-size:12px;word-break:break-all;margin:0;font-family:monospace;">
                        {user_wallet_address}
                    </p>
                </div>

                <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                    <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">Completed</span></p>
                </div>

                    <p style="color:#888;font-size:13px;margin-top:25px;">
                        Thanks for referring users to Global Energy.
                    </p>

            </div>
            </body>
            </html>
            """

            msg = Message(
                subject="Referral Commission - Global Energy",
                recipients=[email],
            )
            msg.html = html_body
            mail.send(msg)

            print("Referral commission email sent:", email)

        except Exception as e:
            print("EMAIL ERROR:", e)
def send_withdraw_request_email(email, username, coin, amount, tx_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Withdrawal Request Received</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Your withdrawal request has been successfully submitted and is under review.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Amount:</p>
                <p style="color:#00ff88;font-size:16px;font-weight:600;margin:0 0 15px 0;">
                    {amount} {coin.upper()}
                </p>
                
                {f'<p style="color:#888;font-size:12px;margin:0 0 5px 0;">Transaction ID:</p><p style="color:#fff;font-size:12px;word-break:break-all;margin:0;font-family:monospace;">{tx_id}</p>' if tx_id else ''}
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#ffc107;font-weight:600;">Pending Review</span></p>
            </div>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                You will be notified once it is processed.
            </p>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                Thanks for using Global Energy.
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message("Withdrawal Request Submitted", recipients=[email])
        msg.html = html_body
        mail.send(msg)

    except Exception as e:
        print("EMAIL ERROR:", e)
def send_withdraw_processing_email(email, username, coin, amount, tx_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Withdrawal Processing</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Your withdrawal request is being processed by our finance team.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Amount:</p>
                <p style="color:#00ff88;font-size:16px;font-weight:600;margin:0 0 15px 0;">
                    {amount} {coin.upper()}
                </p>
                
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Transaction ID:</p>
                <p style="color:#00ff88;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                    {tx_id if tx_id else 'N/A'}
                </p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#ffc107;font-weight:600;">Processing</span></p>
            </div>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Funds will be sent shortly. Please be patient while we complete the transaction.
            </p>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                Thanks for choosing Global Energy.
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message("Withdrawal Processing - Global Energy", recipients=[email])
        msg.html = html_body
        mail.send(msg)

        print("Processing email sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

def send_investment_received_email(email, username, coin, amount_usd, crypto_amount, inv_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Investment Received</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                We have received your investment request of <b style="color:#00ff88;">${amount_usd:.2f}</b> ({coin.upper()}) and it is currently under review.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Investment ID:</p>
                <p style="color:#00ff88;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                    {inv_id if inv_id else 'N/A'}
                </p>
                <p style="color:#888;font-size:12px;margin:10px 0 5px 0;">Crypto Amount:</p>
                <p style="color:#fff;font-size:13px;margin:0;font-family:monospace;">{crypto_amount} {coin.upper()}</p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#ffc107;font-weight:600;">Pending Review</span></p>
            </div>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                You will be notified once your investment is approved.
            </p>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                Thanks for investing with Global Energy.
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message("Investment Received - Global Energy", recipients=[email])
        msg.html = html_body
        mail.send(msg)

        print("Investment received email sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

def send_investment_approved_email(email, username, coin, amount_usd, crypto_amount, inv_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Investment Approved</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Your investment of <b style="color:#00ff88;">${amount_usd:.2f}</b> ({coin.upper()}) has been approved and is now active.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Investment ID:</p>
                <p style="color:#00ff88;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                    {inv_id if inv_id else 'N/A'}
                </p>
                <p style="color:#888;font-size:12px;margin:10px 0 5px 0;">Crypto Amount:</p>
                <p style="color:#fff;font-size:13px;margin:0;font-family:monospace;">{crypto_amount} {coin.upper()}</p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">Approved</span></p>
            </div>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                Thanks for investing with Global Energy.
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message("Investment Approved - Global Energy", recipients=[email])
        msg.html = html_body
        mail.send(msg)

        print("Investment approved email sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

def send_investment_profit_email(email, username, coin, profit_amount_usd, inv_id=None, periods=1):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>
            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Investment Payout Received</p>
            <p style="color:#eee;font-size:15px;line-height:1.6;">Hello <b style="color:#00ff88;">{username}</b>,</p>
            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">A payout of <b style="color:#00ff88;">${profit_amount_usd:.2f}</b> has been added to your account for investment <b>{inv_id if inv_id else 'N/A'}</b> ({periods} period{'s' if periods!=1 else ''}).</p>
            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">Credited</span></p>
            </div>
            <p style="color:#888;font-size:13px;margin-top:25px;">Thanks for investing with Global Energy.</p>
        </div>
        </body>
        </html>
        """

        msg = Message("Investment Payout - Global Energy", recipients=[email])
        msg.html = html_body
        mail.send(msg)

        print("Investment payout email sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)


# -------------------
# Create DB
# -------------------

# =====================================================
# =============== PAGE ROUTES (HTML) ==================
# =====================================================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get("user_id")

        if not user_id:
            return jsonify({"error": "Login required"}), 401

        user = User.query.get(session["user_id"])


        if not user or not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated
@app.route("/api/referrals")
def get_referrals():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session["user_id"])

    # Get users referred by this user
    referred = User.query.filter_by(referred_by=user.username).all()

    return jsonify({
        "referral_code": user.referral_code,
        "referral_link": f"https://globalenergy.trade/signup?ref={user.username}",
        "total_referral_earnings": user.referral_earnings or 0.0,
        "referrals": [
            {
                "username": u.username,
                "email": u.email,
                "date": u.created_at.strftime("%B %d, %Y") if u.created_at else "Unknown"
            } for u in referred
        ]
    })

@app.route("/edit")
def edit_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "edit.html")

@app.route("/earnings-history")
def earnings_history_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "earnings-history.html")

@app.route("/withdrawal-history")
def withdrawal_history_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "withdrawal-history.html")

@app.route("/deposit-history")
def deposit_history_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "deposit-history.html")

@app.route("/ping")
def ping():
    return "ok", 200

@app.route("/")
def home():
    return send_from_directory("scraped_site", "Home.html")

@app.route("/about")
def about():
    return send_from_directory("aboutus", "About.html")

@app.route("/contact-us")
def contact_page():
    return send_from_directory("aboutscraped_site", "Contact-us.html")

@app.route("/login")
def login_page():
    return send_from_directory("login", "login.html")

@app.route("/signup")
def signup_page():
    return send_from_directory("signup", "signup.html")

@app.route("/admin")
@admin_required
def admin_page():
    return send_from_directory("ADMIN", "admin.html")

@app.route("/css/<path:filename>")
def css(filename):
    return send_from_directory("scraped_site/css", filename)

@app.route("/js/<path:filename>")
def js(filename):
    return send_from_directory("scraped_site/js", filename)

@app.route("/img/<path:filename>")
def img(filename):
    return send_from_directory("scraped_site/img", filename)

@app.route("/login/<path:filename>")
def serve_login_files(filename):
    return send_from_directory("login", filename)
@app.route("/signup/<path:filename>")
def serve_signup_files(filename):
    return send_from_directory("signup", filename)
@app.route("/gold")
def gold_page():
    return send_from_directory("gold", "gold.html")

@app.route("/gold/<path:filename>")
def gold_assets(filename):
    return send_from_directory("gold", filename)
@app.route("/forex")
def forex_page():
    return send_from_directory("forex", "forex.html")

@app.route("/forex/<path:filename>")
def forex_assets(filename):
    return send_from_directory("forex", filename)
@app.route("/recovery")
def recovery_page():
    return send_from_directory("recovery", "recovery.html")

@app.route("/recovery/<path:filename>")
def recovery_assets(filename):
    return send_from_directory("recovery", filename)
@app.route("/fonts/<path:filename>")
def fonts(filename):
    return send_from_directory("scraped_site/fonts", filename)

@app.route("/about/img/<path:filename>")
def about_images(filename):
    return send_from_directory("aboutus/img", filename)

@app.route("/contact/img/<path:filename>")
def contact_images(filename):
    return send_from_directory("aboutscraped_site/img", filename)
@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "account.html")

@app.route("/deposit")
def deposit_page():
    return send_from_directory("ACCOUNT", "deposit.html")
# ================= ACCOUNT STATIC FILES =================

@app.route("/account/css/<path:filename>")
def account_css(filename):
    return send_from_directory("ACCOUNT/css", filename)

@app.route("/account/img/<path:filename>")
def account_img(filename):
    return send_from_directory("ACCOUNT/img", filename)

@app.route("/account/js/<path:filename>")
def account_js(filename):
    return send_from_directory("ACCOUNT/js", filename)

@app.route("/transactions")
def transactions_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "transactions.html")
@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")
@app.route("/referral")
def referrals_page():
    if "user_id" not in session:
        return redirect("/login")
    return send_from_directory("ACCOUNT", "referral.html")



# =====================================================
# ================= API ROUTES ========================
# =====================================================

# ---------- REGISTER ----------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    ref_code = data.get("ref")   # referral code from link

    # Validate input
    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    # Check username
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    # Create new user
    user = User(username=username, email=email, referral_code=generate_ref_code())
    user.set_password(password)

    # Handle referral
    referrer = None
    if ref_code:
        referrer = User.query.filter_by(username=ref_code).first()
        if referrer:
            user.referred_by = ref_code

    db.session.add(user)
    db.session.commit()

    # Send welcome email to new user
    try:
        send_welcome_email(email, username)
    except Exception as e:
        print("Email failed:", e)

    # Send referral signup notification to referrer
    if referrer and referrer.email:
        try:
            send_referral_signup_email(referrer.email, referrer.username, username, email)
        except Exception as e:
            print(f"[REFERRAL] Failed to send signup notification: {e}")

    return jsonify({"message": "Registration successful"})


@app.route("/api/update-profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user = User.query.get(session["user_id"])

    fullname = data.get("fullname")
    email = data.get("email")
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if fullname is not None:
        user.fullname = fullname

    if email:
        if User.query.filter_by(email=email).first() and email != user.email:
            return jsonify({"error": "Email already in use"}), 400
        user.email = email

    if new_password:
        if not current_password or not user.check_password(current_password):
            return jsonify({"error": "Current password is incorrect"}), 400
        user.set_password(new_password)

    # Wallet addresses - save if provided
    btc_address = data.get("btc_address")
    eth_address = data.get("eth_address")
    usdt_address = data.get("usdt_address")
    bnb_address = data.get("bnb_address")

    if btc_address is not None:
        user.btc_address = btc_address
    if eth_address is not None:
        user.eth_address = eth_address
    if usdt_address is not None:
        user.usdt_address = usdt_address
    if bnb_address is not None:
        user.bnb_address = bnb_address

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"})

@app.route("/api/earnings-history")
def earnings_history():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    user = User.query.get(user_id)

    # For now, return referral earnings as one entry
    earnings = []
    if user.referral_earnings > 0:
        earnings.append({
            "type": "referral",
            "amount": user.referral_earnings,
            "description": "Referral bonus",
            "created_at": user.created_at.isoformat()
        })

    # Add investment returns (dummy for now)
    investments = Investment.query.filter_by(user_id=user_id, status="approved").all()
    for inv in investments:
        earnings.append({
            "type": "investment",
            "amount": inv.amount_usd * 0.05,  # 5% return
            "description": f"Return from {inv.crypto.upper()} plan {inv.plan_id}",
            "created_at": inv.created_at.isoformat()
        })

    total = sum(e["amount"] for e in earnings)
    return jsonify({"earnings": earnings, "total_earnings": total})

@app.route("/api/recent-transactions")
def recent_transactions():
    """Get recent deposits and withdrawals for public display"""
    limit = 10
    
    # Get recent withdrawals (all statuses to show activity)
    withdrawals = Withdrawal.query.order_by(Withdrawal.created_at.desc()).limit(limit).all()
    
    withdrawal_data = []
    for w in withdrawals:
        user = User.query.get(w.user_id)
        withdrawal_data.append({
            "type": "withdrawal",
            "username": user.username if user else "Unknown",
            "amount": w.amount,
            "crypto": w.crypto.upper(),
            "transaction_id": (w.tx_id if getattr(w, 'tx_id', None) else f"{w.crypto.upper()[-1]}{w.id}"),
            "created_at": w.created_at.isoformat()
        })
    
    # Get recent deposits (all statuses to show activity)
    deposits = Deposit.query.order_by(Deposit.created_at.desc()).limit(limit).all()

    deposit_data = []
    for d in deposits:
        user = User.query.get(d.user_id)
        deposit_data.append({
            "type": "deposit",
            "username": user.username if user else "Unknown",
            "amount": d.amount,
            "crypto": d.crypto.upper(),
            "transaction_id": d.tx_id,
            "created_at": d.created_at.isoformat()
        })

    return jsonify({
        "deposits": deposit_data,
        "withdrawals": withdrawal_data
    })


@app.route("/api/recent-investments")
def recent_investments():
    try:
        limit = 10
        investments = Investment.query.order_by(Investment.id.desc()).limit(limit).all()
        invest_data = []
        for i in investments:
            try:
                user = User.query.get(i.user_id)
                invest_data.append({
                    "id": i.id,
                    "username": user.username if user else "Unknown",
                    "plan": i.plan_id,
                    "amount_usd": i.amount_usd,
                    "crypto": (i.crypto or "N/A").upper(),
                    "crypto_amount": i.crypto_amount,
                    "status": i.status,
                    "created_at": i.created_at.isoformat() if i.created_at else None
                })
            except Exception as row_err:
                print("Row error:", row_err)
                continue
        return jsonify({"investments": invest_data})
    except Exception as e:
        print("recent_investments error:", e)
        return jsonify({"investments": [], "error": str(e)}), 500

@app.route("/api/deposit-history")
def deposit_history():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session["user_id"]
    deposits = Deposit.query.filter_by(user_id=user_id).order_by(Deposit.created_at.desc()).all()

    total = sum(d.amount for d in deposits)
    return jsonify({
        "deposits": [{
            "id": d.id,
            "amount": d.amount,
            "crypto": d.crypto,
            "tx_hash": d.tx_id,
            "status": d.status,
            "created_at": d.created_at.isoformat()
        } for d in deposits],
        "total_deposits": total
    })

@app.route("/api/withdrawal-history")
def withdrawal_history():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session["user_id"]
    withdrawals = Withdrawal.query.filter_by(user_id=user_id).all()

    total = sum(w.amount for w in withdrawals)
    return jsonify({
        "withdrawals": [{
            "id": w.id,
            "crypto": w.crypto,
            "amount": w.amount,
            "tx_hash": w.tx_id,
            "status": w.status,
            "created_at": w.created_at.isoformat()
        } for w in withdrawals],
        "total_withdrawals": total
    })

@app.route("/api/withdraw", methods=["POST"])
def withdraw_request():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user = User.query.get(session["user_id"])

    crypto = data.get("crypto")
    amount = float(data.get("amount", 0))

    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    balance_field_map = {
        "btc": "btc_balance",
        "eth": "eth_balance",
        "usdt": "usdt_balance",
        "bnb": "bnb_balance"
    }

    if crypto not in balance_field_map:
        return jsonify({"error": "Invalid wallet"}), 400

    balance_field = balance_field_map[crypto]
    current_balance = float(getattr(user, balance_field) or 0.0)

    if user.withdrawal_frozen:
        return jsonify({"error": "Your account is currently restricted from withdrawing. Please contact the management for enquiries."}), 403

    if current_balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    # Freeze the balance immediately so user can't spend it twice
    setattr(user, balance_field, current_balance - amount)
    db.session.flush()  # write to DB before creating withdrawal record

    withdrawal = Withdrawal(
        user_id=user.id,
        crypto=crypto,
        amount=amount
    )

    # generate tx id and save it on the withdrawal
    tx_id = f"WD{secrets.token_hex(8)}"
    withdrawal.tx_id = tx_id

    db.session.add(withdrawal)
    db.session.commit()

    if user.email:
        # notify user that request was received (include tx id)
        send_withdraw_request_email(user.email, user.username, withdrawal.crypto, withdrawal.amount, tx_id)
        # also send a processing notification
        send_withdraw_processing_email(user.email, user.username, withdrawal.crypto, withdrawal.amount, tx_id)


    return jsonify({
        "message": "Withdrawal request sent for approval",
        "status": "pending"
    })
@app.route("/admin/api/investments")
@admin_required
def admin_investments():
    investments = Investment.query.filter_by(status="pending").all()

    return jsonify([
        {
            "id": i.id,
            "user_id": i.user_id,
            "username": User.query.get(i.user_id).username if User.query.get(i.user_id) else "Unknown",
            "plan": i.plan_id,
            "amount": i.amount_usd,
            "crypto": i.crypto
        } for i in investments
    ])
@app.route("/admin/api/investments/approve", methods=["POST"])
@admin_required
def approve_investment():
    data = request.json
    inv = Investment.query.get(data["id"])

    if not inv or inv.status != "pending":
        return jsonify({"error": "Invalid investment"}), 400

    inv.status = "approved"
    # initialize payout timer from approval time
    inv.last_payout_at = datetime.utcnow()
    db.session.commit()

    # Notify user via email (if available)
    try:
        user = User.query.get(inv.user_id)
        if user and user.email:
            send_investment_approved_email(user.email, user.username, inv.crypto, inv.amount_usd, inv.crypto_amount, inv.id)
    except Exception as e:
        print("Error sending investment approved email:", e)

    return jsonify({"message": "Investment approved"})
@app.route("/admin/api/deposits")
@admin_required
def admin_deposits():
    deposits = Deposit.query.filter_by(status="pending").all()

    return jsonify([
        {
            "id": d.id,
            "user_id": d.user_id,
            "username": User.query.get(d.user_id).username if User.query.get(d.user_id) else "Unknown",
            "amount": d.amount,
            "crypto": d.crypto,
            "tx_id": d.tx_id,
            "created_at": d.created_at.isoformat()
        } for d in deposits
    ])


@app.route("/admin/api/deposits/approve", methods=["POST"])
@admin_required
def approve_deposit():
    data = request.json
    d = Deposit.query.get(data.get("id"))

    if not d or d.status != "pending":
        return jsonify({"error": "Invalid deposit"}), 400

    user = User.query.get(d.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Credit the user's balance (assume amount is in the crypto's native unit for non-USDT, and USD for USDT)
    if d.crypto == "btc":
        user.btc_balance = (user.btc_balance or 0) + d.amount
    elif d.crypto == "eth":
        user.eth_balance = (user.eth_balance or 0) + d.amount
    elif d.crypto == "bnb":
        user.bnb_balance = (user.bnb_balance or 0) + d.amount
    else:
        # default to usdt
        user.usdt_balance = (user.usdt_balance or 0) + d.amount

    # Prepare for potential referral commission
    ref_to_notify = None
    commission_amount = 0.0
    if user.referred_by:
        ref = User.query.filter_by(referral_code=user.referred_by).first()
        if ref and ref.id != user.id:
            commission_amount = d.amount * 0.05
            if d.crypto == "btc":
                ref.btc_balance = (ref.btc_balance or 0) + commission_amount
            elif d.crypto == "eth":
                ref.eth_balance = (ref.eth_balance or 0) + commission_amount
            elif d.crypto == "bnb":
                ref.bnb_balance = (ref.bnb_balance or 0) + commission_amount
            else:
                ref.usdt_balance = (ref.usdt_balance or 0) + commission_amount

            ref.referral_earnings = (ref.referral_earnings or 0) + commission_amount
            ref_to_notify = (ref, commission_amount)

    d.status = "completed"
    db.session.commit()

    # Notify user by email
    if user.email:
        company_wallets = {
            "btc": "bc1qvlp57rkah6rxz7672fekk57w7y7ecwqy6duhgc",
            "eth": "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff",
            "usdt": "TGmZxR8f9r8gq1bmHqbKdY5MkB7wEw8TBA",
            "bnb": "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff"
        }
        company_wallet = company_wallets.get(d.crypto, "N/A")
        user_wallet = getattr(user, f"{d.crypto}_address", "N/A") if hasattr(user, f"{d.crypto}_address") else "N/A"
        try:
            send_credit_email(user.email, user.username, d.crypto, d.amount, user_wallet, company_wallet, d.tx_id)
        except Exception as e:
            print("Failed to send credit email:", e)

    # If a referrer was credited, notify them by email
    if ref_to_notify:
        ref, amt = ref_to_notify
        try:
            company_wallet = company_wallets.get(d.crypto, "N/A")
            wallet_attr = f"{d.crypto}_address"
            ref_wallet = getattr(ref, wallet_attr, None) or "N/A"
            if ref.email:
                send_referral_commission_email(ref.email, ref.username, d.crypto, amt, ref_wallet, company_wallet, d.tx_id)
                print(f"Referral commission email sent to {ref.email} for ${amt:.2f}")
            else:
                print(f"WARNING: Referrer {ref.username} has no email address")
        except Exception as e:
            print(f"ERROR: Failed to send referral commission email: {e}")
            import traceback
            traceback.print_exc()

    return jsonify({"message": "Deposit approved and user credited"})
@app.route("/admin/api/withdrawals")
@admin_required
def admin_withdrawals():
    withdrawals = Withdrawal.query.filter_by(status="pending").all()

    return jsonify([
        {
            "id": w.id,
            "user_id": w.user_id,
            "username": User.query.get(w.user_id).username if User.query.get(w.user_id) else "Unknown",
            "crypto": w.crypto,
            "amount": w.amount,
            "tx_id": w.tx_id
        } for w in withdrawals
    ])
@app.route("/admin/api/withdrawals/approve", methods=["POST"])
@admin_required
def approve_withdrawal():
    data = request.json
    w = Withdrawal.query.get(data["id"])

    if not w or w.status != "pending":
        return jsonify({"error": "Invalid withdrawal"}), 400

    user = User.query.get(w.user_id)
    w.status = "approved"
    db.session.commit()

    # Use fixed company wallet addresses only (company addresses are unchangeable)
    if user.email:
        company_wallets = {
            "btc": "bc1qvlp57rkah6rxz7672fekk57w7y7ecwqy6duhgc",
            "eth": "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff",
            "usdt": "TGmZxR8f9r8gq1bmHqbKdY5MkB7wEw8TBA",
            "bnb": "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff"
        }

        company_wallet = company_wallets.get(w.crypto, "N/A")
        user_wallet = getattr(user, f"{w.crypto}_address", None) or "N/A"
        send_withdrawal_approved_email(user.email, user.username, w.crypto, w.amount, user_wallet, company_wallet, w.tx_id)

    return jsonify({"message": "Withdrawal approved"})
@app.route("/admin/api/freeze-withdrawal", methods=["POST"])
@admin_required
def freeze_withdrawal():
    data = request.json
    user = User.query.get(data["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.withdrawal_frozen = True
    db.session.commit()
    return jsonify({"message": f"{user.username} withdrawal frozen"})

@app.route("/admin/api/unfreeze-withdrawal", methods=["POST"])
@admin_required
def unfreeze_withdrawal():
    data = request.json
    user = User.query.get(data["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.withdrawal_frozen = False
    db.session.commit()
    return jsonify({"message": f"{user.username} withdrawal unfrozen"})
def send_withdrawal_approved_email(email, username, coin, amount, user_wallet_address, company_wallet_address, tx_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Withdrawal Completed ✅</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Your withdrawal request has been approved and funds have been sent to your wallet.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Amount:</p>
                <p style="color:#00ff88;font-size:16px;font-weight:600;margin:0 0 15px 0;">
                    {amount} {coin.upper()}
                </p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Transaction ID:</p>
                <p style="color:#00ff88;font-size:13px;word-break:break-all;margin:0;font-family:monospace;">
                    {tx_id if tx_id else 'N/A'}
                </p>
            </div>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">From (Company Wallet):</p>
                <p style="color:#fff;font-size:12px;word-break:break-all;margin:0 0 15px 0;font-family:monospace;">{company_wallet_address}</p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">To (Your Wallet):</p>
                <p style="color:#fff;font-size:12px;word-break:break-all;margin:0;font-family:monospace;">{user_wallet_address}</p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">Completed</span></p>
            </div>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Please check your crypto wallet to confirm receipt of the funds.
            </p>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                <b style="color:#00ff88;">Global Energy Team</b><br>
                https://globalenergy.trade
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message(
            subject="Withdrawal Completed - Global Energy",
            recipients=[email],
        )
        msg.html = html_body
        mail.send(msg)

        print("Withdrawal approval sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

def send_deposit_processing_email(email, username, coin, amount, company_wallet_address, tx_id=None):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Deposit Received</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                We received your deposit and it is now being processed.
            </p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Amount:</p>
                <p style="color:#00ff88;font-size:16px;font-weight:600;margin:0 0 15px 0;">
                    ${amount:.2f} ({coin.upper()})
                </p>
                
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">To (Company Wallet):</p>
                <p style="color:#fff;font-size:12px;word-break:break-all;margin:0;font-family:monospace;">
                    {company_wallet_address}
                </p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#ffc107;font-weight:600;">Processing</span></p>
            </div>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                Your funds will be credited to your account once confirmed on the blockchain.
            </p>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                Thanks for choosing Global Energy.
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message("Deposit Processing - Global Energy", recipients=[email])
        msg.html = html_body
        mail.send(msg)

        print("Deposit processing email sent:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

# ---------- LOGIN ----------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Invalid or missing JSON"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user_id"] = user.id

    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "is_admin": user.is_admin
    })
@app.route("/admin/api/stats")
@admin_required
def admin_stats():
    total_users = User.query.count()
    # Include approved investments as part of the platform total balance
    investments_sum = db.session.query(db.func.sum(Investment.amount_usd)).filter(Investment.status == 'approved').scalar() or 0
    total_balance = (db.session.query(db.func.sum(User.usdt_balance)).scalar() or 0) + (investments_sum or 0)
    pending_w = Withdrawal.query.filter_by(status="pending").count()
    pending_i = Investment.query.filter_by(status="pending").count()

    return jsonify({
        "totalUsers": total_users,
        "totalBalance": total_balance,
        "pendingWithdrawals": pending_w,
        "pendingInvestments": pending_i,
        "usersChange":"+0%",
        "balanceChange":"+0%",
        "withdrawalsChange":"+0%",
        "investmentsChange":"+0%"
    })


@app.route("/admin/api/send-investment-profit", methods=["POST"])
@admin_required
def send_investment_profit():
    """Manually send investment profit to a user"""
    data = request.json
    user_id = data.get("user_id")
    profit_amount = float(data.get("profit_amount", 0))
    crypto = data.get("crypto", "usdt").lower()
    investment_id = data.get("investment_id")
    
    if profit_amount <= 0:
        return jsonify({"error": "Invalid profit amount"}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Credit profit to user's wallet
    balance_field = f"{crypto}_balance"
    if hasattr(user, balance_field):
        current = getattr(user, balance_field) or 0.0
        setattr(user, balance_field, current + profit_amount)
    else:
        return jsonify({"error": f"Invalid crypto: {crypto}"}), 400
    
    db.session.commit()
    
    # Send notification email
    if user.email:
        try:
            send_investment_profit_email(user.email, user.username, crypto, profit_amount, investment_id, periods=1)
            print(f"Investment profit email sent to {user.email}: ${profit_amount:.2f}")
        except Exception as e:
            print(f"ERROR: Failed to send investment profit email: {e}")
            import traceback
            traceback.print_exc()
    
    return jsonify({
        "message": f"Profit of ${profit_amount:.2f} credited to {user.username}",
        "user_id": user_id,
        "profit": profit_amount,
        "new_balance": getattr(user, balance_field)
    })


@app.route("/admin/api/process-investment-payouts", methods=["POST"])
@admin_required
def process_investment_payouts():
    """Process approved investments and credit periodic payouts to users.
    This endpoint is intended to be called by a scheduled job (cron) every 24 hours.
    """
    # Plan metadata: period_hours and roi_percent
    plan_map = {
        1: {"period_hours": 24, "roi_percent": 8},   # Bronze
        2: {"period_hours": 24, "roi_percent": 16},  # Silver
        3: {"period_hours": 48, "roi_percent": 33}   # Gold
    }

    now = datetime.utcnow()
    processed = []

    investments = Investment.query.filter_by(status="approved").all()
    for inv in investments:
        meta = plan_map.get(inv.plan_id)
        if not meta:
            continue

        period = meta["period_hours"]
        roi = meta["roi_percent"]

        last = inv.last_payout_at or inv.created_at or inv.id and datetime.utcnow()
        if not last:
            last = inv.created_at or datetime.utcnow()

        elapsed_hours = (now - last).total_seconds() / 3600.0
        periods_due = int(elapsed_hours // period)
        if periods_due <= 0:
            continue

        profit_per_period = inv.amount_usd * (roi / 100.0)
        total_profit = profit_per_period * periods_due

        user = User.query.get(inv.user_id)
        if not user:
            continue

        # Credit profit to user's USDT (USD-equivalent) wallet
        user.usdt_balance = (user.usdt_balance or 0.0) + total_profit

        # advance last_payout_at
        inv.last_payout_at = last + timedelta(hours=period * periods_due)

        db.session.commit()

        # send notification email
        try:
            if user.email:
                send_investment_profit_email(user.email, user.username, inv.crypto, total_profit, inv.id, periods_due)
        except Exception as e:
            print("Error sending investment profit email:", e)

        processed.append({"investment_id": inv.id, "user_id": user.id, "username": user.username, "profit": total_profit, "periods": periods_due})

    return jsonify({"processed_count": len(processed), "processed": processed})

@app.route("/admin/api/remove-balance", methods=["POST"])
@admin_required
def remove_balance():
    data = request.json
    user = User.query.get(data["user_id"])
    coin = data["coin"]
    amount = float(data["amount"])

    balance_map = {
        "btc": "btc_balance",
        "eth": "eth_balance",
        "usdt": "usdt_balance",
        "bnb": "bnb_balance"
    }

    field = balance_map.get(coin)
    if not field:
        return {"error":"Invalid coin"}, 400

    setattr(user, field, max(0, getattr(user, field) - amount))
    db.session.commit()

    return {"message":"Balance removed"}




@app.route("/admin/login")
def admin_login_page():
    return send_from_directory("ADMIN", "admin-login.html")

# ---------- DEPOSIT ----------
@app.route("/api/deposit", methods=["POST"])
def deposit():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    user = User.query.get(session["user_id"])

    if not user:
        return jsonify({"error": "User not found"}), 404

    amount = float(data["amount"])
    crypto = data.get("crypto", "usdt").lower()
    
    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    # Create deposit record as PENDING (not completed)
    tx_id = f"DP{secrets.token_hex(8)}"
    deposit = Deposit(user_id=user.id, amount=amount, crypto=crypto, tx_id=tx_id, status='pending')
    
    # DON'T credit user yet - wait for admin approval
    db.session.add(deposit)
    db.session.commit()

    # Send processing email
    if user.email:
        company_wallet = ""
        if crypto == "btc":
            company_wallet = "bc1qvlp57rkah6rxz7672fekk57w7y7ecwqy6duhgc"
        elif crypto == "eth":
            company_wallet = "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff"
        elif crypto == "bnb":
            company_wallet = "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff"
        elif crypto == "usdt":
            company_wallet = "TGmZxR8f9r8gq1bmHqbKdY5MkB7wEw8TBA"
        
        try:
            send_deposit_processing_email(user.email, user.username, crypto, amount, company_wallet, tx_id)
        except Exception as e:
            print("Failed to send deposit processing email:", e)

    return jsonify({
        "message": "Deposit submitted for approval",
        "tx_id": tx_id,
        "status": "pending"
    })


@app.route("/admin/api/users")
@admin_required
def admin_users():
    users = User.query.filter_by(is_admin=False).all()

    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "btc": u.btc_balance,
            "eth": u.eth_balance,
            "usdt": u.usdt_balance,
            "bnb": u.bnb_balance,
            "referred_by": u.referred_by,
            "withdrawal_frozen": u.withdrawal_frozen or False
        }
        for u in users
    ])
@app.route("/admin/api/delete-user", methods=["POST"])
@admin_required
def delete_user():
    data = request.json
    user_id = data.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user.is_admin:
        return jsonify({"error": "Cannot delete admin accounts"}), 403

    # Delete all related records first
    Deposit.query.filter_by(user_id=user_id).delete()
    Withdrawal.query.filter_by(user_id=user_id).delete()
    Investment.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": f"User {user.username} permanently deleted"})
@app.route("/admin/api/add-balance", methods=["POST"])
@admin_required
def admin_add_balance():
    data = request.json

    user = User.query.get(data["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    coin = data["coin"]
    amount = float(data["amount"])

    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    if coin == "btc":
        user.btc_balance += amount
    elif coin == "eth":
        user.eth_balance += amount
    elif coin == "usdt":
        user.usdt_balance += amount
    elif coin == "bnb":
        user.bnb_balance += amount
    else:
        return jsonify({"error": "Invalid coin"}), 400

    db.session.commit()
    
    # Send credit notification email using fixed company wallet addresses only
    if user.email:
        tx_id = f"AD{secrets.token_hex(8)}"

        company_wallets = {
            "btc": "bc1qvlp57rkah6rxz7672fekk57w7y7ecwqy6duhgc",
            "eth": "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff",
            "usdt": "TGmZxR8f9r8gq1bmHqbKdY5MkB7wEw8TBA",
            "bnb": "0xce8b66d28ec792ecb44a72087d6bbcbbeebe7bff"
        }

        user_wallet = "N/A"
        company_wallet = company_wallets.get(coin, "N/A")
        send_credit_email(user.email, user.username, coin, amount, user_wallet, company_wallet, tx_id)
        
    return jsonify({
        "message": "Balance updated successfully",
        "user_id": user.id
    })

@app.route("/api/invest", methods=["POST"])
def invest():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    user = User.query.get(session["user_id"])

    try:
        plan = int(data.get("plan_id"))
        amount = float(data.get("amount_usd"))
        crypto = (data.get("crypto") or "").lower()
        crypto_amount = float(data.get("crypto_amount"))
    except Exception:
        return jsonify({"error": "Invalid input values"}), 400

    rules = {
        1: (50, 499),
        2: (500, 6999),
        3: (7000, 10_000_000)
    }

    if plan not in rules:
        return jsonify({"error": "Invalid plan"}), 400

    min_amt, max_amt = rules[plan]
    if not (min_amt <= amount <= max_amt):
        return jsonify({"error": "Amount not allowed for this plan"}), 400

    balance_field_map = {
        "btc": "btc_balance",
        "eth": "eth_balance",
        "usdt": "usdt_balance",
        "bnb": "bnb_balance"
    }
    balance_field = balance_field_map.get(crypto)
    if not balance_field:
        return jsonify({"error": "Invalid wallet"}), 400

    current_balance = float(getattr(user, balance_field) or 0.0)
    if current_balance < amount:
        return jsonify({"error": "Insufficient balance", "current_balance": current_balance, "required": amount}), 400

    # Deduct from wallet
    setattr(user, balance_field, current_balance - amount)

    # AUTO APPROVE - no admin needed
    investment = Investment(
        user_id=user.id,
        plan_id=plan,
        amount_usd=amount,
        crypto=crypto,
        crypto_amount=crypto_amount,
        status="approved",
        last_payout_at=datetime.utcnow()
    )

    db.session.add(investment)
    db.session.commit()

    plan_names = {1: "Bronze 8%", 2: "Silver 16%", 3: "Gold 33%"}
    expected_return = round(amount * 1.08, 2) if plan == 1 else round(amount * 1.16, 2) if plan == 2 else round(amount * 1.33, 2)

    # Send investment active email to user
    try:
        if user.email:
            send_investment_approved_email(user.email, user.username, crypto, amount, crypto_amount, investment.id)
    except Exception as e:
        print(f"Error sending investment active email: {e}")

    # Notify manager of new investment
    try:
        manager_email = "katoevelyn220@gmail.com"
        msg = Message("🔔 New Investment Alert - Global Energy", recipients=[manager_email])
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">

            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">🔔 New Investment Alert</p>

            <p style="color:#eee;font-size:15px;">A user just made a new investment on the platform.</p>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Username:</p>
                <p style="color:#00ff88;font-size:15px;font-weight:600;margin:0 0 12px 0;">{user.username}</p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Email:</p>
                <p style="color:#fff;font-size:13px;margin:0 0 12px 0;">{user.email or 'N/A'}</p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Amount Invested:</p>
                <p style="color:#00ff88;font-size:16px;font-weight:600;margin:0 0 12px 0;">${amount:.2f} ({crypto.upper()})</p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Plan:</p>
                <p style="color:#fff;font-size:13px;margin:0 0 12px 0;">{plan_names.get(plan, "Unknown")}</p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Expected Return:</p>
                <p style="color:#00ff88;font-size:13px;margin:0 0 12px 0;">${expected_return:.2f}</p>

                <p style="color:#888;font-size:12px;margin:0 0 5px 0;">Investment ID:</p>
                <p style="color:#fff;font-size:13px;font-family:monospace;margin:0;">{investment.id}</p>
            </div>

            <div style="background:#0f3460;padding:12px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;">Status: <span style="color:#00ff88;font-weight:600;">Active - Payout in 24hrs</span></p>
            </div>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                <b>Global Energy Platform</b><br>
                https://globalenergy.trade
            </p>

        </div>
        </body>
        </html>
        """
        mail.send(msg)
        print(f"[MANAGER] Investment alert sent to {manager_email}")
    except Exception as e:
        print(f"[MANAGER] Failed to send manager alert: {e}")

    return jsonify({
        "message": "Investment active! Your return will be credited in 24 hours.",
        "investment_id": investment.id,
        "amount": amount,
        "expected_return": expected_return
    })






# ---------- BALANCE ----------
@app.route("/api/balance/<int:user_id>")
def balance(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "usdt_balance": user.usdt_balance
    })

@app.route("/dashboard/<int:user_id>")
def dashboard_data(user_id):
    if "user_id" not in session or session["user_id"] != user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(user_id)
    # sum of this user's approved investments
    active_plan_sum = db.session.query(db.func.sum(Investment.amount_usd)).filter(
        Investment.user_id == user_id, Investment.status == 'approved'
    ).scalar() or 0.0

    return jsonify({
        "username": user.username,
        # total balance now includes wallet balances + active investments
      "total_balance": (
        (user.btc_balance or 0) +
        (user.eth_balance or 0) +
        (user.usdt_balance or 0) +
        (user.bnb_balance or 0)
         ),
        "wallets": {
            "btc": user.btc_balance,
            "eth": user.eth_balance,
            "usdt": user.usdt_balance,
            "bnb": user.bnb_balance
        },
        "btc_address": user.btc_address,
        "eth_address": user.eth_address,
        "usdt_address": user.usdt_address,
        "bnb_address": user.bnb_address,

        # Real values
        "earnings": 0.00,
        "active_plan": float(active_plan_sum or 0.0),
        "trade_volume": 0.00,
        "withdraws": 0.00
    })

@app.route("/dashboard/me")
def dashboard_me():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(session["user_id"])
    # Totals from historical records - include all deposits (pending + completed)
    total_deposits = db.session.query(db.func.sum(Deposit.amount)).filter(Deposit.user_id == user.id).scalar() or 0.0
    total_withdrawals = db.session.query(db.func.sum(Withdrawal.amount)).filter(Withdrawal.user_id == user.id, Withdrawal.status == 'approved').scalar() or 0.0
    total_invested = db.session.query(db.func.sum(Investment.amount_usd)).filter(Investment.user_id == user.id, Investment.status == 'approved').scalar() or 0.0
    # counts - include all deposits
    num_deposits = db.session.query(db.func.count(Deposit.id)).filter(Deposit.user_id == user.id).scalar() or 0
    num_withdrawals = db.session.query(db.func.count(Withdrawal.id)).filter( Withdrawal.user_id == user.id,Withdrawal.status == 'approved').scalar() or 0
    num_investments = db.session.query(db.func.count(Investment.id)).filter(Investment.user_id == user.id, Investment.status == 'approved').scalar() or 0

    return jsonify({
        "username": user.username,
        "fullname": user.fullname,
        "email": user.email,
        # Include active (approved) investments in the total balance
        "total_balance": (
       (user.btc_balance or 0) +
       (user.eth_balance or 0) +
       (user.usdt_balance or 0) +
       (user.bnb_balance or 0)
        ),
        "active_investments": float(total_invested or 0.0),
        "wallets": {
            "btc": user.btc_balance,
            "eth": user.eth_balance,
            "usdt": user.usdt_balance,
            "bnb": user.bnb_balance
        },
        "btc_address": user.btc_address,
        "eth_address": user.eth_address,
        "usdt_address": user.usdt_address,
        "bnb_address": user.bnb_address,
        "totals": {
            "total_deposits": float(total_deposits),
            "total_withdrawals": float(total_withdrawals),
            "total_invested": float(total_invested),
            "total_referral_earnings": float(user.referral_earnings or 0.0),
            "num_deposits": int(num_deposits),
            "num_withdrawals": int(num_withdrawals),
            "num_investments": int(num_investments)
        }
    })



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")



# ---------- PASSWORD RECOVERY ----------
@app.route("/forgot-password")
def forgot_password_page():
    return send_from_directory("login", "forgot-password.html")

def send_recovery_code_email(email, username, code):
    try:
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family:Arial;background:#1a1a2e;padding:20px;margin:0;">
        <div style="max-width:600px;margin:auto;background:#16213e;padding:25px;border-radius:12px;border:1px solid #0f3460;">
            
            <div style="text-align:center;margin-bottom:20px;">
                <img src="https://globalenergy.trade/signup/img/admin-ajax-2.png" width="120">
            </div>

            <p style="color:#e94560;font-size:18px;font-weight:600;margin:0 0 20px 0;">Password Recovery Code</p>

            <p style="color:#eee;font-size:15px;line-height:1.6;">
                Hello <b style="color:#00ff88;">{username}</b>,
            </p>

            <p style="color:#ccc;font-size:14px;line-height:1.6;margin:15px 0;">
                We received a request to reset your password. Use the code below to proceed:
            </p>

            <div style="background:#0f3460;padding:20px;border-radius:8px;margin:20px 0;text-align:center;">
                <p style="color:#888;font-size:12px;margin:0 0 10px 0;">Your Recovery Code:</p>
                <p style="color:#00ff88;font-size:32px;font-weight:600;margin:0;letter-spacing:5px;font-family:monospace;">
                    {code}
                </p>
                <p style="color:#888;font-size:11px;margin:10px 0 0 0;">This code expires in 10 minutes</p>
            </div>

            <div style="background:#0f3460;padding:15px;border-radius:8px;margin:20px 0;">
                <p style="color:#888;font-size:12px;margin:0;"><b>⚠️ Security Notice:</b></p>
                <p style="color:#ccc;font-size:13px;margin:8px 0 0 0;">If you didn't request this code, please ignore this email or contact support immediately.</p>
            </div>

            <p style="color:#888;font-size:13px;margin-top:25px;">
                <b style="color:#00ff88;">Global Energy Team</b><br>
                https://globalenergy.trade
            </p>

        </div>
        </body>
        </html>
        """

        msg = Message(
            subject="Password Recovery Code - Global Energy",
            recipients=[email],
        )
        msg.html = html_body
        mail.send(msg)

        print("Recovery code sent to:", email)

    except Exception as e:
        print("EMAIL ERROR:", e)

@app.route("/api/forgot-password/send-code", methods=["POST"])
def forgot_password_send_code():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"success": False, "message": "Email is required"})

    user = User.query.filter_by(email=email).first()

    if not user:
        # For security, don't reveal if email exists
        return jsonify({"success": True, "message": "If email exists, recovery code will be sent"})

    # Generate 6-digit recovery code
    recovery_code = ''.join(random.choices(string.digits, k=6))
    
    # Set expiration time (10 minutes)
    from datetime import datetime, timedelta
    user.recovery_code = recovery_code
    user.recovery_code_expires = datetime.now() + timedelta(minutes=10)
    
    db.session.commit()

    # Send email with recovery code
    send_recovery_code_email(email, user.username, recovery_code)

    return jsonify({"success": True, "message": "Recovery code sent to email"})

@app.route("/api/forgot-password/verify-code", methods=["POST"])
def forgot_password_verify_code():
    data = request.json
    email = data.get("email")
    code = data.get("code")

    if not email or not code:
        return jsonify({"success": False, "message": "Email and code are required"})

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"success": False, "message": "User not found"})

    # Check if code is valid
    from datetime import datetime
    if not user.recovery_code or user.recovery_code != code:
        return jsonify({"success": False, "message": "Invalid recovery code"})

    if user.recovery_code_expires and datetime.now() > user.recovery_code_expires:
        return jsonify({"success": False, "message": "Recovery code has expired"})

    return jsonify({"success": True, "message": "Code verified"})

@app.route("/api/forgot-password/reset", methods=["POST"])
def forgot_password_reset():
    data = request.json
    email = data.get("email")
    code = data.get("code")
    new_password = data.get("new_password")

    if not email or not code or not new_password:
        return jsonify({"success": False, "message": "All fields are required"})

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"success": False, "message": "User not found"})

    # Verify code again for security
    from datetime import datetime
    if not user.recovery_code or user.recovery_code != code:
        return jsonify({"success": False, "message": "Invalid recovery code"})

    if user.recovery_code_expires and datetime.now() > user.recovery_code_expires:
        return jsonify({"success": False, "message": "Recovery code has expired"})

    # Validate password
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters"})

    # Update password and clear recovery code
    user.set_password(new_password)
    user.recovery_code = None
    user.recovery_code_expires = None

    db.session.commit()

    return jsonify({"success": True, "message": "Password reset successfully"})

# ---------- CONTACT ----------
@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.json

    name = data.get("name")
    email = data.get("email")
    message = data.get("message")

    if not name or not email or not message:
        return jsonify({"message": "All fields required"}), 400

    print("CONTACT MESSAGE:")
    print(name, email, message)

    return jsonify({"message": "Message sent successfully"})


# -------------------
# Automatic Scheduled Jobs (Investment Payouts)
# -------------------

def process_investment_payouts_job():
    """Pay out once after 24hrs then mark investment as completed"""
    print("[SCHEDULER] Running investment payout job...")

    plan_map = {
        1: {"period_hours": 24, "roi_percent": 8},
        2: {"period_hours": 24, "roi_percent": 16},
        3: {"period_hours": 48, "roi_percent": 33}
    }

    with app.app_context():
        try:
            now = datetime.utcnow()
            investments = Investment.query.filter_by(status="approved").all()

            for inv in investments:
                try:
                    meta = plan_map.get(inv.plan_id)
                    if not meta:
                        continue

                    if not inv.amount_usd or inv.amount_usd <= 0:
                        continue

                    last = inv.last_payout_at or inv.created_at or now
                    elapsed_hours = (now - last).total_seconds() / 3600.0

                    # Not ready yet
                    if elapsed_hours < meta["period_hours"]:
                        print(f"[SCHEDULER] Investment {inv.id} not due yet ({elapsed_hours:.1f}h elapsed)")
                        continue

                    user = User.query.get(inv.user_id)
                    if not user:
                        continue

                    # Calculate profit + return principal
                    profit = round(inv.amount_usd * (meta["roi_percent"] / 100.0), 2)
                    total_return = round(inv.amount_usd + profit, 2)

                    # Credit principal + profit back to user
                    user.usdt_balance = round((user.usdt_balance or 0.0) + total_return, 2)

                    # Mark investment as completed - user must reinvest manually
                    inv.status = "completed"
                    inv.last_payout_at = now

                    db.session.commit()

                    print(f"[SCHEDULER] ✓ Paid ${total_return:.2f} to {user.username} (${inv.amount_usd} + ${profit} profit)")

                    # Send email
                    try:
                        if user.email:
                            send_investment_profit_email(
                                user.email,
                                user.username,
                                inv.crypto,
                                total_return,
                                inv.id,
                                1
                            )
                    except Exception as e:
                        print(f"[SCHEDULER] Email error: {e}")

                except Exception as inv_err:
                    print(f"[SCHEDULER] Error on investment {inv.id}: {inv_err}")
                    db.session.rollback()
                    continue

        except Exception as e:
            print(f"[SCHEDULER] CRITICAL ERROR: {e}")
            import traceback
            traceback.print_exc()




# -------------------
# Start scheduler for ALL environments (gunicorn + direct)
# -------------------
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=process_investment_payouts_job,
    trigger="interval",
    hours=1,
    id="investment_payouts",
    name="Process Investment Payouts",
    replace_existing=True
)
scheduler.start()
print("[SCHEDULER] ✓ Auto payout scheduler running")
atexit.register(lambda: scheduler.shutdown())


if __name__ == "__main__":
    app.run(debug=True)
