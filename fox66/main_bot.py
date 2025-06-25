# 파일명: main_bot.py (النسخة النهائية مع مرشد الحصول على API)

import asyncio
import json
import random
import os
import sys
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantsAdmins
from telethon import events, Button

# --- استيراد الإعدادات ---
try:
    from bot_config import *
except ImportError:
    print("❌ خطأ: ملف bot_config.py غير موجود أو لم يتم إعداده بشكل صحيح."); exit()

# --- إعدادات الملفات ---
ACCOUNTS_FILE = "accounts.json"
PROXIES_FILE = "proxies.txt"
PROCESSED_USERS_FILE = "processed_users.txt"
QUEUE_FILE = "queue.json"
SETTINGS_FILE = "settings.json"

# --- متغيرات عالمية ---
transfer_in_progress = False
user_states = {}
bot_client = TelegramClient('bot_session', ADMIN_API_ID, ADMIN_API_HASH)

# --- دوال المساعدة ---
def load_json(filename, default_data=None):
    if default_data is None: default_data = []
    if not os.path.exists(filename) or os.path.getsize(filename) == 0: return default_data
    try:
        with open(filename, 'r', encoding='utf-8') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return default_data

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

def load_accounts(): return load_json(ACCOUNTS_FILE, default_data=[])

def save_account(contributor_id, api_id, api_hash, session_string):
    accounts = load_accounts()
    if not any(acc['api_id'] == api_id for acc in accounts):
        accounts.append({"contributor_id": contributor_id, "api_id": api_id, "api_hash": api_hash, "session_string": session_string})
        save_json(ACCOUNTS_FILE, accounts); return True
    return False

def load_processed_users():
    try:
        with open(PROCESSED_USERS_FILE, "r") as f: return {int(line.strip()) for line in f.readlines()}
    except FileNotFoundError: return set()

def save_processed_user(user_id):
    with open(PROCESSED_USERS_FILE, "a") as f: f.write(f"{user_id}\n")

