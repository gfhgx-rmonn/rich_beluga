#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Userbot Features
Модули: Userbot Info | Sender | Time in Nick
Зависимости: pip install telethon aiohttp
БД/сессия: ~/.tg_userbot/ (общая)
Логи: /sdcard/Documents/logs/
"""

import asyncio
import io
import re
import sys
import os
import glob
import sqlite3
import time
import random
import math
from datetime import datetime, timezone, timedelta

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PhoneNumberInvalidError,
    PasswordHashInvalidError,
    FloodWaitError,
    SendCodeUnavailableError,
)
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.auth import ResendCodeRequest

# ════════════════════════════════════════════════════════════════════════════
#  ⚙️  КОНФИГУРАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

SCRIPT_NAME   = "Userbot Features"
SCRIPT_AUTHOR = "@rich_beluga"

PREFIX         = "."
VERSION        = "1.1"
OWNER          = "@rich_beluga"
HOST           = "Ubuntu 22.04"
INFO_IMAGE_URL = "https://i.imgur.com/4M34hi2.png"

# ════════════════════════════════════════════════════════════════════════════
#  ПУТИ
# ════════════════════════════════════════════════════════════════════════════

_DB_DIR    = os.path.expanduser("~/.tg_userbot")
_LOGS_DIR  = "/sdcard/Documents/logs"
os.makedirs(_DB_DIR,  exist_ok=True)
os.makedirs(_LOGS_DIR, exist_ok=True)

SESSION_FILE = os.path.join(_DB_DIR, "session")
CREDS_FILE   = os.path.join(_DB_DIR, "creds")
PID_FILE     = os.path.join(_DB_DIR, "bot.pid")
SENDER_CFG   = os.path.join(_DB_DIR, "sender.cfg")
TZ_CFG_FILE  = os.path.join(_DB_DIR, "time_nick.cfg")
STR_SES_FILE = os.path.join(_DB_DIR, "session.string")  # строка сессии (StringSession)

# ════════════════════════════════════════════════════════════════════════════
#  ЦВЕТА
# ════════════════════════════════════════════════════════════════════════════

R  = "\033[0m";  B  = "\033[1m";  CY = "\033[96m"
GR = "\033[92m"; YE = "\033[93m"; RE = "\033[91m"; DM = "\033[2m"

# ════════════════════════════════════════════════════════════════════════════
#  БАННЕР С РАНДОМНЫМ ГРАДИЕНТОМ
# ════════════════════════════════════════════════════════════════════════════

BANNER_ART = r"""⠀⠀⠀⠀⠀⠀⠀⠀⠀⡟⠀⠀⠀⢠⠏⡆⠀⠀⠀⠀⠀⢀⣀⣤⣤⣤⣀⡀
⠀⠀⠀⠀⠀⡟⢦⡀⠇⠀⠀⣀⠞⠀⠀⠘⡀⢀⡠⠚⣉⠤⠂⠀⠀⠀⠈⠙⢦⡀
⠀⠀⠀⠀⠀⡇⠀⠉⠒⠊⠁⠀⠀⠀⠀⠀⠘⢧⠔⣉⠤⠒⠒⠉⠉⠀⠀⠀⠀⠹⣆
⠀⠀⠀⠀⠀⢰⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⠀⠀⣤⠶⠶⢶⡄⠀⠀⠀⠀⢹⡆
⠀⣀⠤⠒⠒⢺⠒⠀⠀⠀⠀⠀⠀⠀⠀⠤⠊⠀⢸⠀⡿⠀⡀⠀⣀⡟⠀⠀⠀⠀⢸⡇
⠈⠀⠀⣠⠴⠚⢯⡀⠐⠒⠚⠉⠀⢶⠂⠀⣀⠜⠀⢿⡀⠉⠚⠉⠀⠀⠀⠀⣠⠟
⠀⠠⠊⠀⠀⠀⠀⠙⠂⣴⠒⠒⣲⢔⠉⠉⣹⣞⣉⣈⠿⢦⣀⣀⣀⣠⡴⠟⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠉⠀⠉⠉⠉"""

# Пары цветов «близких» тонов для градиента — выбирается одна пара рандомно при запуске
_GRADIENT_PAIRS = [
    ("\033[94m",  "\033[96m"),   # синий + бирюзовый
    ("\033[92m",  "\033[96m"),   # зелёный + бирюзовый
    ("\033[91m",  "\033[93m"),   # красный + оранжево-жёлтый
    ("\033[93m",  "\033[92m"),   # жёлтый + зелёный
    ("\033[95m",  "\033[94m"),   # фиолетовый + синий
    ("\033[96m",  "\033[92m"),   # бирюзовый + зелёный
]

def _gradient_line(line: str, col_a: str, col_b: str) -> str:
    """Красит строку градиентом от col_a к col_b посимвольно."""
    n = len(line)
    if n == 0:
        return line
    out = ""
    for i, ch in enumerate(line):
        # Чередуем цвета по позиции — создаёт плавный визуальный переход
        color = col_a if (i * 2 // max(n, 1)) % 2 == 0 else col_b
        out += f"{color}{ch}{R}"
    return out

def banner(active_modules: list[str] | None = None):
    col_a, col_b = random.choice(_GRADIENT_PAIRS)

    art_lines = BANNER_ART.splitlines()
    art_width  = max(len(l) for l in art_lines) + 2

    # Правая колонка — текст рядом с баннером
    right = [
        f"{B}{SCRIPT_NAME}{R}",
        f"Author: {CY}{SCRIPT_AUTHOR}{R}",
        "",
        f"{DM}БД/сессия : {_DB_DIR}{R}",
        f"{DM}Логи      : {_LOGS_DIR}{R}",
    ]

    print()
    for i, art_line in enumerate(art_lines):
        colored_art = _gradient_line(art_line, col_a, col_b)
        side = right[i] if i < len(right) else ""
        padding = " " * (art_width - len(art_line))
        print(f"{colored_art}{padding}  {side}")

    # Оставшиеся строки правой колонки если баннер короче
    for j in range(len(art_lines), len(right)):
        print(" " * (art_width + 2) + right[j])

    print()

# ════════════════════════════════════════════════════════════════════════════
#  ЛОГГЕР
# ════════════════════════════════════════════════════════════════════════════

class Logger:
    def __init__(self):
        self._file   = None
        self._start  = datetime.now()

    def init_file(self, modules: list[str]):
        ts   = self._start
        name = ts.strftime("%d.%m.%Y_%H-%M") + ".log"
        path = os.path.join(_LOGS_DIR, name)
        try:
            os.makedirs(_LOGS_DIR, exist_ok=True)
            self._file = open(path, "w", encoding="utf-8", buffering=1)
            header = (
                f"Name: {SCRIPT_NAME}\n"
                f"Author: {SCRIPT_AUTHOR}\n"
                f"Modules: {', '.join(modules)}\n"
                f"Time of start: {ts.strftime('%H:%M')}\n"
                f"{'─' * 48}\n"
            )
            self._file.write(header)
            self._file.flush()
            print(f"{DM}  Лог-файл  : {path}{R}")
        except Exception as e:
            print(f"{YE}[Warn] Не удалось создать лог-файл: {e}{R}")
            self._file = None

    def _write(self, level: str, msg: str):
        if self._file:
            ts = datetime.now().strftime("%H:%M:%S")
            try:
                self._file.write(f"[{ts}] [{level}] {msg}\n")
                self._file.flush()
            except Exception:
                pass

    def info(self, msg: str):
        print(f"{GR}[Info]{R} {msg}")
        self._write("Info", msg)

    def warn(self, msg: str):
        print(f"{YE}[Warn]{R} {msg}")
        self._write("Warn", msg)

    def error(self, msg: str):
        print(f"{RE}[Error]{R} {msg}")
        self._write("Error", msg)

    def close(self):
        if self._file:
            try:
                self._file.write(f"{'─' * 48}\n")
                self._file.write(
                    f"[{datetime.now().strftime('%H:%M:%S')}] [Info] Скрипт завершён.\n"
                )
                self._file.close()
            except Exception:
                pass
            self._file = None

log = Logger()

# ════════════════════════════════════════════════════════════════════════════
#  INPUT HELPERS
# ════════════════════════════════════════════════════════════════════════════

async def ainput(prompt: str = "") -> str:
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(None, lambda: input(prompt))).strip()

async def ask(prompt: str, default: str = "") -> str:
    suffix = f" {DM}[{default}]{R}" if default else ""
    try:
        val = await ainput(f"{CY}▶{R} {prompt}{suffix}: ")
    except (EOFError, KeyboardInterrupt):
        log.info("Отменено пользователем."); cleanup(); sys.exit(0)
    return val or default

def ask_sync(prompt: str, default: str = "") -> str:
    suffix = f" {DM}[{default}]{R}" if default else ""
    try:
        val = input(f"{CY}▶{R} {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        log.info("Отменено пользователем."); cleanup(); sys.exit(0)
    return val or default

# ════════════════════════════════════════════════════════════════════════════
#  PID / СЕССИЯ
# ════════════════════════════════════════════════════════════════════════════

def check_single_instance():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            old = f.read().strip()
        try:
            os.kill(int(old), 0)
            log.warn(f"Уже запущен экземпляр (PID {old}).")
            print(f"  {B}1{R} — Остановить старый и продолжить")
            print(f"  {B}2{R} — Выйти")
            ch = input(f"{CY}▶{R} Выбор [1/2]: ").strip()
            if ch == "1":
                try: os.kill(int(old), 15); time.sleep(1)
                except Exception: pass
                _unlock()
            else:
                sys.exit(0)
        except (ProcessLookupError, ValueError):
            _unlock()
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def _unlock():
    for p in (SESSION_FILE+".session-wal", SESSION_FILE+".session-shm", PID_FILE):
        for f in glob.glob(p):
            try: os.remove(f)
            except OSError: pass
    db = SESSION_FILE + ".session"
    if os.path.exists(db):
        try:
            c = sqlite3.connect(db, timeout=3)
            c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            c.close()
        except sqlite3.OperationalError:
            log.warn("Сессия повреждена — пересоздаём.")
            try: os.remove(db)
            except OSError: pass

def cleanup():
    try: os.remove(PID_FILE)
    except OSError: pass

# ════════════════════════════════════════════════════════════════════════════
#  CREDS
# ════════════════════════════════════════════════════════════════════════════

def load_creds():
    if os.path.exists(CREDS_FILE):
        try:
            creds = {}
            with open(CREDS_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        creds[k.strip()] = v.strip()
            return creds.get("api_id",""), creds.get("api_hash","")
        except Exception:
            pass
    return "", ""

def save_creds(api_id, api_hash):
    with open(CREDS_FILE, "w") as f:
        f.write(f"api_id={api_id}\napi_hash={api_hash}\n")
    try: os.chmod(CREDS_FILE, 0o600)
    except OSError: pass

# ════════════════════════════════════════════════════════════════════════════
#  TELEGRAM CLIENT FACTORY
# ════════════════════════════════════════════════════════════════════════════

# Параметры точно соответствуют тому, что отправляет Telegram Desktop 5.9.0 x64.
# lang_pack="tdesktop" — ключевой параметр: именно он заставляет Telegram
# показывать иконку десктопного устройства вместо Android.
_TG_DEVICE    = "PC"                # device_model: ПК-иконка в сессиях
_TG_SYSTEM    = "Windows 10"        # system_version
_TG_APP_VER   = "5.9.0 x64"        # app_version  (Telegram Desktop 5.9.0)
_TG_LANG      = "en"
_TG_SYS_LANG  = "en-US"
_TG_LANG_PACK = "tdesktop"          # ← решает проблему с Android-иконкой

def _make_client(session, api_id: str, api_hash: str) -> TelegramClient:
    client = TelegramClient(
        session,
        int(api_id),
        api_hash,
        device_model     = _TG_DEVICE,
        system_version   = _TG_SYSTEM,
        app_version      = _TG_APP_VER,
        lang_code        = _TG_LANG,
        system_lang_code = _TG_SYS_LANG,
        connection_retries = 10,
        retry_delay        = 2,
    )
    # Telethon жёстко прописывает lang_pack="" в InitConnection,
    # поэтому патчим вручную — так сервер Telegram идентифицирует клиент
    # как Telegram Desktop и показывает правильную иконку.
    try:
        client._init_request.lang_pack = _TG_LANG_PACK
    except AttributeError:
        pass
    return client

# ════════════════════════════════════════════════════════════════════════════
#  STRING SESSION
# ════════════════════════════════════════════════════════════════════════════

def load_string_session() -> str:
    """Загружает сохранённую строку сессии. Возвращает "" если нет."""
    if os.path.exists(STR_SES_FILE):
        try:
            s = open(STR_SES_FILE).read().strip()
            return s if s else ""
        except Exception:
            pass
    return ""

def save_string_session(s: str):
    with open(STR_SES_FILE, "w") as f:
        f.write(s)
    try: os.chmod(STR_SES_FILE, 0o600)
    except OSError: pass

def delete_string_session():
    try: os.remove(STR_SES_FILE)
    except OSError: pass

def choose_auth_method() -> str:
    """
    Спрашивает метод авторизации.
    Возвращает: "code" | "string" | "generate" | "web"
    """
    print(f"\n{B}Метод авторизации Telegram:{R}\n")
    print(f"  {CY}1{R} — Войти через код (SMS / приложение)")
    print(f"  {CY}2{R} — Вставить строку сессии (StringSession)")
    print(f"  {CY}3{R} — Сгенерировать строку сессии через терминал")
    print(f"  {CY}4{R} — {B}Веб-панель{R} — авторизация через браузер")
    print()
    print(f"  {DM}Строка сессии — зашифрованная строка вида 1BVtsOK8Bu...{R}")
    print(f"  {DM}заменяет файл сессии, удобна для переноса между устройствами.{R}\n")
    while True:
        ch = input(f"{CY}▶{R} Выбор [1/2/3/4]: ").strip()
        if ch == "1": return "code"
        if ch == "2": return "string"
        if ch == "3": return "generate"
        if ch == "4": return "web"
        print(f"{YE}  Введите 1, 2, 3 или 4.{R}")

# ════════════════════════════════════════════════════════════════════════════
#  ВЕБ-ПАНЕЛЬ АВТОРИЗАЦИИ
# ════════════════════════════════════════════════════════════════════════════

_WEB_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Userbot — Авторизация</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#c9d1d9;font-family:monospace;
     display:flex;justify-content:center;align-items:center;min-height:100vh;padding:16px}
.card{background:#161b22;border:1px solid #30363d;border-radius:12px;
      padding:36px 40px;width:100%;max-width:440px}
h2{color:#58a6ff;font-size:1.15rem;margin-bottom:4px}
.sub{color:#8b949e;font-size:.8rem;margin-bottom:26px}
.step{color:#8b949e;font-size:.73rem;margin-bottom:18px;
      padding:6px 10px;background:#0d1117;border-radius:6px;border-left:2px solid #30363d}
label{display:block;color:#8b949e;font-size:.78rem;margin-bottom:5px;margin-top:14px}
label:first-of-type{margin-top:0}
input{width:100%;background:#0d1117;border:1px solid #30363d;border-radius:6px;
      padding:10px 14px;color:#c9d1d9;font-family:monospace;font-size:.92rem;
      outline:none;transition:border .15s}
input:focus{border-color:#58a6ff}
.hint{color:#8b949e;font-size:.73rem;margin-top:4px}
a{color:#58a6ff}
button{width:100%;margin-top:20px;padding:11px;background:#238636;
       border:none;border-radius:6px;color:#fff;font-family:monospace;
       font-size:.92rem;cursor:pointer;transition:background .15s}
button:hover{background:#2ea043}
button:disabled{background:#21262d;color:#8b949e;cursor:not-allowed}
.err{color:#f85149;font-size:.79rem;margin-top:12px;display:none}
.ok{color:#3fb950;font-size:.82rem;margin-top:14px}
.session-box{background:#0d1117;border:1px solid #30363d;border-radius:6px;
             padding:12px;word-break:break-all;font-size:.72rem;color:#58a6ff;
             margin-top:14px;user-select:all;cursor:text;line-height:1.5}
.note{color:#8b949e;font-size:.76rem;margin-top:10px;line-height:1.55}
.spinner{display:inline-block;width:12px;height:12px;border:2px solid #ffffff40;
         border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;
         vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<div class="card">
  <h2>🔐 Userbot — Авторизация</h2>
  <p class="sub">Локальная веб-панель · все данные остаются на вашем устройстве</p>

  <!-- Шаг 1: api_id + api_hash -->
  <div id="s1">
    <p class="step">Шаг 1 / 4 — API-ключи Telegram</p>
    <label>api_id</label>
    <input id="api_id" type="text" placeholder="12345678" autocomplete="off">
    <label>api_hash</label>
    <input id="api_hash" type="text" placeholder="abcdef1234567890abcdef1234567890" autocomplete="off">
    <p class="hint">Получить: <a href="https://my.telegram.org" target="_blank">my.telegram.org</a>
       → «API development tools»</p>
    <button id="btn1" onclick="submitApiKeys()">Далее</button>
    <p class="err" id="e1"></p>
  </div>

  <!-- Шаг 2: номер телефона -->
  <div id="s2" style="display:none">
    <p class="step">Шаг 2 / 4 — номер телефона</p>
    <label>Номер телефона</label>
    <input id="phone" type="tel" placeholder="+79001234567" autocomplete="tel">
    <p class="hint">Код придёт в приложение Telegram или по SMS</p>
    <button id="btn2" onclick="sendCode()">Получить код</button>
    <p class="err" id="e2"></p>
  </div>

  <!-- Шаг 3: код -->
  <div id="s3" style="display:none">
    <p class="step">Шаг 3 / 4 — код подтверждения</p>
    <label>Код из Telegram</label>
    <input id="code" type="text" placeholder="12345" maxlength="10" autocomplete="one-time-code">
    <button id="btn3" onclick="signIn()">Войти</button>
    <p class="err" id="e3"></p>
  </div>

  <!-- Шаг 3б: 2FA -->
  <div id="s4" style="display:none">
    <p class="step">Шаг 3б / 4 — двухфакторная аутентификация</p>
    <label>Облачный пароль 2FA</label>
    <input id="pwd" type="password" placeholder="Ваш пароль" autocomplete="current-password">
    <button id="btn4" onclick="verify2fa()">Подтвердить</button>
    <p class="err" id="e4"></p>
  </div>

  <!-- Готово -->
  <div id="sdone" style="display:none">
    <p class="ok">✅ Авторизация успешна!</p>
    <p class="note">Пользователь: <span id="uname" style="color:#c9d1d9"></span></p>
    <p class="note" style="margin-top:8px">Строка сессии сохранена на сервере.<br>
    Можно закрыть эту вкладку — скрипт продолжится автоматически.</p>
    <p class="note" style="margin-top:10px">Строка сессии (нажмите чтобы выделить):</p>
    <div class="session-box" id="sess" onclick="this.focus();document.execCommand('selectAll')"></div>
  </div>
</div>

<script>
function setLoading(btnId, loading) {
  const b = document.getElementById(btnId);
  if (loading) { b.disabled = true; b.innerHTML = '<span class="spinner"></span>Подождите...'; }
  else          { b.disabled = false; b.innerHTML = b._orig || b.innerHTML; }
}
function initBtn(id, text) {
  const b = document.getElementById(id); b._orig = text; b.innerHTML = text;
}
['btn1','btn2','btn3','btn4'].forEach((id,i) => {
  const texts = ['Далее','Получить код','Войти','Подтвердить'];
  initBtn(id, texts[i]);
});
function showErr(id, msg) {
  const e = document.getElementById(id);
  e.textContent = msg; e.style.display = 'block';
}
function hideErr(id) { document.getElementById(id).style.display = 'none'; }

async function post(url, data) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });
  return r.json();
}

async function submitApiKeys() {
  hideErr('e1');
  const api_id   = document.getElementById('api_id').value.trim();
  const api_hash = document.getElementById('api_hash').value.trim();
  if (!api_id || !api_hash) { showErr('e1','Заполните оба поля'); return; }
  if (!/^\\d+$/.test(api_id)) { showErr('e1','api_id должен быть числом'); return; }
  setLoading('btn1', true);
  const r = await post('/auth/setup', {api_id, api_hash});
  setLoading('btn1', false);
  if (r.ok) {
    document.getElementById('s1').style.display = 'none';
    document.getElementById('s2').style.display = 'block';
    document.getElementById('phone').focus();
  } else { showErr('e1', r.error || 'Ошибка'); }
}

async function sendCode() {
  hideErr('e2');
  const phone = document.getElementById('phone').value.trim();
  if (!phone) { showErr('e2','Введите номер телефона'); return; }
  setLoading('btn2', true);
  const r = await post('/auth/send_code', {phone});
  setLoading('btn2', false);
  if (r.ok) {
    document.getElementById('s2').style.display = 'none';
    document.getElementById('s3').style.display = 'block';
    document.getElementById('code').focus();
  } else { showErr('e2', r.error || 'Ошибка'); }
}

async function signIn() {
  hideErr('e3');
  const code = document.getElementById('code').value.trim();
  if (!code) { showErr('e3','Введите код'); return; }
  setLoading('btn3', true);
  const r = await post('/auth/sign_in', {code});
  setLoading('btn3', false);
  if (r.ok) { showDone(r); }
  else if (r.need_2fa) {
    document.getElementById('s3').style.display = 'none';
    document.getElementById('s4').style.display = 'block';
    document.getElementById('pwd').focus();
  } else { showErr('e3', r.error || 'Ошибка'); }
}

async function verify2fa() {
  hideErr('e4');
  const pwd = document.getElementById('pwd').value;
  if (!pwd) { showErr('e4','Введите пароль'); return; }
  setLoading('btn4', true);
  const r = await post('/auth/verify_2fa', {password: pwd});
  setLoading('btn4', false);
  if (r.ok) { showDone(r); }
  else { showErr('e4', r.error || 'Неверный пароль'); }
}

function showDone(r) {
  ['s1','s2','s3','s4'].forEach(id => document.getElementById(id).style.display='none');
  document.getElementById('sdone').style.display = 'block';
  document.getElementById('uname').textContent = r.name || '';
  document.getElementById('sess').textContent  = r.session || '';
}

// Enter для перехода между шагами
document.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  if (document.getElementById('s1').style.display !== 'none') submitApiKeys();
  else if (document.getElementById('s2').style.display !== 'none') sendCode();
  else if (document.getElementById('s3').style.display !== 'none') signIn();
  else if (document.getElementById('s4').style.display !== 'none') verify2fa();
});
</script>
</body>
</html>"""


