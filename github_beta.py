#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitHub Tools
Команды: .git info | .git upload | .git repo create | .git repo del | .git --help
Зависимости: pip install telethon aiohttp
БД/сессия: ~/.tg_userbot/ (общая)
Логи: /sdcard/Documents/logs/
"""

import asyncio
import base64
import io
import re
import sys
import os
import glob
import sqlite3
import time
from datetime import datetime

import aiohttp

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
from telethon.tl.functions.auth import ResendCodeRequest

# ════════════════════════════════════════════════════════════════════════════
#  ⚙️  КОНФИГУРАЦИЯ — редактируй здесь
# ════════════════════════════════════════════════════════════════════════════

SCRIPT_NAME   = "GitHub Tools"
SCRIPT_AUTHOR = "@rich_beluga"

PREFIX = "."           # префикс команд

# ════════════════════════════════════════════════════════════════════════════
#  ПУТИ
# ════════════════════════════════════════════════════════════════════════════

_DB_DIR   = os.path.expanduser("~/.tg_userbot")
_LOGS_DIR = "/sdcard/Documents/logs"
os.makedirs(_DB_DIR,   exist_ok=True)
os.makedirs(_LOGS_DIR, exist_ok=True)

SESSION_FILE  = os.path.join(_DB_DIR, "session")
CREDS_FILE    = os.path.join(_DB_DIR, "creds")
PID_FILE      = os.path.join(_DB_DIR, "bot.pid")
GH_CFG_FILE   = os.path.join(_DB_DIR, "github.cfg")
STR_SES_FILE  = os.path.join(_DB_DIR, "session.string")

# ════════════════════════════════════════════════════════════════════════════
#  ЦВЕТА
# ════════════════════════════════════════════════════════════════════════════

R  = "\033[0m";  B  = "\033[1m";  CY = "\033[96m"
GR = "\033[92m"; YE = "\033[93m"; RE = "\033[91m"; DM = "\033[2m"
WH = "\033[97m"; GY = "\033[90m"

# ════════════════════════════════════════════════════════════════════════════
#  БАННЕР — чёрно-белый логотип GitHub
# ════════════════════════════════════════════════════════════════════════════

_GH_LOGO = r"""                ##################
            ##########################
          ##############################
        ##################################
      ######################################
     ########################################
    ########      ####       ###      ########
   #########                          #########
  ###########                         ##########
 ###########                          ###########
 ##########                            ##########
 #########                              #########
##########                              ##########
##########                              ##########
 ##########                            ##########
 ###########                          ###########
  ###########                        ###########
  #############                    #############
   ###### ###########        ##################
    ######  ########          ################
     #######  #####           ###############
       ######                 #############
        ############          ############
           #########          #########
              ######          ######"""

def banner():
    print()
    for line in _GH_LOGO.splitlines():
        colored = ""
        for ch in line:
            colored += (f"{WH}{B}{ch}{R}" if ch == "#" else f"{GY}{ch}{R}")
        print(colored)
    print()
    print(f"  {B}{WH}{SCRIPT_NAME}{R}  {DM}by {SCRIPT_AUTHOR}{R}")
    print(f"  {DM}БД/сессия : {_DB_DIR}{R}")
    print(f"  {DM}Логи      : {_LOGS_DIR}{R}")
    print()

# ════════════════════════════════════════════════════════════════════════════
#  ЛОГГЕР
# ════════════════════════════════════════════════════════════════════════════

class Logger:
    def __init__(self):
        self._file  = None
        self._start = datetime.now()

    def init_file(self):
        ts   = self._start
        name = ts.strftime("%d.%m.%Y_%H-%M") + ".log"
        path = os.path.join(_LOGS_DIR, name)
        try:
            os.makedirs(_LOGS_DIR, exist_ok=True)
            self._file = open(path, "w", encoding="utf-8", buffering=1)
            self._file.write(
                f"Name: {SCRIPT_NAME}\n"
                f"Author: {SCRIPT_AUTHOR}\n"
                f"Time of start: {ts.strftime('%H:%M')}\n"
                f"{'─'*48}\n"
            )
            self._file.flush()
            print(f"{DM}  Лог-файл  : {path}{R}")
        except Exception as e:
            print(f"{YE}[Warn] Не удалось создать лог-файл: {e}{R}")
            self._file = None

    def _write(self, level, msg):
        if self._file:
            ts = datetime.now().strftime("%H:%M:%S")
            try:
                self._file.write(f"[{ts}] [{level}] {msg}\n")
                self._file.flush()
            except Exception:
                pass

    def info(self, msg):
        print(f"{GR}[Info]{R} {msg}"); self._write("Info", msg)

    def warn(self, msg):
        print(f"{YE}[Warn]{R} {msg}"); self._write("Warn", msg)

    def error(self, msg):
        print(f"{RE}[Error]{R} {msg}"); self._write("Error", msg)

    def close(self):
        if self._file:
            try:
                self._file.write(f"{'─'*48}\n"
                    f"[{datetime.now().strftime('%H:%M:%S')}] [Info] Скрипт завершён.\n")
                self._file.close()
            except Exception:
                pass
            self._file = None

log = Logger()

# ════════════════════════════════════════════════════════════════════════════
#  INPUT HELPERS
# ════════════════════════════════════════════════════════════════════════════

async def ainput(prompt=""):
    loop = asyncio.get_event_loop()
    return (await loop.run_in_executor(None, lambda: input(prompt))).strip()

async def ask(prompt, default=""):
    suffix = f" {DM}[{default}]{R}" if default else ""
    try:
        val = await ainput(f"{CY}▶{R} {prompt}{suffix}: ")
    except (EOFError, KeyboardInterrupt):
        log.info("Отменено."); cleanup(); sys.exit(0)
    return val or default

