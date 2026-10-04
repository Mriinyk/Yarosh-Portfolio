import html
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_notification(contact_request):
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        logger.error("Telegram notification is not configured.")
        return False

    username = contact_request.social_username.replace("@", "")
    profile_url = (
        f"https://t.me/{username}"
        if contact_request.contact_method == "telegram"
        else f"https://instagram.com/{username}"
    )
    text = (
        f"🔥 <b>Нова заявка з сайту! (#ID: {contact_request.pk})</b>\n\n"
        f"<b>Зв'язок:</b> {contact_request.get_contact_method_display()}\n"
        f"<b>Нік:</b> {html.escape(contact_request.social_username)}\n"
        f"<b>Посилання:</b> "
        f'<a href="{html.escape(profile_url, quote=True)}">Перейти до профілю</a>\n\n'
        f"<b>Повідомлення:</b>\n<i>{html.escape(contact_request.message)}</i>"
    )

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5,
        )
        data = response.json()
    except ValueError:
        logger.exception("Telegram returned an invalid notification response.")
        return False
    except requests.RequestException:
        logger.exception("Telegram notification request failed.")
        return False

    if not isinstance(data, dict):
        logger.error("Telegram returned an invalid notification response.")
        return False
    if not response.ok or not data.get("ok"):
        logger.error(
            "Telegram rejected a contact notification (HTTP %s): %s",
            response.status_code,
            data.get("description", "No error description"),
        )
        return False

    result = data.get("result")
    if not isinstance(result, dict):
        logger.error("Telegram notification response did not include a message ID.")
        return False
    message_id = result.get("message_id")
    if not isinstance(message_id, int):
        logger.error("Telegram notification response did not include a message ID.")
        return False

    contact_request.telegram_message_id = message_id
    contact_request.save(update_fields=["telegram_message_id"])
    return True


def delete_telegram_notification(contact_request):
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        logger.error("Telegram deletion is not configured.")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/deleteMessage",
            json={
                "chat_id": chat_id,
                "message_id": contact_request.telegram_message_id,
            },
            timeout=5,
        )
        data = response.json()
    except ValueError:
        logger.exception("Telegram returned an invalid deletion response.")
        return False
    except requests.RequestException:
        logger.exception(
            "Telegram deletion request failed for contact request %s.",
            contact_request.pk,
        )
        return False

    if not isinstance(data, dict):
        logger.error("Telegram returned an invalid deletion response.")
        return False
    if not response.ok or not data.get("ok"):
        logger.error(
            "Telegram rejected deletion for contact request %s (HTTP %s): %s",
            contact_request.pk,
            response.status_code,
            data.get("description", "No error description"),
        )
        return False
    return True
