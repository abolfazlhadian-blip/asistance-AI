import os
import json
import time
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, Response
import requests
from urllib.parse import quote
from gtts import gTTS
import speech_recognition as sr
from pydub import AudioSegment
import imageio_ffmpeg

# Configure pydub to use the packaged ffmpeg
AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__)

# --- Configuration ---
DATA_FILE = 'data.json'
API_URL = 'https://router.bynara.id/v1/chat/completions'
API_KEY = 'sk-nry-tZQJP4JySkZdr-4ZpIr20-KJykh6w7fWasPIzMAK36I'

# --- Data Management ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"tasks": [], "transactions": []}
    return {"tasks": [], "transactions": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- Modern HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>دستیار هوشمند من</title>
    <link rel="stylesheet" href="https://unpkg.com/persian-datepicker@latest/dist/css/persian-datepicker.min.css"/>
    <!-- Vazirmatn Font -->
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
        header { background: var(--card-bg); color: var(--text-main); padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border-color); box-shadow: 0 2px 10px rgba(0,0,0,0.03); }
        header h1 { margin: 0; font-size: 18px; font-weight: 700; color: var(--primary); }
        .header-actions { display: flex; gap: 10px; }
        .icon-btn { background: var(--input-bg); border: none; color: var(--text-main); width: 40px; height: 40px; border-radius: 12px; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .icon-btn:active { transform: scale(0.95); }
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
        .bottom-nav { position: fixed; bottom: 15px; left: 50%; transform: translateX(-50%); width: calc(100% - 30px); max-width: 400px; background: var(--card-bg); display: flex; justify-content: space-around; padding: 10px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); z-index: 1000; border: 1px solid var(--border-color); }
        .nav-btn { background: none; border: none; display: flex; flex-direction: column; align-items: center; color: var(--text-muted); font-size: 11px; font-weight: 500; cursor: pointer; padding: 5px 15px; border-radius: 12px; }
        .nav-btn svg { width: 24px; height: 24px; margin-bottom: 2px; }
        .nav-btn.active { color: var(--primary); background: rgba(99, 102, 241, 0.1); }
        .speaker-icon { font-size: 14px; cursor: pointer; margin-top: 2px; }
        .image-preview { width: 100%; max-height: 200px; object-fit: contain; border-radius: 12px; margin-bottom: 10px; display: none; }
    </style>
