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

TOKEN = os.environ.get('TELEGRAM_TOKEN', '') or "8673635775:AAFO7n_IewlUNJ4Z7_JGisaiSNBOrjM9mrs"
try:
    _admin  = os.environ.get('ADMIN_CHAT_ID', '0') or "@errorthem4"
    ADMIN_CHAT_ID = int(_admin)
except Exception:
    ADMIN_CHAT_ID =0
    
CHANNEL_ID = os.environ.get('CHANNEL_ID', '') or "@errorsthem"
GMAIL_USER = os.environ.get('GMAIL_USER', '') or "try0t0000@gmail.com"
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD', '') or "vexb idgj pihv cooh"

FORCE_PUBLISH = os.environ.get('FORCE_PUBLISH', 'false').lower() == 'true'

try:
    CHECK_DAYS = int(os.environ.get('CHECK_DAYS', '7'))
except Exception:
    CHECK_DAYS = 7

try:
    GRACE_DAYS = int(os.environ.get('GRACE_DAYS', '3'))
except Exception:
    GRACE_DAYS = 3
    
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
            "📱 تيليجرام: @errorthem4\n"
            "👥 فيسبوك: https://www.facebook.com/khaledmohsultan"
        )
    }
]

def get_egypt_offset():
    
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
    return datetime.now(get_egypt_tz())


def now_utc(): 
    return datetime.now(timezone.utc)

# السجل
def log(msg):
    egypt = now_egypt().strftime('%Y-%m-%d %H:%M:%S')  
    utc   = now_utc().strftime('%H:%M')                
    line  = f"[مصر {egypt} | UTC {utc}] {msg}"
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
            log("⚠️ schedule.json غير موجود")
            return []
        
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            log("⚠️ schedule.json فارغ")
            return []
        
        data = json.loads(content)
        log(f"📋 تم تحميل {len(data)} منشور من schedule.json")
        return data
    
    except Exception as e:
        log(f"❌ خطأ في قراءة schedule.json: {e}")
        return []
    

def save_schedule(data):
    try:
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log("💾 تم حفظ الجدول")
    except Exception as e:
        log(f"❌ خطأ في حفظ schedule.json: {e}")


# القسم 9 — دوال الحالة مفتاح الرجل الميت
def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass

    
    state = {"last_checkin": now_egypt().isoformat(), "triggered": False}
    save_state(state)
    return state

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        log(f"❌ خطأ حفظ الحالة: {e}")


# إرسال تيليجرام
def send_telegram(bot, text, chat_id=None):
    try:
        target = chat_id or CHANNEL_ID  # إذا لم يُحدد، استخدم القناة
        
        if not target:
            log("❌ لا يوجد CHANNEL_ID — تحقق من الإعدادات")
            return False
        
        bot.send_message(chat_id=target, text=text)
        log(f"✅ تيليجرام نجح → {target}")
        return True
    
    except Exception as e:
        log(f"❌ تيليجرام فشل: {e}")
        return False

# إرسال إيميل
def send_email(to, subject, body):
    if not to or '@' not in to or 'http' in to:
        log(f"⚠️ تجاهل — ليس إيميلاً: {to}")
        return False
    
    # تحقق أن Gmail مضبوط
    if not GMAIL_USER or not GMAIL_PASSWORD or 'ضع' in GMAIL_USER:
        log("⚠️ Gmail غير مضبوط — تجاهل")
        return False
    
    try:
        # بناء رسالة الإيميل
        msg            = MIMEMultipart('alternative')
        msg['From']    = GMAIL_USER    # المرسل
        msg['To']      = to            # المستلم
        msg['Subject'] = subject       # الموضوع
        msg.attach(MIMEText(body, 'html', 'utf-8'))  # المحتوى HTML
        
        # الاتصال بـ Gmail وإرسال الرسالة
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.send_message(msg)
        
        log(f"✅ إيميل نجح → {to}")
        return True
    
    except Exception as e:
        log(f"❌ إيميل فشل → {to}: {e}")
        return False

def send_emails_to_list(recipients, subject, body):
    for email in recipients:
        send_email(email, subject, body)
        time.sleep(20)  # انتظر 3 ثواني

# النشر الطارئ
def emergency_publish(bot):
    log("🚨 بدء النشر الطارئ الكامل")
    