def ask_sync(prompt, default=""):
    suffix = f" {DM}[{default}]{R}" if default else ""
    try:
        val = input(f"{CY}▶{R} {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        log.info("Отменено."); cleanup(); sys.exit(0)
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
            print(f"  {B}1{R} — Остановить старый и продолжить\n  {B}2{R} — Выйти")
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
#  TELEGRAM CREDS
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

_TG_DEVICE    = "PC"
_TG_SYSTEM    = "Windows 10"
_TG_APP_VER   = "5.9.0 x64"
_TG_LANG      = "en"
_TG_SYS_LANG  = "en-US"
_TG_LANG_PACK = "tdesktop"   # ← показывает иконку Telegram Desktop, а не Android

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
    # Патч lang_pack: Telethon по умолчанию отправляет "",
    # Telegram Desktop отправляет "tdesktop" — именно это определяет иконку сессии.
    try:
        client._init_request.lang_pack = _TG_LANG_PACK
    except AttributeError:
        pass
    return client

# ════════════════════════════════════════════════════════════════════════════
#  STRING SESSION
# ════════════════════════════════════════════════════════════════════════════

def load_string_session() -> str:
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

def choose_auth_method() -> str:
    print(f"\n{B}Метод авторизации Telegram:{R}\n")
    print(f"  {CY}1{R} — Войти через код (SMS / приложение)")
    print(f"  {CY}2{R} — Вставить строку сессии (StringSession)")
    print(f"  {CY}3{R} — Сгенерировать строку сессии через терминал")
    print(f"  {CY}4{R} — {B}Веб-панель{R} — авторизация через браузер")
    print()
    print(f"  {DM}Строка сессии — зашифрованная строка вида 1BVtsOK8Bu...{R}")
    print(f"  {DM}Заменяет файл сессии, удобна для переноса между устройствами.{R}\n")
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
<title>GitHub Tools — Авторизация</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,300;8..144,400;8..144,500;8..144,700&display=swap" rel="stylesheet">
<style>
/* ═══════════════════════════════════════════════════════════
   MD3 DARK THEME — Color Tokens (Tonal Palette: Teal/Green)
   Generated from source color #1B6B4A
   ═══════════════════════════════════════════════════════════ */
:root {
  /* Primary */
  --md-primary:               #4FDBA8;
  --md-on-primary:            #003826;
  --md-primary-container:     #005238;
  --md-on-primary-container:  #6FF7C3;

  /* Secondary */
  --md-secondary:             #B2CCBD;
  --md-on-secondary:          #1D352A;
  --md-secondary-container:   #334C40;
  --md-on-secondary-container:#CEECDA;

  /* Tertiary */
  --md-tertiary:              #82CDD8;
  --md-on-tertiary:           #00363D;
  --md-tertiary-container:    #004F57;

  /* Error */
  --md-error:                 #FFB4AB;
  --md-on-error:              #690005;
  --md-error-container:       #93000A;
  --md-on-error-container:    #FFDAD6;

  /* Background / Surface */
  --md-background:            #101411;
  --md-on-background:         #DFE4DE;
  --md-surface:               #101411;
  --md-on-surface:            #DFE4DE;

  /* Surface containers (elevation tones) */
  --md-surface-dim:           #101411;
  --md-surface-bright:        #353A35;
  --md-surface-container-lowest:  #0B0F0C;
  --md-surface-container-low:     #181D18;
  --md-surface-container:         #1C211C;
  --md-surface-container-high:    #262B26;
  --md-surface-container-highest: #313630;

  /* Variants */
  --md-on-surface-variant:    #BEC9BE;
  --md-outline:               #889388;
  --md-outline-variant:       #3D4A3D;

  /* Scrim */
  --md-scrim:                 #000000;

  /* ── Shape ── */
  --shape-xs:    4px;
  --shape-sm:    8px;
  --shape-md:    12px;
  --shape-lg:    16px;
  --shape-xl:    28px;
  --shape-full:  9999px;

  /* ── Motion ── */
  --motion-standard:    cubic-bezier(.2, 0, 0, 1);
  --motion-decelerate:  cubic-bezier(0, 0, 0, 1);
  --motion-accelerate:  cubic-bezier(.3, 0, 1, 1);
  --dur-short1:  50ms;
  --dur-short2:  100ms;
  --dur-short3:  150ms;
  --dur-short4:  200ms;
  --dur-medium1: 250ms;
  --dur-medium2: 300ms;
  --dur-medium3: 350ms;
  --dur-medium4: 400ms;
  --dur-long1:   450ms;
  --dur-long2:   500ms;

  /* ── Elevation (surface tonal overlay) ── */
  --elev-1: rgba(79,219,168,.05);
  --elev-2: rgba(79,219,168,.08);
  --elev-3: rgba(79,219,168,.11);
}

/* ── Reset ──────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { height: 100%; }

body {
  font-family: 'Roboto Flex', 'Roboto', sans-serif;
  font-variation-settings: 'opsz' 14;
  background: var(--md-background);
  color: var(--md-on-background);
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  /* Subtle noise grain on background */
  position: relative;
}
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.04'/%3E%3C/svg%3E");
  background-size: 256px;
  pointer-events: none;
  z-index: 0;
}

/* ═══════════════════════════════════════════════════════════
   LINEAR PROGRESS INDICATOR (MD3 indeterminate)
   ═══════════════════════════════════════════════════════════ */
#progress {
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 4px;
  background: var(--md-outline-variant);
  z-index: 999;
  overflow: hidden;
  opacity: 0;
  transition: opacity var(--dur-short4) var(--motion-standard);
}
#progress.visible { opacity: 1; }

/* Stop-indicator dots */
#progress::before,
#progress::after {
  content: '';
  position: absolute;
  top: 0; height: 100%;
  background: var(--md-primary);
  border-radius: 0 2px 2px 0;
}
#progress::before {
  width: 40%;
  left: -45%;
  animation: md3-p1 1.8s var(--motion-standard) infinite;
}
#progress::after {
  width: 65%;
  left: -70%;
  animation: md3-p2 1.8s var(--motion-standard) .4s infinite;
  opacity: .6;
}
@keyframes md3-p1 {
  0%   { left: -45%; }
  60%  { left: 110%; }
  100% { left: 110%; }
}
@keyframes md3-p2 {
  0%   { left: -70%; }
  70%  { left: 110%; }
  100% { left: 110%; }
}

/* ═══════════════════════════════════════════════════════════
   SURFACE / CARD  — Elevation level 1 (surface-container)
   ═══════════════════════════════════════════════════════════ */
.surface {
  position: relative;
  z-index: 1;
  background: var(--md-surface-container);
  border-radius: var(--shape-xl);
  padding: 28px 24px 24px;
  width: 100%;
  max-width: 400px;
  /* MD3 elevation = shadow + tonal overlay */
  box-shadow:
    0 1px 3px 1px rgba(0,0,0,.35),
    0 1px 2px rgba(0,0,0,.3);
  overflow: hidden;
}

/* Tonal overlay (elevation level 1) */
.surface::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--elev-1);
  pointer-events: none;
}

/* ═══════════════════════════════════════════════════════════
   TOP APP BAR (mini — inside card)
   ═══════════════════════════════════════════════════════════ */
.app-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.app-bar-leading {
  width: 44px; height: 44px;
  border-radius: var(--shape-md);
  background: var(--md-primary-container);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}
/* Headline Small */
.headline-sm {
  font-size: 20px;
  line-height: 28px;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--md-on-surface);
}
/* Body Medium */
.body-md {
  font-size: 14px;
  line-height: 20px;
  letter-spacing: .25px;
  color: var(--md-on-surface-variant);
  margin-bottom: 20px;
  font-weight: 400;
}

/* ═══════════════════════════════════════════════════════════
   STEP INDICATOR DOTS
   ═══════════════════════════════════════════════════════════ */
.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
}
.step-dot {
  height: 8px;
  border-radius: var(--shape-full);
  background: var(--md-outline-variant);
  flex-shrink: 0;
  transition:
    width     var(--dur-medium2) var(--motion-standard),
    background var(--dur-short4) var(--motion-standard);
  width: 8px;
}
.step-dot.done {
  background: var(--md-primary);
  opacity: .45;
}
.step-dot.active {
  width: 28px;
  background: var(--md-primary);
  opacity: 1;
}

/* ═══════════════════════════════════════════════════════════
   STEP PAGES  — slide + fade transition
   ═══════════════════════════════════════════════════════════ */
