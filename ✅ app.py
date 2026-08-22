from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify, flash, send_from_directory
import re
import os
import json
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from rag.pipeline import rag_pipeline

load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-this-secret-key')

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')

# ----- DATABASE CONFIGURATION -----
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'ai_project'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Dhanu@143')
}

# ----- DATABASE CONNECTION -----
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None

# ----- CREATE TABLES IF NOT EXISTS -----
def init_db():
    conn = get_db_connection()
    if conn is None:
        return
    
    cursor = conn.cursor()
    
    # Users table (kept for authentication)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Note: chat_sessions and chat_messages tables are NO LONGER used
    # Chat history is now stored locally in IndexedDB on the user's device
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Database initialized successfully (users table only)")

# Initialize database on startup
init_db()

# ----- PASSWORD HELPER -----
def verify_password(stored_hash, provided_password):
    """
    Verify a password against stored hash.
    Supports both Werkzeug hashes (scrypt/pbkdf2) and legacy plaintext for migration.
    """
    # Werkzeug hashes start with 'scrypt:' or 'pbkdf2:sha256:'
    if stored_hash.startswith('scrypt:') or stored_hash.startswith('pbkdf2:'):
        return check_password_hash(stored_hash, provided_password)
    # Legacy plaintext - verify and return True if match (will be upgraded on next login)
    return stored_hash == provided_password

# ----- LOGIN REQUIRED DECORATOR -----
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please login to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# ----- HTML TEMPLATES -----

