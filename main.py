import asyncio
import logging
import os
from os.path import join
from time import sleep
from pathlib import Path

from os.path import join, dirname
from dotenv import load_dotenv
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from csa import csa_report
from discord import Embed, HTTPException, Webhook

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

#################### LOG CONFIG #########################

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# create console handler and set level to debug
consolelog = logging.StreamHandler()
consolelog.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s')

# add formatter to ch
consolelog.setFormatter(formatter)

# create file handler and set level to debug
log_dir = Path(__file__).parent.absolute()
log_dir.mkdir(parents=True, exist_ok=True)
filelog = logging.FileHandler(
    log_dir / 'csa_singcert_logfile.log', "a", "utf-8")
filelog.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to fh
filelog.setFormatter(formatter)

# add ch and fh to logger
logger.addHandler(consolelog)
logger.addHandler(filelog)

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
    csa.get_new_alerts()
    csa.get_new_advs()
    csa.get_new_pubs()

    for alert in csa.new_alerts:
        alert_msg = csa.generate_new_alert_message(alert)
        await send_discord_message(alert_msg)

    for adv in csa.new_advs:
        adv_msg = csa.generate_new_adv_message(adv)
        await send_discord_message(adv_msg)

    for pub in csa.new_pubs:
        pub_msg = csa.generate_new_pub_message(pub)
        await send_discord_message(pub_msg)

    csa.update_lasttimes()

if __name__ == "__main__":
    scheduler = AsyncIOScheduler(timezone="Asia/Singapore")
    scheduler.add_job(
        itscheckintime, "cron", day_of_week="mon-fri", hour="8-18/1"
    )
    scheduler.start()
    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        logger.warning(e)
        raise e
