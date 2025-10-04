import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from fastapi import FastAPI
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- إعدادات الحساب ----------
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "7693967127"))

if not API_ID or not API_HASH or not STRING_SESSION:
    logger.error("الرجاء ضبط API_ID و API_HASH و STRING_SESSION في متغيرات البيئة.")
    raise SystemExit(1)

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "running"}

@client.on(events.NewMessage(pattern=r'^\.مؤقت\s+(.+)\s+(\d+)\s+(\d+)$'))
async def periodic_sender(event):
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

    MAX_COUNT = int(os.environ.get("MAX_COUNT", "200"))
    if count > MAX_COUNT:
        await event.reply(f"الحد الأقصى للرسائل هو {MAX_COUNT}.")
        return

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

    await event.reply("انتهى الإرسال.")

async def start_client():
    await client.start()
    logger.info("Telegram client started.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    loop = asyncio.get_event_loop()
    loop.create_task(start_client())
    uvicorn.run(app, host="0.0.0.0", port=port)