# INDEX HTML
INDEX_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>College Assistant · Home</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            background: #1a3a8a;
            position: relative;
            overflow-x: hidden;
        }

        .bg-container {
            position: fixed;
            inset: 0;
            z-index: 0;
            background: linear-gradient(145deg, #1a3a8a 0%, #2a5fc1 50%, #1e4a9e 100%);
            overflow: hidden;
            pointer-events: none;
        }

        .bg-shape {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.06);
            filter: blur(90px);
            animation: floatShape 20s ease-in-out infinite alternate;
            pointer-events: none;
        }

        .bg-shape:nth-child(1) {
            width: 600px;
            height: 600px;
            top: -15%;
            left: -10%;
            background: rgba(255, 255, 255, 0.07);
            animation-duration: 24s;
        }
        .bg-shape:nth-child(2) {
            width: 700px;
            height: 700px;
            bottom: -20%;
            right: -10%;
            background: rgba(255, 255, 255, 0.05);
            animation-duration: 28s;
            animation-delay: -5s;
        }
        .bg-shape:nth-child(3) {
            width: 400px;
            height: 400px;
            top: 30%;
            left: 55%;
            background: rgba(255, 255, 255, 0.04);
            animation-duration: 22s;
            animation-delay: -9s;
        }
        .bg-shape:nth-child(4) {
            width: 350px;
            height: 350px;
            bottom: 15%;
            left: 10%;
            background: rgba(255, 255, 255, 0.05);
            animation-duration: 26s;
            animation-delay: -3s;
        }

        @keyframes floatShape {
            0% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(40px, -30px) scale(1.03); }
            66% { transform: translate(-30px, 40px) scale(0.97); }
            100% { transform: translate(20px, -15px) scale(1.02); }
        }

        .bg-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 30% 40%, rgba(255, 255, 255, 0.04) 0%, transparent 60%);
            animation: glowShift 18s ease-in-out infinite alternate;
        }

        @keyframes glowShift {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.02); }
            100% { opacity: 0.3; transform: scale(1); }
        }

        .hero-card {
            position: relative;
            z-index: 1;
            max-width: 700px;
            width: 100%;
            background: rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 48px;
            padding: 3.5rem 3rem 3rem;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 32px 80px rgba(0, 0, 0, 0.2);
            text-align: center;
            animation: cardEntrance 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes cardEntrance {
            0% { opacity: 0; transform: translateY(30px) scale(0.96); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }

        .brand {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.6rem;
            margin-bottom: 2.5rem;
        }

        .brand .icon {
            font-size: 2.2rem;
            color: #fff;
            background: rgba(79, 110, 247, 0.25);
            width: 54px;
            height: 54px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .brand .name {
            font-weight: 700;
            font-size: 1.4rem;
            color: #fff;
            letter-spacing: -0.01em;
        }

        .quote-container {
            margin-bottom: 2.5rem;
        }

        .quote-text {
            font-size: 3.5rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
            letter-spacing: 0.04em;
            max-width: 550px;
            margin: 0 auto;
            text-transform: uppercase;
            text-shadow: 0 2px 20px rgba(0,0,0,0.08);
        }

        .quote-text .highlight {
            color: #ffffff;
        }

        .quote-sub {
            color: rgba(255, 255, 255, 0.4);
            font-size: 0.85rem;
            margin-top: 0.75rem;
            font-weight: 400;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .btn-group {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .btn {
            padding: 0.9rem 2.5rem;
            border-radius: 60px;
            font-weight: 600;
            font-size: 1rem;
            font-family: 'Inter', sans-serif;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            letter-spacing: -0.01em;
        }

        .btn-primary {
            background: #4F6EF7;
            color: #fff;
            box-shadow: 0 8px 28px rgba(79, 110, 247, 0.3);
        }

        .btn-primary:hover {
            background: #3b5de7;
            transform: translateY(-2px);
            box-shadow: 0 12px 36px rgba(79, 110, 247, 0.4);
        }

        .btn-primary:active {
            transform: scale(0.97);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(4px);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.25);
        }

        .btn-secondary:active {
            transform: scale(0.97);
        }

        .btn i {
            font-size: 0.9rem;
        }

        .footer-text {
            margin-top: 2.5rem;
            color: rgba(255, 255, 255, 0.25);
            font-size: 0.8rem;
            letter-spacing: 0.02em;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 1.5rem;
        }

        @media (max-width: 768px) {
            .hero-card {
                padding: 2.5rem 1.5rem 2rem;
                border-radius: 32px;
            }
            .quote-text {
                font-size: 2.5rem;
            }
            .brand .name {
                font-size: 1.2rem;
            }
            .btn {
                padding: 0.8rem 1.8rem;
                font-size: 0.9rem;
                width: 100%;
                justify-content: center;
            }
            .btn-group {
                flex-direction: column;
                align-items: center;
            }
            .btn-group .btn {
                max-width: 300px;
            }
        }

        @media (max-width: 480px) {
            .hero-card {
                padding: 2rem 1.2rem 1.5rem;
                border-radius: 24px;
            }
            .quote-text {
                font-size: 2rem;
            }
            .brand .icon {
                width: 44px;
                height: 44px;
                font-size: 1.6rem;
            }
            .brand .name {
                font-size: 1rem;
            }
        }
    </style>
</head>
<body>
    <div class="bg-container" aria-hidden="true">
        <div class="bg-shape"></div>
        <div class="bg-shape"></div>
        <div class="bg-shape"></div>
        <div class="bg-shape"></div>
    </div>

    <div class="hero-card">
        <div class="brand">
            <div class="icon"><i class="fas fa-graduation-cap"></i></div>
            <div class="name">College Assistant</div>
        </div>

        <div class="quote-container">
            <div class="quote-text">
                ASK <span class="highlight">MY</span> SELF
            </div>
            <div class="quote-sub">— Knowledge begins with a question</div>
        </div>

        <div class="btn-group">
            <a href="{{ url_for('login') }}" class="btn btn-primary">
                <i class="fas fa-sign-in-alt"></i> Login
            </a>
            <a href="{{ url_for('signup') }}" class="btn btn-secondary">
                <i class="fas fa-rocket"></i> Get Started
            </a>
        </div>

        <div class="footer-text">
            <i class="fas fa-robot" style="margin-right: 0.4rem;"></i> Powered by AI · University Knowledge Base
        </div>
    </div>
</body>
</html>
'''

LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>Login · College Assistant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            background: #1a3a8a;
            position: relative;
            overflow-x: hidden;
        }
        .bg-container {
            position: fixed;
            inset: 0;
            z-index: 0;
            background: linear-gradient(145deg, #1a3a8a 0%, #2a5fc1 50%, #1e4a9e 100%);
            overflow: hidden;
            pointer-events: none;
        }
        .bg-shape {
            position: absolute;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            filter: blur(90px);
            animation: floatShape 20s ease-in-out infinite alternate;
            pointer-events: none;
        }
        .bg-shape:nth-child(1) { width: 600px; height: 600px; top: -15%; left: -10%; background: rgba(255,255,255,0.07); animation-duration: 24s; }
        .bg-shape:nth-child(2) { width: 700px; height: 700px; bottom: -20%; right: -10%; background: rgba(255,255,255,0.05); animation-duration: 28s; animation-delay: -5s; }
        .bg-shape:nth-child(3) { width: 400px; height: 400px; top: 30%; left: 55%; background: rgba(255,255,255,0.04); animation-duration: 22s; animation-delay: -9s; }
        .bg-shape:nth-child(4) { width: 350px; height: 350px; bottom: 15%; left: 10%; background: rgba(255,255,255,0.05); animation-duration: 26s; animation-delay: -3s; }
        @keyframes floatShape {
            0% { transform: translate(0,0) scale(1); }
            33% { transform: translate(40px,-30px) scale(1.03); }
            66% { transform: translate(-30px,40px) scale(0.97); }
            100% { transform: translate(20px,-15px) scale(1.02); }
        }
        .bg-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 30% 40%, rgba(255,255,255,0.04) 0%, transparent 60%);
            animation: glowShift 18s ease-in-out infinite alternate;
        }
        @keyframes glowShift {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.02); }
            100% { opacity: 0.3; transform: scale(1); }
        }
        .login-card {
            position: relative;
            z-index: 1;
            max-width: 440px;
            width: 100%;
            background: #FFFFFF;
            border-radius: 36px;
            box-shadow: 0 24px 64px rgba(0,20,60,0.25), 0 8px 24px rgba(0,0,0,0.06);
            padding: 2.5rem 2rem;
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(2px);
            transition: box-shadow 0.3s ease, transform 0.2s ease;
            animation: cardEntrance 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
        }
        @keyframes cardEntrance {
            0% { opacity: 0; transform: translateY(24px) scale(0.96); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .brand-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.75rem; }
        .brand-icon { font-size: 1.9rem; color: #4F6EF7; background: rgba(79,110,247,0.08); width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; border-radius: 16px; }
        .brand-name { font-weight: 600; font-size: 1.2rem; color: #1E293B; background: linear-gradient(135deg, #1E293B, #2d3a4f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .form-heading h1 { font-size: 1.8rem; font-weight: 600; color: #1E293B; }
        .form-sub { color: #64748B; font-size: 0.95rem; margin-top: 0.2rem; margin-bottom: 1.8rem; }
        .input-group { margin-bottom: 1.25rem; position: relative; }
        .input-group label { display: block; font-weight: 500; font-size: 0.85rem; color: #1E293B; margin-bottom: 0.3rem; }
        .input-wrapper { position: relative; display: flex; align-items: center; }
        .input-wrapper input {
            width: 100%; padding: 0.85rem 1rem; padding-right: 3rem;
            font-size: 0.95rem; font-family: 'Inter', sans-serif;
            background: #fff; border: 1.5px solid #E2E8F0;
            border-radius: 18px; outline: none;
            transition: border 0.25s, box-shadow 0.25s;
            color: #1E293B;
        }
        .input-wrapper input:focus { border-color: #4F6EF7; box-shadow: 0 0 0 4px rgba(79,110,247,0.08), 0 2px 8px rgba(79,110,247,0.02); }
        .input-wrapper input::placeholder { color: #94A3B8; }
        .input-group.error .input-wrapper input { border-color: #EF4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.05); }
        .error-message {
            font-size: 0.8rem; color: #EF4444; margin-top: 0.3rem;
            display: flex; align-items: center; gap: 0.25rem;
            opacity: 0; transform: translateY(-4px);
            transition: opacity 0.25s, transform 0.25s;
        }
        .input-group.error .error-message { opacity: 1; transform: translateY(0); }
        .toggle-password {
            position: absolute; right: 1rem;
            background: none; border: none;
            color: #94A3B8; font-size: 1.1rem;
            cursor: pointer; padding: 0.25rem;
            transition: color 0.2s;
        }
        .toggle-password:hover { color: #4F6EF7; }
        .forgot-link { text-align: right; margin-top: -0.25rem; margin-bottom: 0.75rem; }
        .forgot-link a { font-size: 0.85rem; color: #64748B; text-decoration: none; font-weight: 500; }
        .forgot-link a:hover { color: #4F6EF7; }
        .btn-primary {
            width: 100%; padding: 0.9rem;
            background: #4F6EF7; color: #fff;
            border: none; border-radius: 40px;
            font-weight: 600; font-size: 1rem;
            cursor: pointer; transition: all 0.25s;
            box-shadow: 0 4px 14px rgba(79,110,247,0.25);
            display: flex; align-items: center; justify-content: center;
            gap: 0.5rem; font-family: 'Inter', sans-serif;
        }
        .btn-primary:hover:not(:disabled) { background: #3b5de7; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(79,110,247,0.30); }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; transform: scale(0.98); }
        .btn-primary .spinner {
            display: inline-block; width: 1.1rem; height: 1.1rem;
            border: 2.5px solid rgba(255,255,255,0.25);
            border-top: 2.5px solid #fff;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .success-message {
            display: none; background: #F0FDF4;
            border: 1px solid #BBF7D0; border-radius: 24px;
            padding: 1rem 1.2rem; margin-top: 1rem;
            color: #15803D; font-weight: 500;
            align-items: center; gap: 0.6rem;
            animation: successPop 0.4s cubic-bezier(0.16,1,0.3,1);
        }
        .success-message.show { display: flex; }
        @keyframes successPop {
            0% { opacity: 0; transform: scale(0.94) translateY(6px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        .form-footer { margin-top: 1.8rem; text-align: center; font-size: 0.95rem; color: #64748B; }
        .form-footer a { color: #4F6EF7; font-weight: 600; text-decoration: none; border-bottom: 1.5px solid transparent; transition: border-color 0.2s; cursor: pointer; }
        .form-footer a:hover { border-bottom-color: #4F6EF7; }
        .flash-message {
            padding: 0.75rem 1rem; border-radius: 12px; margin-bottom: 1rem;
            font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem;
        }
        .flash-error { background: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; }
        .flash-success { background: #DCFCE7; color: #16A34A; border: 1px solid #86EFAC; }
        @media (max-width: 520px) {
            .login-card { padding: 1.8rem 1.2rem; border-radius: 28px; }
            .form-heading h1 { font-size: 1.6rem; }
        }
    </style>
</head>
<body>
    <div class="bg-container" aria-hidden="true">
        <div class="bg-shape"></div><div class="bg-shape"></div>
        <div class="bg-shape"></div><div class="bg-shape"></div>
    </div>
    <div class="login-card">
        <div class="brand-header">
            <div class="brand-icon"><i class="fas fa-graduation-cap"></i></div>
            <div class="brand-name">College Assistant</div>
        </div>
        <div class="form-heading">
            <h1>Welcome Back</h1>
            <div class="form-sub">Ask anything about your college.</div>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message flash-{{ category }}"><i class="fas fa-circle-exclamation"></i> {{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST" action="{{ url_for('login') }}" novalidate onsubmit="handleLoginSubmit()">
            <div class="input-group {% if email_error %}error{% endif %}" id="emailGroup">
                <label for="email">College Email</label>
                <div class="input-wrapper">
                    <input type="email" id="email" name="email" placeholder="Enter your college email" value="{{ email or '' }}" />
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span>{% if email_error %}{{ email_error }}{% else %}Invalid email or password.{% endif %}</span></div>
            </div>
            <div class="input-group {% if password_error %}error{% endif %}" id="passwordGroup">
                <label for="password">Password</label>
                <div class="input-wrapper">
                    <input type="password" id="password" name="password" placeholder="Enter your password" />
                    <button type="button" class="toggle-password" onclick="togglePassword()"><i class="fas fa-eye" id="passwordIcon"></i></button>
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span>{% if password_error %}{{ password_error }}{% else %}Invalid email or password.{% endif %}</span></div>
            </div>
            <div class="forgot-link"><a href="#">Forgot password?</a></div>
            <button type="submit" class="btn-primary" id="loginBtn"><span id="loginBtnText">Login</span><span id="loginSpinner" style="display:none;" class="spinner"></span></button>
        </form>
        <div class="form-footer">Don't have an account? <a href="{{ url_for('signup') }}">Sign Up</a></div>
    </div>
    <script>
        function togglePassword() {
            const pwd = document.getElementById('password');
            const icon = document.getElementById('passwordIcon');
            if (pwd.type === 'password') { pwd.type = 'text'; icon.classList.replace('fa-eye','fa-eye-slash'); }
            else { pwd.type = 'password'; icon.classList.replace('fa-eye-slash','fa-eye'); }
        }
        function handleLoginSubmit() {
            document.getElementById('loginBtn').disabled = true;
            document.getElementById('loginBtnText').textContent = 'Logging in...';
            document.getElementById('loginSpinner').style.display = 'inline-block';
        }
    </script>
</body>
</html>
'''

SIGNUP_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>Sign Up · College Assistant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            background: #1a3a8a;
            position: relative;
            overflow-x: hidden;
        }
        .bg-container {
            position: fixed;
            inset: 0;
            z-index: 0;
            background: linear-gradient(145deg, #1a3a8a 0%, #2a5fc1 50%, #1e4a9e 100%);
            overflow: hidden;
            pointer-events: none;
        }
        .bg-shape {
            position: absolute;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            filter: blur(90px);
            animation: floatShape 20s ease-in-out infinite alternate;
            pointer-events: none;
        }
        .bg-shape:nth-child(1) { width: 600px; height: 600px; top: -15%; left: -10%; background: rgba(255,255,255,0.07); animation-duration: 24s; }
        .bg-shape:nth-child(2) { width: 700px; height: 700px; bottom: -20%; right: -10%; background: rgba(255,255,255,0.05); animation-duration: 28s; animation-delay: -5s; }
        .bg-shape:nth-child(3) { width: 400px; height: 400px; top: 30%; left: 55%; background: rgba(255,255,255,0.04); animation-duration: 22s; animation-delay: -9s; }
        .bg-shape:nth-child(4) { width: 350px; height: 350px; bottom: 15%; left: 10%; background: rgba(255,255,255,0.05); animation-duration: 26s; animation-delay: -3s; }
        @keyframes floatShape {
            0% { transform: translate(0,0) scale(1); }
            33% { transform: translate(40px,-30px) scale(1.03); }
            66% { transform: translate(-30px,40px) scale(0.97); }
            100% { transform: translate(20px,-15px) scale(1.02); }
        }
        .bg-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 30% 40%, rgba(255,255,255,0.04) 0%, transparent 60%);
            animation: glowShift 18s ease-in-out infinite alternate;
        }
        @keyframes glowShift {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.02); }
            100% { opacity: 0.3; transform: scale(1); }
        }
        .signup-card {
            position: relative;
            z-index: 1;
            max-width: 480px;
            width: 100%;
            background: #FFFFFF;
            border-radius: 36px;
            box-shadow: 0 24px 64px rgba(0,20,60,0.25), 0 8px 24px rgba(0,0,0,0.06);
            padding: 2.5rem 2rem;
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(2px);
            transition: box-shadow 0.3s ease, transform 0.2s ease;
            animation: cardEntrance 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
        }
        @keyframes cardEntrance {
            0% { opacity: 0; transform: translateY(24px) scale(0.96); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .brand-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.75rem; }
        .brand-icon { font-size: 1.9rem; color: #4F6EF7; background: rgba(79,110,247,0.08); width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; border-radius: 16px; }
        .brand-name { font-weight: 600; font-size: 1.2rem; color: #1E293B; background: linear-gradient(135deg, #1E293B, #2d3a4f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .form-heading h1 { font-size: 1.8rem; font-weight: 600; color: #1E293B; }
        .form-sub { color: #64748B; font-size: 0.95rem; margin-top: 0.2rem; margin-bottom: 1.8rem; }
        .input-group { margin-bottom: 1.25rem; position: relative; }
        .input-group label { display: block; font-weight: 500; font-size: 0.85rem; color: #1E293B; margin-bottom: 0.3rem; }
        .input-wrapper { position: relative; display: flex; align-items: center; }
        .input-wrapper input {
            width: 100%; padding: 0.85rem 1rem; padding-right: 3rem;
            font-size: 0.95rem; font-family: 'Inter', sans-serif;
            background: #fff; border: 1.5px solid #E2E8F0;
            border-radius: 18px; outline: none;
            transition: border 0.25s, box-shadow 0.25s;
            color: #1E293B;
        }
        .input-wrapper input:focus { border-color: #4F6EF7; box-shadow: 0 0 0 4px rgba(79,110,247,0.08), 0 2px 8px rgba(79,110,247,0.02); }
        .input-wrapper input::placeholder { color: #94A3B8; }
        .input-group.error .input-wrapper input { border-color: #EF4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.05); }
        .error-message {
            font-size: 0.8rem; color: #EF4444; margin-top: 0.3rem;
            display: flex; align-items: center; gap: 0.25rem;
            opacity: 0; transform: translateY(-4px);
            transition: opacity 0.25s, transform 0.25s;
        }
        .input-group.error .error-message { opacity: 1; transform: translateY(0); }
        .toggle-password {
            position: absolute; right: 1rem;
            background: none; border: none;
            color: #94A3B8; font-size: 1.1rem;
            cursor: pointer; padding: 0.25rem;
            transition: color 0.2s;
        }
        .toggle-password:hover { color: #4F6EF7; }
        .btn-primary {
            width: 100%; padding: 0.9rem;
            background: #4F6EF7; color: #fff;
            border: none; border-radius: 40px;
            font-weight: 600; font-size: 1rem;
            cursor: pointer; transition: all 0.25s;
            box-shadow: 0 4px 14px rgba(79,110,247,0.25);
            display: flex; align-items: center; justify-content: center;
            gap: 0.5rem; font-family: 'Inter', sans-serif;
        }
        .btn-primary:hover:not(:disabled) { background: #3b5de7; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(79,110,247,0.30); }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; transform: scale(0.98); }
        .btn-primary .spinner {
            display: inline-block; width: 1.1rem; height: 1.1rem;
            border: 2.5px solid rgba(255,255,255,0.25);
            border-top: 2.5px solid #fff;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .success-message {
            display: none; background: #F0FDF4;
            border: 1px solid #BBF7D0; border-radius: 24px;
            padding: 1rem 1.2rem; margin-top: 1rem;
            color: #15803D; font-weight: 500;
            align-items: center; gap: 0.6rem;
            animation: successPop 0.4s cubic-bezier(0.16,1,0.3,1);
        }
        .success-message.show { display: flex; }
        @keyframes successPop {
            0% { opacity: 0; transform: scale(0.94) translateY(6px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        .form-footer { margin-top: 1.8rem; text-align: center; font-size: 0.95rem; color: #64748B; }
        .form-footer a { color: #4F6EF7; font-weight: 600; text-decoration: none; border-bottom: 1.5px solid transparent; transition: border-color 0.2s; cursor: pointer; }
        .form-footer a:hover { border-bottom-color: #4F6EF7; }
        .flash-message {
            padding: 0.75rem 1rem; border-radius: 12px; margin-bottom: 1rem;
            font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem;
        }
        .flash-error { background: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; }
        .flash-success { background: #DCFCE7; color: #16A34A; border: 1px solid #86EFAC; }
        @media (max-width: 520px) {
            .signup-card { padding: 1.8rem 1.2rem; border-radius: 28px; }
            .form-heading h1 { font-size: 1.6rem; }
        }
    </style>
</head>
<body>
    <div class="bg-container" aria-hidden="true">
        <div class="bg-shape"></div><div class="bg-shape"></div>
        <div class="bg-shape"></div><div class="bg-shape"></div>
    </div>
    <div class="signup-card">
        <div class="brand-header">
            <div class="brand-icon"><i class="fas fa-graduation-cap"></i></div>
            <div class="brand-name">College Assistant</div>
        </div>
        <div class="form-heading">
            <h1>Create your account</h1>
            <div class="form-sub">Start asking questions about your college.</div>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash-message flash-{{ category }}"><i class="fas fa-circle-exclamation"></i> {{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <form method="POST" action="{{ url_for('signup') }}" novalidate onsubmit="handleSignupSubmit()">
            <div class="input-group {% if name_error %}error{% endif %}">
                <label for="fullName">Full Name</label>
                <div class="input-wrapper">
                    <input type="text" id="fullName" name="full_name" placeholder="Enter your full name" value="{{ full_name or '' }}" />
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span>{% if name_error %}{{ name_error }}{% else %}Please enter your full name.{% endif %}</span></div>
            </div>
            <div class="input-group {% if email_error %}error{% endif %}">
                <label for="email">College Email</label>
                <div class="input-wrapper">
                    <input type="email" id="email" name="email" placeholder="Enter your college email" value="{{ email or '' }}" />
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span>{% if email_error %}{{ email_error }}{% else %}Please enter a valid college email.{% endif %}</span></div>
            </div>
            <div class="input-group {% if password_error %}error{% endif %}">
                <label for="password">Password</label>
                <div class="input-wrapper">
                    <input type="password" id="password" name="password" placeholder="Enter your password" />
                    <button type="button" class="toggle-password" onclick="togglePassword('password','passwordIcon1')"><i class="fas fa-eye" id="passwordIcon1"></i></button>
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span>{% if password_error %}{{ password_error }}{% else %}Password must be at least 8 characters.{% endif %}</span></div>
            </div>
            <div class="input-group {% if confirm_error %}error{% endif %}">
                <label for="confirmPassword">Confirm Password</label>
                <div class="input-wrapper">
                    <input type="password" id="confirmPassword" name="confirm_password" placeholder="Confirm your password" />
                    <button type="button" class="toggle-password" onclick="togglePassword('confirmPassword','passwordIcon2')"><i class="fas fa-eye" id="passwordIcon2"></i></button>
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span>{% if confirm_error %}{{ confirm_error }}{% else %}Passwords do not match.{% endif %}</span></div>
            </div>
            <button type="submit" class="btn-primary" id="signupBtn"><span id="signupBtnText">Create Account</span><span id="signupSpinner" style="display:none;" class="spinner"></span></button>
        </form>
        <div class="form-footer">Already have an account? <a href="{{ url_for('login') }}">Login</a></div>
    </div>
    <script>
        function togglePassword(inputId, iconId) {
            const pwd = document.getElementById(inputId);
            const icon = document.getElementById(iconId);
            if (pwd.type === 'password') { pwd.type = 'text'; icon.classList.replace('fa-eye','fa-eye-slash'); }
            else { pwd.type = 'password'; icon.classList.replace('fa-eye-slash','fa-eye'); }
        }
        function handleSignupSubmit() {
            document.getElementById('signupBtn').disabled = true;
            document.getElementById('signupBtnText').textContent = 'Creating account...';
            document.getElementById('signupSpinner').style.display = 'inline-block';
        }
    </script>
</body>
</html>
'''

# ----- CHAT HTML with history support and centered delete confirmation -----
CHAT_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>College Assistant · Chat</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <script src="{{ url_for('static', filename='js/local-db.js') }}"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: #1a3a8a;
            height: 100vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .bg-container {
            position: fixed;
            inset: 0;
            z-index: 0;
            background: linear-gradient(145deg, #1a3a8a 0%, #2a5fc1 50%, #1e4a9e 100%);
            overflow: hidden;
            pointer-events: none;
        }
        .bg-shape {
            position: absolute;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            filter: blur(90px);
            animation: floatShape 22s ease-in-out infinite alternate;
            pointer-events: none;
        }
        .bg-shape:nth-child(1) { width: 600px; height: 600px; top: -15%; left: -10%; background: rgba(255,255,255,0.07); animation-duration: 24s; }
        .bg-shape:nth-child(2) { width: 700px; height: 700px; bottom: -20%; right: -10%; background: rgba(255,255,255,0.05); animation-duration: 28s; animation-delay: -5s; }
        .bg-shape:nth-child(3) { width: 400px; height: 400px; top: 30%; left: 55%; background: rgba(255,255,255,0.04); animation-duration: 20s; animation-delay: -9s; }
        .bg-shape:nth-child(4) { width: 350px; height: 350px; bottom: 15%; left: 10%; background: rgba(255,255,255,0.05); animation-duration: 26s; animation-delay: -3s; }
        @keyframes floatShape {
            0% { transform: translate(0,0) scale(1); }
            33% { transform: translate(40px,-30px) scale(1.03); }
            66% { transform: translate(-30px,40px) scale(0.97); }
            100% { transform: translate(20px,-15px) scale(1.02); }
        }
        .bg-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 30% 40%, rgba(255,255,255,0.04) 0%, transparent 60%);
            animation: glowShift 18s ease-in-out infinite alternate;
        }
        @keyframes glowShift {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.02); }
            100% { opacity: 0.3; transform: scale(1); }
        }
        .app-container {
            position: relative;
            z-index: 1;
            display: flex;
            height: 100vh;
            max-width: 1440px;
            width: 100%;
            margin: 0 auto;
            padding: 0.75rem;
            gap: 0.75rem;
        }
        .sidebar {
            width: 260px;
            min-width: 260px;
            background: #FFFFFF;
            border-radius: 24px;
            box-shadow: 0 4px 20px rgba(0,20,60,0.15);
            border: 1px solid rgba(255,255,255,0.1);
            padding: 1.25rem 1rem;
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow-y: auto;
            transition: transform 0.3s ease;
        }
        .sidebar-header { display: flex; align-items: center; gap: 0.5rem; padding-bottom: 1rem; border-bottom: 1px solid #E2E8F0; margin-bottom: 1.25rem; }
        .sidebar-header .brand-icon { font-size: 1.3rem; color: #4F6EF7; }
        .sidebar-header .brand-name { font-weight: 600; font-size: 0.95rem; color: #1E293B; }
        .new-chat-btn {
            width: 100%; padding: 0.65rem;
            border-radius: 14px; border: 1.5px dashed #4F6EF7;
            background: rgba(79,110,247,0.04); color: #4F6EF7;
            font-weight: 600; font-size: 0.9rem;
            cursor: pointer; transition: all 0.25s;
            display: flex; align-items: center; justify-content: center;
            gap: 0.5rem; margin-bottom: 1rem; font-family: 'Inter', sans-serif;
        }
        .new-chat-btn:hover { background: rgba(79,110,247,0.08); border-color: #4F6EF7; transform: translateY(-1px); }
        .history-section { flex: 1; overflow-y: auto; }
        .history-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #94A3B8; margin: 0.5rem 0 0.3rem 0; }
        .chat-item {
            padding: 0.5rem 0.75rem;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 0.6rem;
            color: #1E293B;
            font-size: 0.82rem;
            margin-bottom: 0.1rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .chat-item i { color: #94A3B8; font-size: 0.75rem; width: 16px; flex-shrink: 0; }
        .chat-item:hover { background: #F7FAFF; }
        .chat-item.active { background: #EEF4FF; color: #4F6EF7; font-weight: 500; }
        .chat-item.active i { color: #4F6EF7; }
        .chat-item .delete-btn {
            margin-left: auto;
            color: #94A3B8;
            background: none;
            border: none;
            cursor: pointer;
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
            font-size: 0.7rem;
            transition: all 0.2s;
            visibility: hidden;
        }
        .chat-item:hover .delete-btn { visibility: visible; }
        .chat-item .delete-btn:hover { color: #EF4444; background: #FEE2E2; }
        .main-chat {
            flex: 1;
            background: #FFFFFF;
            border-radius: 24px;
            box-shadow: 0 4px 20px rgba(0,20,60,0.1);
            border: 1px solid rgba(255,255,255,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-width: 0;
        }
        .chat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.9rem 1.5rem;
            border-bottom: 1px solid #E2E8F0;
            flex-shrink: 0;
        }
        .chat-header-left { display: flex; align-items: center; gap: 1rem; }
        .chat-header-left .menu-toggle { display: none; background: none; border: none; font-size: 1.2rem; color: #1E293B; cursor: pointer; padding: 0.25rem; }
        .chat-header-left .brand-name { font-weight: 600; font-size: 1rem; color: #1E293B; display: flex; align-items: center; gap: 0.4rem; }
        .chat-header-left .brand-name i { color: #4F6EF7; }
        .chat-header-right { 
            display: flex; 
            align-items: center; 
            gap: 0.75rem; 
            position: relative;
        }
        .user-avatar { 
            width: 34px; 
            height: 34px; 
            border-radius: 50%; 
            background: #4F6EF7; 
            color: #fff; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-weight: 600; 
            font-size: 0.85rem; 
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .user-avatar:hover { opacity: 0.85; transform: scale(1.05); }
        .user-menu { position: relative; display: inline-block; }
        .user-menu .user-name {
            font-size: 0.85rem;
            font-weight: 500;
            color: #1E293B;
            cursor: pointer;
            padding: 0.25rem 0.5rem;
            border-radius: 8px;
            transition: background 0.2s;
        }
        .user-menu .user-name:hover { background: #F7FAFF; }
        .user-menu .user-name i { font-size: 0.7rem; color: #94A3B8; margin-left: 0.3rem; }
        .dropdown-menu {
            display: none;
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 0.5rem;
            background: #FFFFFF;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            border: 1px solid #E2E8F0;
            min-width: 200px;
            overflow: hidden;
            z-index: 1000;
            animation: dropdownFade 0.2s ease;
        }
        .dropdown-menu.open { display: block; }
        @keyframes dropdownFade {
            0% { opacity: 0; transform: translateY(-8px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        .dropdown-menu .dropdown-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.7rem 1.2rem;
            color: #1E293B;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: background 0.2s;
            cursor: pointer;
            border: none;
            background: none;
            width: 100%;
            text-align: left;
            font-family: 'Inter', sans-serif;
        }
        .dropdown-menu .dropdown-item:hover { background: #F7FAFF; }
        .dropdown-menu .dropdown-item i { color: #64748B; width: 18px; font-size: 0.9rem; }
        .dropdown-menu .dropdown-divider { height: 1px; background: #E2E8F0; margin: 0.25rem 0; }
        .dropdown-menu .dropdown-item.logout-item { color: #EF4444; }
        .dropdown-menu .dropdown-item.logout-item i { color: #EF4444; }
        .dropdown-menu .dropdown-item.logout-item:hover { background: #FEF2F2; }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1.5rem 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }
        .empty-state {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 2rem;
            animation: fadeIn 0.6s ease;
        }
        .empty-state .icon { font-size: 3.5rem; color: #4F6EF7; background: rgba(79,110,247,0.06); width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; border-radius: 50%; margin-bottom: 1rem; }
        .empty-state h2 { font-size: 1.5rem; font-weight: 600; color: #1E293B; margin-bottom: 0.25rem; }
        .empty-state p { color: #64748B; font-size: 0.95rem; margin-bottom: 1.5rem; }
        .empty-categories { display: flex; gap: 0.75rem; flex-wrap: wrap; justify-content: center; margin-bottom: 1.5rem; }
        .empty-categories span { background: #F7FAFF; padding: 0.35rem 1rem; border-radius: 40px; font-size: 0.8rem; color: #64748B; border: 1px solid #E2E8F0; }
        .suggestion-grid { display: flex; flex-wrap: wrap; gap: 0.6rem; justify-content: center; max-width: 600px; }
        .suggestion-btn { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 40px; padding: 0.6rem 1.2rem; font-size: 0.85rem; color: #1E293B; cursor: pointer; transition: all 0.25s; font-family: 'Inter', sans-serif; white-space: nowrap; }
        .suggestion-btn:hover { border-color: #4F6EF7; background: #EEF4FF; transform: translateY(-1px); box-shadow: 0 2px 8px rgba(79,110,247,0.06); }
        .message { display: flex; flex-direction: column; max-width: 80%; animation: fadeIn 0.3s ease; }
        .message.user { align-self: flex-end; }
        .message.ai { align-self: flex-start; }
        .message .msg-label { font-size: 0.7rem; font-weight: 600; color: #94A3B8; margin-bottom: 0.2rem; letter-spacing: 0.02em; }
        .message .bubble { padding: 0.85rem 1.2rem; border-radius: 18px; font-size: 0.95rem; line-height: 1.6; word-wrap: break-word; }
        .message.user .bubble { background: #EEF4FF; color: #1E293B; border-bottom-right-radius: 4px; }
        .message.ai .bubble { background: #FFFFFF; border: 1px solid #E2E8F0; color: #1E293B; border-bottom-left-radius: 4px; }
        .source-section { margin-top: 0.75rem; padding: 0.75rem 1rem; background: #F7FAFF; border-radius: 14px; border: 1px solid #E2E8F0; max-width: 100%; }
        .source-section .source-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: #64748B; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.3rem; }
        .source-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.3rem 0; font-size: 0.8rem; color: #1E293B; }
        .source-item i { color: #4F6EF7; width: 16px; font-size: 0.8rem; }
        .source-item .doc-name { font-weight: 500; }
        .source-item .page-num { color: #64748B; font-size: 0.7rem; background: #E2E8F0; padding: 0.05rem 0.5rem; border-radius: 20px; }
        .loading-dots { display: flex; gap: 0.3rem; padding: 0.5rem 0; }
        .loading-dots span { width: 8px; height: 8px; background: #4F6EF7; border-radius: 50%; animation: dotPulse 1.4s infinite ease-in-out; }
        .loading-dots span:nth-child(2) { animation-delay: 0.2s; }
        .loading-dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes dotPulse {
            0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
            40% { opacity: 1; transform: scale(1); }
        }
        .loading-status { font-size: 0.8rem; color: #64748B; margin-top: 0.2rem; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        .chat-input-area { padding: 0.75rem 1.5rem 1.25rem; border-top: 1px solid #E2E8F0; flex-shrink: 0; background: #FFFFFF; border-radius: 0 0 24px 24px; }
        .input-wrapper {
            display: flex; align-items: flex-end; gap: 0.5rem;
            background: #F7FAFF; border-radius: 20px;
            padding: 0.3rem 0.3rem 0.3rem 1rem;
            border: 1.5px solid #E2E8F0;
            transition: border 0.25s, box-shadow 0.25s;
        }
        .input-wrapper:focus-within { border-color: #4F6EF7; box-shadow: 0 0 0 4px rgba(79,110,247,0.06), 0 2px 8px rgba(79,110,247,0.02); }
        .input-wrapper textarea {
            flex: 1; border: none; background: transparent;
            padding: 0.6rem 0; font-family: 'Inter', sans-serif;
            font-size: 0.9rem; resize: none; outline: none;
            color: #1E293B; min-height: 24px; max-height: 120px;
            line-height: 1.5;
        }
        .input-wrapper textarea::placeholder { color: #94A3B8; }
        .input-wrapper .send-btn {
            background: #4F6EF7; border: none; color: #fff;
            width: 40px; height: 40px; border-radius: 50%;
            cursor: pointer; transition: all 0.25s;
            display: flex; align-items: center; justify-content: center;
            flex-shrink: 0; font-size: 1rem;
        }
        .input-wrapper .send-btn:hover:not(:disabled) { background: #3b5de7; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(79,110,247,0.2); }
        .input-wrapper .send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        
        /* ----- DELETE CONFIRMATION MODAL (centered) ----- */
        .delete-modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.35);
            backdrop-filter: blur(6px);
            z-index: 2000;
            align-items: center;
            justify-content: center;
            animation: modalFadeIn 0.25s ease;
        }
        .delete-modal-overlay.active {
            display: flex;
        }
        @keyframes modalFadeIn {
            0% { opacity: 0; }
            100% { opacity: 1; }
        }
        .delete-modal {
            background: #FFFFFF;
            border-radius: 28px;
            max-width: 400px;
            width: 100%;
            padding: 2rem 2rem 1.8rem;
            box-shadow: 0 24px 64px rgba(0,0,0,0.2);
            text-align: center;
            animation: modalSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes modalSlideUp {
            0% { opacity: 0; transform: scale(0.95) translateY(16px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        .delete-modal .modal-icon {
            font-size: 2.5rem;
            color: #EF4444;
            margin-bottom: 0.5rem;
        }
        .delete-modal h3 {
            font-size: 1.3rem;
            font-weight: 600;
            color: #1E293B;
            margin-bottom: 0.3rem;
        }
        .delete-modal p {
            color: #64748B;
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }
        .delete-modal .modal-actions {
            display: flex;
            gap: 0.75rem;
            justify-content: center;
        }
        .delete-modal .modal-actions .btn-modal {
            padding: 0.65rem 2rem;
            border-radius: 40px;
            font-weight: 600;
            font-size: 0.95rem;
            border: none;
            cursor: pointer;
            transition: all 0.25s;
            font-family: 'Inter', sans-serif;
        }
        .delete-modal .modal-actions .btn-cancel {
            background: #F7FAFF;
            color: #1E293B;
            border: 1px solid #E2E8F0;
        }
        .delete-modal .modal-actions .btn-cancel:hover {
            background: #EEF4FF;
        }
        .delete-modal .modal-actions .btn-delete {
            background: #EF4444;
            color: #fff;
            box-shadow: 0 4px 14px rgba(239,68,68,0.2);
        }
        .delete-modal .modal-actions .btn-delete:hover {
            background: #DC2626;
            transform: translateY(-1px);
            box-shadow: 0 8px 24px rgba(239,68,68,0.25);
        }

        @media (max-width: 1024px) { .sidebar { width: 220px; min-width: 220px; } }
        @media (max-width: 768px) {
            .app-container { padding: 0.5rem; gap: 0.5rem; }
            .sidebar {
                position: fixed; top: 0; left: 0;
                width: 280px; height: 100vh; z-index: 100;
                border-radius: 0 20px 20px 0;
                transform: translateX(-120%);
                transition: transform 0.3s cubic-bezier(0.16,1,0.3,1);
                box-shadow: 0 8px 40px rgba(0,0,0,0.2);
                padding: 1.25rem 1rem;
            }
            .sidebar.open { transform: translateX(0); }
            .sidebar-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 99; }
            .sidebar-overlay.active { display: block; }
            .chat-header-left .menu-toggle { display: block; }
            .chat-messages { padding: 1rem; }
            .message { max-width: 92%; }
            .suggestion-grid { flex-direction: column; align-items: center; }
            .suggestion-btn { white-space: normal; width: 100%; max-width: 320px; text-align: center; }
            .chat-input-area { padding: 0.5rem 1rem 0.75rem; }
            .user-menu .user-name { display: none; }
            .dropdown-menu { right: -0.5rem; min-width: 180px; }
            .delete-modal { margin: 1rem; padding: 1.5rem; }
            .delete-modal .modal-actions { flex-direction: column; }
            .delete-modal .modal-actions .btn-modal { width: 100%; }
        }
        @media (max-width: 480px) {
            .chat-header { padding: 0.6rem 1rem; }
            .chat-messages { padding: 0.75rem; }
            .empty-state .icon { width: 60px; height: 60px; font-size: 2.5rem; }
            .empty-state h2 { font-size: 1.2rem; }
        }
    </style>
</head>
<body>
    <div class="bg-container" aria-hidden="true">
        <div class="bg-shape"></div><div class="bg-shape"></div>
        <div class="bg-shape"></div><div class="bg-shape"></div>
    </div>
    
    <!-- DELETE CONFIRMATION MODAL (centered) -->
    <div class="delete-modal-overlay" id="deleteModalOverlay">
        <div class="delete-modal">
            <div class="modal-icon"><i class="fas fa-trash-alt"></i></div>
            <h3>Delete Chat?</h3>
            <p>This will permanently delete this conversation. This action cannot be undone.</p>
            <div class="modal-actions">
                <button class="btn-modal btn-cancel" id="modalCancelBtn">Cancel</button>
                <button class="btn-modal btn-delete" id="modalDeleteBtn">Delete</button>
            </div>
        </div>
    </div>

    <div class="app-container">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <span class="brand-icon"><i class="fas fa-graduation-cap"></i></span>
                <span class="brand-name">College Assistant</span>
            </div>
            <button class="new-chat-btn" id="newChatBtn" data-session-id="">
                <i class="fas fa-plus"></i> New Chat
            </button>
            <div class="history-section" id="historySection">
                <!-- History items rendered by JS -->
            </div>
        </div>
        <div class="sidebar-overlay" id="sidebarOverlay"></div>
        <div class="main-chat">
            <div class="chat-header">
                <div class="chat-header-left">
                    <button class="menu-toggle" id="menuToggle"><i class="fas fa-bars"></i></button>
                    <div class="brand-name"><i class="fas fa-graduation-cap"></i> College Assistant</div>
                </div>
                <div class="chat-header-right">
                    <div class="user-menu">
                        <span class="user-name" id="userNameToggle">
                            {{ session.get('user_name', 'Student') }}
                            <i class="fas fa-chevron-down"></i>
                        </span>
                        <div class="dropdown-menu" id="dropdownMenu">
                            <div class="dropdown-item" onclick="window.location.href='{{ url_for('profile') }}'">
                                <i class="fas fa-user"></i> Profile
                            </div>
                            <div class="dropdown-item" onclick="window.location.href='{{ url_for('change_password') }}'">
                                <i class="fas fa-key"></i> Change Password
                            </div>
                            <div class="dropdown-divider"></div>
                            <div class="dropdown-item logout-item" onclick="window.location.href='{{ url_for('logout') }}'">
                                <i class="fas fa-sign-out-alt"></i> Logout
                            </div>
                        </div>
                    </div>
                    <div class="user-avatar" id="avatarToggle">{{ session.get('user_name', 'S')[0]|upper }}</div>
                </div>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="empty-state" id="emptyState">
                    <div class="icon"><i class="fas fa-graduation-cap"></i></div>
                    <h2>College Assistant</h2>
                    <p>How can I help you today?<br />Ask questions about your college.</p>
                    <div class="empty-categories">
                        <span>Academic Rules</span><span>Exams</span>
                        <span>Attendance</span><span>Fees</span>
                    </div>
                    <div class="suggestion-grid">
                        <button class="suggestion-btn" data-question="What is the minimum attendance requirement?">What is the minimum attendance requirement?</button>
                        <button class="suggestion-btn" data-question="When are the semester exams?">When are the semester exams?</button>
                        <button class="suggestion-btn" data-question="What are the exam eligibility rules?">What are the exam eligibility rules?</button>
                        <button class="suggestion-btn" data-question="What is the fee structure?">What is the fee structure?</button>
                    </div>
                </div>
            </div>
            <div class="chat-input-area">
                <div class="input-wrapper">
                    <textarea id="chatInput" rows="1" placeholder="Ask anything about your college..."></textarea>
                    <button class="send-btn" id="sendBtn"><i class="fas fa-arrow-right"></i></button>
                </div>
            </div>
        </div>
    </div>
    <script type="module">
        import localDB from '/static/js/local-db.js';

        const chatMessages = document.getElementById('chatMessages');
        const emptyState = document.getElementById('emptyState');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const newChatBtn = document.getElementById('newChatBtn');
        const menuToggle = document.getElementById('menuToggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        const historySection = document.getElementById('historySection');
        
        // Delete modal elements
        const deleteModalOverlay = document.getElementById('deleteModalOverlay');
        const modalCancelBtn = document.getElementById('modalCancelBtn');
        const modalDeleteBtn = document.getElementById('modalDeleteBtn');

        // Get current user ID from session (passed via template)
        const currentUserId = {{ session.get('user_id', 'anonymous') | tojson }};

        let isProcessing = false;
        let currentSessionId = null;
        let pendingDeleteId = null;

        // ---------- DELETE MODAL ----------
        function showDeleteModal(sessionId) {
            pendingDeleteId = sessionId;
            deleteModalOverlay.classList.add('active');
        }

        function hideDeleteModal() {
            deleteModalOverlay.classList.remove('active');
            pendingDeleteId = null;
        }

        modalCancelBtn.addEventListener('click', hideDeleteModal);
        deleteModalOverlay.addEventListener('click', function(e) {
            if (e.target === this) hideDeleteModal();
        });

        modalDeleteBtn.addEventListener('click', async function() {
            if (pendingDeleteId !== null) {
                await performDelete(pendingDeleteId);
                hideDeleteModal();
            }
        });

        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') hideDeleteModal();
        });

        // ---------- DROPDOWN TOGGLE ----------
        const userNameToggle = document.getElementById('userNameToggle');
        const avatarToggle = document.getElementById('avatarToggle');
        const dropdownMenu = document.getElementById('dropdownMenu');

        function toggleDropdown(e) {
            e.stopPropagation();
            dropdownMenu.classList.toggle('open');
        }

        userNameToggle.addEventListener('click', toggleDropdown);
        avatarToggle.addEventListener('click', toggleDropdown);

        document.addEventListener('click', function(e) {
            if (!dropdownMenu.contains(e.target) && 
                !userNameToggle.contains(e.target) && 
                !avatarToggle.contains(e.target)) {
                dropdownMenu.classList.remove('open');
            }
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') dropdownMenu.classList.remove('open');
        });

        // ---------- SIDEBAR TOGGLE (mobile) ----------
        function toggleSidebar(open) {
            sidebar.classList.toggle('open', open);
            overlay.classList.toggle('active', open);
        }
        menuToggle.addEventListener('click', () => toggleSidebar(true));
        overlay.addEventListener('click', () => toggleSidebar(false));

        // ---------- AUTO-RESIZE TEXTAREA ----------
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // ---------- LOAD HISTORY ----------
        async function loadHistory() {
            try {
                const sessions = await localDB.getAllSessions(currentUserId);
                renderHistory(sessions);
                if (sessions.length > 0) {
                    await loadSession(sessions[0].id);
                }
            } catch (error) {
                console.error('Error loading history:', error);
                showHistoryError();
            }
        }

        function showHistoryError() {
            historySection.innerHTML = '';
            const emptyMsg = document.createElement('div');
            emptyMsg.style.cssText = 'color: #EF4444; font-size: 0.8rem; text-align: center; padding: 1rem 0;';
            emptyMsg.textContent = 'Unable to load chat history';
            historySection.appendChild(emptyMsg);
        }

        function renderHistory(sessions) {
            historySection.innerHTML = '';
            if (sessions.length === 0) {
                const emptyMsg = document.createElement('div');
                emptyMsg.style.cssText = 'color: #94A3B8; font-size: 0.8rem; text-align: center; padding: 1rem 0;';
                emptyMsg.textContent = 'No chat history';
                historySection.appendChild(emptyMsg);
                return;
            }

            let currentLabel = '';
            sessions.forEach(session => {
                const date = new Date(session.created_at);
                const today = new Date();
                const yesterday = new Date(today);
                yesterday.setDate(yesterday.getDate() - 1);
                
                let label = '';
                if (date.toDateString() === today.toDateString()) label = 'Today';
                else if (date.toDateString() === yesterday.toDateString()) label = 'Yesterday';
                else label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

                if (label !== currentLabel) {
                    currentLabel = label;
                    const labelEl = document.createElement('div');
                    labelEl.className = 'history-label';
                    labelEl.textContent = label;
                    historySection.appendChild(labelEl);
                }

                const item = document.createElement('div');
                item.className = 'chat-item' + (session.id === currentSessionId ? ' active' : '');
                item.dataset.sessionId = session.id;
                item.innerHTML = `
                    <i class="fas fa-message"></i>
                    <span>${escapeHtml(session.title)}</span>
                    <button class="delete-btn" data-session-id="${session.id}"><i class="fas fa-xmark"></i></button>
                `;
                item.addEventListener('click', () => loadSession(session.id));
                const deleteBtn = item.querySelector('.delete-btn');
                deleteBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    showDeleteModal(session.id);
                });
                historySection.appendChild(item);
            });
        }

        async function loadSession(sessionId) {
            try {
                const messages = await localDB.getMessages(sessionId);
                currentSessionId = sessionId;
                newChatBtn.dataset.sessionId = sessionId;
                
                document.querySelectorAll('.message').forEach(m => m.remove());
                emptyState.style.display = 'none';

                messages.forEach(msg => {
                    if (msg.role === 'user') {
                        addUserMessage(msg.content, false);
                    } else {
                        addAIMessage(msg.content, msg.sources || [], false);
                    }
                });

                if (messages.length === 0) {
                    emptyState.style.display = 'flex';
                }

                document.querySelectorAll('.chat-item').forEach(el => {
                    el.classList.toggle('active', el.dataset.sessionId === sessionId);
                });

                scrollToBottom();
            } catch (error) {
                console.error('Error loading session:', error);
            }
        }

        async function performDelete(sessionId) {
            try {
                await localDB.deleteSession(sessionId);
                if (currentSessionId === sessionId) {
                    document.querySelectorAll('.message').forEach(m => m.remove());
                    emptyState.style.display = 'flex';
                    currentSessionId = null;
                    newChatBtn.dataset.sessionId = '';
                }
                await loadHistory();
            } catch (error) {
                console.error('Error deleting session:', error);
            }
        }

        async function createNewSession() {
            try {
                // Generate title from first message later, or use default
                const session = await localDB.createSession(currentUserId, 'New Chat');
                currentSessionId = session.id;
                newChatBtn.dataset.sessionId = session.id;
                document.querySelectorAll('.message').forEach(m => m.remove());
                emptyState.style.display = 'flex';
                await loadHistory();
                chatInput.focus();
                if (window.innerWidth <= 768) toggleSidebar(false);
            } catch (error) {
                console.error('Error creating session:', error);
            }
        }

        // ---------- SEND MESSAGE ----------
        function sendMessage() {
            const text = chatInput.value.trim();
            if (!text || isProcessing) return;
            chatInput.value = '';
            chatInput.style.height = 'auto';
            emptyState.style.display = 'none';
            
            if (!currentSessionId) {
                createNewSessionAndSend(text);
                return;
            }
            
            addUserMessage(text, true);
            requestAIResponse(text, currentSessionId);
        }

        async function createNewSessionAndSend(text) {
            try {
                const session = await localDB.createSession(currentUserId, generateTitle(text));
                currentSessionId = session.id;
                newChatBtn.dataset.sessionId = session.id;
                await loadHistory();
                addUserMessage(text, true);
                await localDB.addMessage(currentSessionId, 'user', text, []);
                requestAIResponse(text, currentSessionId);
            } catch (error) {
                console.error('Error creating session:', error);
            }
        }

        function generateTitle(text) {
            // Generate a short title from the first user message
            const maxLen = 40;
            let title = text.trim();
            if (title.length > maxLen) {
                title = title.substring(0, maxLen).trim() + '...';
            }
            return title || 'New Chat';
        }

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                chatInput.value = this.dataset.question;
                sendMessage();
            });
        });

        newChatBtn.addEventListener('click', createNewSession);

        // ---------- ADD MESSAGE ----------
        function addUserMessage(text, save = true) {
            const div = document.createElement('div');
            div.className = 'message user';
            div.innerHTML = `<div class="msg-label">You</div><div class="bubble">${escapeHtml(text)}</div>`;
            chatMessages.appendChild(div);
            scrollToBottom();
        }

        function addAIMessage(text, sources, save = true) {
            const div = document.createElement('div');
            div.className = 'message ai';
            let sourceHtml = '';
            if (sources && sources.length > 0) {
                sourceHtml = `<div class="source-section"><div class="source-label"><i class="fas fa-book-open"></i> Sources (${sources.length})</div>
                    ${sources.map(s => `<div class="source-item"><i class="fas fa-file-pdf"></i><span class="doc-name">${escapeHtml(s.doc)}</span><span class="page-num">Page ${s.page}</span></div>`).join('')}
                </div>`;
            }
            div.innerHTML = `<div class="msg-label">College Assistant</div><div class="bubble">${escapeHtml(text)}${sourceHtml}</div>`;
            chatMessages.appendChild(div);
            scrollToBottom();
        }

        function addLoadingMessage() {
            const div = document.createElement('div');
            div.className = 'message ai';
            div.id = 'loadingMessage';
            div.innerHTML = `<div class="msg-label">College Assistant</div><div class="bubble">
                <div class="loading-dots"><span></span><span></span><span></span></div>
                <div class="loading-status" id="loadingStatus">Generating answer...</div>
            </div>`;
            chatMessages.appendChild(div);
            scrollToBottom();
            return div;
        }

        function removeLoadingMessage() {
            const el = document.getElementById('loadingMessage');
            if (el) el.remove();
        }

        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // ---------- AI REQUEST ----------
        async function requestAIResponse(userText, sessionId) {
            isProcessing = true;
            sendBtn.disabled = true;
            addLoadingMessage();
            const statusEl = document.getElementById('loadingStatus');
            statusEl.textContent = 'Generating answer...';

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userText, session_id: sessionId })
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'Request failed');
                removeLoadingMessage();
                addAIMessage(result.answer, result.sources, true);
                // Save AI response to IndexedDB
                await localDB.addMessage(sessionId, 'assistant', result.answer, result.sources || []);
                // Update session title if it's still "New Chat"
                const session = await localDB.getSession(sessionId);
                if (session && session.title === 'New Chat') {
                    await localDB.updateSession(sessionId, { title: generateTitle(userText) });
                    await loadHistory();
                }
            } catch (error) {
                removeLoadingMessage();
                addAIMessage(error.message || 'Unable to get a response right now.', []);
            } finally {
                isProcessing = false;
                sendBtn.disabled = false;
                chatInput.focus();
            }
        }

        // ---------- INIT ----------
        await loadHistory();
        chatInput.focus();

        window.addEventListener('resize', function() {
            if (window.innerWidth > 768) toggleSidebar(false);
        });
    </script>
</body>
</html>
'''

# ----- CHANGE PASSWORD HTML -----
CHANGE_PASSWORD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>Change Password · College Assistant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            background: #1a3a8a;
            position: relative;
            overflow-x: hidden;
        }
        .bg-container {
            position: fixed;
            inset: 0;
            z-index: 0;
            background: linear-gradient(145deg, #1a3a8a 0%, #2a5fc1 50%, #1e4a9e 100%);
            overflow: hidden;
            pointer-events: none;
        }
        .bg-shape {
            position: absolute;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            filter: blur(90px);
            animation: floatShape 20s ease-in-out infinite alternate;
            pointer-events: none;
        }
        .bg-shape:nth-child(1) { width: 600px; height: 600px; top: -15%; left: -10%; background: rgba(255,255,255,0.07); animation-duration: 24s; }
        .bg-shape:nth-child(2) { width: 700px; height: 700px; bottom: -20%; right: -10%; background: rgba(255,255,255,0.05); animation-duration: 28s; animation-delay: -5s; }
        .bg-shape:nth-child(3) { width: 400px; height: 400px; top: 30%; left: 55%; background: rgba(255,255,255,0.04); animation-duration: 22s; animation-delay: -9s; }
        .bg-shape:nth-child(4) { width: 350px; height: 350px; bottom: 15%; left: 10%; background: rgba(255,255,255,0.05); animation-duration: 26s; animation-delay: -3s; }
        @keyframes floatShape {
            0% { transform: translate(0,0) scale(1); }
            33% { transform: translate(40px,-30px) scale(1.03); }
            66% { transform: translate(-30px,40px) scale(0.97); }
            100% { transform: translate(20px,-15px) scale(1.02); }
        }
        .bg-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 30% 40%, rgba(255,255,255,0.04) 0%, transparent 60%);
            animation: glowShift 18s ease-in-out infinite alternate;
        }
        @keyframes glowShift {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.02); }
            100% { opacity: 0.3; transform: scale(1); }
        }
        .password-card {
            position: relative;
            z-index: 1;
            max-width: 440px;
            width: 100%;
            background: #FFFFFF;
            border-radius: 36px;
            box-shadow: 0 24px 64px rgba(0,20,60,0.25), 0 8px 24px rgba(0,0,0,0.06);
            padding: 2.5rem 2rem;
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(2px);
            transition: box-shadow 0.3s ease, transform 0.2s ease;
            animation: cardEntrance 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
        }
        @keyframes cardEntrance {
            0% { opacity: 0; transform: translateY(24px) scale(0.96); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .password-card:hover { box-shadow: 0 28px 72px rgba(0,20,60,0.3), 0 8px 24px rgba(0,0,0,0.04); }
        .brand-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.5rem; }
        .brand-icon { font-size: 1.9rem; color: #4F6EF7; background: rgba(79,110,247,0.08); width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; border-radius: 16px; }
        .brand-name { font-weight: 600; font-size: 1.2rem; color: #1E293B; background: linear-gradient(135deg, #1E293B, #2d3a4f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .form-heading h1 { font-size: 1.6rem; font-weight: 600; color: #1E293B; margin-bottom: 0.15rem; }
        .form-sub { color: #64748B; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .flash-message { padding: 0.75rem 1rem; border-radius: 12px; margin-bottom: 1rem; font-size: 0.9rem; display: flex; align-items: center; gap: 0.5rem; }
        .flash-error { background: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; }
        .flash-success { background: #DCFCE7; color: #16A34A; border: 1px solid #86EFAC; }
        .input-group { margin-bottom: 1.25rem; position: relative; }
        .input-group label { display: block; font-weight: 500; font-size: 0.85rem; color: #1E293B; margin-bottom: 0.3rem; }
        .input-wrapper { position: relative; display: flex; align-items: center; }
        .input-wrapper input {
            width: 100%; padding: 0.85rem 1rem; padding-right: 3rem;
            font-size: 0.95rem; font-family: 'Inter', sans-serif;
            background: #fff; border: 1.5px solid #E2E8F0;
            border-radius: 18px; outline: none;
            transition: border 0.25s, box-shadow 0.25s;
            color: #1E293B;
        }
        .input-wrapper input:focus { border-color: #4F6EF7; box-shadow: 0 0 0 4px rgba(79,110,247,0.08), 0 2px 8px rgba(79,110,247,0.02); }
        .input-wrapper input::placeholder { color: #94A3B8; }
        .input-group.error .input-wrapper input { border-color: #EF4444; box-shadow: 0 0 0 3px rgba(239,68,68,0.05); }
        .error-message {
            font-size: 0.8rem; color: #EF4444; margin-top: 0.3rem;
            display: flex; align-items: center; gap: 0.25rem;
            opacity: 0; transform: translateY(-4px);
            transition: opacity 0.25s, transform 0.25s;
        }
        .input-group.error .error-message { opacity: 1; transform: translateY(0); }
        .toggle-password {
            position: absolute; right: 1rem;
            background: none; border: none;
            color: #94A3B8; font-size: 1.1rem;
            cursor: pointer; padding: 0.25rem;
            transition: color 0.2s;
        }
        .toggle-password:hover { color: #4F6EF7; }
        .btn-primary {
            width: 100%; padding: 0.9rem;
            background: #4F6EF7; color: #fff;
            border: none; border-radius: 40px;
            font-weight: 600; font-size: 1rem;
            cursor: pointer; transition: all 0.25s;
            box-shadow: 0 4px 14px rgba(79,110,247,0.25);
            display: flex; align-items: center; justify-content: center;
            gap: 0.5rem; font-family: 'Inter', sans-serif;
        }
        .btn-primary:hover:not(:disabled) { background: #3b5de7; transform: translateY(-2px); box-shadow: 0 8px 24px rgba(79,110,247,0.30); }
        .btn-primary:disabled { opacity: 0.7; cursor: not-allowed; transform: scale(0.98); }
        .btn-primary .spinner {
            display: inline-block; width: 1.1rem; height: 1.1rem;
            border: 2.5px solid rgba(255,255,255,0.25);
            border-top: 2.5px solid #fff;
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .success-message {
            display: none; background: #F0FDF4;
            border: 1px solid #BBF7D0; border-radius: 24px;
            padding: 1rem 1.2rem; margin-top: 1rem;
            color: #15803D; font-weight: 500;
            align-items: center; gap: 0.6rem;
            animation: successPop 0.4s cubic-bezier(0.16,1,0.3,1);
        }
        .success-message.show { display: flex; }
        @keyframes successPop {
            0% { opacity: 0; transform: scale(0.94) translateY(6px); }
            100% { opacity: 1; transform: scale(1) translateY(0); }
        }
        .form-footer { margin-top: 1.5rem; text-align: center; font-size: 0.95rem; color: #64748B; }
        .form-footer a { color: #4F6EF7; font-weight: 600; text-decoration: none; border-bottom: 1.5px solid transparent; transition: border-color 0.2s; cursor: pointer; }
        .form-footer a:hover { border-bottom-color: #4F6EF7; }
        .password-strength { margin-top: 0.4rem; display: flex; gap: 0.3rem; }
        .password-strength .bar { flex: 1; height: 4px; background: #E2E8F0; border-radius: 4px; transition: background 0.3s; }
        .password-strength .bar.active.weak { background: #EF4444; }
        .password-strength .bar.active.medium { background: #F59E0B; }
        .password-strength .bar.active.strong { background: #22C55E; }
        .strength-text { font-size: 0.7rem; color: #64748B; margin-top: 0.2rem; }
        @media (max-width: 520px) {
            .password-card { padding: 1.8rem 1.2rem; border-radius: 28px; }
            .form-heading h1 { font-size: 1.4rem; }
            .brand-name { font-size: 1rem; }
            .input-wrapper input { padding: 0.8rem 1rem; padding-right: 3rem; font-size: 0.9rem; }
            .btn-primary { font-size: 0.95rem; padding: 0.8rem; }
        }
    </style>
</head>
<body>
    <div class="bg-container" aria-hidden="true">
        <div class="bg-shape"></div><div class="bg-shape"></div>
        <div class="bg-shape"></div><div class="bg-shape"></div>
    </div>
    <div class="password-card">
        <div class="brand-header">
            <div class="brand-icon"><i class="fas fa-graduation-cap"></i></div>
            <div class="brand-name">College Assistant</div>
        </div>
        <div class="form-heading">
            <h1>Change Password</h1>
            <div class="form-sub">Update your account password</div>
        </div>
        <div id="flashContainer">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="flash-message flash-{{ category }}"><i class="fas fa-circle-exclamation"></i> {{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        <form method="POST" action="{{ url_for('change_password') }}" novalidate>
            <div class="input-group" id="currentGroup">
                <label for="currentPassword">Current Password</label>
                <div class="input-wrapper">
                    <input type="password" id="currentPassword" name="current_password" placeholder="Enter your current password" />
                    <button type="button" class="toggle-password" onclick="togglePassword('currentPassword', 'currentIcon')">
                        <i class="fas fa-eye" id="currentIcon"></i>
                    </button>
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span id="currentError">Please enter your current password.</span></div>
            </div>
            <div class="input-group" id="newGroup">
                <label for="newPassword">New Password</label>
                <div class="input-wrapper">
                    <input type="password" id="newPassword" name="new_password" placeholder="Enter your new password" />
                    <button type="button" class="toggle-password" onclick="togglePassword('newPassword', 'newIcon')">
                        <i class="fas fa-eye" id="newIcon"></i>
                    </button>
                </div>
                <div class="password-strength" id="strengthBars">
                    <div class="bar" id="bar1"></div>
                    <div class="bar" id="bar2"></div>
                    <div class="bar" id="bar3"></div>
                    <div class="bar" id="bar4"></div>
                </div>
                <div class="strength-text" id="strengthText">Password must be at least 8 characters</div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span id="newError">Password must be at least 8 characters.</span></div>
            </div>
            <div class="input-group" id="confirmGroup">
                <label for="confirmPassword">Confirm New Password</label>
                <div class="input-wrapper">
                    <input type="password" id="confirmPassword" name="confirm_password" placeholder="Confirm your new password" />
                    <button type="button" class="toggle-password" onclick="togglePassword('confirmPassword', 'confirmIcon')">
                        <i class="fas fa-eye" id="confirmIcon"></i>
                    </button>
                </div>
                <div class="error-message"><i class="fas fa-circle-exclamation"></i> <span id="confirmError">Passwords do not match.</span></div>
            </div>
            <button type="submit" class="btn-primary" id="submitBtn">
                <span id="btnText">Update Password</span>
                <span id="btnSpinner" style="display: none;" class="spinner"></span>
            </button>
            <div class="success-message" id="successMessage">
                <i class="fas fa-check-circle"></i> Password updated successfully! Redirecting…
            </div>
        </form>
        <div class="form-footer">
            <a href="{{ url_for('chat') }}">← Back to Chat</a>
        </div>
    </div>
    <script>
        function togglePassword(inputId, iconId) {
            const input = document.getElementById(inputId);
            const icon = document.getElementById(iconId);
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        }

        function checkPasswordStrength(password) {
            let strength = 0;
            if (password.length >= 8) strength++;
            if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
            if (password.match(/\\d/)) strength++;
            if (password.match(/[^a-zA-Z0-9]/)) strength++;
            return strength;
        }

        const newPassword = document.getElementById('newPassword');
        const confirmPassword = document.getElementById('confirmPassword');
        const bar1 = document.getElementById('bar1');
        const bar2 = document.getElementById('bar2');
        const bar3 = document.getElementById('bar3');
        const bar4 = document.getElementById('bar4');
        const strengthText = document.getElementById('strengthText');

        newPassword.addEventListener('input', function() {
            const bars = [bar1, bar2, bar3, bar4];
            const strength = checkPasswordStrength(this.value);
            bars.forEach((bar, index) => {
                bar.className = 'bar';
                if (index < strength) {
                    bar.classList.add('active');
                    if (strength <= 2) bar.classList.add('weak');
                    else if (strength === 3) bar.classList.add('medium');
                    else bar.classList.add('strong');
                }
            });
            const texts = ['Weak', 'Weak', 'Medium', 'Strong', 'Strong'];
            const colors = ['#EF4444', '#EF4444', '#F59E0B', '#22C55E', '#22C55E'];
            if (this.value.length === 0) {
                strengthText.textContent = 'Password must be at least 8 characters';
                strengthText.style.color = '#64748B';
            } else {
                strengthText.textContent = `Password strength: ${texts[strength]}`;
                strengthText.style.color = colors[strength];
            }
        });

        document.querySelector('form').addEventListener('submit', function(e) {
            const current = document.getElementById('currentPassword').value;
            const newPwd = document.getElementById('newPassword').value;
            const confirm = document.getElementById('confirmPassword').value;
            let valid = true;

            if (!current) {
                document.getElementById('currentGroup').classList.add('error');
                valid = false;
            } else {
                document.getElementById('currentGroup').classList.remove('error');
            }

            if (newPwd.length < 8) {
                document.getElementById('newGroup').classList.add('error');
                valid = false;
            } else {
                document.getElementById('newGroup').classList.remove('error');
            }

            if (newPwd !== confirm) {
                document.getElementById('confirmGroup').classList.add('error');
                valid = false;
            } else {
                document.getElementById('confirmGroup').classList.remove('error');
            }

            if (!valid) {
                e.preventDefault();
            } else {
                document.getElementById('submitBtn').disabled = true;
                document.getElementById('btnText').textContent = 'Updating...';
                document.getElementById('btnSpinner').style.display = 'inline-block';
            }
        });
    </script>
</body>
</html>
'''

# ----- PROFILE HTML -----
PROFILE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes" />
    <title>Profile · College Assistant</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            background: #1a3a8a;
            position: relative;
            overflow-x: hidden;
        }
        .bg-container {
            position: fixed;
            inset: 0;
            z-index: 0;
            background: linear-gradient(145deg, #1a3a8a 0%, #2a5fc1 50%, #1e4a9e 100%);
            overflow: hidden;
            pointer-events: none;
        }
        .bg-shape {
            position: absolute;
            border-radius: 50%;
            background: rgba(255,255,255,0.06);
            filter: blur(90px);
            animation: floatShape 20s ease-in-out infinite alternate;
            pointer-events: none;
        }
        .bg-shape:nth-child(1) { width: 600px; height: 600px; top: -15%; left: -10%; background: rgba(255,255,255,0.07); animation-duration: 24s; }
        .bg-shape:nth-child(2) { width: 700px; height: 700px; bottom: -20%; right: -10%; background: rgba(255,255,255,0.05); animation-duration: 28s; animation-delay: -5s; }
        .bg-shape:nth-child(3) { width: 400px; height: 400px; top: 30%; left: 55%; background: rgba(255,255,255,0.04); animation-duration: 22s; animation-delay: -9s; }
        .bg-shape:nth-child(4) { width: 350px; height: 350px; bottom: 15%; left: 10%; background: rgba(255,255,255,0.05); animation-duration: 26s; animation-delay: -3s; }
        @keyframes floatShape {
            0% { transform: translate(0,0) scale(1); }
            33% { transform: translate(40px,-30px) scale(1.03); }
            66% { transform: translate(-30px,40px) scale(0.97); }
            100% { transform: translate(20px,-15px) scale(1.02); }
        }
        .bg-container::after {
            content: '';
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at 30% 40%, rgba(255,255,255,0.04) 0%, transparent 60%);
            animation: glowShift 18s ease-in-out infinite alternate;
        }
        @keyframes glowShift {
            0% { opacity: 0.3; transform: scale(1); }
            50% { opacity: 0.7; transform: scale(1.02); }
            100% { opacity: 0.3; transform: scale(1); }
        }
        .profile-card {
            position: relative;
            z-index: 1;
            max-width: 500px;
            width: 100%;
            background: #FFFFFF;
            border-radius: 36px;
            box-shadow: 0 24px 64px rgba(0,20,60,0.25), 0 8px 24px rgba(0,0,0,0.06);
            padding: 2.5rem 2rem;
            border: 1px solid rgba(255,255,255,0.15);
            backdrop-filter: blur(2px);
            transition: box-shadow 0.3s ease, transform 0.2s ease;
            animation: cardEntrance 0.7s cubic-bezier(0.16,1,0.3,1) forwards;
        }
        @keyframes cardEntrance {
            0% { opacity: 0; transform: translateY(24px) scale(0.96); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .profile-card:hover { box-shadow: 0 28px 72px rgba(0,20,60,0.3), 0 8px 24px rgba(0,0,0,0.04); }
        .brand-header { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.5rem; }
        .brand-icon { font-size: 1.9rem; color: #4F6EF7; background: rgba(79,110,247,0.08); width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; border-radius: 16px; }
        .brand-name { font-weight: 600; font-size: 1.2rem; color: #1E293B; background: linear-gradient(135deg, #1E293B, #2d3a4f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .form-heading h1 { font-size: 1.6rem; font-weight: 600; color: #1E293B; margin-bottom: 0.15rem; }
        .form-sub { color: #64748B; font-size: 0.9rem; margin-bottom: 1.5rem; }
        .field { margin: 1rem 0; padding: 0.75rem 1rem; background: #F7FAFF; border-radius: 12px; border: 1px solid #E2E8F0; }
        .field label { font-size: 0.75rem; color: #64748B; display: block; margin-bottom: 0.15rem; font-weight: 500; }
        .field .value { font-weight: 500; color: #1E293B; }
        .btn-group { display: flex; gap: 0.75rem; margin-top: 1.5rem; flex-wrap: wrap; }
        .btn { background: #4F6EF7; color: #fff; border: none; padding: 0.75rem 2rem; border-radius: 40px; font-weight: 600; cursor: pointer; text-decoration: none; display: inline-block; font-family: 'Inter', sans-serif; transition: all 0.25s; }
        .btn:hover { background: #3b5de7; transform: translateY(-1px); }
        .btn-secondary { background: #E2E8F0; color: #1E293B; }
        .btn-secondary:hover { background: #CBD5E1; }
        @media (max-width: 520px) {
            .profile-card { padding: 1.8rem 1.2rem; border-radius: 28px; }
            .form-heading h1 { font-size: 1.4rem; }
            .brand-name { font-size: 1rem; }
            .btn-group { flex-direction: column; }
            .btn { width: 100%; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="bg-container" aria-hidden="true">
        <div class="bg-shape"></div><div class="bg-shape"></div>
        <div class="bg-shape"></div><div class="bg-shape"></div>
    </div>
    <div class="profile-card">
        <div class="brand-header">
            <div class="brand-icon"><i class="fas fa-graduation-cap"></i></div>
            <div class="brand-name">College Assistant</div>
        </div>
        <div class="form-heading">
            <h1>👤 Profile</h1>
            <div class="form-sub">Your account information</div>
        </div>
        <div class="field">
            <label>Full Name</label>
            <div class="value">{{ user.name }}</div>
        </div>
        <div class="field">
            <label>Email</label>
            <div class="value">{{ user.email }}</div>
        </div>
        <div class="field">
            <label>Member Since</label>
            <div class="value">{{ user.created_at }}</div>
        </div>
        <div class="btn-group">
            <a href="{{ url_for('chat') }}" class="btn">← Back to Chat</a>
            <a href="{{ url_for('change_password') }}" class="btn btn-secondary">Change Password</a>
        </div>
    </div>
</body>
</html>
'''

# ----- ROUTES -----

@app.route('/')
def index():
    if 'user_email' in session:
        return redirect(url_for('chat'))
    return render_template_string(INDEX_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_email' in session:
        return redirect(url_for('chat'))
    
    email_error = None
    password_error = None
    email = ''
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        if not email:
            email_error = 'Please enter your college email.'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            email_error = 'Please enter a valid college email.'
        
        if not password:
            password_error = 'Please enter your password.'
        
        if not email_error and not password_error:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if user and verify_password(user['password'], password):
                    # Upgrade plaintext password to hash if needed
                    if not (user['password'].startswith('scrypt:') or user['password'].startswith('pbkdf2:')):
                        conn = get_db_connection()
                        if conn:
                            cursor = conn.cursor()
                            hashed_password = generate_password_hash(password)
                            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, user['id']))
                            conn.commit()
                            cursor.close()
                            conn.close()
                    
                    session['user_email'] = email
                    session['user_name'] = user['name']
                    session['user_id'] = user['id']
                    flash('Login successful! Welcome back.', 'success')
                    return redirect(url_for('chat'))
                else:
                    email_error = 'Invalid email or password.'
                    password_error = 'Invalid email or password.'
            else:
                flash('Database connection error. Please try again.', 'error')
    
    return render_template_string(LOGIN_HTML, 
                                 email=email,
                                 email_error=email_error,
                                 password_error=password_error)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_email' in session:
        return redirect(url_for('chat'))
    
    name_error = None
    email_error = None
    password_error = None
    confirm_error = None
    full_name = ''
    email = ''
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not full_name:
            name_error = 'Please enter your full name.'
        
        if not email:
            email_error = 'Please enter your college email.'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            email_error = 'Please enter a valid college email.'
        
        if not password:
            password_error = 'Please enter a password.'
        elif len(password) < 8:
            password_error = 'Password must be at least 8 characters.'
        
        if password != confirm_password:
            confirm_error = 'Passwords do not match.'
        elif not confirm_password:
            confirm_error = 'Please confirm your password.'
        
        if not any([name_error, email_error, password_error, confirm_error]):
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    hashed_password = generate_password_hash(password)
                    cursor.execute('INSERT INTO users (email, name, password) VALUES (%s, %s, %s)',
                                 (email, full_name, hashed_password))
                    conn.commit()
                    user_id = cursor.lastrowid
                    cursor.close()
                    conn.close()
                    
                    flash('Account created successfully! Please login with your credentials.', 'success')
                    return redirect(url_for('login'))
                except mysql.connector.IntegrityError:
                    email_error = 'This email is already registered.'
                except Error as e:
                    flash(f'Database error: {e}', 'error')
            else:
                flash('Database connection error. Please try again.', 'error')
    
    return render_template_string(SIGNUP_HTML,
                                 full_name=full_name,
                                 email=email,
                                 name_error=name_error,
                                 email_error=email_error,
                                 password_error=password_error,
                                 confirm_error=confirm_error)

@app.route('/chat')
@login_required
def chat():
    return render_template_string(CHAT_HTML)

# ----- API ROUTES FOR CHAT HISTORY -----

# NOTE: Chat history API routes have been removed.
# Chat history is now stored locally in IndexedDB on the user's device.
# The following routes are no longer needed:
# - GET /api/history
# - GET /api/session/<id>
# - POST /api/session
# - DELETE /api/session/<id>

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    if not GROQ_API_KEY:
        return jsonify({'error': 'GROQ_API_KEY is not configured on the server.'}), 500

    data = request.get_json(silent=True) or {}
    message = str(data.get('message', '')).strip()
    # session_id is now a local UUID from IndexedDB - we accept it for logging but don't validate against MySQL
    local_session_id = data.get('session_id')
    
    if not message:
        return jsonify({'error': 'Message is required.'}), 400

    try:
        # Run RAG pipeline
        result = rag_pipeline(message)
        answer = result['answer']
        sources = result['sources']

        # NOTE: Chat history is now stored locally in IndexedDB on the user's device.
        # The backend no longer stores chat messages/sessions in MySQL.
        # The local_session_id is received for correlation/logging only.

        return jsonify({'answer': answer, 'sources': sources})
    except Exception as error:
        print(f'RAG pipeline error: {error}')
        return jsonify({'error': 'The AI service is unavailable right now.'}), 502

@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT id, email, name, created_at FROM users WHERE id = %s', (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template_string(PROFILE_HTML, user=user)
    return redirect(url_for('chat'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password', '').strip()
        new = request.form.get('new_password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT password FROM users WHERE id = %s', (session['user_id'],))
            user = cursor.fetchone()
            
            if not user or not check_password_hash(user['password'], current):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('change_password'))
            
            if len(new) < 8:
                flash('New password must be at least 8 characters.', 'error')
                return redirect(url_for('change_password'))
            
            if new != confirm:
                flash('Passwords do not match.', 'error')
                return redirect(url_for('change_password'))
            
            hashed_new = generate_password_hash(new)
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_new, session['user_id']))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Password changed successfully!', 'success')
            return redirect(url_for('chat'))
    
    return render_template_string(CHANGE_PASSWORD_HTML)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)