import asyncio
import logging
import os
import pathlib
import sys
from os.path import join

from os.path import join, dirname
from dotenv import load_dotenv
import aiohttp
import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from csa import csa_report
from discord import Embed, HTTPException, Webhook
#from keep_alive import keep_alive

#################### LOG CONFIG #########################

dotenv_path = join(dirname(__file__), ".env")
load_dotenv(dotenv_path)

log = logging.getLogger("csa-reporter")
log.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(message)s",
                              "%Y-%m-%d %H:%M:%S")

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

#################### LOADING #########################


def load_keywords():
    # Load keywords from config file
    KEYWORDS_CONFIG_PATH = join(
        pathlib.Path(__file__).parent.absolute(), "config/config.yaml")
    try:

        with open(KEYWORDS_CONFIG_PATH, "r") as yaml_file:
            keywords_config = yaml.safe_load(yaml_file)
            print(f"Loaded keywords: {keywords_config}")
            ALL_VALID = keywords_config["ALL_VALID"]
            DESCRIPTION_KEYWORDS_I = keywords_config["DESCRIPTION_KEYWORDS_I"]
            DESCRIPTION_KEYWORDS = keywords_config["DESCRIPTION_KEYWORDS"]
            PRODUCT_KEYWORDS_I = keywords_config["PRODUCT_KEYWORDS_I"]
            PRODUCT_KEYWORDS = keywords_config["PRODUCT_KEYWORDS"]

            return (
                ALL_VALID,
                DESCRIPTION_KEYWORDS,
                DESCRIPTION_KEYWORDS_I,
                PRODUCT_KEYWORDS,
                PRODUCT_KEYWORDS_I,
            )
    except Exception as e:
        log.error(e)
        sys.exit(1)


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
        # except RateLimited(600.0):
        #    log.debug("ratelimited error")
        #    os.system("kill 1")
        except HTTPException:
            log.debug("http error")
            os.system("kill 1")
            # await webhook.send(embed=content)


#################### MAIN BODY #########################
async def itscheckintime():

    (
        ALL_VALID,
        DESCRIPTION_KEYWORDS,
        DESCRIPTION_KEYWORDS_I,
        PRODUCT_KEYWORDS,
        PRODUCT_KEYWORDS_I,
    ) = load_keywords()

    csa = csa_report(
        ALL_VALID,
        DESCRIPTION_KEYWORDS,
        DESCRIPTION_KEYWORDS_I,
        PRODUCT_KEYWORDS,
        PRODUCT_KEYWORDS_I,
    )
    csa.load_lasttimes()
    new_alerts = csa.get_new_alerts()

    alert_title = [new_alert["title"] for new_alert in new_alerts]
    print(f"CSA Alerts: {alert_title}")

    for alert in new_alerts:
        alert_msg = csa.generate_new_alert_message(alert)
        print("passed")
        await send_discord_message(alert_msg)

    #print("passed")

    csa.update_lasttimes()


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job(itscheckintime, "interval", minutes=60)
    scheduler.start()
    print("Press Ctrl+{0} to exit".format("Break" if os.name == "nt" else "C"))

    # Execution will block here until Ctrl+C (Ctrl+Break on Windows) is pressed.
    try:
        #keep_alive()
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit) as e:
        log.error(f"{e}")
        raise e
