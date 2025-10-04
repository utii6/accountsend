import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات من المتغيرات البيئية (Render)
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")  # يفضل وضع هذا
OWNER_ID = int(os.environ.get("OWNER_ID", "7693967127"))

if not API_ID or not API_HASH:
    logger.error("الرجاء ضبط API_ID و API_HASH في متغيرات البيئة.")
    raise SystemExit(1)

# اختياري: إذا لم توفر STRING_SESSION سيُنشأ ملف جلسة محلي باسم session
if STRING_SESSION:
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
else:
    client = TelegramClient("session", API_ID, API_HASH)

@client.on(events.NewMessage(pattern=r'^\.مؤقت\s+(.+)\s+(\d+)\s+(\d+)$'))
async def periodic_sender(event):
    # يتأكد أن المرسل هو المالك
    try:
        sender = await event.get_sender()
        sender_id = getattr(sender, "id", None)
    except Exception:
        sender_id = event.sender_id

    if sender_id != OWNER_ID:
        return  # لا يستجيب لغير المالك

    full_msg, count_s, delay_s = event.pattern_match.groups()
    try:
        count = int(count_s)
        delay = int(delay_s)
    except ValueError:
        await event.reply("صيغة غير صحيحة للأرقام.")
        return

    if count <= 0 or delay < 0:
        await event.reply("العدد يجب أن يكون موجب والفاصل >= 0.")
        return

    # حماية بسيطة لمنع الإرسال المفرط عن طريق الخطأ
    MAX_COUNT = int(os.environ.get("MAX_COUNT", "200"))
    if count > MAX_COUNT:
        await event.reply(f"الحد الأقصى للرسائل هو {MAX_COUNT}.")
        return

    chat = await event.get_chat()
    chat_id = event.chat_id
    await event.reply(f"بدء الإرسال: {count} رسالة كل {delay} ثانية.")

    for i in range(count):
        try:
            await client.send_message(chat_id, full_msg)
        except FloodWaitError as e:
            wait = int(e.seconds) + 2
            logger.warning(f"FloodWait {wait}s — الانتظار ثم المتابعة")
            await asyncio.sleep(wait)
            await client.send_message(chat_id, full_msg)
        except Exception as e:
            logger.exception("خطأ أثناء الإرسال:")
            await event.reply(f"حدث خطأ أثناء الإرسال: {e}")
            break

        if i < count - 1:
            await asyncio.sleep(delay)

    await event.reply("😎انتهى الإرسال.")

def main():
    with client:
        logger.info("👍البوت يعمل الآن. بانتظار الأوامر.")
        client.run_until_disconnected()

if __name__ == "__main__":
    main()
