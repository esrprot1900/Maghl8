import sys
import types

# حل مشكلة imghdr
imghdr = types.ModuleType('imghdr')
imghdr.what = lambda file, h=None: None
sys.modules['imghdr'] = imghdr

from telegram import Bot
from datetime import datetime, timezone, timedelta
import json
import os
import time
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ==============================================
# الإعدادات من GitHub Secrets
# ==============================================
TOKEN = os.environ.get('TELEGRAM_TOKEN', '')

try:
    ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', '0'))
except Exception:
    ADMIN_CHAT_ID = 0

CHANNEL_ID     = os.environ.get('CHANNEL_ID', '')
GMAIL_USER     = os.environ.get('GMAIL_USER', '')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', '')
FORCE_PUBLISH  = os.environ.get('FORCE_PUBLISH', 'false').lower() == 'true'

try:
    CHECK_DAYS = int(os.environ.get('CHECK_DAYS', '7'))
except Exception:
    CHECK_DAYS = 7

try:
    GRACE_DAYS = int(os.environ.get('GRACE_DAYS', '3'))
except Exception:
    GRACE_DAYS = 3

# ==============================================
# المسارات
# ==============================================
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(BASE_DIR, "schedule.json")
STATE_FILE    = os.path.join(BASE_DIR, "state.json")
LOG_FILE      = os.path.join(BASE_DIR, "system_log.txt")

# ==============================================
# قوائم المستلمين
# ==============================================
EMAIL_LIST = [
    "taghreed.is.good@gmail.com",
    "cepeh37@gmail.com"
]

# ==============================================
# المنشورات الطارئة
# ==============================================
EMERGENCY_POSTS = [
    {
        "type": "text",
        "content": (
            "🚨 رسالة طارئة تلقائية\n\n"
            "📎 رابط الملف:\n"
            "https://drive.google.com/file/d/1omIp1NU3Mtu8HT082uOmVy-BCjysu8h1/view\n\n"
            "📱 تيليجرام: https://t.me/errorthem4\n"
            "👥 فيسبوك: https://www.facebook.com/khaledmohsultan"
        )
    }
]

# ==============================================
# التوقيت — يعمل من أي دولة تلقائياً
# ==============================================
def get_egypt_offset():
    """
    توقيت مصر دائماً بغض النظر عن موقعك
    صيف = UTC+3
    شتاء = UTC+2
    """
    now   = datetime.utcnow()
    year  = now.year
    start = datetime(year, 4, 30)
    while start.weekday() != 4:
        start -= timedelta(days=1)
    end = datetime(year, 10, 31)
    while end.weekday() != 4:
        end -= timedelta(days=1)
    return 3 if start <= now <= end else 2

def get_egypt_tz():
    return timezone(timedelta(hours=get_egypt_offset()))

def now_egypt():
    """الوقت الحالي بتوقيت مصر — من أي مكان في العالم"""
    return datetime.now(get_egypt_tz())

def now_utc():
    return datetime.now(timezone.utc)

# ==============================================
# السجل
# ==============================================
def log(msg):
    egypt = now_egypt().strftime('%Y-%m-%d %H:%M:%S')
    utc   = now_utc().strftime('%H:%M')
    line  = f"[مصر {egypt} | UTC {utc}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

# ==============================================
# تحميل وحفظ الجدول
# ==============================================
def load_schedule():
    try:
        if not os.path.exists(SCHEDULE_FILE):
            log("⚠️ schedule.json غير موجود")
            return []
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            log("⚠️ schedule.json فارغ")
            return []
        data = json.loads(content)
        log(f"📋 تم تحميل {len(data)} منشور")
        return data
    except Exception as e:
        log(f"❌ خطأ تحميل: {e}")
        return []

def save_schedule(data):
    try:
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log("💾 تم حفظ الجدول")
    except Exception as e:
        log(f"❌ خطأ حفظ: {e}")

# ==============================================
# تحميل وحفظ الحالة
# ==============================================
def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    state = {
        "last_checkin": now_egypt().isoformat(),
        "triggered":    False
    }
    save_state(state)
    return state

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"❌ خطأ حالة: {e}")

# ==============================================
# إرسال تيليجرام
# ==============================================
def send_telegram(bot, text, chat_id=None):
    try:
        target = chat_id or CHANNEL_ID
        if not target:
            log("❌ لا يوجد CHANNEL_ID")
            return False
        bot.send_message(chat_id=target, text=text)
        log(f"✅ تيليجرام → {target}")
        return True
    except Exception as e:
        log(f"❌ تيليجرام فشل: {e}")
        return False

# ==============================================
# إرسال إيميل
# ==============================================
def send_email(to, subject, body):
    if not to or '@' not in to or 'http' in to:
        log(f"⚠️ تجاهل — ليس إيميلاً: {to}")
        return False
    if not GMAIL_USER or not GMAIL_PASSWORD:
        log("⚠️ Gmail غير مضبوط")
        return False
    try:
        msg            = MIMEMultipart('alternative')
        msg['From']    = GMAIL_USER
        msg['To']      = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        log(f"✅ إيميل → {to}")
        return True
    except Exception as e:
        log(f"❌ إيميل فشل → {to}: {e}")
        return False

def send_emails_to_list(recipients, subject, body):
    for email in recipients:
        send_email(email, subject, body)
        time.sleep(3)

