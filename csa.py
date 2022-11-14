import datetime
import json
import logging
import os
import pathlib
from enum import Enum
from os.path import join

import pytz
import requests
from discord import Color, Embed

utc = pytz.UTC


class time_type(Enum):
    created = "created"
    modified = "modified"


class csa_report:
    def __init__(self, valid, keywords, keywords_i, product, product_i):
        self.valid = valid
        self.keywords = keywords
        self.keywords_i = keywords_i
        self.product = product
        self.product_i = product_i

        self.ALIENVAULT_UR = "https://otx.alienvault.com/api/v1/pulses/subscribed?"
        self.PUBLISH_ALIEN_JSON_PATH = join(
            pathlib.Path(__file__).parent.absolute(), "output/record.json"
        )
        self.ALIEN_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
        self.ALIEN_MODIFIED = datetime.datetime.now(utc) - datetime.timedelta(days=1)
        self.ALIEN_CREATED = datetime.datetime.now(utc) - datetime.timedelta(days=1)
        self.logger = logging.getLogger("cybersecstories")

    ################## LOAD CONFIGURATIONS ####################

    def load_lasttimes(self):
        # Load lasttimes from json file

        try:

            with open(self.PUBLISH_ALIEN_JSON_PATH, "r") as json_file:
                alien_time = json.load(json_file)
                self.ALIEN_MODIFIED = datetime.datetime.strptime(
                    alien_time["MODIFIED"], self.ALIEN_TIME_FORMAT
                )
                self.ALIEN_CREATED = datetime.datetime.strptime(
                    alien_time["CREATED"], self.ALIEN_TIME_FORMAT
                )

        except Exception as e:  # If error, just keep the fault date (today - 1 day)
            self.logger.error(f"ERROR: {e}")

    # print(f"Last_Published: {LAST_PUBLISHED}")

    def update_lasttimes(self):
        # Save lasttimes in json file
        try:

            with open(self.PUBLISH_ALIEN_JSON_PATH, "w") as json_file:
                json.dump(
                    {
                        "MODIFIED": self.ALIEN_MODIFIED.strftime(
                            self.ALIEN_TIME_FORMAT
                        ),
                        "CREATED": self.ALIEN_CREATED.strftime(self.ALIEN_TIME_FORMAT),
                    },
                    json_file,
                )

        except Exception as e:
            self.logger.error(f"ERROR: {e}")

    ################## GET PULSES FROM OTX ALIEN  ####################

    def get_sub_pulse(self):

        now = datetime.datetime.now() - datetime.timedelta(days=1)
        now_str = now.strftime("%Y-%m-%d")
        limit = 100

        headers = {
            "Content-Type": "application/json",
            "X-OTX-API-KEY": os.getenv("ALIEN_VAULT_API"),
        }

        r = requests.get(
            f"{self.ALIENVAULT_UR}limit={limit}&modified_since={now_str}",
            headers=headers,
        )

        return r.json()

    def filter_pulse(
        self, stories, last_create: datetime.datetime, tt_filter: time_type
    ):

        filtered_stories = []
        new_last_time = last_create

        for story in stories:

            story_time = datetime.datetime.strptime(
                story[tt_filter.value], self.ALIEN_TIME_FORMAT
            )
            if story_time > last_create:
                if self.valid or self.is_summ_keyword_present(story["description"]):

                    filtered_stories.append(story)

            if story_time > new_last_time:
                new_last_time = story_time

        return filtered_stories, new_last_time

    def is_summ_keyword_present(self, summary: str):
        # Given the summary check if any keyword is present

        return any(w in summary for w in self.keywords) or any(
            w.lower() in summary.lower() for w in self.keywords_i
        )  # for each of the word in description keyword config, check if it exists in summary.

    def get_new_pulse(self):

        stories = self.get_sub_pulse()
        filtered_pulses, new_last_time = self.filter_pulse(
            stories["results"], self.ALIEN_CREATED, time_type.created
        )
        self.ALIEN_CREATED = new_last_time

        return filtered_pulses

    def get_modified_pulse(self):

        stories = self.get_sub_pulse()
        filtered_pulses, new_last_time = self.filter_pulse(
            stories["results"], self.ALIEN_MODIFIED, time_type.created
        )
        self.ALIEN_MODIFIED = new_last_time

        return filtered_pulses

    def generate_new_pulse_message(self, new_story) -> Embed:
        # Generate new CVE message for sending to slack
        nl = "\n"
        embed = Embed(
            title=f"🔈 *{new_story['name']}*",
            description=new_story["description"]
            if len(new_story["description"]) < 500
            else new_story["description"][:500] + "...",
            timestamp=datetime.datetime.utcnow(),
            color=Color.light_gray(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_story['created']}", inline=True
        )
        embed.add_field(
            name=f"📅  *Last Modified*", value=f"{new_story['modified']}", inline=True
        )
        embed.add_field(
            name=f"More Information (_limit to 5_)",
            value=f"{nl.join(new_story['references'][:5])}",
            inline=False,
        )

        return embed

    def generate_mod_pulse_message(self, new_story) -> Embed:
        # Generate new CVE message for sending to slack
        nl = "\n"
        embed = Embed(
            title=f"🔈 *Updated: {new_story['name']}*",
            description=new_story["description"]
            if len(new_story["description"]) < 500
            else new_story["description"][:500] + "...",
            timestamp=datetime.datetime.utcnow(),
            color=Color.light_gray(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_story['created']}", inline=True
        )
        embed.add_field(
            name=f"📅  *Last Modified*", value=f"{new_story['modified']}", inline=True
        )
        embed.add_field(
            name=f"More Information (_limit to 5_)",
            value=f"{nl.join(new_story['references'][:5])}",
            inline=False,
        )

        return embed
