# discord_csa_reporter

Description (According to ChatGPT, Kudos)
This script is used to gather information from the Cyber Security Agency of Singapore (CSA) and send that information to a specified Discord channel through a webhook. The script uses the csa library to gather information from CSA and the dotenv library to load environment variables from a .env file, including the webhook URL. The script uses the apscheduler library to schedule the message sending and the aiohttp library to send the messages asynchronously, which allows for efficient and non-blocking execution of the script. The script also uses logging for debugging purpose and storing it in a log file, which allows for easy identification and troubleshooting of any issues that may arise during the script's execution. The script also uses the asyncio library to schedule and send messages through a Discord webhook and Embed message for sending the message in a more structured way. The script will check for new Alerts, Advisories, and Publications, and sends them to the discord channel in an embedded format. It runs on schedule using the cron job and only runs on weekdays between 8am to 6pm.
