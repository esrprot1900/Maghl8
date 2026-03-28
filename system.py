import sys
import types
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

# الإعدادات من GitHub Secrets

TOKEN          = os.environ.get('TELEGRAM_TOKEN', '')

try:
    ADMIN_CHAT_ID  = int(os.environ.get('ADMIN_CHAT_ID', '0'))
except:
    ADMIN_CHAT_ID=0
CHANNEL_ID     = os.environ.get('CHANNEL_ID', '')
GMAIL_USER     = os.environ.get('GMAIL_USER', '')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', '')

# للاختبار السريع = دقيقتان
# للاستخدام الحقيقي = غيّرهم لـ 7 و 3
CHECK_MINUTES  = int(os.environ.get('CHECK_MINUTES', '2'))
GRACE_MINUTES  = int(os.environ.get('GRACE_MINUTES', '2'))

# المسارات
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_FILE = os.path.join(BASE_DIR, "schedule.json")
STATE_FILE    = os.path.join(BASE_DIR, "state.json")
LOG_FILE      = os.path.join(BASE_DIR, "system_log.txt")

# قوائم المستلمين — إيميلات فقط
EMAIL_LIST = [
    "taghreed.is.good@gmail.com",
    "cepeh37@gmail.com"
]

# المنشورات الطارئة
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

# توقيت مصر التلقائي
def get_egypt_tz():
    now   = datetime.utcnow()
    year  = now.year
    start = datetime(year, 4, 30)
    while start.weekday() != 4:
        start -= timedelta(days=1)
    end = datetime(year, 10, 31)
    while end.weekday() != 4:
        end -= timedelta(days=1)
    if start <= now <= end:
        return timezone(timedelta(hours=3))
    return timezone(timedelta(hours=2))

def now_egypt():
    return datetime.now(get_egypt_tz())

# السجل
def log(msg):
    now  = now_egypt().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{now}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except:
        pass

# تحميل وحفظ الجدول
def load_schedule():
    try:
        if not os.path.exists(SCHEDULE_FILE):
            return []
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if not content:
            return []
        data = json.loads(content)
        log(f"📋 تم تحميل {len(data)} منشور")
        return data
    except Exception as e:
        log(f"خطأ تحميل: {e}")
        return []

def save_schedule(data):
    try:
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"خطأ حفظ: {e}")

# تحميل وحفظ الحالة
def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except:
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
        log(f"خطأ حالة: {e}")

# إرسال تيليجرام
def send_telegram(bot, text, chat_id=None):
    try:
        target = chat_id or CHANNEL_ID
        bot.send_message(chat_id=target, text=text)
        log(f"✅ تيليجرام نجح: {target}")
        return True
    except Exception as e:
        log(f"❌ تيليجرام فشل: {e}")
        return False

# إرسال إيميل
def send_email(to, subject, body):
    try:
        msg            = MIMEMultipart('alternative')
        msg['From']    = GMAIL_USER
        msg['To']      = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        log(f"✅ إيميل نجح: {to}")
        return True
    except Exception as e:
        log(f"❌ إيميل فشل {to}: {e}")
        return False

def send_emails_to_list(recipients, subject, body):
    for email in recipients:
        # تأكد أنه إيميل حقيقي وليس رابط
        if '@' in email:
            send_email(email, subject, body)
            time.sleep(3)
        else:
            log(f"⚠️ تجاهل — ليس إيميلاً: {email}")

# النشر الطارئ
def emergency_publish(bot):
    log("🚨 بدء النشر الطارئ الكامل")

    # إشعار شخصي
    try:
        bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="🚨 تم تفعيل مفتاح الرجل الميت\nبدء النشر الطارئ..."
        )
    except:
        pass

    # نشر على تيليجرام
    for post in EMERGENCY_POSTS:
        send_telegram(bot, post['content'])
        time.sleep(3)

    # إيميلات
    email_body = """
    <html><body dir="rtl" style="font-family:Arial">
    <p>السيد/ة الكريم/ة،</p>
    <p>هذه رسالة تلقائية تحتوي على معلومات مهمة.</p>
    <p>
    📱 تيليجرام: https://t.me/errorthem4<br>
    👥 فيسبوك: https://www.facebook.com/khaledmohsultan/
    </p>
    </body></html>
    """
    send_emails_to_list(
        EMAIL_LIST,
        "معلومات مهمة تستحق النشر",
        email_body
    )
    log("✅ انتهى النشر الطارئ")