# إشعار شخصي أولاً
    if ADMIN_CHAT_ID:
        try:
            bot.send_message(chat_id=ADMIN_CHAT_ID, text="🚨 تم تفعيل مفتاح الرجل الميت\nبدء النشر الطارئ...")
        except Exception:
            pass
    
    # نشر المنشورات الطارئة على تيليجرام
    for post in EMERGENCY_POSTS:
        send_telegram(bot, post['content'])
        time.sleep(20)

    # إيميلات
    email_body = """
    <html><body dir="rtl" style="font-family:Arial;font-size:14px">
    <p>السيد/ة الكريم/ة،</p>
    <p>هذه رسالة تلقائية تحتوي على معلومات مهمة.</p>
    <p>
    📱 تيليجرام: @errorthem4<br>
    👥 فيسبوك: https://www.facebook.com/khaledmohsultan/
    </p>
    </body></html>
    """
    send_emails_to_list(EMAIL_LIST, "رسالة طارئة مهمة", email_body)
    log("✅ انتهى النشر الطارئ")

# فحص مفتاح الرجل الميت — بالدقائق للاختبار
def check_dms(bot):
    try:
        state   = load_state()
        last_str= state.get('last_checkin', now_egypt().isoformat())
        last    = datetime.fromisoformat(last_str)
        now     = now_egypt()
        
        # تأكد أن التواريخ بنفس المنطقة الزمنية
        if last.tzinfo is None:
            last = last.replace(tzinfo=get_egypt_tz())
        
        days_passed = (now - last).days  # كم يوم مضى
        total_days  = CHECK_DAYS + GRACE_DAYS
        
        log(f"⏱️ أيام منذ آخر تحقق: {days_passed}/{total_days}")

        if days_passed >= total_days and not state.get('triggered'):
            # انتهت المدة — تفعيل النشر الطارئ
            state['triggered'] = True
            save_state(state)
            emergency_publish(bot)
        
        elif days_passed >= CHECK_DAYS:
            # حان وقت التذكير الأسبوعي
            if ADMIN_CHAT_ID:
                try:
                    bot.send_message(chat_id=ADMIN_CHAT_ID, text=(
                            f"⚠️ تذكير أسبوعي\n\n"
                            f"هل أنت بخير؟\n"
                            f"أرسل /alive للتأكيد\n\n"
                            f"أيام منذ آخر تحقق: {days_passed}\n"
                            f"لديك {GRACE_DAYS} أيام قبل النشر الطارئ"
                        ))
                except Exception:
                    pass
    
    except Exception as e:
        log(f"❌ خطأ مفتاح الرجل الميت: {e}")

# منع توقف GitHub بعد 60 يوم
def keep_alive():
    try:
        # إعداد git
        subprocess.run(['git', 'config', 'user.email', 'auto@publisher.com'],
            capture_output=True)
        
        subprocess.run(['git', 'config', 'user.name', 'AutoPublisher'],
            capture_output=True)
        
        # كتابة ملف صغير بوقت آخر تشغيل
        with open('last_run.txt', 'w', encoding='utf-8') as f:
            f.write(f"آخر تشغيل: {now_egypt().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"UTC+{get_egypt_offset()}")
        
        # GitHub رفع التغيير لـ 
        subprocess.run(['git', 'add', 'last_run.txt'], capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'auto:{now_egypt().strftime("%Y-%m-%d %H:%M")}'],
            capture_output=True
        )
        subprocess.run(['git', 'push'], capture_output=True)
        log("✅ GitHub kept alive")
    
    except Exception as e:
        log(f"⚠️ keep alive: {e}")