def get_random_proxy():
    try:
        with open(PROXIES_FILE, "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
        if not proxies: return None
        random_proxy_line = random.choice(proxies)
        parts = random_proxy_line.split(':')
        scheme = parts[0]
        if '@' in parts[1]:
            user_pass, host = parts[1].split('@', 1)
            user, password = user_pass.split(':', 1)
            port = int(parts[2])
        else:
            host = parts[1]; port = int(parts[2])
            user = parts[3] if len(parts) > 3 and parts[3] else None
            password = parts[4] if len(parts) > 4 and parts[4] else None
        return {"scheme": scheme, "hostname": host, "port": port, "username": user, "password": password}
    except (FileNotFoundError, IndexError, ValueError):
        return None

async def check_account_status(account_info):
    proxy_data = get_random_proxy()
    temp_client = TelegramClient(StringSession(account_info['session_string']), account_info['api_id'], account_info['api_hash'], proxy=proxy_data)
    try:
        await temp_client.connect()
        if await temp_client.is_user_authorized(): return "✅ فعال"
        else: return "❌ يحتاج لتسجيل"
    except Exception: return "⚠️ خطأ"
    finally:
        if temp_client.is_connected(): await temp_client.disconnect()

# --- محرك النقل ---
async def transfer_engine(client, from_group, to_group, max_adds, processed_users, status_message=None, terminal_mode=False):
    added_count = 0
    try:
        if terminal_mode: print(f"🔍 [TERMINAL] سحب الأعضاء من {from_group}...")
        participants = await client.get_participants(from_group, limit=3000)
        random.shuffle(participants)
        for user in participants:
            if added_count >= max_adds: break
            if user.id in processed_users or user.bot or user.deleted: continue
            try:
                await client(functions.channels.InviteToChannelRequest(channel=to_group, users=[user]))
                added_count += 1; processed_users.add(user.id); save_processed_user(user.id)
                if terminal_mode: print(f"➕ [{added_count}/{max_adds}] تمت إضافة: {user.first_name}")
                elif status_message and added_count % 5 == 0: await status_message.edit(f"⏳ جاري النقل... تمت إضافة **{added_count}** عضو.")
                await asyncio.sleep(random.uniform(45, 100))
            except errors.FloodWaitError as e: await asyncio.sleep(e.seconds + 20)
            except (errors.UserPrivacyRestrictedError, errors.UserNotMutualContactError, errors.UserChannelsTooMuchError): processed_users.add(user.id); save_processed_user(user.id)
            except Exception: processed_users.add(user.id); save_processed_user(user.id)
    except Exception as e:
        error_msg = f"🚨 خطأ في المحرك: {e}"
        if terminal_mode: print(error_msg)
        elif status_message: await status_message.edit(error_msg)
    return added_count

# --- دوال البوت ---
@bot_client.on(events.NewMessage(pattern='/bot_off', from_users=ADMIN_USER_ID))
async def bot_off_handler(event):
    save_json(SETTINGS_FILE, {"is_active": False}); await event.reply("🔴 **تم إيقاف البوت.**")

@bot_client.on(events.NewMessage(pattern='/bot_on', from_users=ADMIN_USER_ID))
async def bot_on_handler(event):
    save_json(SETTINGS_FILE, {"is_active": True}); await event.reply("🟢 **تم تشغيل البوت.**")

@bot_client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await event.reply(WELCOME_MESSAGE, buttons=[
        [Button.inline("❓ كيفية الحصول على API", "get_api_guide")],
        [Button.inline("➕ إضافة حساب جديد", "add_account"), Button.inline("👤 حساباتي", "my_accounts")],
        [Button.inline("🔄 بدء عملية نقل", "new_transfer")]
    ])

@bot_client.on(events.CallbackQuery(data='get_api_guide'))
async def get_api_guide_handler(event):
    await event.edit(API_GUIDE_MESSAGE, buttons=[Button.url("🌐 افتح موقع تيليجرام", "https://my.telegram.org/"), Button.inline("✅ فهمت، لنضف الحساب", "add_account")], link_preview=False)

@bot_client.on(events.CallbackQuery(data='my_accounts'))
async def my_accounts_handler(event):
    user_id = event.sender_id
    accounts = load_accounts()
    user_accounts = [acc for acc in accounts if acc.get('contributor_id') == user_id]
    if not user_accounts: await event.answer(NO_ACCOUNTS_MESSAGE, alert=True); return
    status_msg = await event.edit(CHECKING_ACCOUNTS_MESSAGE)
    tasks = [check_account_status(acc) for acc in user_accounts]
    results = await asyncio.gather(*tasks)
    response_text = MY_ACCOUNTS_HEADER
    for i, account in enumerate(user_accounts): response_text += f"**- الحساب {i+1}** (ID: `{account['api_id']}`) - **الحالة:** {results[i]}\n"
    await status_msg.edit(response_text, buttons=[Button.inline("➕ إضافة حساب آخر", "add_account")])

@bot_client.on(events.CallbackQuery(data='new_transfer'))
async def new_transfer_callback(event):
    user_id = event.sender_id
    settings = load_json(SETTINGS_FILE, default_data={"is_active": True})
    if not settings.get("is_active", True) and user_id != ADMIN_USER_ID: await event.answer(BOT_MAINTENANCE_MESSAGE, alert=True); return
    try:
        user_entity = await bot_client.get_entity(user_id)
        await bot_client(functions.channels.GetParticipantRequest(channel=TARGET_CHANNEL, participant=user_entity))
    except (errors.UserNotParticipantError, errors.ChannelPrivateError, ValueError): await event.answer(FORCE_SUB_MESSAGE, alert=True); return
    accounts = load_accounts()
    if not any(acc.get('contributor_id') == user_id for acc in accounts) and user_id != ADMIN_USER_ID: await event.answer(REQUIRE_ACCOUNT_MESSAGE, alert=True); return
    global transfer_in_progress
    if transfer_in_progress: await event.answer("⏳ يوجد عملية نقل قيد التنفيذ حالياً.", alert=True); return
    user_states[user_id] = "awaiting_from_group"
    await event.edit("ممتاز! أنت مساهم.\n\n**الخطوة 1:** أرسل يوزر المجموعة **المصدر**.")

@bot_client.on(events.CallbackQuery(data='add_account'))
async def add_account_start(event):
    user_states[event.sender_id] = {"state": "awaiting_api_id"}
    await event.edit(ADD_ACCOUNT_INTRO)

@bot_client.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id
    if user_id not in user_states or not event.text or event.text.startswith('/'): return
    if user_id == ADMIN_USER_ID and event.text.lower() in ['/bot_on', '/bot_off']: return
    state_data = user_states.get(user_id)
    if isinstance(state_data, dict) and "state" in state_data:
        current_state = state_data["state"]
        if current_state == "awaiting_api_id":
            try:
                state_data['api_id'] = int(event.text)
                state_data['state'] = "awaiting_api_hash"
                await event.reply("✅ تم. الآن أرسل **API HASH**.")
            except ValueError: await event.reply("❌ خطأ: الـ API ID يجب أن يكون رقماً.")
        elif current_state == "awaiting_api_hash":
            state_data['api_hash'] = event.text
            state_data['state'] = "awaiting_phone"
            await event.reply("✅ تم. الآن أرسل **رقم الهاتف** مع رمز الدولة.")
        elif current_state == "awaiting_phone":
            state_data['phone'] = event.text
            proxy_data = get_random_proxy()
            temp_client = TelegramClient(StringSession(), state_data['api_id'], state_data['api_hash'], proxy=proxy_data)
            try:
                await temp_client.connect()
                sent_code = await temp_client.send_code_request(state_data['phone'])
                state_data['phone_code_hash'] = sent_code.phone_code_hash
                state_data['state'] = "awaiting_code"
                state_data['client'] = temp_client
                await event.reply(f"✅ تم إرسال الكود. أرسله هنا.")
            except Exception as e: await event.reply(f"❌ خطأ: `{e}`\n\nابدأ من جديد /start."); del user_states[user_id]
        elif current_state == "awaiting_code":
            code = event.text; temp_client = state_data['client']
            try:
                await temp_client.sign_in(state_data['phone'], code, phone_code_hash=state_data['phone_code_hash'])
                session_str = temp_client.session.save()
                save_account(user_id, state_data['api_id'], state_data['api_hash'], session_str)
                await event.reply("🎉 **نجاح!** تم إضافة حسابك. يمكنك الآن استخدام البوت أو إضافة المزيد.")
                del user_states[user_id]
            except errors.SessionPasswordNeededError: state_data['state'] = "awaiting_password"; await event.reply("🔑 حسابك محمي بكلمة مرور. أرسلها الآن.")
            except Exception as e: await event.reply(f"❌ خطأ: `{e}`."); del user_states[user_id]
            finally:
                if temp_client.is_connected(): await temp_client.disconnect(); await event.delete()
        elif current_state == "awaiting_password":
            password = event.text; temp_client = state_data['client']
            try:
                await temp_client.sign_in(password=password)
                session_str = temp_client.session.save()
                save_account(user_id, state_data['api_id'], state_data['api_hash'], session_str)
                await event.reply("🎉 **نجاح!** تم إضافة حسابك.")
                del user_states[user_id]
            except Exception as e: await event.reply(f"❌ خطأ: `{e}`.")
            finally:
                if temp_client.is_connected(): await temp_client.disconnect(); await event.delete()
        if user_id in user_states: user_states[user_id] = state_data
    elif state_data == "awaiting_from_group":
        user_states[user_id] = {"state": "awaiting_to_group", "from_group": event.text}
        await event.reply("**الخطوة 2:** أرسل يوزر مجموعتك **الهدف**.")
    elif isinstance(state_data, dict) and state_data.get("state") == "awaiting_to_group":
        from_group, to_group = state_data['from_group'], event.text
        try:
            bot_info = await bot_client.get_me()
            admins = await bot_client.get_participants(to_group, filter=ChannelParticipantsAdmins)
            if bot_info.id not in [admin.id for admin in admins]: await event.reply("❌ **خطأ:** أنا لست مشرفاً في المجموعة الهدف!"); del user_states[user_id]; return
        except Exception: await event.reply(f"❌ **خطأ:** لا يمكنني الوصول للمجموعة الهدف."); del user_states[user_id]; return
        queue = load_json(QUEUE_FILE)
        queue.append({"user_id": user_id, "from_group": from_group, "to_group": to_group})
        save_json(QUEUE_FILE, queue)
        await event.reply("✅ **تم استلام طلبك!** سيتم إعلامك عند البدء والانتهاء.")
        del user_states[user_id]

# --- المدقق والعامل الخلفي ---
async def account_checker_worker():
    while True:
        await asyncio.sleep(6 * 3600)
        print("🕵️ [Checker] Starting accounts validity check...")
        accounts = load_accounts()
        valid_accounts = []
        if not accounts: print("🕵️ [Checker] No accounts to check."); continue
        for account in accounts:
            is_valid = False
            try:
                status = await check_account_status(account)
                if status == "✅ فعال": is_valid = True
            except Exception: pass
            if is_valid: valid_accounts.append(account)
            else:
                try: await bot_client.send_message(account['contributor_id'], INVALID_ACCOUNT_NOTICE)
                except Exception: pass
        if len(valid_accounts) != len(accounts): save_json(ACCOUNTS_FILE, valid_accounts); print(f"💾 [Checker] Database updated. Valid accounts: {len(valid_accounts)}")
        else: print("🕵️ [Checker] All accounts are valid.")

async def background_worker():
    global transfer_in_progress
    while True:
        await asyncio.sleep(10)
        queue = load_json(QUEUE_FILE)
        if not queue: continue
        transfer_in_progress = True
        task = queue.pop(0); save_json(QUEUE_FILE, queue)
        accounts = load_accounts()
        if not accounts: await bot_client.send_message(task['user_id'], "لا توجد حسابات متاحة حالياً في المجمع."); continue
        status_message = await bot_client.send_message(task['user_id'], f"🚀 بدء النقل من `{task['from_group']}` إلى `{task['to_group']}`...")
        processed_users = load_processed_users()
        total_added, MAX_ADDS_PER_TASK = 0, 200
        random.shuffle(accounts)
        for acc_data in accounts:
            if total_added >= MAX_ADDS_PER_TASK: break
            proxy = get_random_proxy()
            client = TelegramClient(StringSession(acc_data['session_string']), acc_data['api_id'], acc_data['api_hash'], proxy=proxy)
            try:
                await client.connect()
                if not await client.is_user_authorized(): continue
                added = await transfer_engine(client, task['from_group'], task['to_group'], 40, processed_users, status_message)
                total_added += added
            except Exception: pass
            finally:
                if client.is_connected(): await client.disconnect()
        await status_message.edit(f"🎉 اكتمل النقل! إجمالي الإضافات: **{total_added}**")
        transfer_in_progress = False

# --- المشغل الرئيسي ---
async def run_bot_mode():
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ البوت يعمل الآن.")
    asyncio.create_task(background_worker())
    print("✅ عامل النقل يعمل الآن.")
    asyncio.create_task(account_checker_worker())
    print("✅ مدقق الحسابات يعمل الآن.")
    await bot_client.run_until_disconnected()

async def run_terminal_mode():
    _, from_g, to_g, max_a_str = sys.argv
    print("--- 🚀 وضع النقل اليدوي للمطور 🚀 ---")
    try: max_adds = int(max_a_str)
    except ValueError: print("❌ الحد الأقصى يجب أن يكون رقمًا."); return
    accounts = load_accounts()
    if not accounts: print("❌ لا توجد حسابات متاحة."); return
    processed_users = load_processed_users()
    total_added = 0
    for acc_data in accounts:
        if total_added >= max_adds: break
        proxy = get_random_proxy()
        client = TelegramClient(StringSession(acc_data['session_string']), acc_data['api_id'], acc_data['api_hash'], proxy=proxy)
        try:
            await client.connect()
            if not await client.is_user_authorized(): continue
            added = await transfer_engine(client, from_g, to_g, 40, processed_users, terminal_mode=True)
            total_added += added
        except Exception as e: print(f"🚨 خطأ في الحساب: {e}")
        finally:
            if client.is_connected(): await client.disconnect()
    print(f"🎉 انتهت العملية. إجمالي الإضافات: {total_added}")

async def main():
    if len(sys.argv) == 4 and sys.argv[1] == 'transfer':
        await run_terminal_mode()
    else:
        await run_bot_mode()

if __name__ == "__main__":
    asyncio.run(main())