async def web_auth_panel(port: int = 8080) -> tuple[str, str, str]:
    """
    Запускает локальный HTTP-сервер.
    Пользователь вводит api_id, api_hash, номер, код, 2FA в браузере.
    Возвращает (api_id, api_hash, session_str).
    """
    from aiohttp import web as aiohttp_web

    # Состояние — меняется по мере прохождения шагов
    state: dict = {
        "api_id":   None,
        "api_hash": None,
        "phone":    None,
        "hash":     None,
        "client":   None,
        "done":     asyncio.Event(),
        "result":   {},       # {api_id, api_hash, session}
    }

    app = aiohttp_web.Application()

    async def handle_index(request):
        return aiohttp_web.Response(text=_WEB_HTML, content_type="text/html")

    async def handle_setup(request):
        """Шаг 1: принять api_id + api_hash, создать клиент."""
        data     = await request.json()
        api_id   = str(data.get("api_id","")).strip()
        api_hash = str(data.get("api_hash","")).strip()
        if not api_id or not api_hash:
            return aiohttp_web.json_response({"ok": False, "error": "api_id и api_hash обязательны"})
        try:
            client = _make_client(StringSession(), api_id, api_hash)
            await client.connect()
            state["api_id"]   = api_id
            state["api_hash"] = api_hash
            state["client"]   = client
            log.info(f"Веб-панель: api_id={api_id} принят, соединение установлено.")
            return aiohttp_web.json_response({"ok": True})
        except Exception as e:
            return aiohttp_web.json_response({"ok": False, "error": f"Ошибка подключения: {e}"})

    async def handle_send_code(request):
        """Шаг 2: отправить код на номер."""
        client = state.get("client")
        if not client:
            return aiohttp_web.json_response({"ok": False, "error": "Сначала введите API-ключи"})
        data  = await request.json()
        phone = data.get("phone","").strip()
        try:
            sent = await client.send_code_request(phone)
            state["phone"] = phone
            state["hash"]  = sent.phone_code_hash
            ctype = type(sent.type).__name__
            log.info(f"Веб-панель: код запрошен для {phone} ({ctype})")
            return aiohttp_web.json_response({"ok": True})
        except PhoneNumberInvalidError:
            return aiohttp_web.json_response({"ok": False, "error": "Неверный номер телефона"})
        except FloodWaitError as e:
            return aiohttp_web.json_response({"ok": False, "error": f"FloodWait: подождите {e.seconds} сек."})
        except Exception as e:
            return aiohttp_web.json_response({"ok": False, "error": str(e)})

    async def handle_sign_in(request):
        """Шаг 3: войти по коду."""
        client = state.get("client")
        data   = await request.json()
        code   = data.get("code","").strip()
        try:
            await client.sign_in(
                phone=state["phone"], code=code,
                phone_code_hash=state["hash"],
            )
            return await _finish(client)
        except PhoneCodeInvalidError:
            return aiohttp_web.json_response({"ok": False, "error": "Неверный код"})
        except PhoneCodeExpiredError:
            return aiohttp_web.json_response({"ok": False, "error": "Код истёк — перезапустите скрипт"})
        except SessionPasswordNeededError:
            log.info("Веб-панель: требуется 2FA")
            return aiohttp_web.json_response({"ok": False, "need_2fa": True})
        except Exception as e:
            return aiohttp_web.json_response({"ok": False, "error": str(e)})

    async def handle_2fa(request):
        """Шаг 3б: 2FA пароль."""
        client = state.get("client")
        data   = await request.json()
        pwd    = data.get("password","")
        try:
            await client.sign_in(password=pwd)
            return await _finish(client)
        except PasswordHashInvalidError:
            return aiohttp_web.json_response({"ok": False, "error": "Неверный пароль 2FA"})
        except Exception as e:
            return aiohttp_web.json_response({"ok": False, "error": str(e)})

    async def _finish(client) -> aiohttp_web.Response:
        session_str = client.session.save()
        me          = await client.get_me()
        name        = f"{me.first_name or ''} (@{me.username or me.id})"
        save_string_session(session_str)
        save_creds(state["api_id"], state["api_hash"])
        state["result"] = {
            "api_id":   state["api_id"],
            "api_hash": state["api_hash"],
            "session":  session_str,
        }
        log.info(f"Веб-панель: авторизация завершена — {name}")
        state["done"].set()
        return aiohttp_web.json_response({"ok": True, "session": session_str, "name": name})

    app.router.add_get ("/",                handle_index)
    app.router.add_post("/auth/setup",      handle_setup)
    app.router.add_post("/auth/send_code",  handle_send_code)
    app.router.add_post("/auth/sign_in",    handle_sign_in)
    app.router.add_post("/auth/verify_2fa", handle_2fa)

    runner = aiohttp_web.AppRunner(app)
    await runner.setup()
    site = aiohttp_web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    url = f"http://127.0.0.1:{port}"
    log.info(f"Веб-панель запущена: {url}")
    print(f"\n{GR}{B}  Веб-панель авторизации запущена:{R}")
    print(f"\n      {CY}{B}{url}{R}\n")
    print(f"  {DM}Откройте ссылку в браузере.{R}")
    print(f"  {DM}Введите api_id, api_hash, номер, код (и 2FA если есть).{R}")
    print(f"  {DM}После авторизации скрипт продолжится автоматически.{R}\n")

    try:
        import webbrowser
        webbrowser.open(url)
    except Exception:
        pass

    await state["done"].wait()
    await asyncio.sleep(1)   # дать браузеру получить ответ
    await runner.cleanup()

    r = state["result"]
    return r["api_id"], r["api_hash"], r["session"]