.steps-wrap { overflow: hidden; }

.step-page {
  display: none;
  animation: step-enter var(--dur-medium2) var(--motion-decelerate) both;
}
.step-page.active { display: block; }
@keyframes step-enter {
  from { opacity: 0; transform: translateX(16px); }
  to   { opacity: 1; transform: translateX(0); }
}

/* Label Medium */
.label-md {
  font-size: 12px;
  line-height: 16px;
  font-weight: 500;
  letter-spacing: .5px;
  text-transform: uppercase;
  color: var(--md-on-surface-variant);
  margin-bottom: 18px;
}

/* ═══════════════════════════════════════════════════════════
   OUTLINED TEXT FIELD (MD3 spec-accurate)
   ═══════════════════════════════════════════════════════════ */
.field {
  position: relative;
  margin-top: 18px;
}
.field:first-of-type { margin-top: 0; }

/* Outline container */
.field-outline {
  position: absolute;
  inset: 0;
  display: flex;
  pointer-events: none;
  border-radius: var(--shape-sm);
}
.field-outline-start {
  width: 12px;
  border: 1px solid var(--md-outline);
  border-right: none;
  border-radius: var(--shape-sm) 0 0 var(--shape-sm);
  transition: border-color var(--dur-short4), border-width var(--dur-short4);
}
.field-outline-notch {
  border-top: 1px solid var(--md-outline);
  border-bottom: 1px solid var(--md-outline);
  transition: border-color var(--dur-short4), border-width var(--dur-short4), width var(--dur-short4) var(--motion-standard);
  flex: 0 0 0;
  overflow: hidden;
}
.field-outline-end {
  flex: 1;
  border: 1px solid var(--md-outline);
  border-left: none;
  border-radius: 0 var(--shape-sm) var(--shape-sm) 0;
  transition: border-color var(--dur-short4), border-width var(--dur-short4);
}

.field input {
  display: block;
  width: 100%;
  height: 56px;
  padding: 28px 16px 8px;
  background: transparent;
  border: none;
  outline: none;
  color: var(--md-on-surface);
  font-family: inherit;
  font-size: 16px;
  line-height: 24px;
  letter-spacing: .5px;
  caret-color: var(--md-primary);
  position: relative;
  z-index: 1;
}

/* Floating label */
.field label {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 16px;
  line-height: 24px;
  letter-spacing: .5px;
  color: var(--md-on-surface-variant);
  pointer-events: none;
  z-index: 2;
  transition:
    top       var(--dur-short4) var(--motion-standard),
    font-size  var(--dur-short4) var(--motion-standard),
    color      var(--dur-short4),
    letter-spacing var(--dur-short4);
  transform-origin: left center;
  background: transparent;
  padding: 0;
  white-space: nowrap;
}

/* Focused / filled state — label floats up */
.field input:focus + .field-outline .field-outline-start,
.field input:not(:placeholder-shown) + .field-outline .field-outline-start {
  border-width: 2px;
  border-color: var(--md-primary);
}
.field input:not(:focus):not(:placeholder-shown) + .field-outline .field-outline-start {
  border-color: var(--md-outline);
  border-width: 1px;
}
.field input:focus + .field-outline .field-outline-notch,
.field input:not(:placeholder-shown) + .field-outline .field-outline-notch {
  border-top: none;
  border-width: 2px;
  border-color: var(--md-primary);
}
.field input:not(:focus):not(:placeholder-shown) + .field-outline .field-outline-notch {
  border-top: none;
  border-color: var(--md-outline);
  border-width: 1px;
}
.field input:focus + .field-outline .field-outline-end,
.field input:not(:placeholder-shown) + .field-outline .field-outline-end {
  border-width: 2px;
  border-color: var(--md-primary);
}
.field input:not(:focus):not(:placeholder-shown) + .field-outline .field-outline-end {
  border-color: var(--md-outline);
  border-width: 1px;
}

/* Label float uses JS to add .float class */
.field.floating label {
  top: 8px;
  font-size: 12px;
  letter-spacing: .4px;
  color: var(--md-primary);
  transform: translateY(0);
}
.field:not(.focused).floating label {
  color: var(--md-on-surface-variant);
}
.field.focused label {
  color: var(--md-primary);
}

/* Error state */
.field.has-error .field-outline-start,
.field.has-error .field-outline-notch,
.field.has-error .field-outline-end {
  border-color: var(--md-error) !important;
}
.field.has-error.floating label,
.field.has-error.focused label {
  color: var(--md-error) !important;
}

/* Supporting text */
.field-support {
  font-size: 12px;
  line-height: 16px;
  letter-spacing: .4px;
  color: var(--md-error);
  padding: 4px 16px 0;
  min-height: 20px;
  display: none;
}
.field.has-error .field-support { display: block; }

/* Hint */
.field-hint {
  font-size: 12px;
  line-height: 16px;
  letter-spacing: .4px;
  color: var(--md-on-surface-variant);
  padding: 4px 16px 0;
}
.field-hint a { color: var(--md-primary); text-decoration: none; }
.field-hint a:hover { text-decoration: underline; }

/* Focus indicator (state layer) inside field */
.field input:hover ~ .field-hover { opacity: 1; }
.field-hover {
  position: absolute;
  inset: 0;
  border-radius: var(--shape-sm);
  background: var(--md-on-surface);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--dur-short4);
}

/* ═══════════════════════════════════════════════════════════
   FILLED BUTTON (MD3)
   ═══════════════════════════════════════════════════════════ */
.btn {
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 40px;
  margin-top: 24px;
  padding: 0 24px;
  background: var(--md-primary);
  color: var(--md-on-primary);
  border: none;
  border-radius: var(--shape-full);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: .1px;
  cursor: pointer;
  user-select: none;
  transition:
    box-shadow var(--dur-short4) var(--motion-standard),
    background var(--dur-short4);
  -webkit-tap-highlight-color: transparent;
}
/* State layer */
.btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--md-on-primary);
  opacity: 0;
  border-radius: inherit;
  transition: opacity var(--dur-short4);
}
.btn:not(:disabled):hover::before  { opacity: .08; }
.btn:not(:disabled):active::before { opacity: .12; }
.btn:not(:disabled):hover {
  box-shadow: 0 1px 2px rgba(0,0,0,.3), 0 1px 3px 1px rgba(0,0,0,.15);
}
/* Ripple */
.btn .ripple {
  position: absolute;
  border-radius: 50%;
  transform: scale(0);
  animation: ripple-expand .5s var(--motion-standard) forwards;
  background: rgba(0,56,38,.4);
  pointer-events: none;
}
@keyframes ripple-expand {
  to { transform: scale(4); opacity: 0; }
}
/* Disabled */
.btn:disabled {
  background: rgba(223,228,222,.12);
  color: rgba(223,228,222,.38);
  cursor: not-allowed;
  box-shadow: none;
}
.btn:disabled::before { display: none; }

/* ── MD3 Circular Progress Indicator (indeterminate) inside button ──
   Реализует спецификацию MD3: дуга одновременно вращается и меняет длину.
   Источник: m3.material.io/components/progress-indicators/specs        */
