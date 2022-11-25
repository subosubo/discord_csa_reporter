import asyncio
import logging
import os
from os.path import join
from time import sleep

from os.path import join, dirname
from dotenv import load_dotenv
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from csa import csa_report
from discord import Embed, HTTPException, Webhook

#################### LOG CONFIG #########################

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

log = logging.getLogger("csa-reporter")
log.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"
)

# Log to file
filehandler = logging.FileHandler("csa_reporter.log", "a", "utf-8")
filehandler.setLevel(logging.DEBUG)
filehandler.setFormatter(formatter)
log.addHandler(filehandler)

# Log to stdout too
streamhandler = logging.StreamHandler()
streamhandler.setLevel(logging.INFO)
streamhandler.setFormatter(formatter)
log.addHandler(streamhandler)


#################### SEND MESSAGES #########################


async def send_discord_message(message: Embed):
    """Send a message to the discord channel webhook"""

    discord_webhok_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not discord_webhok_url:
        print("DISCORD_WEBHOOK_URL wasn't configured in the secrets!")
        return

    await sendtowebhook(webhookurl=discord_webhok_url, content=message)


async def sendtowebhook(webhookurl: str, content: Embed):
    async with aiohttp.ClientSession() as session:
        try:
            webhook = Webhook.from_url(webhookurl, session=session)
            await webhook.send(embed=content)

        except HTTPException:
            sleep(180)
            await webhook.send(embed=content)


#################### MAIN BODY #########################
async def itscheckintime():

    csa = csa_report()
    csa.load_lasttimes()
    new_alerts = csa.get_new_alerts()

    if csa.new_alerts:
        for alert in new_alerts:
            alert_msg = csa.generate_new_alert_message(alert)
            await send_discord_message(alert_msg)

    csa.update_lasttimes()


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(itscheckintime, "interval", minutes=60)
    scheduler.start()
    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        log.error(f"{e}")
        raise e