# ════════════════════════════════════════════════════════════════════════════
#  SENDER CONFIG
# ════════════════════════════════════════════════════════════════════════════

def load_sender_cfg():
    if os.path.exists(SENDER_CFG):
        try:
            cfg = {}
            with open(SENDER_CFG) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        cfg[k.strip()] = v.strip()
            return cfg
        except Exception:
            pass
    return {}

def save_sender_cfg(message, count, delay_sec, chat):
    with open(SENDER_CFG, "w") as f:
        f.write(f"message={message}\ncount={count}\ndelay_sec={delay_sec}\nchat={chat}\n")

# ════════════════════════════════════════════════════════════════════════════
#  УТИЛИТЫ
# ════════════════════════════════════════════════════════════════════════════

def parse_delay(raw: str) -> int:
    units = {"mo":2592000,"w":604800,"d":86400,"h":3600,"min":60,"s":1}
    matches = re.findall(r"(\d+)\s*(mo|min|[hwds])", raw.strip(), re.IGNORECASE)
    if not matches:
        raise ValueError("Не удалось распознать интервал.")
    total = sum(int(v)*units[u.lower()] for v,u in matches)
    if total <= 0:
        raise ValueError("Интервал должен быть больше нуля.")
    return total

def seconds_to_human(sec: int) -> str:
    parts = []
    for label, size in [("мес.",2592000),("нед.",604800),("д.",86400),
                        ("ч.",3600),("мин.",60),("сек.",1)]:
        if sec >= size:
            parts.append(f"{sec//size} {label}")
            sec %= size
    return " ".join(parts) or "0 сек."

