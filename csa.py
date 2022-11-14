import datetime
import json
import logging
import pathlib
from os.path import join
from bs4 import BeautifulSoup

import pytz
import requests
from discord import Color, Embed

utc = pytz.UTC


class csa_report:
    def __init__(self, valid, keywords, keywords_i, product, product_i):
        self.valid = valid
        self.keywords = keywords
        self.keywords_i = keywords_i
        self.product = product
        self.product_i = product_i

        self.CSA_URL = "https://www.csa.gov.sg/singcert/Alerts"
        self.PUBLISH_JSON_PATH = join(
            pathlib.Path(__file__).parent.absolute(), "output/record.json"
        )
        self.CSA_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
        self.CSA_CREATED = datetime.datetime.now(utc) - datetime.timedelta(days=1)
        self.logger = logging.getLogger("csa-reporter")

    ################## LOAD CONFIGURATIONS ####################

    def load_lasttimes(self):
        # Load lasttimes from json file

        try:

            with open(self.PUBLISH_JSON_PATH, "r") as json_file:
                csa_time = json.load(json_file)
                self.CSA_CREATED = datetime.datetime.strptime(
                    csa_time["CREATED"], self.CSA_TIME_FORMAT
                )

        except Exception as e:  # If error, just keep the fault date (today - 1 day)
            self.logger.error(f"ERROR: {e}")

    # print(f"Last_Published: {LAST_PUBLISHED}")

    def update_lasttimes(self):
        # Save lasttimes in json file
        try:

            with open(self.PUBLISH_JSON_PATH, "w") as json_file:
                json.dump(
                    {
                        "CREATED": self.CSA_CREATED.strftime(self.CSA_TIME_FORMAT),
                    },
                    json_file,
                )

        except Exception as e:
            self.logger.error(f"ERROR: {e}")

    ################## GET ALERTS FROM CSA  ####################

    def get_alerts(self):

        r = requests.get(f"{self.CSA_URL}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text(), "lxml")
            for elem in soup.select(".sc-card-block"):
                subdir = elem.get("href")
                print (elem)


    #def filter_alerts(self, stories, last_create: datetime.datetime):

        # filtered_stories = []
        # new_last_time = last_create

        # for story in stories:

        #     story_time = datetime.datetime.strptime(
        #         story[tt_filter.value], self.ALIEN_TIME_FORMAT
        #     )
        #     if story_time > last_create:
        #         if self.valid or self.is_summ_keyword_present(story["description"]):

        #             filtered_stories.append(story)

        #     if story_time > new_last_time:
        #         new_last_time = story_time

        # return filtered_stories, new_last_time

    def is_summ_keyword_present(self, summary: str):
        # Given the summary check if any keyword is present

        return any(w in summary for w in self.keywords) or any(
            w.lower() in summary.lower() for w in self.keywords_i
        )  # for each of the word in description keyword config, check if it exists in summary.

    def get_new_alerts(self):

        # stories = self.get_sub_pulse()
        # filtered_pulses, new_last_time = self.filter_pulse(
        #     stories["results"], self.ALIEN_CREATED, time_type.created
        # )
        # self.ALIEN_CREATED = new_last_time

        # return filtered_pulses

    def generate_new_alert_message(self, new_alerts) -> Embed:
        # Generate new CVE message for sending to slack
        nl = "\n"
        embed = Embed(
            title=f"🔈 *{new_alerts['name']}*",
            description=new_alerts["description"]
            if len(new_alerts["description"]) < 500
            else new_alerts["description"][:500] + "...",
            timestamp=datetime.datetime.utcnow(),
            color=Color.light_gray(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_alerts['created']}", inline=True
        )
        embed.add_field(
            name=f"📅  *Last Modified*", value=f"{new_alerts['modified']}", inline=True
        )
        embed.add_field(
            name=f"More Information (_limit to 5_)",
            value=f"{nl.join(new_alerts['references'][:5])}",
            inline=False,
        )

        return embed