# ==============================================
# النشر الطارئ
# ==============================================
def emergency_publish(bot):
    log("🚨 بدء النشر الطارئ")
    if ADMIN_CHAT_ID:
        try:
            bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text="🚨 تم تفعيل مفتاح الرجل الميت"
            )
        except Exception:
            pass
    for post in EMERGENCY_POSTS:
        send_telegram(bot, post['content'])
        time.sleep(3)
    email_body = """
    <html><body dir="rtl" style="font-family:Arial">
    <p>هذه رسالة طارئة تلقائية.</p>
    <p>📱 تيليجرام: https://t.me/errorthem4</p>
    </body></html>
    """
    send_emails_to_list(EMAIL_LIST, "معلومات مهمة", email_body)
    log("✅ انتهى النشر الطارئ")

# ==============================================
# فحص مفتاح الرجل الميت
# ==============================================
def check_dms(bot):
    try:
        state       = load_state()
        last        = datetime.fromisoformat(state.get('last_checkin', now_egypt().isoformat()))
        now         = now_egypt()
        if last.tzinfo is None:
            last    = last.replace(tzinfo=get_egypt_tz())
        days_passed = (now - last).days
        total       = CHECK_DAYS + GRACE_DAYS
        log(f"⏱️ أيام منذ آخر تحقق: {days_passed}/{total}")
        if days_passed >= total and not state.get('triggered'):
            state['triggered'] = True
            save_state(state)
            emergency_publish(bot)
        elif days_passed >= CHECK_DAYS:
            if ADMIN_CHAT_ID:
                try:
                    bot.send_message(
                        chat_id=ADMIN_CHAT_ID,
                        text=(
                            f"⚠️ تذكير أسبوعي\n"
                            f"أرسل /alive للتأكيد\n"
                            f"أيام منذ آخر تحقق: {days_passed}\n"
                            f"لديك {GRACE_DAYS} أيام"
                        )
                    )
                except Exception:
                    pass
    except Exception as e:
        log(f"❌ خطأ مفتاح: {e}")

# ==============================================
# منع توقف GitHub بعد 60 يوم
# ==============================================
def keep_alive():
    try:
        subprocess.run(['git', 'config', 'user.email', 'auto@publisher.com'], capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'AutoPublisher'], capture_output=True)
        with open('last_run.txt', 'w', encoding='utf-8') as f:
            f.write(f"{now_egypt().strftime('%Y-%m-%d %H:%M:%S')} UTC+{get_egypt_offset()}")
        subprocess.run(['git', 'add', 'last_run.txt'], capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'auto: {now_egypt().strftime("%Y-%m-%d %H:%M")}'], capture_output=True)
        subprocess.run(['git', 'push'], capture_output=True)
        log("✅ GitHub kept alive")
    except Exception as e:
        log(f"⚠️ keep alive: {e}")

# ==============================================
# النشر المجدول
# ==============================================
def run_scheduled(bot):
    posts   = load_schedule()
    current = now_egypt()
    changed = False

    log(f"⏰ الوقت بمصر: {current.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"🌍 UTC: {now_utc().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"📍 UTC+{get_egypt_offset()} ({'صيفي' if get_egypt_offset()==3 else 'شتوي'})")
    log(f"⚡ FORCE_PUBLISH: {FORCE_PUBLISH}")

    for post in posts:
        if post.get('published', False):
            log(f"⏭️ تم نشره مسبقاً: {post.get('title','?')}")
            continue
        try:
            scheduled = datetime.strptime(post['time'], '%Y-%m-%d %H:%M')
            scheduled = scheduled.replace(tzinfo=get_egypt_tz())
            diff      = (current - scheduled).total_seconds()

            log(f"📅 {post.get('title','?')}: موعد={post['time']} | فارق={diff:.0f}ث")

            # النشر لو:
            # 1. حان وقته (خلال ساعة ماضية)
            # 2. أو FORCE_PUBLISH = true
            if FORCE_PUBLISH or (0 <= diff <= 3600):
                log(f"🔔 ينشر: {post.get('title','?')}")
                channels = post.get('channels', ['telegram'])
                success  = False

                if 'telegram' in channels:
                    if send_telegram(bot, post['content']):
                        success = True

                if 'email' in channels:
                    body = f"""<html><body dir='rtl' style='font-family:Arial'>
                    {post['content'].replace(chr(10),'<br>')}
                    </body></html>"""
                    send_emails_to_list(
                        EMAIL_LIST,
                        post.get('email_subject', post.get('title','')),
                        body
                    )
                    success = True

                if success:
                    post['published']    = True
                    post['published_at'] = current.isoformat()
                    changed              = True
                    log(f"✅ نُشر بنجاح: {post.get('title','?')}")
            else:
                log(f"⏳ لم يحن الوقت بعد: {post.get('title','?')}")

        except Exception as e:
            log(f"❌ خطأ: {e}")

    if changed:
        save_schedule(posts)

# ==============================================
# التشغيل الرئيسي
# ==============================================
def run_once():
    log("=" * 55)
    log("🚀 GitHub Actions — بدء التشغيل")
    log("=" * 55)

    if not TOKEN:
        log("❌ TELEGRAM_TOKEN مفقود من Secrets")
        sys.exit(1)

    if not CHANNEL_ID:
        log("❌ CHANNEL_ID مفقود من Secrets")
        sys.exit(1)

    try:
        bot = Bot(token=TOKEN)
        me  = bot.get_me()
        log(f"✅ اتصال تيليجرام نجح: @{me.username}")
    except Exception as e:
        log(f"❌ فشل الاتصال: {e}")
        sys.exit(1)

    run_scheduled(bot)
    check_dms(bot)
    keep_alive()

    log("=" * 55)
    log("✅ انتهى التشغيل")
    log("=" * 55)

if __name__ == "__main__":
    run_once()