def parse_chat(raw: str):
    try:
        val = int(raw)
        if val > 0 and len(str(val)) >= 10:
            val = -val
        return val
    except ValueError:
        return raw

# ════════════════════════════════════════════════════════════════════════════
#  ЧАСОВОЙ ПОЯС
# ════════════════════════════════════════════════════════════════════════════

TZ_PRESETS = {
    "1":  ("UTC+0  — Лондон",               0),
    "2":  ("UTC+1  — Берлин, Париж",         1),
    "3":  ("UTC+2  — Киев, Калининград",     2),
    "4":  ("UTC+3  — Москва, Минск",         3),
    "5":  ("UTC+4  — Баку, Тбилиси",         4),
    "6":  ("UTC+5  — Ташкент",               5),
    "7":  ("UTC+5:30 — Индия",               5.5),
    "8":  ("UTC+6  — Алматы, Омск",          6),
    "9":  ("UTC+7  — Красноярск, Бангкок",   7),
    "10": ("UTC+8  — Пекин, Сингапур",       8),
    "11": ("UTC+9  — Токио, Сеул",           9),
    "12": ("UTC+10 — Владивосток",           10),
    "13": ("UTC+11 — Магадан",               11),
    "14": ("UTC+12 — Камчатка",              12),
    "15": ("UTC-5  — Нью-Йорк",             -5),
    "16": ("UTC-6  — Чикаго",               -6),
    "17": ("UTC-7  — Денвер",               -7),
    "18": ("UTC-8  — Лос-Анджелес",         -8),
    "c":  ("Ввести вручную (напр. +5.5)",    None),
}