.btn .md3-circular {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  animation: md3-circ-rotate 1333ms linear infinite;
  transform-origin: center;
}
.btn .md3-circular circle {
  fill: none;
  stroke: var(--md-on-primary);
  stroke-width: 2.5;
  stroke-linecap: round;
  /* r=8.75 → circumference ≈ 55  */
  stroke-dasharray: 55;
  stroke-dashoffset: 55;
  animation: md3-circ-dash 1333ms var(--motion-standard) infinite;
  transform-origin: center;
}
/* Rotation — чуть медленнее чем dasharray чтобы создавался "спираль" эффект */
@keyframes md3-circ-rotate {
  0%   { transform: rotate(-90deg); }
  100% { transform: rotate(270deg); }
}
/* Дуга: растёт от 5% до 80% окружности, потом схлопывается */
@keyframes md3-circ-dash {
  0%   { stroke-dashoffset: 52; }
  25%  { stroke-dashoffset: 14; }   /* дуга максимальная */
  50%  { stroke-dashoffset: 52; }   /* дуга схлопнулась  */
  75%  { stroke-dashoffset: 14; }
  100% { stroke-dashoffset: 52; }
}

/* ═══════════════════════════════════════════════════════════
   DIVIDER
   ═══════════════════════════════════════════════════════════ */
.divider {
  height: 1px;
  background: var(--md-outline-variant);
  margin: 20px 0;
}

/* ═══════════════════════════════════════════════════════════
   SUCCESS SCREEN
   ═══════════════════════════════════════════════════════════ */
.done-icon-wrap {
  width: 80px; height: 80px;
  border-radius: 50%;
  background: var(--md-primary-container);
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 20px;
  animation: icon-pop var(--dur-medium3) var(--motion-decelerate) both;
}
@keyframes icon-pop {
  from { transform: scale(.5); opacity: 0; }
  to   { transform: scale(1);  opacity: 1; }
}
.done-check {
  width: 40px; height: 40px;
  stroke: var(--md-on-primary-container);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
  stroke-dasharray: 56;
  stroke-dashoffset: 56;
  animation: draw-path var(--dur-medium4) var(--dur-medium1) var(--motion-standard) forwards;
}
@keyframes draw-path { to { stroke-dashoffset: 0; } }

.done-title {
  font-size: 20px;
  line-height: 28px;
  font-weight: 400;
  color: var(--md-on-surface);
  text-align: center;
  margin-bottom: 6px;
  animation: fade-up var(--dur-medium2) var(--dur-medium2) var(--motion-decelerate) both;
}
.done-sub {
  font-size: 14px;
  line-height: 20px;
  letter-spacing: .25px;
  color: var(--md-on-surface-variant);
  text-align: center;
  margin-bottom: 20px;
  animation: fade-up var(--dur-medium2) var(--dur-medium3) var(--motion-decelerate) both;
}
@keyframes fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* User chip */
.user-chip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--md-surface-container-high);
  border-radius: var(--shape-md);
  margin-bottom: 14px;
  animation: fade-up var(--dur-medium2) var(--dur-medium4) var(--motion-decelerate) both;
}
.user-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: var(--md-secondary-container);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.user-name {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: .1px;
  color: var(--md-on-surface);
}
.user-sub {
  font-size: 12px;
  letter-spacing: .4px;
  color: var(--md-on-surface-variant);
  margin-top: 1px;
}

/* Session string container */
.session-card {
  background: var(--md-surface-container-highest);
  border-radius: var(--shape-md);
  padding: 14px 16px;
  animation: fade-up var(--dur-medium2) var(--dur-long1) var(--motion-decelerate) both;
}
.session-eyebrow {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: .8px;
  text-transform: uppercase;
  color: var(--md-primary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.session-eyebrow::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--md-outline-variant);
  border-radius: 1px;
}
.session-val {
  font-size: 11px;
  line-height: 1.7;
  letter-spacing: .2px;
  color: var(--md-on-surface-variant);
  word-break: break-all;
  cursor: text;
  user-select: all;
}
.session-tip {
  font-size: 11px;
  letter-spacing: .3px;
  color: var(--md-outline);
  margin-top: 8px;
}
</style>
</head>
<body>

<!-- ── Linear Progress Indicator ── -->
<div id="progress"></div>

<!-- ── Surface Card ── -->
<div class="surface">

  <!-- Top App Bar (inline) -->
  <div class="app-bar">
    <div class="app-bar-leading">🔐</div>
    <span class="headline-sm">GitHub Tools</span>
  </div>
  <p class="body-md">Авторизация Telegram &middot; данные остаются на устройстве</p>

  <!-- Step Dots -->
  <div class="step-row" id="dots-row">
    <div class="step-dot active"  id="dot0"></div>
    <div class="step-dot"         id="dot1"></div>
    <div class="step-dot"         id="dot2"></div>
    <div class="step-dot"         id="dot3"></div>
  </div>

  <div class="steps-wrap">

    <!-- ── Page 1: API keys ── -->
    <div class="step-page active" id="p1">
      <p class="label-md">Шаг&nbsp;1&nbsp;/ 4 &mdash; API-ключи Telegram</p>

      <!-- api_id field -->
      <div class="field" id="f-api_id">
        <div class="field-hover"></div>
        <input id="api_id" type="text" placeholder=" " autocomplete="off" inputmode="numeric">
        <div class="field-outline">
          <div class="field-outline-start"></div>
          <div class="field-outline-notch"></div>
          <div class="field-outline-end"></div>
        </div>
        <label for="api_id">api_id</label>
        <p class="field-support" id="e-api_id">Введите api_id</p>
      </div>

      <!-- api_hash field -->
      <div class="field" id="f-api_hash">
        <div class="field-hover"></div>
        <input id="api_hash" type="text" placeholder=" " autocomplete="off">
        <div class="field-outline">
          <div class="field-outline-start"></div>
          <div class="field-outline-notch"></div>
          <div class="field-outline-end"></div>
        </div>
        <label for="api_hash">api_hash</label>
        <p class="field-support" id="e-api_hash">Введите api_hash</p>
        <p class="field-hint">
          <a href="https://my.telegram.org" target="_blank">my.telegram.org</a>
          &rarr; «API development tools»
        </p>
      </div>

      <button class="btn" id="btn1" onclick="step1()">Далее</button>
    </div>

    <!-- ── Page 2: Phone ── -->
    <div class="step-page" id="p2">
      <p class="label-md">Шаг&nbsp;2&nbsp;/ 4 &mdash; Номер телефона</p>

      <div class="field" id="f-phone">
        <div class="field-hover"></div>
        <input id="phone" type="tel" placeholder=" " autocomplete="tel">
        <div class="field-outline">
          <div class="field-outline-start"></div>
          <div class="field-outline-notch"></div>
          <div class="field-outline-end"></div>
        </div>
        <label for="phone">Номер телефона</label>
        <p class="field-support" id="e-phone">Введите номер</p>
        <p class="field-hint">Код придёт в Telegram или по SMS</p>
      </div>

      <button class="btn" id="btn2" onclick="step2()">Получить код</button>
    </div>

    <!-- ── Page 3: Code ── -->
    <div class="step-page" id="p3">
      <p class="label-md">Шаг&nbsp;3&nbsp;/ 4 &mdash; Код подтверждения</p>

      <div class="field" id="f-code">
        <div class="field-hover"></div>
        <input id="code" type="text" placeholder=" " maxlength="10"
               autocomplete="one-time-code" inputmode="numeric">
        <div class="field-outline">
          <div class="field-outline-start"></div>
          <div class="field-outline-notch"></div>
          <div class="field-outline-end"></div>
        </div>
        <label for="code">Код из Telegram</label>
        <p class="field-support" id="e-code">Введите код</p>
      </div>

      <button class="btn" id="btn3" onclick="step3()">Войти</button>
    </div>

    <!-- ── Page 3b: 2FA ── -->
    <div class="step-page" id="p4">
      <p class="label-md">Шаг&nbsp;3б&nbsp;/ 4 &mdash; Двухфакторная аутентификация</p>

      <div class="field" id="f-pwd">
        <div class="field-hover"></div>
        <input id="pwd" type="password" placeholder=" " autocomplete="current-password">
        <div class="field-outline">
          <div class="field-outline-start"></div>
          <div class="field-outline-notch"></div>
          <div class="field-outline-end"></div>
        </div>
        <label for="pwd">Облачный пароль 2FA</label>
        <p class="field-support" id="e-pwd">Введите пароль</p>
      </div>

      <button class="btn" id="btn4" onclick="step4()">Подтвердить</button>
    </div>

    <!-- ── Done ── -->
    <div class="step-page" id="pdone">
      <div class="done-icon-wrap">
        <svg class="done-check" viewBox="0 0 24 24">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </div>
      <p class="done-title">Авторизация прошла успешно</p>
      <p class="done-sub">Строка сессии сохранена.<br>Можно закрыть эту вкладку.</p>

      <div class="user-chip">
        <div class="user-avatar">👤</div>
        <div>
          <div class="user-name" id="done-name">&mdash;</div>
          <div class="user-sub">Telegram · авторизован</div>
        </div>
      </div>

      <div class="session-card">
        <div class="session-eyebrow">Строка сессии</div>
        <div class="session-val" id="done-sess"></div>
        <div class="session-tip">Нажмите, чтобы выделить целиком</div>
      </div>
    </div>

  </div><!-- steps-wrap -->
