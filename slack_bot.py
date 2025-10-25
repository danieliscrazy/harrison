
import os
import logging
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.models.blocks import SectionBlock, ActionsBlock, ButtonElement
from slack_sdk.models.views import View
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
CHANNEL_ID = "C09B4LFK7BK"
MENTION_USER_ID = "U07E6TW9DL0"

client = WebClient(token=SLACK_BOT_TOKEN)


# Respond to mentions
def process_events(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        event = req.payload["event"]
        if event.get("type") == "app_mention":
            user = event.get("user")
            thread_ts = event.get("ts")
            channel = event.get("channel")
            text = event.get("text", "")
            logging.info(f"Mention detected from user {user} in channel {channel} (thread {thread_ts})")
            # Manual trigger command
            if "trigger daily" in text.lower():
                if user == MENTION_USER_ID:
                    send_daily_message()
                    client.web_client.chat_postMessage(
                        channel=channel,
                        thread_ts=thread_ts,
                        text="Daily message triggered manually."
                    )
                    logging.info(f"Manual daily message triggered by {user}")
                else:
                    client.web_client.chat_postEphemeral(
                        channel=channel,
                        user=user,
                        text="nuh uh"
                    )
                    logging.info(f"Unauthorized manual trigger attempt by {user}")
            else:
                client.web_client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f"Hi <@{user}>!"
                )
                logging.info(f"Replied to mention from user {user} in thread {thread_ts}")
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))
    elif req.type == "interactive":
        payload = req.payload
        actions = payload.get("actions", [])
        if actions and actions[0].get("action_id") == "pester_button":
            user = payload["user"]["id"]
            channel = payload["channel"]["id"]
            message_ts = payload["message"]["ts"]
            # Remove the button by updating the message
            client.web_client.chat_update(
                channel=channel,
                ts=message_ts,
                text=payload["message"]["text"],
                blocks=[]
            )
            # Send the pester message
            client.web_client.chat_postMessage(
                channel=CHANNEL_ID,
                text=f"<@{MENTION_USER_ID}> <@{user}> decided to pester you further"
            )
            logging.info(f"Pester button pressed by {user}")


def send_daily_message():
    logging.info(f"Sending daily message to channel {CHANNEL_ID}")
    try:
        client.chat_postMessage(
            channel=CHANNEL_ID,
            text=f"<@{MENTION_USER_ID}> say something and also do the fact of the day",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<@{MENTION_USER_ID}> say something and also do the fact of the day"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "pester"
                            },
                            "style": "primary",
                            "action_id": "pester_button"
                        }
                    ]
                }
            ]
        )
        logging.info("Daily message sent.")
    except Exception as e:
        logging.error(f"Failed to send daily message: {e}")


def schedule_daily_message():
    scheduler = BackgroundScheduler(timezone=pytz.timezone("US/Eastern"))
    scheduler.add_job(send_daily_message, 'cron', hour=17, minute=0)
    scheduler.start()
    logging.info("Scheduled daily message at 5PM EST.")


if __name__ == "__main__":
    logging.info("Bot is starting up...")
    # Send a message to the channel on start
    try:
        client.chat_postMessage(
            channel=CHANNEL_ID,
            text="Bot is now online!"
        )
        logging.info(f"Startup message sent to channel {CHANNEL_ID}.")
    except Exception as e:
        logging.error(f"Failed to send startup message: {e}")

    schedule_daily_message()
    socket_mode_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=client)
    socket_mode_client.socket_mode_request_listeners.append(process_events)
    socket_mode_client.connect()
    logging.info("Socket mode client connected. Bot is running.")
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Bot is shutting down...")