# فحص مفتاح الرجل الميت — بالدقائق للاختبار
def check_dms(bot):
    try:
        state         = load_state()
        last          = datetime.fromisoformat(state['last_checkin'])
        now           = now_egypt()
        if last.tzinfo is None:
            last      = last.replace(tzinfo=get_egypt_tz())
        minutes_passed = (now - last).total_seconds() / 60
        total_minutes  = CHECK_MINUTES + GRACE_MINUTES

        log(f"⏱️ دقائق منذ آخر تحقق: {minutes_passed:.1f}/{total_minutes}")

        if minutes_passed >= total_minutes and not state.get('triggered'):
            state['triggered'] = True
            save_state(state)
            log("🚨 انتهت المدة — تفعيل النشر الطارئ")
            emergency_publish(bot)

        elif minutes_passed >= CHECK_MINUTES:
            try:
                bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(
                        f"⚠️ تذكير اختبار\n"
                        f"دقائق منذ آخر تحقق: {minutes_passed:.1f}\n"
                        f"أرسل /alive للتأكيد"
                    )
                )
            except:
                pass

    except Exception as e:
        log(f"خطأ مفتاح: {e}")

# منع توقف GitHub بعد 60 يوم
def keep_alive():
    try:
        subprocess.run(
            ['git', 'config', 'user.email', 'auto@publisher.com'],
            capture_output=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', 'AutoPublisher'],
            capture_output=True
        )
        with open('last_run.txt', 'w') as f:
            f.write(now_egypt().isoformat())
        subprocess.run(['git', 'add', 'last_run.txt'], capture_output=True)
        subprocess.run(
            ['git', 'commit', '-m',
             f'auto: {now_egypt().strftime("%Y-%m-%d %H:%M")}'],
            capture_output=True
        )
        subprocess.run(['git', 'push'], capture_output=True)
        log("✅ GitHub kept alive")
    except Exception as e:
        log(f"خطأ keep alive: {e}")

# النشر المجدول
def run_scheduled(bot):
    posts   = load_schedule()
    current = now_egypt()
    changed = False

    for post in posts:
        if post.get('published', False):
            continue
        try:
            scheduled = datetime.strptime(
                post['time'], '%Y-%m-%d %H:%M'
            )
            scheduled = scheduled.replace(tzinfo=get_egypt_tz())
            diff      = (current - scheduled).total_seconds()

            # نافذة ساعة كاملة
            if 0 <= diff <= 3600:
                log(f"🔔 ينشر: {post['title']}")
                channels = post.get('channels', ['telegram'])

                if 'telegram' in channels:
                    if send_telegram(bot, post['content']):
                        post['published']    = True
                        post['published_at'] = current.isoformat()
                        changed = True

                if 'email' in channels:
                    send_emails_to_list(
                        EMAIL_LIST,
                        post.get('email_subject', post['title']),
                        f"<html><body dir='rtl'>{post['content']}</body></html>"
                    )

        except Exception as e:
            log(f"خطأ نشر: {e}")

    if changed:
        save_schedule(posts)

# التشغيل الرئيسي
def run_once():
    log("=" * 50)
    log("🔄 تشغيل من GitHub Actions")
    log(f"⏰ {now_egypt().strftime('%Y-%m-%d %H:%M:%S')}")

    if not TOKEN:
        log("❌ لا يوجد TELEGRAM_TOKEN — تحقق من GitHub Secrets")
        return

    bot = Bot(token=TOKEN)

    # 1 — النشر المجدول
    run_scheduled(bot)

    # 2 — فحص مفتاح الرجل الميت
    check_dms(bot)

    # 3 — منع توقف GitHub
    keep_alive()

    log("✅ انتهى التشغيل بنجاح")
    log("=" * 50)

if __name__ == "__main__":
    run_once()