</div><!-- surface -->

<script>
/* ── Floating label via JS (because CSS :focus-within is easier but
      we need notch width too) ────────────────────────────────────── */
function initFields() {
  document.querySelectorAll('.field').forEach(wrap => {
    const inp   = wrap.querySelector('input');
    const lbl   = wrap.querySelector('label');
    const notch = wrap.querySelector('.field-outline-notch');

    function updateFloat(focused) {
      const filled = inp.value.length > 0;
      const shouldFloat = focused || filled;
      wrap.classList.toggle('floating', shouldFloat);
      wrap.classList.toggle('focused',  focused);
      /* Notch width = label width * 0.75 + 8px padding */
      if (shouldFloat && lbl) {
        notch.style.width = (lbl.offsetWidth * .75 + 8) + 'px';
      } else {
        notch.style.width = '0';
      }
    }

    inp.addEventListener('focus',  () => updateFloat(true));
    inp.addEventListener('blur',   () => updateFloat(false));
    inp.addEventListener('input',  () => updateFloat(document.activeElement === inp));
    /* Initial state */
    updateFloat(false);
  });
}

/* ── Ripple ────────────────────────────────────────────────────────── */
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('pointerdown', e => {
    if (btn.disabled) return;
    const r    = document.createElement('span');
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2.2;
    r.className = 'ripple';
    r.style.cssText =
      `width:${size}px;height:${size}px;` +
      `left:${e.clientX - rect.left - size/2}px;` +
      `top:${e.clientY  - rect.top  - size/2}px`;
    btn.appendChild(r);
    r.addEventListener('animationend', () => r.remove());
  });
});

/* ── Progress bar ──────────────────────────────────────────────────── */
const $prog = document.getElementById('progress');
function showProgress() { $prog.classList.add('visible'); }
function hideProgress() { $prog.classList.remove('visible'); }

/* ── Step navigation ───────────────────────────────────────────────── */
const PAGES = ['p1','p2','p3','p4'];
const BTNS  = ['btn1','btn2','btn3','btn4'];
const ORIG  = ['Далее','Получить код','Войти','Подтвердить'];
let curStep = 0;

function goStep(n) {
  PAGES.forEach((id, i) => {
    document.getElementById(id).classList.toggle('active', i === n);
  });
  for (let i = 0; i < 4; i++) {
    const d = document.getElementById('dot' + i);
    d.className = 'step-dot' + (i === n ? ' active' : i < n ? ' done' : '');
  }
  curStep = n;
  const page = document.getElementById(PAGES[n]);
  if (page) {
    const inp = page.querySelector('input');
    if (inp) setTimeout(() => { inp.focus(); }, 60);
  }
}

function showDots(v) {
  document.getElementById('dots-row').style.display = v ? '' : 'none';
}

/* ── Loading state ─────────────────────────────────────────────────── */
/* MD3 circular indeterminate SVG — вставляется в кнопку при загрузке */
const MD3_CIRCULAR_SVG =
  '<svg class="md3-circular" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">' +
  '<circle cx="10" cy="10" r="7.5"/>' +
  '</svg>';

function setLoading(idx, on) {
  const btn = document.getElementById(BTNS[idx]);
  if (on) {
    btn.disabled = true;
    btn.innerHTML = MD3_CIRCULAR_SVG;
    showProgress();
  } else {
    btn.disabled  = false;
    btn.innerHTML = ORIG[idx];
    hideProgress();
  }
}

/* ── Field error / clear ───────────────────────────────────────────── */
function setError(fieldId, errId, msg) {
  const w = document.getElementById(fieldId);
  const e = document.getElementById(errId);
  w.classList.add('has-error');
  if (e) e.textContent = msg || e.textContent;
  /* Shake animation */
  w.animate(
    [{transform:'translateX(-5px)'},{transform:'translateX(5px)'},
     {transform:'translateX(-3px)'},{transform:'translateX(3px)'},
     {transform:'translateX(0)'}],
    {duration:320, easing:'ease-out'}
  );
}
function clearError(fieldId) {
  document.getElementById(fieldId).classList.remove('has-error');
}

/* ── fetch helper ──────────────────────────────────────────────────── */
async function post(url, data) {
  const r = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify(data)
  });
  return r.json();
}

