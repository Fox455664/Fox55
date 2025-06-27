# 파일명: generate_session.py (النسخة المطورة والمعدلة لحفظ JSON)

import asyncio
import json
from telethon import TelegramClient

# تم تغيير اسم الملف إلى .json
ACCOUNTS_FILE = "accounts.json"

def save_account_to_json(new_account_data):
    """
    تقوم هذه الدالة بحفظ بيانات الحساب في ملف accounts.json
    وتتأكد من عدم وجود تكرار بناءً على الـ api_id.
    """
    accounts = []
    # الخطوة 1: قراءة الملف الموجود إن وجد
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            accounts = json.load(f)
            # التأكد من أن الملف يحتوي على قائمة
            if not isinstance(accounts, list):
                print(f"⚠️ تحذير: ملف '{ACCOUNTS_FILE}' لا يحتوي على التنسيق الصحيح (قائمة). سيتم إعادة كتابته.")
                accounts = []
    except (FileNotFoundError, json.JSONDecodeError):
        # إذا لم يكن الملف موجودًا أو فارغًا، سنبدأ بقائمة جديدة
        pass

    # الخطوة 2: التحقق من وجود الحساب بالفعل
    api_id_to_check = new_account_data["api_id"]
    account_exists = any(acc.get("api_id") == api_id_to_check for acc in accounts)

    if account_exists:
        print(f"⚠️ تحذير: الحساب صاحب الـ API ID ({api_id_to_check}) موجود بالفعل في الملف. تم التخطي.")
        return False

    # الخطوة 3: إضافة الحساب الجديد إلى القائمة
    accounts.append(new_account_data)

    # الخطوة 4: كتابة القائمة المحدثة بالكامل إلى الملف
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=4) # indent=4 يجعل الملف قابلاً للقراءة

    print(f"✅ تم حفظ الحساب بنجاح في ملف '{ACCOUNTS_FILE}'.")
    return True

async def generate_and_save_session():
    """
    الدالة الرئيسية التي تدير عملية إنشاء وحفظ جلسة واحدة.
    """
    print("\n--- ➕ إضافة حساب جديد ---")
    try:
        api_id = int(input("🔑 أدخل الـ API ID الخاص بالحساب الجديد: "))
        api_hash = input("🔒 أدخل الـ API HASH الخاص بالحساب الجديد: ")
    except ValueError:
        print("❌ خطأ: الـ API ID يجب أن يكون رقمًا. يرجى المحاولة مرة أخرى.")
        return

    # استخدام الذاكرة لتجنب إنشاء ملفات .session غير مرغوب فيها
    async with TelegramClient(':memory:', api_id, api_hash) as client:
        try:
            await client.start()
            
            if not await client.is_user_authorized():
                print("❌ فشل تسجيل الدخول. قد تكون أدخلت بيانات غير صحيحة.")
                return
                
            print("\n✅ تم تسجيل الدخول بنجاح!")
            
            # الحصول على البيانات المطلوبة
            session_string = client.session.save()
            me = await client.get_me()
            
            # تجهيز قاموس البيانات للحفظ
            new_account_data = {
                "contributor_id": me.id,
                "api_id": api_id,
                "api_hash": api_hash,
                "session_string": session_string
            }
            
            # حفظ البيانات في ملف JSON
            save_account_to_json(new_account_data)

        except Exception as e:
            print(f"❌ حدث خطأ أثناء محاولة الاتصال أو تسجيل الدخول: {e}")

async def main():
    """
    المشغل الرئيسي الذي يسمح بإضافة حسابات متعددة.
    """
    print("--- 🚀 مولد الجلسات التلقائي V2 🚀 ---")
    print(f"سيتم حفظ الحسابات تلقائياً في ملف '{ACCOUNTS_FILE}'.")
    
    while True:
        await generate_and_save_session()
        
        another = input("\n🤔 هل تريد إضافة حساب آخر؟ (اكتب 'نعم' للمتابعة أو اضغط Enter للخروج): ").lower()
        if another not in ['نعم', 'yes', 'y']:
            break
            
    print("\n🎉 انتهت عملية إضافة الحسابات. يمكنك الآن تشغيل البوت الرئيسي.")

if __name__ == "__main__":
    # DeprecationWarning: There is no current event loop
    # هذا الكود يعالج التحذير الذي كان يظهر
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = None

    if loop and loop.is_running():
        loop.create_task(main())
    else:
        asyncio.run(main())