def load_tz_cfg():
    if os.path.exists(TZ_CFG_FILE):
        try:
            with open(TZ_CFG_FILE) as f:
                return float(f.read().strip())
        except Exception:
            pass
    return None

def save_tz_cfg(offset: float):
    with open(TZ_CFG_FILE, "w") as f:
        f.write(str(offset))

def choose_timezone() -> float:
    saved = load_tz_cfg()
    if saved is not None:
        sign = "+" if saved >= 0 else ""
        print(f"{DM}Сохранённый часовой пояс: UTC{sign}{saved}{R}")
        if ask_sync("Использовать? (y/n)", "y").lower() in ("y","yes","д","да"):
            log.info(f"Часовой пояс: UTC{sign}{saved} (из конфига)")
            return saved

    print(f"\n{B}Выберите часовой пояс:{R}\n")
    for key, (label, _) in TZ_PRESETS.items():
        marker = f" {GR}← дефолт (МСК){R}" if key == "4" else ""
        print(f"  {CY}{key:>2}{R} — {label}{marker}")

    while True:
        choice = ask_sync("\nНомер или «c»", "4")
        if choice in TZ_PRESETS:
            _, offset = TZ_PRESETS[choice]
            if offset is None:
                while True:
                    raw = ask_sync("Смещение UTC (напр. +3, -5, +5.5)")
                    try:
                        offset = float(raw.replace(",","."))
                        if -12 <= offset <= 14: break
                        print(f"{YE}  Диапазон: -12 … +14{R}")
                    except ValueError:
                        print(f"{YE}  Введите число.{R}")
            sign = "+" if offset >= 0 else ""
            log.info(f"Выбран часовой пояс: UTC{sign}{offset}")
            save_tz_cfg(offset)
            return offset
        print(f"{YE}  Введите номер из списка или «c».{R}")