# النشر المجدول
def run_scheduled(bot):
    posts   = load_schedule()
    current = now_egypt()
    changed = False            # هل تغيّر شيء؟ (لتحديد إذا نحفظ أم لا)
    
    # طباعة معلومات التوقيت للتشخيص
    log(f"⏰ وقت مصر الآن: {current.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"🌍 UTC الآن: {now_utc().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"📍 الفارق: UTC+{get_egypt_offset()} ({'صيفي' if get_egypt_offset()==3 else 'شتوي'})")
    log(f"⚡ FORCE_PUBLISH: {FORCE_PUBLISH}")
    
    if not posts:
        log("📭 لا توجد منشورات في schedule.json")
        return
    
    for post in posts:
        # تخطي المنشورات المنشورة مسبقاً
        if post.get('published', False):
            log(f"⏭️ تم نشره مسبقاً: {post.get('title', '?')}")
            continue
        
        try:
            scheduled = datetime.strptime(post['time'], '%Y-%m-%d %H:%M')
            scheduled = scheduled.replace(tzinfo=get_egypt_tz())
            diff = (current - scheduled).total_seconds()
            
            log(
                f"📅 {post.get('title','?')}: "
                f"مجدول الساعة {post['time']} | "
                f"فارق {diff:.0f} ثانية "
                f"({'حان' if diff >= 0 else 'لم يحن بعد'})"
            )
            
            should_publish = FORCE_PUBLISH or (0 <= diff <= 3600)
            
            if should_publish:
                log(f"🔔 جاري النشر: {post.get('title','?')}")
                channels = post.get('channels', ['telegram'])
                success  = False

                # نشر على تيليجرام
                if 'telegram' in channels:
                    if send_telegram(bot, post['content']):
                        success = True
                        log(f"✅ تيليجرام: {post.get('title','?')}")
                
                # إرسال إيميل
                if 'email' in channels:
                    email_body = (
                        f"<html><body dir='rtl' style='font-family:Arial'>"
                        f"{post['content'].replace(chr(10), '<br>')}"
                        f"</body></html>")
                    send_emails_to_list(EMAIL_LIST,
                        post.get('email_subject', post.get('title', 'رسالة مهمة')), email_body)
                    
                    success = True
                
                # تحديث حالة المنشور لـ published: true
                if success:
                    post['published'] = True
                    post['published_at'] = current.isoformat()
                    changed = True
                    log(f"✅ نُشر بنجاح: {post.get('title','?')}")
            
            else:
                log(f"⏳ لم يحن وقته بعد: {post.get('title','?')}")
        
        except Exception as e:
            log(f"❌ خطأ في معالجة المنشور: {e}")
    
    # حفظ التغييرات فقط إذا نُشر شيء
    if changed:
        save_schedule(posts)


# القسم 16 — التشغيل الرئيسي
def run_once():
    log("=" * 60)
    log("🚀 بدء التشغيل من GitHub Actions")
    log(f"⏰ توقيت مصر: {now_egypt().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"🌍 توقيت UTC: {now_utc().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)
    
    # التحقق من وجود التوكن
    if not TOKEN or 'ضع' in TOKEN:
        log("❌ TELEGRAM_TOKEN غير مضبوط")
        log("   أضفه في GitHub Secrets أو في الكود مباشرة")
        sys.exit(1)  # إيقاف البرنامج برمز خطأ 1
    
    # التحقق من وجود قناة التيليجرام
    if not CHANNEL_ID or 'اسم' in CHANNEL_ID:
        log("❌ CHANNEL_ID غير مضبوط")
        log("   أضفه في GitHub Secrets أو في الكود مباشرة")
        sys.exit(1)
    
    # اختبار الاتصال بتيليجرام
    try:
        bot = Bot(token=TOKEN)      # إنشاء كائن البوت
        me = bot.get_me()          # طلب معلومات البوت
        log(f"✅ اتصال تيليجرام نجح: @{me.username}")
        
    except Exception as e:
        log(f"❌ فشل الاتصال بتيليجرام: {e}")
        log("   تحقق من صحة TELEGRAM_TOKEN")
        sys.exit(1)
    
    # 1 — النشر المجدول
    log("\n--- القسم 1: النشر المجدول ---")
    run_scheduled(bot)
    
    # 2 — فحص مفتاح الرجل الميت
    log("\n--- القسم 2: مفتاح الرجل الميت ---")
    check_dms(bot)
    
    # 3 — Keep Alive
    log("\n--- القسم 3: Keep Alive ---")
    keep_alive()
    
    log("=" * 60)
    log("✅ انتهى التشغيل بنجاح")
    log("=" * 60)

# نقطة البداية
# ============================================================
# if __name__ == "__main__" تعني:
# "شغّل هذا الكود فقط لو هذا الملف نفسه هو الذي يُشغَّل"
# وليس لو استُدعي من ملف آخر

if __name__ == "__main__":
    run_once()