/* ── STEP 1 — API keys ─────────────────────────────────────────────── */
async function step1() {
  clearError('f-api_id'); clearError('f-api_hash');
  const api_id   = document.getElementById('api_id').value.trim();
  const api_hash = document.getElementById('api_hash').value.trim();
  let ok = true;
  if (!api_id)                  { setError('f-api_id',   'e-api_id',   'Введите api_id');                    ok=false; }
  else if (!/^\\d+$/.test(api_id)) { setError('f-api_id', 'e-api_id', 'api_id должен быть числом'); ok=false; }
  if (!api_hash)                { setError('f-api_hash', 'e-api_hash', 'Введите api_hash');                   ok=false; }
  if (!ok) return;

  setLoading(0, true);
  try {
    const r = await post('/auth/setup', {api_id, api_hash});
    setLoading(0, false);
    if (r.ok) goStep(1);
    else setError('f-api_hash', 'e-api_hash', r.error || 'Ошибка подключения');
  } catch { setLoading(0, false); setError('f-api_hash', 'e-api_hash', 'Нет связи с сервером'); }
}

/* ── STEP 2 — Phone ────────────────────────────────────────────────── */
async function step2() {
  clearError('f-phone');
  const phone = document.getElementById('phone').value.trim();
  if (!phone) { setError('f-phone', 'e-phone', 'Введите номер телефона'); return; }

  setLoading(1, true);
  try {
    const r = await post('/auth/send_code', {phone});
    setLoading(1, false);
    if (r.ok) goStep(2);
    else setError('f-phone', 'e-phone', r.error || 'Ошибка');
  } catch { setLoading(1, false); setError('f-phone', 'e-phone', 'Нет связи с сервером'); }
}

/* ── STEP 3 — Code ─────────────────────────────────────────────────── */
async function step3() {
  clearError('f-code');
  const code = document.getElementById('code').value.trim();
  if (!code) { setError('f-code', 'e-code', 'Введите код'); return; }

  setLoading(2, true);
  try {
    const r = await post('/auth/sign_in', {code});
    setLoading(2, false);
    if (r.ok)          showDone(r);
    else if (r.need_2fa) goStep(3);
    else               setError('f-code', 'e-code', r.error || 'Неверный код');
  } catch { setLoading(2, false); setError('f-code', 'e-code', 'Нет связи с сервером'); }
}

/* ── STEP 4 — 2FA ──────────────────────────────────────────────────── */
async function step4() {
  clearError('f-pwd');
  const pwd = document.getElementById('pwd').value;
  if (!pwd) { setError('f-pwd', 'e-pwd', 'Введите пароль'); return; }

  setLoading(3, true);
  try {
    const r = await post('/auth/verify_2fa', {password: pwd});
    setLoading(3, false);
    if (r.ok) showDone(r);
    else      setError('f-pwd', 'e-pwd', r.error || 'Неверный пароль');
  } catch { setLoading(3, false); setError('f-pwd', 'e-pwd', 'Нет связи с сервером'); }
}

/* ── Done screen ───────────────────────────────────────────────────── */
function showDone(r) {
  hideProgress();
  PAGES.forEach(id => document.getElementById(id).classList.remove('active'));
  document.getElementById('pdone').classList.add('active');
  showDots(false);
  document.getElementById('done-name').textContent = r.name || '—';
  document.getElementById('done-sess').textContent  = r.session || '';
}

/* Select session string on click */
document.getElementById('done-sess').addEventListener('click', function() {
  const sel = window.getSelection();
  const rng = document.createRange();
  rng.selectNodeContents(this);
  sel.removeAllRanges();
  sel.addRange(rng);
});

/* ── Enter key ─────────────────────────────────────────────────────── */
document.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;
  [step1, step2, step3, step4][curStep]?.();
});

/* ── Init ──────────────────────────────────────────────────────────── */
initFields();
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

    state: dict = {
        "api_id":   None,
        "api_hash": None,
        "phone":    None,
        "hash":     None,
        "client":   None,
        "done":     asyncio.Event(),
        "result":   {},
    }

    app = aiohttp_web.Application()

    async def handle_index(request):
        return aiohttp_web.Response(text=_WEB_HTML, content_type="text/html")

    async def handle_setup(request):
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
    await asyncio.sleep(1)
    await runner.cleanup()

    r = state["result"]
    return r["api_id"], r["api_hash"], r["session"]

# ════════════════════════════════════════════════════════════════════════════
#  GITHUB CONFIG (токен + username)
# ════════════════════════════════════════════════════════════════════════════

def load_gh_cfg():
    if os.path.exists(GH_CFG_FILE):
        try:
            cfg = {}
            with open(GH_CFG_FILE) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        k, _, v = line.partition("=")
                        cfg[k.strip()] = v.strip()
            return cfg.get("token",""), cfg.get("username","")
        except Exception:
            pass
    return "", ""

def save_gh_cfg(token, username):
    with open(GH_CFG_FILE, "w") as f:
        f.write(f"token={token}\nusername={username}\n")
    try: os.chmod(GH_CFG_FILE, 0o600)
    except OSError: pass

def setup_github() -> tuple[str, str]:
    """Запрашивает GitHub-токен и username, сохраняет в cfg."""
    token, username = load_gh_cfg()
    if token and username:
        log.info(f"GitHub: конфиг загружен (пользователь: {username})")
        return token, username

    print(f"""
{YE}Для работы GitHub-модуля нужен Personal Access Token.
Получить: {B}https://github.com/settings/tokens{R}{YE}
Права токена: {B}repo{R}{YE} (полный доступ к репозиториям).{R}
""")
    token    = ask_sync("GitHub Personal Access Token")
    username = ask_sync("GitHub username (ваш логин)")
    if not token or not username:
        log.error("Токен и username обязательны."); cleanup(); sys.exit(1)
    save_gh_cfg(token, username)
    log.info(f"GitHub конфиг сохранён (пользователь: {username})")
    return token, username

# ════════════════════════════════════════════════════════════════════════════
#  GITHUB API HELPERS
# ════════════════════════════════════════════════════════════════════════════

GH_API = "https://api.github.com"

def _gh_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

async def gh_get(token: str, path: str) -> tuple[int, dict]:
    url = f"{GH_API}{path}"
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=_gh_headers(token)) as r:
            return r.status, await r.json()

async def gh_post(token: str, path: str, data: dict) -> tuple[int, dict]:
    url = f"{GH_API}{path}"
    async with aiohttp.ClientSession() as s:
        async with s.post(url, headers=_gh_headers(token), json=data) as r:
            return r.status, await r.json()

async def gh_put(token: str, path: str, data: dict) -> tuple[int, dict]:
    url = f"{GH_API}{path}"
    async with aiohttp.ClientSession() as s:
        async with s.put(url, headers=_gh_headers(token), json=data) as r:
            return r.status, await r.json()

async def gh_delete(token: str, path: str) -> int:
    url = f"{GH_API}{path}"
    async with aiohttp.ClientSession() as s:
        async with s.delete(url, headers=_gh_headers(token)) as r:
            return r.status

# ════════════════════════════════════════════════════════════════════════════
#  ЛОКАЛИЗАЦИЯ
# ════════════════════════════════════════════════════════════════════════════