</head>
<body data-theme="light">
    <header>
        <h1>✨ دستیار هوشمند</h1>
        <div class="header-actions">
            <button class="icon-btn" id="theme-btn" onclick="toggleTheme()">☀️</button>
            <button class="icon-btn" onclick="checkConnection()">🔌</button>
        </div>
    </header>
    
    <div class="container">
        <div id="chat-section" class="tab-content active-tab">
            <div class="card chat-card">
                <div class="chat-box" id="chat-display">
                    <div class="chat-message ai-msg"><span>سلام! عکس فیش رو بفرست یا دکمه میکروفون رو بزن و حرف بزن.</span></div>
                </div>
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
    </div>

    <!-- Alarm Audio Element -->
    <audio id="alarm-audio" src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" preload="auto"></audio>

    <nav class="bottom-nav">
        <button class="nav-btn active" onclick="switchTab('chat-section', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>چت</button>
        <button class="nav-btn" onclick="switchTab('tasks', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/></svg>کارها</button>
        <button class="nav-btn" onclick="switchTab('finance', this)"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>حسابداری</button>
    </nav>

    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://unpkg.com/persian-date@latest/dist/persian-date.min.js"></script>
    <script src="https://unpkg.com/persian-datepicker@latest/dist/js/persian-datepicker.min.js"></script>

    <script>
        let appData = { tasks: [], transactions: [] };
        let currentAudio = null;
        let uploadedImage = null;
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        let notifiedTasks = new Set();
        
        function loadTheme() { const theme = localStorage.getItem('theme') || 'light'; document.body.setAttribute('data-theme', theme); document.getElementById('theme-btn').innerText = theme === 'dark' ? '🌙' : '☀️'; }
        function toggleTheme() { const c = document.body.getAttribute('data-theme'); const n = c === 'dark' ? 'light' : 'dark'; document.body.setAttribute('data-theme', n); localStorage.setItem('theme', n); document.getElementById('theme-btn').innerText = n === 'dark' ? '🌙' : '☀️'; }

        // --- Text To Speech (Google TTS) ---
        async function speakText(text) {
            if (currentAudio) currentAudio.pause();
            try {
                const res = await fetch('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
                if (!res.ok) throw new Error("TTS failed");
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                currentAudio = new Audio(url);
                currentAudio.play();
            } catch(e) { console.error("Audio play failed:", e); }
        }

        // --- Notification & Alarm System ---
        function requestNotificationPermission() {
            if ('Notification' in window && Notification.permission !== 'granted') {
                Notification.requestPermission();
            }
        }

        function checkAlarms() {
            const now = new Date();
            appData.tasks.forEach(task => {
                if (task.done || !task.due || notifiedTasks.has(task.id)) return;
                
                const dueDate = new Date(task.due);
                if (dueDate.getTime() <= now.getTime()) {
                    notifiedTasks.add(task.id);
                    triggerAlarm(task.title);
                }
            });
        }

        function triggerAlarm(title) {
            const alarmAudio = document.getElementById('alarm-audio');
            alarmAudio.play().catch(e => console.error("Alarm play failed", e));
            
            addChatMessage("⏰ یادآوری: زمان انجام کار فرا رسید: " + title, 'system');
            
            if ('Notification' in window && Notification.permission === 'granted') {
                new Notification("⏰ یادآوری کار", { body: title });
            } else {
                alert("⏰ یادآوری کار: " + title);
            }
        }

        // Check alarms every 15 seconds
        setInterval(checkAlarms, 15000);

        document.getElementById('image-upload').addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    uploadedImage = e.target.result;
                    document.getElementById('image-preview').src = uploadedImage;
                    document.getElementById('image-preview').style.display = 'block';
                }
                reader.readAsDataURL(file);
            }
        });

        $(document).ready(function() {
            function toGregorian(unixTime) {
                let d = new Date(unixTime);
                return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
            }
            $("#task-due-display").persianDatepicker({ altField: '#task-due', altFormat: 'YYYY-MM-DDTHH:mm', format: 'YYYY/MM/DD HH:mm', autoClose: true, altFieldFormatter: function(unixTime) { return toGregorian(unixTime); } });
            $("#filter-from-display").persianDatepicker({ altField: '#filter-from', altFormat: 'YYYY-MM-DD', format: 'YYYY/MM/DD', autoClose: true, altFieldFormatter: function(unixTime) { let d = new Date(unixTime); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }, onSelect: function() { renderAll(); } });
            $("#filter-to-display").persianDatepicker({ altField: '#filter-to', altFormat: 'YYYY-MM-DD', format: 'YYYY/MM/DD', autoClose: true, altFieldFormatter: function(unixTime) { let d = new Date(unixTime); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }, onSelect: function() { renderAll(); } });
        });

        async function fetchAppData() {
            const res = await fetch('/api/data');
            appData = await res.json();
            renderAll();
        }
        async function checkConnection() {
            addChatMessage("⏳ در حال تست اتصال...", 'system');
            try {
                const res = await fetch('/api/test');
                const data = await res.json();
                if(data.status === 'success') addChatMessage("✅ اتصال برقرار است!", 'system');
                else addChatMessage("❌ خطا: " + data.message, 'system');
            } catch(e) { addChatMessage("❌ خطای سرور!", 'system'); }
        }
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active-tab'));
            document.getElementById(tabId).classList.add('active-tab');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        }

        // --- Advanced Audio Recording ---
        async function toggleMic() {
            const micBtn = document.getElementById('mic-btn');
            
            if (isRecording) {
                mediaRecorder.stop();
                micBtn.classList.remove('recording');
                micBtn.innerText = '🎤';
                isRecording = false;
                addChatMessage("⏳ در حال پردازش صدا...", 'system');
            } else {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    
                    let mimeType = 'audio/webm';
                    if (!MediaRecorder.isTypeSupported(mimeType)) {
                        mimeType = 'audio/mp4';
                        if (!MediaRecorder.isTypeSupported(mimeType)) {
                            mimeType = ''; // Default
                        }
                    }
                    
                    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType: mimeType } : undefined);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = event => {
                        if (event.data.size > 0) audioChunks.push(event.data);
                    };
                    
                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: mimeType || 'audio/webm' });
                        const formData = new FormData();
                        const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
                        formData.append('audio', audioBlob, `voice.${ext}`);
                        
                        try {
                            const res = await fetch('/api/stt', { method: 'POST', body: formData });
                            const data = await res.json();
                            if (data.text && data.text.trim().length > 0) {
                                document.getElementById('user-input').value = data.text;
                                addChatMessage("📝 متن تبدیل شده آماده ارسال است.", 'system');
                                sendToAI();
                            } else {
                                addChatMessage("❌ صدایی شنیده نشد. خطا: " + (data.error || "نامشخص"), 'system');
                            }
                        } catch (e) {
                            addChatMessage("❌ خطا در ارتباط با سرور تبدیل صدا.", 'system');
                        }
                    };
                    
                    mediaRecorder.start();
                    isRecording = true;
                    micBtn.classList.add('recording');
                    micBtn.innerText = '⏹';
                    addChatMessage("🎙 در حال ضبط... دوباره دکمه را بزنید تا متوقف شود.", 'system');
                    
                } catch (err) {
                    addChatMessage('🚫 دسترسی به میکروفون رد شد: ' + err.message, 'system');
                }
            }
        }

        async function sendToAI() {
            const inputField = document.getElementById('user-input');
            const sendBtn = document.getElementById('send-btn');
            const userText = inputField.value.trim();
            if (!userText && !uploadedImage) return alert("متن بنویسید یا عکس اضافه کنید.");
            
            addChatMessage(userText || "[عکس ارسال شد]", 'user');
            sendBtn.disabled = true; sendBtn.innerText = '...';
            
            try {
                const res = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: userText, image: uploadedImage }) });
                const data = await res.json();
                if(data.reply) addChatMessage(data.reply, 'ai');
                else addChatMessage("خطا در پردازش.", 'ai');
                uploadedImage = null;
                document.getElementById('image-preview').style.display = 'none';
                document.getElementById('image-upload').value = '';
                fetchAppData();
            } catch (error) { addChatMessage("ارتباط با سرور قطع شد.", 'ai'); }
            finally { inputField.value = ''; sendBtn.disabled = false; sendBtn.innerText = 'ارسال'; }
        }
        
        function addChatMessage(text, sender) {
            const chatDisplay = document.getElementById('chat-display');
            const msgDiv = document.createElement('div');
            msgDiv.className = `chat-message ${sender}-msg`;
            if (sender === 'ai') {
                const speakBtn = document.createElement('span');
                speakBtn.className = 'speaker-icon'; speakBtn.innerHTML = '🔊';
                speakBtn.onclick = () => speakText(text);
                const textSpan = document.createElement('span'); textSpan.innerText = text;
                msgDiv.appendChild(speakBtn); msgDiv.appendChild(textSpan);
                speakText(text);
            } else { msgDiv.innerText = text; }
            chatDisplay.appendChild(msgDiv);
            chatDisplay.scrollTop = chatDisplay.scrollHeight;
        }

        async function addManualTask() {
            const title = document.getElementById('task-title').value;
            const due = document.getElementById('task-due').value;
            if (!title) return alert('عنوان کار را وارد کنید');
            await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'task', title, due }) });
            document.getElementById('task-title').value = ''; document.getElementById('task-due').value = ''; document.getElementById('task-due-display').value = ''; fetchAppData();
        }
        async function toggleTask(id) { await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'toggle_task', id }) }); fetchAppData(); }
        async function deleteTask(id) { await fetch('/api/manual', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ type: 'delete_task', id }) }); fetchAppData(); }
        async function addManualTransaction() {
            const type = document.getElementById('trans-type').value;
            const account = document.getElementById('trans-account').value || 'کیف پول';
            const amount = parseInt(document.getElementById('trans-amount').value);
            const desc = document.getElementById('trans-desc').value;
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

            const filterFrom = document.getElementById('filter-from').value;
            const filterTo = document.getElementById('filter-to').value;
            const filterAcc = document.getElementById('filter-account').value;
            const accountsList = document.getElementById('accounts-list');
            const filterAccSelect = document.getElementById('filter-account');
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

        // Init
        loadTheme();
        requestNotificationPermission();
        fetchAppData();
    </script>
</body>
</html>
"""

# --- Routes ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    return jsonify(load_data())

@app.route('/api/tts', methods=['POST'])
def tts():
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
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400
        
    audio_file = request.files['audio']
    temp_path = f"temp_{audio_file.filename}"
    audio_file.save(temp_path)
    
    try:
        # Convert to WAV using pydub and imageio_ffmpeg
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
    data = request.json
    app_data = load_data()
    current_time = datetime.now().isoformat()
    
    if data['type'] == 'task':
        app_data['tasks'].append({"id": int(time.time() * 1000), "title": data['title'], "due": data.get('due', ''), "done": False})
    elif data['type'] == 'toggle_task':
        for t in app_data['tasks']:
            if t['id'] == data['id']: t['done'] = not t['done']; break
    elif data['type'] == 'delete_task':
        app_data['tasks'] = [t for t in app_data['tasks'] if t['id'] != data['id']]
    elif data['type'] == 'transaction':
        app_data['transactions'].append({
            "id": int(time.time() * 1000),
            "type": data['trans_type'],
            "account": data.get('account', 'کیف پول'),
            "amount": data['amount'],
            "desc": data.get('desc', ''),
            "date": current_time
        })
    elif data['type'] == 'delete_trans':
        app_data['transactions'] = [t for t in app_data['transactions'] if t['id'] != data['id']]
        
    save_data(app_data)
    return jsonify({"status": "success"})

@app.route('/api/test')
def test_conn():
    try:
        payload = {"model": "agnes-2.0-flash", "messages": [{"role": "user", "content": "Test"}]}
        headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200: return jsonify({"status": "success"})
        else: return jsonify({"status": "error", "message": f"API Error {response.status_code}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_text = data.get('text', '')
    image_b64 = data.get('image', None)
    app_data = load_data()
    current_dt = datetime.now().isoformat()
    
    current_tasks = "\n".join([f"- {t['title']} (Done: {'Yes' if t['done'] else 'No'}, Due: {t.get('due', 'N/A')})" for t in app_data['tasks']]) or "None"
    current_trans = "\n".join([f"- {t['type']}: {t['amount']} ({t.get('desc', '')}) [Account: {t.get('account', 'N/A')}]" for t in app_data['transactions']]) or "None"

    system_prompt = f"""You are a smart personal assistant. The user speaks Persian.
Your task is to extract Tasks and financial Transactions from the user's text or image.
Also, provide a short analysis and suggestion based on current and new data.

CRITICAL RULES:
1. Current Date and Time is: {current_dt}. Use this to calculate relative dates like "tomorrow".
2. All dates MUST be in Gregorian ISO format: YYYY-MM-DDTHH:MM.
3. If a transaction doesn't have a specific date, use the Current Date and Time.
4. Amounts must be numeric (Toman).
5. If the user mentions an account, extract it as "account". If not mentioned, default "account" to "کیف پول".
6. If an image is provided, analyze it (receipt, bank slip, bill) to extract amount, date, description, and account.
7. Your response MUST be ONLY a valid JSON object.

Current User Data:
Tasks:
{current_tasks}
Transactions:
{current_trans}

Respond in this exact JSON format:
{{
  "new_tasks": [{{"title": "Task title in Persian", "due": "YYYY-MM-DDTHH:MM" or null}}],
  "new_transactions": [{{"type": "income or expense", "amount": number, "desc": "Description", "account": "Account name in Persian", "date": "YYYY-MM-DDTHH:MM"}}],
  "reply": "Friendly Persian text response with analysis"
}}

If no new tasks or transactions, leave the array empty."""

    user_content = []
    if user_text:
        user_content.append({"type": "text", "text": user_text})
    elif image_b64:
        user_content.append({"type": "text", "text": "لطفا اطلاعات این فیش را خوانده و تراکنش آن را ثبت کن."})
        
    if image_b64:
        user_content.append({"type": "image_url", "image_url": {"url": image_b64}})

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
                app_data['tasks'].append({
                    "id": int(time.time() * 1000),
                    "title": t['title'],
                    "due": t.get('due', ''),
                    "done": False
                })
                
        if 'new_transactions' in parsed:
            for t in parsed['new_transactions']:
                trans_date = t.get('date', current_dt)
                app_data['transactions'].append({
                    "id": int(time.time() * 1000),
                    "type": t['type'],
                    "amount": int(t['amount']),
                    "desc": t.get('desc', ''),
                    "account": t.get('account', 'کیف پول'),
                    "date": trans_date
                })
                
        save_data(app_data)
        return jsonify({"reply": parsed.get('reply', 'ثبت شد!')})
        
    except Exception as e:
        return jsonify({"reply": f"خطا در پردازش هوش مصنوعی: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
