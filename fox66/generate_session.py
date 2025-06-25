# 파일명: generate_session.py (النسخة المطورة)

import asyncio
from telethon import TelegramClient

ACCOUNTS_FILE = "accounts.txt"

def save_account_to_file(session_string, api_id, api_hash):
    """
    تقوم هذه الدالة بحفظ بيانات الحساب في ملف accounts.txt
    وتتأكد من عدم وجود تكرار.
    """
    line_to_add = f"{session_string}|{api_id}|{api_hash}"
    
    # قراءة الملف أولاً للتحقق من وجود الحساب
    try:
        with open(ACCOUNTS_FILE, "r") as f:
            for line in f:
                # نتحقق من الـ api_id لتجنب تكرار نفس الحساب
                if str(api_id) in line:
                    print(f"⚠️ تحذير: الحساب صاحب الـ API ID ({api_id}) موجود بالفعل في الملف. تم التخطي.")
                    return False
    except FileNotFoundError:
        # إذا لم يكن الملف موجودًا، سيتم إنشاؤه
        pass

    # إضافة الحساب الجديد في سطر جديد
    with open(ACCOUNTS_FILE, "a") as f:
        f.write(line_to_add + "\n")
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
            # client.start() هو الذي يبدأ عملية تسجيل الدخول التفاعلية
            # إذا كان الحساب مسجلاً بالفعل، فلن يطلب شيئًا
            await client.start()
            
            # التأكد من أن تسجيل الدخول تم بنجاح
            if not await client.is_user_authorized():
                print("❌ فشل تسجيل الدخول. قد تكون أدخلت بيانات غير صحيحة.")
                # client.send_code_request() و client.sign_in() يمكن استخدامهما هنا لمزيد من التحكم
                # ولكن الطريقة التلقائية في .start() كافية لمعظم الحالات.
                return
                
            print("\n✅ تم تسجيل الدخول بنجاح!")
            
            # الحصول على session string
            session_string = client.session.save()
            
            # حفظ البيانات في الملف
            save_account_to_file(session_string, api_id, api_hash)

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
        
        # سؤال المستخدم إذا كان يريد إضافة حساب آخر
        another = input("\n🤔 هل تريد إضافة حساب آخر؟ (اكتب 'نعم' للمتابعة أو اضغط Enter للخروج): ").lower()
        if another not in ['نعم', 'yes', 'y']:
            break
            
    print("\n🎉 انتهت عملية إضافة الحسابات. يمكنك الآن تشغيل البوت الرئيسي.")

if __name__ == "__main__":
    # هذا السطر ضروري في ويندوز لتجنب خطأ معين مع asyncio
    if asyncio.get_event_loop().is_running():
         asyncio.get_event_loop().create_task(main())
    else:
         asyncio.run(main())