def file_word(n: int) -> str:
    """
    Русское склонение слова «файл»:
      1        → файл   (обрабатывается отдельно в вызывающем коде)
      2–4, 22–24, 32–34 ... → файла
      21, 31, 41 ...         → файл
      остальные              → файлов
    """
    mod100 = n % 100
    mod10  = n % 10
    if 11 <= mod100 <= 19:
        return "файлов"
    if mod10 == 1:
        return "файл"
    if 2 <= mod10 <= 4:
        return "файла"
    return "файлов"

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
    log.info(f"Код → {_CODE_TYPES.get(ctype, ctype)}")
    if "App" in ctype:
        print(f"{YE}   ℹ  Нет уведомления? Нажмите Enter → «1» для SMS.{R}")

    while True:
        code = await ask("\nКод (Enter → повторить)")
        if not code:
            print(f"\n{CY}1{R} — Повторить   {CY}2{R} — Выйти")
            ch = await ask("Выбор", "1")
            if ch == "1":
                try:
                    await client(ResendCodeRequest(phone, sent.phone_code_hash))
                    log.info("Код повторно запрошен.")
                except Exception as e:
                    log.warn(f"Не удалось повторить: {e}")
            else:
                log.info("Отмена."); cleanup(); sys.exit(0)
            continue

        try:
            await client.sign_in(phone=phone, code=code,
                                  phone_code_hash=sent.phone_code_hash)
            break
        except PhoneCodeExpiredError:
            log.warn("Код истёк.")
            try:
                sent = await client.send_code_request(phone)
                log.info(f"Новый код → {_CODE_TYPES.get(type(sent.type).__name__,'')}")
            except Exception as e:
                log.error(f"Ошибка: {e}"); cleanup(); sys.exit(1)
        except PhoneCodeInvalidError:
            log.warn("Неверный код.")
        except SessionPasswordNeededError:
            log.info("Требуется 2FA.")
            print(f"\n{YE}━━━  2FA  ━━━{R}")
            for i in range(1, 4):
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
    log.info(f"Авторизован — {me.first_name} (@{me.username or me.id})")


async def authorize(client: TelegramClient):
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

    await _auth_via_code(client)

# ════════════════════════════════════════════════════════════════════════════
#  ОБРАБОТЧИКИ КОМАНД
# ════════════════════════════════════════════════════════════════════════════