def get_tz(offset: float):
    return timezone(timedelta(hours=offset))

def current_time_str(offset: float) -> str:
    return datetime.now(get_tz(offset)).strftime("%H:%M")

# ════════════════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════════════════

_CODE_TYPES = {
    "SentCodeTypeApp":        "📱  уведомление в приложении Telegram",
    "SentCodeTypeSms":        "💬  SMS",
    "SentCodeTypeCall":       "📞  голосовой звонок",
    "SentCodeTypeFlashCall":  "📞  пропущенный звонок",
    "SentCodeTypeMissedCall": "📞  пропущенный звонок",
    "SentCodeTypeEmailCode":  "📧  email",
    "SentCodeTypeFragment":   "🔗  Fragment",
}

async def _auth_via_code(client: TelegramClient):
    """Авторизация через SMS-код / уведомление в приложении."""
    print(f"\n{YE}━━━  Вход в аккаунт Telegram  ━━━{R}\n")
    phone = await ask("Номер телефона (+79001234567)")
    if not phone:
        log.error("Номер не введён."); cleanup(); sys.exit(1)

    log.info("Запрашиваем код...")
    try:
        sent = await client.send_code_request(phone)
    except PhoneNumberInvalidError:
        log.error(f"Неверный номер: {phone}"); cleanup(); sys.exit(1)
    except FloodWaitError as e:
        log.error(f"FloodWait {e.seconds} сек."); cleanup(); sys.exit(1)
    except Exception as e:
        log.error(f"Ошибка запроса кода: {e}"); cleanup(); sys.exit(1)

    ctype = type(sent.type).__name__
    log.info(f"Код отправлен — {_CODE_TYPES.get(ctype, ctype)}")
    if "App" in ctype:
        print(f"{YE}   ℹ  Нет уведомления? Нажмите Enter → выберите «1» для SMS.{R}")

    while True:
        code = await ask("\nКод (Enter → повторить)")
        if not code:
            print(f"\n{CY}1{R} — Повторить (SMS/звонок)   {CY}2{R} — Выйти")
            ch = await ask("Выбор", "1")
            if ch == "1":
                try:
                    await client(ResendCodeRequest(phone, sent.phone_code_hash))
                    log.info("Код повторно запрошен.")
                except SendCodeUnavailableError:
                    log.warn("Telegram исчерпал все методы доставки кода.")
                    print(f"\n{YE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}")
                    print(f"{YE}  Telegram больше не может отправить код:{R}")
                    print(f"{YE}  использованы все доступные методы{R}")
                    print(f"{YE}  (уведомление в приложении, SMS, звонок).{R}")
                    print(f"{YE}  Подождите несколько минут и попробуйте{R}")
                    print(f"{YE}  запустить скрипт заново.{R}")
                    print(f"{YE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{R}\n")
                except FloodWaitError as e:
                    log.warn(f"FloodWait при повторном запросе: {e.seconds} сек.")
                    print(f"{YE}  Подождите {e.seconds} сек. перед следующей попыткой.{R}")
                except Exception as e:
                    log.warn(f"Не удалось повторить запрос кода: {e}")
            else:
                log.info("Отмена входа."); cleanup(); sys.exit(0)
            continue

        try:
            await client.sign_in(phone=phone, code=code,
                                  phone_code_hash=sent.phone_code_hash)
            break
        except PhoneCodeExpiredError:
            log.warn("Код истёк — запрашиваем новый.")
            try:
                sent = await client.send_code_request(phone)
                log.info(f"Новый код → {_CODE_TYPES.get(type(sent.type).__name__,'')}")
            except Exception as e:
                log.error(f"Не удалось запросить новый код: {e}"); cleanup(); sys.exit(1)
        except PhoneCodeInvalidError:
            log.warn("Неверный код.")
        except SessionPasswordNeededError:
            log.info("Требуется 2FA.")
            print(f"\n{YE}━━━  2FA  ━━━{R}")
            for i in range(1,4):
                pw = await ask(f"Пароль 2FA (попытка {i}/3)")
                if not pw: continue
                try:
                    await client.sign_in(password=pw)
                    log.info("2FA принят."); break
                except PasswordHashInvalidError:
                    if i == 3:
                        log.error("2FA не принят 3 раза."); cleanup(); sys.exit(1)
                    log.warn(f"Неверный пароль (попытка {i}/3).")
                except Exception as e:
                    log.error(f"Ошибка 2FA: {e}"); cleanup(); sys.exit(1)
            break
        except Exception as e:
            log.error(f"Ошибка входа: {e}"); cleanup(); sys.exit(1)

    me = await client.get_me()
    log.info(f"Авторизация успешна — {me.first_name} (@{me.username or me.id})")


async def authorize(client: TelegramClient):
    """
    Подключается и авторизуется.
    Если клиент создан через StringSession — сессия уже внутри, просто connect().
    Если через файл и не авторизован — запускает код-авторизацию.
    """
    log.info("Подключаемся к Telegram...")
    try:
        await client.connect()
    except sqlite3.OperationalError as e:
        log.warn(f"SQLite заблокирован ({e}) — сбрасываем...")
        _unlock(); await asyncio.sleep(1); await client.connect()

    log.info("Соединение установлено.")

    if await client.is_user_authorized():
        me = await client.get_me()
        log.info(f"Сессия активна — {me.first_name} (@{me.username or me.id})")
        return

    # Не авторизован — только для файловой сессии
    await _auth_via_code(client)

# ════════════════════════════════════════════════════════════════════════════
#  МОДУЛЬ 1: USERBOT INFO (.info)
# ════════════════════════════════════════════════════════════════════════════

def _prefix_label(p: str) -> str:
    labels = {".": '"." - префикс-точка', ",": '"," - префикс-запятая'}
    return labels.get(p, f'"{p}" - кастом-префикс')

