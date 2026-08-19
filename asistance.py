import os
import json
import time
import io
import uuid
from datetime import datetime, date
from flask import Flask, request, jsonify, render_template_string, Response, session
import requests
from urllib.parse import quote
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
import imageio_ffmpeg
from werkzeug.security import generate_password_hash, check_password_hash

# Configure pydub to use the packaged ffmpeg
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-key-12345')

# --- Configuration ---
API_URL = 'https://router.bynara.id/v1/chat/completions'
API_KEY = 'sk-nry-tZQJP4JySkZdr-4ZpIr20-KJykh6w7fWasPIzMAK36I'

# --- Data Directory Setup ---
DATA_DIR = 'data_files'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

USERS_FILE = os.path.join(DATA_DIR, 'users.json')

# --- Data Management ---
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"users": {}}
    return {"users": {}}

def save_users(data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_user_data(user_id):
    file_path = os.path.join(DATA_DIR, f'user_{user_id}.json')
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {"tasks": [], "transactions": [], "chat_logs": {}}

def save_user_data(user_id, data):
    file_path = os.path.join(DATA_DIR, f'user_{user_id}.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_current_user_id():
    return session.get('user_id')

# --- Modern HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>دستیار هوشمند من</title>
    <link rel="stylesheet" href="https://unpkg.com/persian-datepicker@latest/dist/css/persian-datepicker.min.css"/>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #f8fafc; --card-bg: #ffffff; --primary: #6366f1; --primary-dark: #4f46e5;
            --success: #10b981; --danger: #ef4444; --warning: #f59e0b; --text-main: #1e293b;
            --text-muted: #64748b; --border-color: #e2e8f0; --input-bg: #f1f5f9;
            --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
        }
        body[data-theme="dark"] {
            --bg-color: #0f172a; --card-bg: #1e293b; --primary: #818cf8; --primary-dark: #6366f1;
            --text-main: #f1f5f9; --text-muted: #94a3b8; --border-color: #334155; --input-bg: #334155;
            --shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; font-family: 'Vazirmatn', 'Tahoma', sans-serif; transition: background-color 0.3s, color 0.3s, border-color 0.3s; }
        body { margin: 0; padding: 0; background-color: var(--bg-color); color: var(--text-main); padding-bottom: 110px; line-height: 1.5; }
        
        .auth-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
        .auth-card { background: var(--card-bg); padding: 30px; border-radius: 20px; box-shadow: var(--shadow); width: 100%; max-width: 350px; }
        .auth-card h2 { text-align: center; margin-top: 0; color: var(--primary); }
        .auth-card input { margin-bottom: 15px; }
        .auth-btn { width: 100%; padding: 12px; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; margin-bottom: 10px; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-secondary { background: transparent; color: var(--primary); border: 1px solid var(--primary); }
        
        .app-screen { display: none; }
        header { background: var(--card-bg); color: var(--text-main); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border-color); box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
        header h1 { margin: 0; font-size: 18px; font-weight: 700; color: var(--primary); }
        .header-actions { display: flex; gap: 10px; }
        .icon-btn { background: var(--input-bg); border: none; color: var(--text-main); width: 40px; height: 40px; border-radius: 12px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .container { padding: 15px; max-width: 600px; margin: 0 auto; width: 100%; }
        .tab-content { display: none; }
        .active-tab { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .card { background: var(--card-bg); border-radius: 16px; padding: 20px; margin-bottom: 15px; box-shadow: var(--shadow); border: 1px solid transparent; }
        h3 { font-size: 16px; margin: 0 0 15px 0; color: var(--text-main); display: flex; align-items: center; gap: 8px; }
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .stat-box { padding: 15px; border-radius: 14px; text-align: center; }
        .stat-box h4 { margin: 0 0 5px 0; font-size: 12px; color: var(--text-muted); font-weight: 500; }
        .stat-box span { font-size: 16px; font-weight: 700; display: block; }
        .stat-income { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .stat-expense { background: rgba(239, 68, 68, 0.1); color: var(--danger); }
        .stat-balance { background: rgba(99, 102, 241, 0.1); color: var(--primary); grid-column: span 2; }
        .chat-card { margin-bottom: 80px; }
        .chat-box { background: var(--bg-color); border-radius: 16px; padding: 15px; margin-bottom: 15px; min-height: 250px; max-height: 50vh; overflow-y: auto; border: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 12px; }
        .chat-message { padding: 12px 16px; border-radius: 16px; font-size: 14px; line-height: 1.6; max-width: 85%; display: flex; align-items: flex-start; gap: 8px; }
        .ai-msg { background: var(--card-bg); color: var(--text-main); border-bottom-right-radius: 4px; align-self: flex-start; box-shadow: var(--shadow); }
        .user-msg { background: var(--primary); color: white; border-bottom-left-radius: 4px; align-self: flex-end; }
        .system-msg { background: transparent; color: var(--text-muted); font-size: 12px; text-align: center; align-self: center; padding: 5px 10px; border: 1px dashed var(--border-color); border-radius: 20px; }
        input, select, textarea { width: 100%; padding: 14px; margin-bottom: 12px; border: 1px solid var(--border-color); border-radius: 12px; font-size: 15px; outline: none; font-family: inherit; background: var(--input-bg); color: var(--text-main); }
        input:focus, select:focus, textarea:focus { border-color: var(--primary); }
        textarea { resize: none; }
        .input-row { display: flex; gap: 10px; align-items: stretch; margin-bottom: 12px; }
        .input-row textarea { flex: 1; margin-bottom: 0; }
        .filter-row { display: flex; gap: 10px; margin-bottom: 12px; }
        .filter-row > div { flex: 1; }
        .filter-row label { font-size: 12px; color: var(--text-muted); margin-bottom: 5px; display: block; }
        button.btn { padding: 14px; background: var(--primary); color: white; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; cursor: pointer; width: 100%; }
        button.btn:active { background: var(--primary-dark); transform: scale(0.98); }
        button.btn:disabled { background: var(--text-muted); cursor: not-allowed; }
        .input-action-btn { background: var(--input-bg); width: 50px; min-width: 50px; display: flex; align-items: center; justify-content: center; font-size: 20px; border-radius: 12px; color: var(--text-main); border: none; cursor: pointer; }
        .input-action-btn.mic { background: var(--danger); color: white; }
        .input-action-btn.mic.recording { animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); } 70% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }
        .list-item { display: flex; justify-content: space-between; align-items: center; padding: 15px 0; border-bottom: 1px solid var(--border-color); }
        .list-item:last-child { border-bottom: none; }
        .item-info { flex: 1; }
        .item-info h4 { margin: 0 0 5px 0; font-size: 15px; font-weight: 600; }
        .item-info small { color: var(--text-muted); font-size: 12px; display: flex; align-items: center; gap: 4px; }
        .item-action { background: var(--input-bg); border: none; color: var(--danger); font-size: 16px; cursor: pointer; padding: 8px 12px; border-radius: 8px; }
        .item-action.success { color: var(--success); }
        .task-done { text-decoration: line-through; color: var(--text-muted); }
        .bottom-nav { position: fixed; bottom: 15px; left: 50%; transform: translateX(-50%); width: calc(100% - 30px); max-width: 500px; background: var(--card-bg); display: flex; justify-content: space-around; padding: 10px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); z-index: 1000; border: 1px solid var(--border-color); }
        .nav-btn { background: none; border: none; display: flex; flex-direction: column; align-items: center; color: var(--text-muted); font-size: 11px; font-weight: 500; cursor: pointer; padding: 5px 10px; border-radius: 12px; }
        .nav-btn svg { width: 24px; height: 24px; margin-bottom: 2px; }
        .nav-btn.active { color: var(--primary); background: rgba(99, 102, 241, 0.1); }
        .speaker-icon { font-size: 14px; cursor: pointer; margin-top: 2px; }
        .image-preview { width: 100%; max-height: 200px; object-fit: contain; border-radius: 12px; margin-bottom: 10px; display: none; }
    </style>
</head>
<body data-theme="light">

    <!-- Auth Screen -->
    <div id="auth-screen" class="auth-screen">
        <div class="auth-card">
            <h2>ورود به سیستم</h2>
            <input type="text" id="auth-username" placeholder="نام کاربری">
            <input type="password" id="auth-password" placeholder="رمز عبور">
            <button class="auth-btn btn-primary" onclick="login()">ورود</button>
            <button class="auth-btn btn-secondary" onclick="register()">ثبت نام</button>
            <div id="auth-error" style="color: var(--danger); text-align: center; font-size: 13px; margin-top: 10px; display: none;"></div>
        </div>
    </div>

    <!-- App Screen -->
    <div id="app-screen" class="app-screen">
        <header>
            <h1>✨ دستیار هوشمند</h1>
            <div class="header-actions">
                <button class="icon-btn" id="theme-btn" onclick="toggleTheme()">☀️</button>
                <button class="icon-btn" onclick="logout()">🚪</button>
            </div>
        </header>
        
        <div class="container">
            <div id="chat-section" class="tab-content active-tab">
                <div class="card chat-card">
                    <div class="chat-box" id="chat-display"></div>
                    <img id="image-preview" class="image-preview" alt="پیش‌نمایش">
                    <div class="input-row">
                        <textarea id="user-input" rows="1" placeholder="صحبت کن یا تایپ کن..."></textarea>
                        <input type="file" accept="image/*" id="image-upload" hidden>
                        <button class="input-action-btn" onclick="document.getElementById('image-upload').click()">📎</button>
                        <button class="input-action-btn mic" id="mic-btn" onclick="toggleMic()">🎤</button>
                    </div>
                    <button class="btn" id="send-btn" onclick="sendToAI()">ارسال</button>
                </div>
            </div>

            <div id="tasks" class="tab-content">
                <div class="card">
                    <h3>➕ افزودن کار جدید</h3>
                    <input type="text" id="task-title" placeholder="عنوان کار">
                    <input type="text" id="task-due-display" placeholder="تاریخ شمسی (کلیک کنید)" readonly>
                    <input type="hidden" id="task-due">
                    <button class="btn" onclick="addManualTask()">ثبت کار</button>
                </div>
                <div class="card">
                    <h3>📋 لیست کارها</h3>
                    <div id="all-tasks"></div>
                </div>
            </div>

            <div id="finance" class="tab-content">
                <div class="card">
                    <h3>📊 وضعیت مالی کلی</h3>
                    <div class="stats-grid">
                        <div class="stat-box stat-income"><h4>درآمد کل</h4><span id="quick-income">۰</span></div>
                        <div class="stat-box stat-expense"><h4>هزینه کل</h4><span id="quick-expense">۰</span></div>
                        <div class="stat-box stat-balance"><h4>برآیند تمام حساب‌ها</h4><span id="quick-balance">۰</span></div>
                    </div>
                </div>
                <div class="card">
                    <h3>🔍 فیلتر و گزارش‌گیری</h3>
                    <div class="filter-row">
                        <div>
                            <label>از تاریخ</label>
                            <input type="text" id="filter-from-display" placeholder="انتخاب تاریخ" readonly>
                            <input type="hidden" id="filter-from">
                        </div>
                        <div>
                            <label>تا تاریخ</label>
                            <input type="text" id="filter-to-display" placeholder="انتخاب تاریخ" readonly>
                            <input type="hidden" id="filter-to">
                        </div>
                    </div>
                    <label>حساب بانکی</label>
                    <select id="filter-account" onchange="renderAll()">
                        <option value="all">همه حساب‌ها</option>
                    </select>
                    <div class="stats-grid" style="margin-top: 15px;">
                        <div class="stat-box stat-income"><h4>درآمد فیلتر شده</h4><span id="filter-income">۰</span></div>
                        <div class="stat-box stat-expense"><h4>هزینه فیلتر شده</h4><span id="filter-expense">۰</span></div>
                    </div>
                </div>
                <div class="card">
                    <h3>➕ ثبت تراکنش جدید</h3>
                    <select id="trans-type"><option value="income">دخل (درآمد)</option><option value="expense">خرج (هزینه)</option></select>
                    <input type="text" id="trans-account" placeholder="نام حساب (مثلاً: کیف پول)" list="accounts-list" value="کیف پول">
                    <datalist id="accounts-list"></datalist>
                    <input type="number" id="trans-amount" placeholder="مبلغ (تومان)">
                    <input type="text" id="trans-desc" placeholder="توضیحات">
                    <button class="btn" onclick="addManualTransaction()">ثبت تراکنش</button>
                </div>
                <div class="card">
                    <h3>💳 تراکنش‌های فیلتر شده</h3>
                    <div id="all-transactions"></div>
                </div>
            </div>

            <!-- Settings Tab -->
            <div id="settings" class="tab-content">
                <div class="card">
                    <h3>🔑 تغییر رمز عبور</h3>
                    <input type="password" id="old-pass" placeholder="رمز عبور فعلی">
                    <input type="password" id="new-pass" placeholder="رمز عبور جدید">
                    <button class="btn" onclick="changePassword()">تغییر رمز</button>
                </div>
                
                <!-- Admin Panel (Only visible for admin) -->
                <div class="card" id="admin-panel" style="display: none;">
                    <h3>👑 مدیریت کاربران</h3>
                    <div id="user-list"></div>
                </div>
            </div>
        </div>

        <audio id="alarm-audio" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" preload="auto"></audio>

        <nav class="bottom-nav">
            <button class="nav-btn active" onclick="switchTab('chat-section', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>چت</button>
            <button class="nav-btn" onclick="switchTab('tasks', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>کارها</button>
            <button class="nav-btn" onclick="switchTab('finance', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>حسابداری</button>
            <button class="nav-btn" onclick="switchTab('settings', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>تنظیمات</button>
        </nav>
    </div>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://unpkg.com/persian-date@latest/dist/persian-date.min.js"></script>
    <script src="https://unpkg.com/persian-datepicker@latest/dist/js/persian-datepicker.min.js"></script>

    <script>
        let appData = { tasks: [], transactions: [], chat_logs: {} };
        let currentAudio = null, uploadedImage = null, mediaRecorder, audioChunks = [], isRecording = false;
        let notifiedTasks = new Set();
        
        function loadTheme() { const theme = localStorage.getItem('theme') || 'light'; document.body.setAttribute('data-theme', theme); document.getElementById('theme-btn').innerText = theme === 'dark' ? '🌙' : '☀️'; }
        function toggleTheme() { const c = document.body.getAttribute('data-theme'); const n = c === 'dark' ? 'light' : 'dark'; document.body.setAttribute('data-theme', n); localStorage.setItem('theme', n); document.getElementById('theme-btn').innerText = n === 'dark' ? '🌙' : '☀️'; }

        async function checkAuth() {
            const res = await fetch('/api/check_auth');
            const data = await res.json();
            if (data.authenticated) {
                document.getElementById('auth-screen').style.display = 'none';
                document.getElementById('app-screen').style.display = 'block';
                fetchAppData();
                if (data.is_admin) {
                    document.getElementById('admin-panel').style.display = 'block';
                    loadAdminUsers();
                }
            } else {
                document.getElementById('auth-screen').style.display = 'flex';
                document.getElementById('app-screen').style.display = 'none';
            }
        }

        async function login() {
            const username = document.getElementById('auth-username').value;
            const password = document.getElementById('auth-password').value;
            const errBox = document.getElementById('auth-error'); errBox.style.display = 'none';
            const res = await fetch('/api/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password}) });
            const data = await res.json();
            if (data.status === 'success') checkAuth();
            else { errBox.innerText = data.message; errBox.style.display = 'block'; }
        }

        async function register() {
            const username = document.getElementById('auth-username').value;
            const password = document.getElementById('auth-password').value;
            const errBox = document.getElementById('auth-error'); errBox.style.display = 'none';
            const res = await fetch('/api/register', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username, password}) });
            const data = await res.json();
            if (data.status === 'success') checkAuth();
            else { errBox.innerText = data.message; errBox.style.display = 'block'; }
        }

        async function logout() { await fetch('/api/logout'); checkAuth(); }

        // Settings Logic
        async function changePassword() {
            const oldPass = document.getElementById('old-pass').value;
            const newPass = document.getElementById('new-pass').value;
            const res = await fetch('/api/change_password', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({old_pass: oldPass, new_pass: newPass}) });
            const data = await res.json();
            if (data.status === 'success') alert('رمز عبور با موفقیت تغییر کرد');
            else alert('خطا: ' + data.message);
        }

        async function loadAdminUsers() {
            const res = await fetch('/api/admin/users');
            const data = await res.json();
            const list = document.getElementById('user-list');
            if (data.users.length === 0) list.innerHTML = "<p>هیچ کاربری وجود ندارد.</p>";
            else list.innerHTML = data.users.map(u => `<div class="list-item"><div class="item-info"><h4>${u.username}</h4></div><button class="item-action" onclick="deleteUser('${u.username}')">🗑</button></div>`).join('');
        }

        async function deleteUser(username) {
            if (!confirm(`آیا از حذف کاربر ${username} مطمئن هستید؟`)) return;
            await fetch('/api/admin/delete_user', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username}) });
            loadAdminUsers();
        }

        async function speakText(text) {
            if (currentAudio) currentAudio.pause();
            try {
                const res = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
                const blob = await res.blob(); const url = URL.createObjectURL(blob);
                currentAudio = new Audio(url); currentAudio.play();
            } catch(e) { console.error(e); }
        }

        function checkAlarms() {
            const now = new Date();
            appData.tasks.forEach(task => {
                if (task.done || !task.due || notifiedTasks.has(task.id)) return;
                if (new Date(task.due).getTime() <= now.getTime()) {
                    notifiedTasks.add(task.id); triggerAlarm(task.title);
                }
            });
        }
        function triggerAlarm(title) {
            document.getElementById('alarm-audio').play().catch(e => console.error(e));
            addChatMessage("⏰ یادآوری: " + title, 'system');
            if ('Notification' in window && Notification.permission === 'granted') new Notification("⏰ یادآوری کار", { body: title });
        }
        setInterval(checkAlarms, 15000);

        document.getElementById('image-upload').addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) { uploadedImage = e.target.result; document.getElementById('image-preview').src = uploadedImage; document.getElementById('image-preview').style.display = 'block'; }
                reader.readAsDataURL(file);
            }
        });

        $(document).ready(function() {
            function toGregorian(unixTime) { let d = new Date(unixTime); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; }
            $("#task-due-display").persianDatepicker({ altField: '#task-due', altFormat: 'YYYY-MM-DDTHH:mm', format: 'YYYY/MM/DD HH:mm', autoClose: true, altFieldFormatter: function(unixTime) { return toGregorian(unixTime); } });
            $("#filter-from-display").persianDatepicker({ altField: '#filter-from', altFormat: 'YYYY-MM-DD', format: 'YYYY/MM/DD', autoClose: true, altFieldFormatter: function(unixTime) { let d = new Date(unixTime); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }, onSelect: function() { renderAll(); } });
            $("#filter-to-display").persianDatepicker({ altField: '#filter-to', altFormat: 'YYYY-MM-DD', format: 'YYYY/MM/DD', autoClose: true, altFieldFormatter: function(unixTime) { let d = new Date(unixTime); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }, onSelect: function() { renderAll(); } });
        });

        async function fetchAppData() {
            const res = await fetch('/api/data'); if (res.status === 401) { logout(); return; }
            appData = await res.json(); renderAll(); renderChatHistory();
        }

        function renderChatHistory() {
            const chatDisplay = document.getElementById('chat-display'); chatDisplay.innerHTML = '';
            const today = new Date().toISOString().split('T')[0];
            const logs = appData.chat_logs[today] || [];
            if (logs.length === 0) { addChatMessage("سلام! عکس فیش رو بفرست یا دکمه میکروفون رو بزن.", 'ai'); return; }
            logs.forEach(log => {
                const msgDiv = document.createElement('div'); msgDiv.className = `chat-message ${log.sender}-msg`;
                if (log.sender === 'ai') {
                    const speakBtn = document.createElement('span'); speakBtn.className = 'speaker-icon'; speakBtn.innerHTML = '🔊'; speakBtn.onclick = () => speakText(log.text);
                    const textSpan = document.createElement('span'); textSpan.innerText = log.text;
                    msgDiv.appendChild(speakBtn); msgDiv.appendChild(textSpan);
                } else { msgDiv.innerText = log.text; }
                chatDisplay.appendChild(msgDiv);
            });
            chatDisplay.scrollTop = chatDisplay.scrollHeight;
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active-tab'));
            document.getElementById(tabId).classList.add('active-tab');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }

        async function toggleMic() {
            const micBtn = document.getElementById('mic-btn');
            if (isRecording) {
                mediaRecorder.stop(); micBtn.classList.remove('recording'); micBtn.innerText = '🎤'; isRecording = false; addChatMessage("⏳ در حال پردازش صدا...", 'system');
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    let mimeType = 'audio/webm'; if (!MediaRecorder.isTypeSupported(mimeType)) { mimeType = 'audio/mp4'; if (!MediaRecorder.isTypeSupported(mimeType)) mimeType = ''; }
                    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType: mimeType } : undefined); audioChunks = [];
                    mediaRecorder.ondataavailable = event => { if (event.data.size > 0) audioChunks.push(event.data); };
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
                        const formData = new FormData(); formData.append('audio', audioBlob, `voice.${mimeType.includes('mp4') ? 'mp4' : 'webm'}`);
                        try {
                            const res = await fetch('/api/stt', { method: 'POST', body: formData }); const data = await res.json();
                            if (data.text && data.text.trim().length > 0) { document.getElementById('user-input').value = data.text; sendToAI(); }
                            else { addChatMessage("❌ صدایی شنیده نشد.", 'system'); }
                        } catch (e) { addChatMessage("❌ خطا در تبدیل صدا.", 'system'); }
                    };
                    mediaRecorder.start(); isRecording = true; micBtn.classList.add('recording'); micBtn.innerText = '⏹';
                } catch (err) { addChatMessage('🚫 دسترسی میکروفون رد شد.', 'system'); }
            }
        }

        async function sendToAI() {
            const inputField = document.getElementById('user-input'); const sendBtn = document.getElementById('send-btn');
            const userText = inputField.value.trim();
            if (!userText && !uploadedImage) return alert("متن بنویسید یا عکس اضافه کنید.");
            addChatMessage(userText || "[عکس ارسال شد]", 'user'); sendBtn.disabled = true; sendBtn.innerText = '...';
            try {
                const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: userText, image: uploadedImage }) });
                const data = await res.json();
                if(data.reply) addChatMessage(data.reply, 'ai'); else addChatMessage("خطا در پردازش.", 'ai');
                uploadedImage = null; document.getElementById('image-preview').style.display = 'none'; document.getElementById('image-upload').value = '';
                fetchAppData();
            } catch (error) { addChatMessage("ارتباط با سرور قطع شد.", 'ai'); }
            finally { inputField.value = ''; sendBtn.disabled = false; sendBtn.innerText = 'ارسال'; }
        }
        
        function addChatMessage(text, sender) {
            const chatDisplay = document.getElementById('chat-display'); const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${sender}-msg`;
            if (sender === 'ai') {
                const speakBtn = document.createElement('span'); speakBtn.className = 'speaker-icon'; speakBtn.innerHTML = '🔊'; speakBtn.onclick = () => speakText(text);
                const textSpan = document.createElement('span'); textSpan.innerText = text;
                msgDiv.appendChild(speakBtn); msgDiv.appendChild(textSpan);
            } else { msgDiv.innerText = text; }
            chatDisplay.appendChild(msgDiv); chatDisplay.scrollTop = chatDisplay.scrollHeight;
        }

        async function addManualTask() {
            const title = document.getElementById('task-title').value; const due = document.getElementById('task-due').value;
            if (!title) return alert('عنوان کار را وارد کنید');
            await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'task', title, due }) });
            document.getElementById('task-title').value = ''; document.getElementById('task-due').value = ''; document.getElementById('task-due-display').value = ''; fetchAppData();
        }
        async function toggleTask(id) { await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'toggle_task', id }) }); fetchAppData(); }
        async function deleteTask(id) { await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'delete_task', id }) }); fetchAppData(); }
        async function addManualTransaction() {
            const type = document.getElementById('trans-type').value; const account = document.getElementById('trans-account').value || 'کیف پول';
            const amount = parseInt(document.getElementById('trans-amount').value); const desc = document.getElementById('trans-desc').value;
            if (!amount || amount <= 0) return alert('مبلغ صحیح وارد کنید');
            await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'transaction', trans_type: type, account, amount, desc }) });
            document.getElementById('trans-amount').value = ''; document.getElementById('trans-desc').value = ''; fetchAppData();
        }
        async function deleteTransaction(id) { await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'delete_trans', id }) }); fetchAppData(); }

        function formatNumber(num) { return num.toLocaleString('fa-IR') + ' تومان'; }
        function formatDate(dateStr) { if(!dateStr) return 'بدون تاریخ'; try { const date = new Date(dateStr); return date.toLocaleDateString('fa-IR', { month: 'long', day: 'numeric' }) + ' - ' + date.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }); } catch(e) { return dateStr; } }

        function renderAll() {
            const container = document.getElementById('all-tasks');
            appData.tasks.sort((a,b) => (a.done - b.done) || (a.due || '9999').localeCompare(b.due || '9999'));
            if (appData.tasks.length === 0) container.innerHTML = "<p style='text-align:center; color:var(--text-muted); font-size:14px; padding:10px;'>کاری ثبت نشده است.</p>";
            else container.innerHTML = appData.tasks.map(t => `<div class="list-item"><div class="item-info"><h4 class="${t.done ? 'task-done' : ''}">${t.title}</h4><small>📅 ${formatDate(t.due)}</small></div><div style="display:flex; gap:5px;"><button class="item-action success" onclick="toggleTask(${t.id})">✓</button><button class="item-action" onclick="deleteTask(${t.id})">🗑</button></div></div>`).join('');

            const filterFrom = document.getElementById('filter-from').value; const filterTo = document.getElementById('filter-to').value; const filterAcc = document.getElementById('filter-account').value;
            const accountsList = document.getElementById('accounts-list'); const filterAccSelect = document.getElementById('filter-account');
            const uniqueAccounts = [...new Set(appData.transactions.map(t => t.account).filter(Boolean))];
            accountsList.innerHTML = uniqueAccounts.map(acc => `<option value="${acc}">`).join('');
            const currentFilterAcc = filterAccSelect.value;
            filterAccSelect.innerHTML = '<option value="all">همه حساب‌ها</option>' + uniqueAccounts.map(acc => `<option value="${acc}" ${acc === currentFilterAcc ? 'selected' : ''}>${acc}</option>`).join('');

            let filteredTrans = appData.transactions.filter(t => {
                let match = true;
                if (filterFrom && new Date(t.date) < new Date(filterFrom)) match = false;
                if (filterTo) { const toDate = new Date(filterTo); toDate.setHours(23, 59, 59); if (new Date(t.date) > toDate) match = false; }
                if (filterAcc !== 'all' && t.account !== filterAcc) match = false;
                return match;
            });
            const transContainer = document.getElementById('all-transactions');
            if (filteredTrans.length === 0) transContainer.innerHTML = "<p style='text-align:center; color:var(--text-muted); font-size:14px; padding:10px;'>هیچ تراکنشی یافت نشد.</p>";
            else transContainer.innerHTML = [...filteredTrans].reverse().map(t => `<div class="list-item"><div class="item-info"><h4>${t.desc || 'بدون توضیح'}</h4><small>📅 ${formatDate(t.date)} | 🏦 ${t.account || 'نامشخص'}</small></div><div style="text-align:left"><span style="color:${t.type === 'income' ? 'var(--success)' : 'var(--danger)'}; font-weight:bold; display:block; font-size:14px;">${t.type === 'income' ? '+' : '-'} ${formatNumber(t.amount)}</span><button class="item-action" style="font-size:12px; margin-top:5px;" onclick="deleteTransaction(${t.id})">حذف</button></div></div>`).join('');

            let fIncome = filteredTrans.filter(t => t.type === 'income').reduce((a, b) => a + b.amount, 0);
            let fExpense = filteredTrans.filter(t => t.type === 'expense').reduce((a, b) => a + b.amount, 0);
            document.getElementById('filter-income').innerText = formatNumber(fIncome);
            document.getElementById('filter-expense').innerText = formatNumber(fExpense);
            let income = appData.transactions.filter(t => t.type === 'income').reduce((a, b) => a + b.amount, 0);
            let expense = appData.transactions.filter(t => t.type === 'expense').reduce((a, b) => a + b.amount, 0);
            document.getElementById('quick-income').innerText = formatNumber(income);
            document.getElementById('quick-expense').innerText = formatNumber(expense);
            document.getElementById('quick-balance').innerText = formatNumber(income - expense);
        }

        loadTheme(); checkAuth();
    </script>
</body>
</html>
"""

# --- Auth Routes ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password: return jsonify({"status": "error", "message": "نام کاربری و رمز عبور الزامی است"}), 400
    
    users = load_users()
    if username in users['users']: return jsonify({"status": "error", "message": "این نام کاربری قبلا ثبت شده"}), 400
    
    user_id = str(uuid.uuid4())
    users['users'][username] = {"password": generate_password_hash(password), "user_id": user_id}
    save_users(users)
    
    session['user_id'] = user_id
    session['username'] = username
    return jsonify({"status": "success"})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    users = load_users()
    
    if username not in users['users']: return jsonify({"status": "error", "message": "نام کاربری یا رمز عبور اشتباه است"}), 401
    
    user = users['users'][username]
    if not check_password_hash(user['password'], password): return jsonify({"status": "error", "message": "نام کاربری یا رمز عبور اشتباه است"}), 401
    
    session['user_id'] = user['user_id']
    session['username'] = username
    return jsonify({"status": "success"})

@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route('/api/check_auth')
def check_auth():
    if 'user_id' in session:
        return jsonify({"authenticated": True, "is_admin": session.get('username') == 'admin'})
    return jsonify({"authenticated": False})

# --- Settings & Admin Routes ---
@app.route('/api/change_password', methods=['POST'])
def change_password():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    users = load_users()
    username = session.get('username')
    
    if not check_password_hash(users['users'][username]['password'], data['old_pass']):
        return jsonify({"status": "error", "message": "رمز عبور فعلی اشتباه است"}), 400
        
    users['users'][username]['password'] = generate_password_hash(data['new_pass'])
    save_users(users)
    return jsonify({"status": "success"})

@app.route('/api/admin/users')
def admin_users():
    if session.get('username') != 'admin': return jsonify({"error": "Forbidden"}), 403
    users = load_users()
    safe_users = [{"username": u} for u in users['users'].keys()]
    return jsonify({"users": safe_users})

@app.route('/api/admin/delete_user', methods=['POST'])
def delete_user():
    if session.get('username') != 'admin': return jsonify({"error": "Forbidden"}), 403
    data = request.json
    username_to_delete = data.get('username')
    if username_to_delete == 'admin': return jsonify({"status": "error", "message": "نمی‌توانید ادمین اصلی را حذف کنید"}), 400
    
    users = load_users()
    if username_to_delete in users['users']:
        del users['users'][username_to_delete]
        save_users(users)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "کاربر یافت نشد"}), 404

# --- App Routes ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    return jsonify(load_user_data(user_id))

@app.route('/api/tts', methods=['POST'])
def tts():
    user_id = get_current_user_id()
    if not user_id: return Response("", status=401)
    text = request.json.get('text', '')
    if not text: return Response("", status=400)
    try:
        tts = gTTS(text, lang='fa')
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return Response(mp3_fp, mimetype='audio/mpeg')
    except Exception as e:
        return Response("", status=500)

@app.route('/api/stt', methods=['POST'])
def stt():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    if 'audio' not in request.files: return jsonify({"error": "No audio file"}), 400
        
    audio_file = request.files['audio']
    temp_path = f"temp_{audio_file.filename}"
    audio_file.save(temp_path)
    
    try:
        audio = AudioSegment.from_file(temp_path)
        wav_path = temp_path.rsplit('.', 1)[0] + '.wav'
        audio.export(wav_path, format='wav')
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="fa-IR")
            return jsonify({"text": text})
    except sr.UnknownValueError:
        return jsonify({"error": "صدایی شنیده نشد"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)
        if 'wav_path' in locals() and os.path.exists(wav_path): os.remove(wav_path)

@app.route('/api/manual', methods=['POST'])
def manual_op():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    user_data = load_user_data(user_id)
    current_time = datetime.now().isoformat()
    
    if data['type'] == 'task':
        user_data['tasks'].append({"id": int(time.time() * 1000), "title": data['title'], "due": data.get('due', ''), "done": False})
    elif data['type'] == 'toggle_task':
        for t in user_data['tasks']:
            if t['id'] == data['id']: t['done'] = not t['done']; break
    elif data['type'] == 'delete_task':
        user_data['tasks'] = [t for t in user_data['tasks'] if t['id'] != data['id']]
    elif data['type'] == 'transaction':
        user_data['transactions'].append({
            "id": int(time.time() * 1000), "type": data['trans_type'],
            "account": data.get('account', 'کیف پول'), "amount": data['amount'],
            "desc": data.get('desc', ''), "date": current_time
        })
    elif data['type'] == 'delete_trans':
        user_data['transactions'] = [t for t in user_data['transactions'] if t['id'] != data['id']]
        
    save_user_data(user_id, user_data)
    return jsonify({"status": "success"})

@app.route('/api/chat', methods=['POST'])
def chat():
    user_id = get_current_user_id()
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    user_text = data.get('text', '')
    image_b64 = data.get('image', None)
    
    user_data = load_user_data(user_id)
    current_dt = datetime.now().isoformat()
    today_str = date.today().isoformat()
    
    current_tasks = "\n".join([f"- {t['title']} (Done: {'Yes' if t['done'] else 'No'}, Due: {t.get('due', 'N/A')})" for t in user_data['tasks']]) or "None"
    current_trans = "\n".join([f"- {t['type']}: {t['amount']} ({t.get('desc', '')}) [Account: {t.get('account', 'N/A')}]" for t in user_data['transactions']]) or "None"

    system_prompt = f"""You are a smart personal assistant. The user speaks Persian.
Your task is to extract Tasks and financial Transactions from the user's text or image.
Also, provide a short analysis and suggestion based on current and new data.

CRITICAL RULES:
1. Current Date and Time is: {current_dt}.
2. All dates MUST be in Gregorian ISO format: YYYY-MM-DDTHH:MM.
3. If a transaction doesn't have a specific date, use the Current Date and Time.
4. Amounts must be numeric (Toman).
5. If the user mentions an account, extract it as "account". If not mentioned, default "account" to "کیف پول".
6. If an image is provided, analyze it to extract amount, date, description, and account.
7. Your response MUST be ONLY a valid JSON object.

Current User Data:
Tasks: {current_tasks}
Transactions: {current_trans}

Respond in this exact JSON format:
{{
  "new_tasks": [{{"title": "Task title", "due": "YYYY-MM-DDTHH:MM" or null}}],
  "new_transactions": [{{"type": "income or expense", "amount": number, "desc": "Description", "account": "Account name", "date": "YYYY-MM-DDTHH:MM"}}],
  "reply": "Friendly Persian text response"
}}

If no new tasks or transactions, leave the array empty."""

    user_content = []
    if user_text: user_content.append({"type": "text", "text": user_text})
    elif image_b64: user_content.append({"type": "text", "text": "لطفا اطلاعات این فیش را خوانده و تراکنش آن را ثبت کن."})
    if image_b64: user_content.append({"type": "image_url", "image_url": {"url": image_b64}})

    payload = {
        "model": "agnes-2.0-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content if len(user_content) > 1 else (user_text if user_text else "Error")}
        ]
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        ai_content = response.json()['choices'][0]['message']['content']
        ai_content = ai_content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(ai_content)

        if 'new_tasks' in parsed:
            for t in parsed['new_tasks']:
                user_data['tasks'].append({"id": int(time.time() * 1000), "title": t['title'], "due": t.get('due', ''), "done": False})
                
        if 'new_transactions' in parsed:
            for t in parsed['new_transactions']:
                user_data['transactions'].append({
                    "id": int(time.time() * 1000), "type": t['type'], "amount": int(t['amount']),
                    "desc": t.get('desc', ''), "account": t.get('account', 'کیف پول'), "date": t.get('date', current_dt)
                })
                
        ai_reply = parsed.get('reply', 'ثبت شد!')
        
        if today_str not in user_data['chat_logs']:
            user_data['chat_logs'][today_str] = []
        user_data['chat_logs'][today_str].append({"sender": "user", "text": user_text or "[عکس ارسال شد]"})
        user_data['chat_logs'][today_str].append({"sender": "ai", "text": ai_reply})
        
        save_user_data(user_id, user_data)
        return jsonify({"reply": ai_reply})
        
    except Exception as e:
        return jsonify({"reply": f"خطا در پردازش هوش مصنوعی: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