def register_handlers(client: TelegramClient, gh_token: str, gh_user: str):

    pat = re.escape(PREFIX)

    # ── .git --help ───────────────────────────────────────────────────────────
    @client.on(events.NewMessage(
        pattern=rf"^{pat}git\s+--help$", outgoing=True))
    async def cmd_help(event):
        await event.delete()
        log.info("Команда .git --help")

        commands = [
            (f"{PREFIX}git info <пользователь>",
             "Информация об аккаунте GitHub-пользователя"),
            (f"{PREFIX}git upload <репозиторий>",
             "Загрузить файл в репозиторий (ответом на файл)"),
            (f"{PREFIX}git upload <репозиторий> <имя>",
             "Загрузить файл с кастомным именем (расширение подставляется автоматически)"),
            (f"{PREFIX}git repo create <имя>",
             "Создать новый репозиторий"),
            (f"{PREFIX}git repo del <имя>",
             "Удалить репозиторий"),
            (f"{PREFIX}git --help",
             "Показать этот список команд"),
        ]

        lines = []
        for cmd, desc in commands:
            lines.append(f"<code>{cmd}</code> — {desc}")

        body = "\n".join(lines)
        # expandable=True — сворачиваемая цитата (поддерживается в Telegram)
        text = f'<blockquote expandable><b>Полный список команд:</b>\n\n{body}</blockquote>'
        await event.respond(text, parse_mode="html")

    # ── .git info <user> ──────────────────────────────────────────────────────
    @client.on(events.NewMessage(
        pattern=rf"^{pat}git\s+info\s+(\S+)$", outgoing=True))
    async def cmd_info(event):
        await event.delete()
        target = event.pattern_match.group(1)
        log.info(f"Команда .git info {target}")

        status, data = await gh_get(gh_token, f"/users/{target}")

        if status != 200:
            err = data.get("message", f"HTTP {status}")
            log.warn(f".git info: ошибка {status} для {target}: {err}")
            await event.respond(
                f"<blockquote>⚠ Пользователь <code>{target}</code> не найден.\n"
                f"Ошибка: {err}</blockquote>",
                parse_mode="html"
            )
            return

        login    = data.get("login", target)
        name     = data.get("name")          # None если не задано
        pub_repos= data.get("public_repos", 0)

        lines = [f"Имя пользователя: <code>{login}</code>"]
        if name:
            lines.append(f"Отображаемое имя: {name}")
        lines.append(f"Количество репозиториев: {pub_repos}")

        text = "<blockquote>" + "\n".join(lines) + "</blockquote>"
        log.info(f".git info: {login}, repos={pub_repos}")
        await event.respond(text, parse_mode="html")

    # ── .git upload <repo> [custom_name] (ответом на файл) ───────────────────
    # Паттерн: обязательный аргумент repo, необязательный custom_name
    @client.on(events.NewMessage(
        pattern=rf"^{pat}git\s+upload\s+(\S+)(?:\s+(\S+))?$", outgoing=True))
    async def cmd_upload(event):
        await event.delete()
        repo_name   = event.pattern_match.group(1)
        custom_name = event.pattern_match.group(2)  # None если не указано

        # Проверяем что команда — ответ на сообщение с файлом
        reply = await event.get_reply_message()
        if not reply or not reply.file:
            await event.respond(
                "<blockquote>⚠ Ответьте командой на сообщение с файлом.</blockquote>",
                parse_mode="html"
            )
            return

        # ── Определяем имя файла ─────────────────────────────────────────────
        from telethon.tl.types import DocumentAttributeFilename
        import mimetypes

        # Сначала определяем расширение из оригинального файла
        detected_ext = None

        # 1. Атрибуты документа
        if hasattr(reply.media, "document") and reply.media.document:
            for attr in reply.media.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    _, detected_ext = os.path.splitext(attr.file_name)
                    break

        # 2. reply.file.name
        if not detected_ext and reply.file.name:
            _, detected_ext = os.path.splitext(reply.file.name)

        # 3. Из MIME-типа
        if not detected_ext:
            mime = reply.file.mime_type or "application/octet-stream"
            ext  = mimetypes.guess_extension(mime) or ""
            ext_fix = {".jpe": ".jpg", ".jpeg": ".jpg", ".jfif": ".jpg"}
            detected_ext = ext_fix.get(ext, ext)

        # Если указано кастомное имя — берём его + автоматическое расширение
        if custom_name:
            # Если пользователь сам указал расширение в имени — не дублируем
            if "." in custom_name:
                filename = custom_name
            else:
                filename = f"{custom_name}{detected_ext}"
            log.info(f"Кастомное имя файла: {filename}")
        else:
            # Автоматическое имя
            if reply.file.name and reply.file.name != "file":
                filename = reply.file.name
            else:
                mime = reply.file.mime_type or "application/octet-stream"
                base_names = {
                    "image": "photo", "video": "video",
                    "audio": "audio", "text":  "document",
                }
                base = base_names.get(mime.split("/")[0], "file")
                filename = f"{base}{detected_ext}"

        files_to_upload = [(filename, reply)]
        log.info(f"Команда .git upload {repo_name}: файл={filename}")

        uploaded = []
        errors   = []

        for fname, msg in files_to_upload:
            log.info(f"Скачиваем {fname} из Telegram...")
            file_bytes = await msg.download_media(bytes)
            if file_bytes is None:
                errors.append((fname, "Не удалось скачать файл из Telegram"))
                continue

            content_b64 = base64.b64encode(file_bytes).decode()
            api_path    = f"/repos/{gh_user}/{repo_name}/contents/{fname}"

            sha = None
            s_check, d_check = await gh_get(gh_token, api_path)
            if s_check == 200:
                sha = d_check.get("sha")

            payload = {
                "message": f"Upload {fname} via Telegram Userbot",
                "content": content_b64,
            }
            if sha:
                payload["sha"] = sha

            status, data = await gh_put(gh_token, api_path, payload)

            if status in (200, 201):
                file_url = data.get("content", {}).get("html_url", "")
                uploaded.append((fname, file_url))
                log.info(f"Загружен {fname} → {file_url}")
            else:
                err_msg = data.get("message", f"HTTP {status}")
                errors.append((fname, f"HTTP {status}: {err_msg}"))
                log.warn(f"Ошибка загрузки {fname}: {err_msg}")

        # ── Формируем ответ (всё в цитате) ───────────────────────────────────
        parts = []

        if uploaded:
            n = len(uploaded)
            if n == 1:
                fn, url = uploaded[0]
                link = f'<a href="{url}">{fn}</a>' if url else fn
                parts.append(
                    f"✅ Успешно загружен {link} в репозиторий <code>{repo_name}</code>"
                )
            else:
                word = file_word(n)
                file_links = ", ".join(
                    f'<a href="{u}">{f}</a>' if u else f for f, u in uploaded
                )
                parts.append(
                    f"✅ Успешно загружено {n} {word} в репозиторий "
                    f"<code>{repo_name}</code>: {file_links}"
                )

        for fn, err in errors:
            parts.append(
                f"❌ Не удалось загрузить файл в репозиторий "
                f"<code>{repo_name}</code>\nОшибка: {err}"
            )

        text = "<blockquote>" + "\n".join(parts) + "</blockquote>"
        await event.respond(text, parse_mode="html")

    # ── .git repo create <name> ───────────────────────────────────────────────
    @client.on(events.NewMessage(
        pattern=rf"^{pat}git\s+repo\s+create\s+(\S+)$", outgoing=True))
    async def cmd_repo_create(event):
        await event.delete()
        repo_name = event.pattern_match.group(1)
        log.info(f"Команда .git repo create {repo_name}")

        status, data = await gh_post(gh_token, "/user/repos", {
            "name": repo_name,
            "private": False,
            "auto_init": True,
        })

        if status == 201:
            url = data.get("html_url", "")
            log.info(f"Репозиторий создан: {url}")
            await event.respond(
                f'<blockquote>✅ Репозиторий <code>{repo_name}</code> создан.\n'
                f'Ссылка: <a href="{url}">{url}</a></blockquote>',
                parse_mode="html"
            )
        else:
            err = data.get("message", f"HTTP {status}")
            log.warn(f"Ошибка создания репозитория {repo_name}: {err}")
            await event.respond(
                f"<blockquote>❌ Не удалось создать репозиторий <code>{repo_name}</code>\n"
                f"Ошибка: {err}</blockquote>",
                parse_mode="html"
            )

    # ── .git repo del <name> ──────────────────────────────────────────────────
    @client.on(events.NewMessage(
        pattern=rf"^{pat}git\s+repo\s+del\s+(\S+)$", outgoing=True))
    async def cmd_repo_del(event):
        await event.delete()
        repo_name = event.pattern_match.group(1)
        log.info(f"Команда .git repo del {repo_name}")

        status = await gh_delete(gh_token, f"/repos/{gh_user}/{repo_name}")

        if status == 204:
            log.info(f"Репозиторий {repo_name} удалён.")
            await event.respond(
                f"<blockquote>✅ Репозиторий <code>{repo_name}</code> удалён.</blockquote>",
                parse_mode="html"
            )
        elif status == 404:
            log.warn(f"Репозиторий {repo_name} не найден.")
            await event.respond(
                f"<blockquote>❌ Репозиторий <code>{repo_name}</code> не найден.\n"
                f"Ошибка: HTTP 404 — Not Found</blockquote>",
                parse_mode="html"
            )
        elif status == 403:
            log.warn(f"Нет прав на удаление {repo_name}.")
            await event.respond(
                f"<blockquote>❌ Нет прав на удаление <code>{repo_name}</code>.\n"
                f"Ошибка: HTTP 403 — Forbidden. Проверьте права токена (нужен scope: delete_repo)</blockquote>",
                parse_mode="html"
            )
        else:
            log.warn(f"Ошибка удаления {repo_name}: HTTP {status}")
            await event.respond(
                f"<blockquote>❌ Не удалось удалить репозиторий <code>{repo_name}</code>\n"
                f"Ошибка: HTTP {status}</blockquote>",
                parse_mode="html"
            )

    log.info(f"GitHub-модуль зарегистрирован. Команды: {PREFIX}git --help")

# ════════════════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════════════════

async def main():
    banner()

    log.init_file()
    log.info("Скрипт запущен.")

    check_single_instance()
    log.info(f"PID: {os.getpid()}")

    # ── GitHub конфиг (не зависит от метода авторизации) ─────────────────────
    gh_token, gh_user = setup_github()

    # ── Клиент — выбор метода авторизации ────────────────────────────────────
    saved_str_session = load_string_session()

    if saved_str_session:
        # Строка сессии уже есть — грузим ключи и стартуем без вопросов
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
            # Все остальные методы — api_id/api_hash вводятся в терминале
            api_id, api_hash = load_creds()
            if api_id and api_hash:
                log.info(f"Telegram API-ключи загружены из {CREDS_FILE}")
            else:
                print(f"{YE}Нужны API-ключи → https://my.telegram.org → «API development tools»{R}\n")
                api_id   = ask_sync("api_id")
                api_hash = ask_sync("api_hash")
                if not api_id or not api_hash:
                    log.error("api_id / api_hash не введены."); cleanup(); sys.exit(1)
                save_creds(api_id, api_hash)
                log.info("Telegram API-ключи сохранены.")

            if auth_method == "string":
                print(f"\n{DM}Строку сессии можно получить через вариант «3» или «4» (веб-панель).{R}\n")
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
    register_handlers(client, gh_token, gh_user)

    me = await client.get_me()
    print(f"\n{GR}{B}GitHub-модуль запущен.{R}  "
          f"Аккаунт: {B}{me.first_name}{R}  "
          f"GitHub: {B}{gh_user}{R}")
    print(f"{DM}Справка: {PREFIX}git --help   |   Ctrl+C для остановки{R}\n")

    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        log.info("Получен сигнал остановки.")
    finally:
        await client.disconnect()
        log.info("Соединение закрыто.")
        log.close()
        cleanup()


if __name__ == "__main__":
    asyncio.run(main())