def build_caption() -> str:
    block1 = (f"<blockquote>Owner: {OWNER}\nVersion: {VERSION}</blockquote>")
    block2 = (f"<blockquote>Prefix: {_prefix_label(PREFIX)}\nHost: {HOST}</blockquote>")
    return f"{block1}\n{block2}"

def register_info_handler(client: TelegramClient):
    @client.on(events.NewMessage(pattern=rf"^{re.escape(PREFIX)}info$", outgoing=True))
    async def cmd_info(event):
        await event.delete()
        caption = build_caption()
        log.info(f"Команда {PREFIX}info вызвана в чате {event.chat_id}")

        if INFO_IMAGE_URL:
            try:
                import aiohttp
                import mimetypes
                import posixpath
                from urllib.parse import urlparse

                async with aiohttp.ClientSession() as session:
                    async with session.get(INFO_IMAGE_URL) as resp:
                        img_bytes = await resp.read()
                        # Определяем имя файла из URL (как делает Heroku userbot)
                        url_path  = urlparse(INFO_IMAGE_URL).path
                        filename  = posixpath.basename(url_path) or "banner.jpg"
                        # Если у файла нет расширения — добавляем по Content-Type
                        if "." not in filename:
                            ct  = resp.headers.get("Content-Type", "image/jpeg")
                            ext = mimetypes.guess_extension(ct.split(";")[0].strip()) or ".jpg"
                            ext_fix = {".jpe": ".jpg", ".jfif": ".jpg"}
                            ext = ext_fix.get(ext, ext)
                            filename = f"banner{ext}"

                # BytesIO с именем — Telegram подберёт правильный тип и не назовёт "unnamed"
                buf = io.BytesIO(img_bytes)
                buf.name = filename   # ← ключевой приём из Heroku userbot

                await client.send_file(
                    event.chat_id,
                    file=buf,
                    caption=caption,
                    parse_mode="html",
                    force_document=False,
                )
                log.info(f"Фото «{filename}» отправлено в чат {event.chat_id}")
            except Exception as e:
                log.warn(f"Фото недоступно ({e}), отправляем текст.")
                await client.send_message(event.chat_id,
                    f"⚠ Фото недоступно: {e}\n\n{caption}", parse_mode="html")
        else:
            await client.send_message(event.chat_id, caption, parse_mode="html")

    log.info(f"Модуль «Userbot Info» активен. Команда: {PREFIX}info")

# ════════════════════════════════════════════════════════════════════════════
#  МОДУЛЬ 2: SENDER (авто-отправка)
# ════════════════════════════════════════════════════════════════════════════

def configure_sender():
    print(f"\n{B}━━━  Настройка Sender  ━━━{R}\n")
    cfg = load_sender_cfg()

    message = ask_sync("Текст сообщения", cfg.get("message",""))
    if not message:
        log.error("Сообщение пустое."); cleanup(); sys.exit(1)

    while True:
        try:
            count = int(ask_sync("Количество раз (0 = бесконечно)", cfg.get("count","0")))
            if count >= 0: break
        except ValueError:
            pass
        print(f"{YE}  Введите целое неотрицательное число.{R}")

    while True:
        try:
            raw = ask_sync("Интервал", cfg.get("delay_sec","3600"))
            try:
                delay_sec = int(raw)
                if delay_sec <= 0: raise ValueError
            except ValueError:
                delay_sec = parse_delay(raw)
            break
        except ValueError as e:
            print(f"{YE}  {e}  Примеры: 30min | 2h | 1d{R}")

    chat_raw = ask_sync("ID чата / @username", cfg.get("chat",""))
    if not chat_raw:
        log.error("Чат не указан."); cleanup(); sys.exit(1)

    save_sender_cfg(message, count, delay_sec, chat_raw)
    return message, count, delay_sec, chat_raw

async def sender_loop(client: TelegramClient, entity, message: str,
                      count: int, delay_sec: int):
    infinite = count == 0
    sent_count = 0
    log.info(f"Sender запущен. Интервал: {seconds_to_human(delay_sec)}, "
             f"раз: {'∞' if infinite else count}")
    while True:
        try:
            await client.send_message(entity, message)
            sent_count += 1
            log.info(f"[Sender {sent_count}] Сообщение отправлено.")
        except FloodWaitError as e:
            log.warn(f"Sender FloodWait {e.seconds} сек...")
            await asyncio.sleep(e.seconds)
            continue
        except Exception as e:
            log.warn(f"Sender ошибка отправки: {e}")

        if not infinite and sent_count >= count:
            log.info(f"Sender завершён: {count} сообщений отправлено.")
            break
        await asyncio.sleep(delay_sec)

# ════════════════════════════════════════════════════════════════════════════
#  МОДУЛЬ 3: TIME IN NICK
# ════════════════════════════════════════════════════════════════════════════

async def time_nick_loop(client: TelegramClient, offset: float,
                         original_last_name: str):
    me = await client.get_me()
    first_name = me.first_name or ""
    sign = "+" if offset >= 0 else ""
    log.info(f"Time in Nick запущен. UTC{sign}{offset}, аккаунт: {first_name}")
    last_set = ""
    while True:
        time_str  = current_time_str(offset)
        last_name = f"| {time_str}"
        if time_str != last_set:
            try:
                await client(UpdateProfileRequest(last_name=last_name))
                last_set = time_str
                log.info(f"Time in Nick: ник обновлён → «{first_name} {last_name}»")
            except FloodWaitError as e:
                log.warn(f"Time in Nick FloodWait {e.seconds} сек...")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                log.warn(f"Time in Nick ошибка обновления: {e}")
        now = datetime.now(get_tz(offset))
        await asyncio.sleep(60 - now.second)

async def restore_last_name(client: TelegramClient, original: str):
    try:
        await client(UpdateProfileRequest(last_name=original))
        log.info(f"Фамилия восстановлена: «{original}»")
    except Exception as e:
        log.warn(f"Не удалось восстановить фамилию: {e}")

# ════════════════════════════════════════════════════════════════════════════
#  МЕНЮ ВЫБОРА МОДУЛЕЙ
# ════════════════════════════════════════════════════════════════════════════

MODULES = {
    "1": "Userbot Info",
    "2": "Sender",
    "3": "Time in Nick",
}

def choose_modules() -> list[str]:
    """
    Возвращает список выбранных ключей, напр. ["1","3"].
    Поддерживает ввод через пробел: "1 2" или "1 2 3".
    """
    print(f"{B}Список модулей:{R}\n")
    for k, name in MODULES.items():
        print(f"  {CY}{k}{R} — {name}")
    print()

    while True:
        raw = input(f"{CY}▶{R} Введите номер пункта: ").strip()
        keys = raw.split()
        valid = [k for k in keys if k in MODULES]
        invalid = [k for k in keys if k not in MODULES]
        if invalid:
            print(f"{YE}  Неизвестные номера: {', '.join(invalid)}. Допустимые: 1, 2, 3.{R}")
            continue
        if not valid:
            print(f"{YE}  Введите хотя бы один номер.{R}")
            continue
        return valid

# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

async def main():
    banner()

    # ── Выбор модулей ─────────────────────────────────────────────────────────
    selected_keys  = choose_modules()
    selected_names = [MODULES[k] for k in selected_keys]

    # ── Инициализация лога ────────────────────────────────────────────────────
    log.init_file(selected_names)
    log.info(f"Скрипт запущен. Модули: {', '.join(selected_names)}")

    check_single_instance()
    log.info(f"PID: {os.getpid()}")

    # ── Клиент — выбор метода авторизации ────────────────────────────────────
    saved_str_session = load_string_session()

    if saved_str_session:
        # Строка сессии уже сохранена — грузим ключи и стартуем без вопросов
        api_id, api_hash = load_creds()
        if not api_id or not api_hash:
            log.warn("Строка сессии есть, но API-ключи не найдены — введите вручную.")
            api_id   = ask_sync("api_id")
            api_hash = ask_sync("api_hash")
            save_creds(api_id, api_hash)
        log.info("Строка сессии найдена — используем StringSession.")
        client = _make_client(StringSession(saved_str_session), api_id, api_hash)

    else:
        auth_method = choose_auth_method()

        if auth_method == "web":
            # Веб-панель собирает всё сама: api_id, api_hash, номер, код, 2FA
            log.info("Запускаем веб-панель авторизации.")
            api_id, api_hash, session_str = await web_auth_panel()
            log.info("Веб-панель: авторизация завершена, строка сессии сохранена.")
            print(f"\n{GR}✔ Строка сессии сохранена.{R} "
                  f"{DM}При следующем запуске авторизация не потребуется.{R}\n")
            client = _make_client(StringSession(session_str), api_id, api_hash)

        else:
            # Все остальные методы требуют api_id/api_hash в терминале
            api_id, api_hash = load_creds()
            if api_id and api_hash:
                log.info(f"API-ключи загружены из {CREDS_FILE}")
            else:
                print(f"{YE}Нужны API-ключи → https://my.telegram.org → «API development tools»{R}\n")
                api_id   = ask_sync("api_id")
                api_hash = ask_sync("api_hash")
                if not api_id or not api_hash:
                    log.error("api_id / api_hash не введены."); cleanup(); sys.exit(1)
                save_creds(api_id, api_hash)
                log.info("API-ключи сохранены.")

            if auth_method == "string":
                print(f"\n{DM}Строку сессии можно получить через вариант «3» или «4».{R}\n")
                raw = ask_sync("Вставьте строку сессии")
                if not raw:
                    log.error("Строка сессии не введена."); cleanup(); sys.exit(1)
                save_string_session(raw)
                log.info("Строка сессии сохранена.")
                client = _make_client(StringSession(raw), api_id, api_hash)

            elif auth_method == "generate":
                log.info("Генерация строки сессии через код-авторизацию.")
                gen_client = _make_client(StringSession(), api_id, api_hash)
                await _auth_via_code(gen_client)
                session_str = gen_client.session.save()
                await gen_client.disconnect()
                save_string_session(session_str)
                log.info("Строка сессии сгенерирована и сохранена.")
                print(f"\n{GR}{B}✔ Строка сессии сгенерирована:{R}\n")
                print(f"{CY}{session_str}{R}\n")
                print(f"{DM}Сохранена в: {STR_SES_FILE}{R}")
                print(f"{DM}При следующем запуске авторизация не потребуется.{R}\n")
                client = _make_client(StringSession(session_str), api_id, api_hash)

            else:
                # Вариант 1: обычный вход через код, файловая сессия
                client = _make_client(SESSION_FILE, api_id, api_hash)

    await authorize(client)
    me = await client.get_me()
    original_last_name = me.last_name or ""

    # ── Настройка Sender если выбран (после авторизации) ─────────────────────
    sender_params = None
    message = count = delay_sec = chat_raw = None
    if "2" in selected_keys:
        sender_params = configure_sender()
        message, count, delay_sec, chat_raw = sender_params
        log.info(f"Sender настроен: чат={chat_raw}, раз={'∞' if count==0 else count}, "
                 f"интервал={seconds_to_human(delay_sec)}")

    # ── Настройка Time in Nick если выбран ────────────────────────────────────
    tz_offset = None
    if "3" in selected_keys:
        tz_offset = choose_timezone()

    # ── Регистрация обработчиков ──────────────────────────────────────────────
    if "1" in selected_keys:
        register_info_handler(client)

    # ── Сборка задач для gather ───────────────────────────────────────────────
    tasks = [asyncio.create_task(client.run_until_disconnected())]

    if "2" in selected_keys:
        chat = parse_chat(chat_raw)
        try:
            entity = await client.get_entity(chat)
        except Exception as e:
            log.error(f"Чат не найден: {e}")
            await client.disconnect(); cleanup(); sys.exit(1)
        chat_title = getattr(entity,"title",None) or getattr(entity,"first_name",str(chat))
        log.info(f"Sender: чат найден — «{chat_title}»")
        tasks.append(asyncio.create_task(
            sender_loop(client, entity, message, count, delay_sec)
        ))

    if "3" in selected_keys:
        tasks.append(asyncio.create_task(
            time_nick_loop(client, tz_offset, original_last_name)
        ))

    print(f"\n{GR}{B}Запущено.{R}  Ctrl+C для остановки.\n")

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        log.info("Получен сигнал остановки (Ctrl+C).")
    except Exception as e:
        log.error(f"Неожиданная ошибка: {e}")
    finally:
        # Восстановление фамилии если Time in Nick был активен
        if "3" in selected_keys:
            print(f"\n{B}Что сделать с фамилией?{R}")
            print(f"  {CY}1{R} — Восстановить оригинальную «{original_last_name}»")
            print(f"  {CY}2{R} — Оставить время в нике")
            try:
                ch = input(f"{CY}▶{R} Выбор [1/2]: ").strip()
            except (EOFError, KeyboardInterrupt):
                ch = "1"
            if ch == "1":
                await restore_last_name(client, original_last_name)
            else:
                log.info("Фамилия оставлена как есть.")

        await client.disconnect()
        log.info("Соединение закрыто.")
        log.close()
        cleanup()


if __name__ == "__main__":
    asyncio.run(main())
