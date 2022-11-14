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

        self.CSA_URL = "https://www.csa.gov.sg"
        self.PUBLISH_JSON_PATH = join(
            pathlib.Path(__file__).parent.absolute(), "output/record.json")
        self.CSA_TIME_FORMAT = "%d %b %Y"
        self.CSA_CREATED = datetime.datetime.now(utc) - datetime.timedelta(
            days=1)
        self.logger = logging.getLogger("csa-reporter")

    ################## LOAD CONFIGURATIONS ####################

    def load_lasttimes(self):
        # Load lasttimes from json file

        try:

            with open(self.PUBLISH_JSON_PATH, "r") as json_file:
                csa_time = json.load(json_file)
                self.CSA_CREATED = datetime.datetime.strptime(
                    csa_time["CREATED"], self.CSA_TIME_FORMAT)

        except Exception as e:  # If error, just keep the fault date (today - 1 day)
            self.logger.error(f"ERROR: {e}")

    # print(f"Last_Published: {LAST_PUBLISHED}")

    def update_lasttimes(self):
        # Save lasttimes in json file
        try:

            with open(self.PUBLISH_JSON_PATH, "w") as json_file:
                json.dump(
                    {
                        "CREATED": self.CSA_CREATED.strftime(
                            self.CSA_TIME_FORMAT),
                    },
                    json_file,
                )

        except Exception as e:
            self.logger.error(f"ERROR: {e}")

    ################## GET ALERTS FROM CSA  ####################

    def get_alerts(self):
        
        results = []
        r = requests.get(f"{self.CSA_URL}/singcert/Alerts")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            for elem in soup.select(".sc-card-block"):
                result = {}
                result['csa'] = f"{self.CSA_URL}{elem.get('href')}"
                result['title']=elem.find(class_="sc-card-title").get_text(" ", strip=True)
                result['description']=elem.find("p", class_="sc-card-desc").get_text(" ", strip=True)
                result['created'] = elem.find(
                    "div", class_="sc-card-publish").get_text(
                        " ", strip=True).split(" on ")[1]
                results.append(result)

            return results

    def filter_alerts(self, alerts, last_create: datetime.datetime):

        filtered_alerts = []
        new_last_time = last_create

        for alert in alerts:
            alert_time = datetime.datetime.strptime(alert["created"],
                                                    self.CSA_TIME_FORMAT)
            if alert_time > last_create:
                if self.valid or self.is_summ_keyword_present(
                        alert["description"]):
                    filtered_alerts.append(alert)

            if alert_time > new_last_time:
                new_last_time = alert_time

        return filtered_alerts, new_last_time

    def is_summ_keyword_present(self, summary: str):
        # Given the summary check if any keyword is present

        return any(w in summary for w in self.keywords) or any(
            w.lower() in summary.lower() for w in self.keywords_i
        )  # for each of the word in description keyword config, check if it exists in summary.

    def get_new_alerts(self):

        alerts = self.get_alerts()
        #print(alerts)
        filtered_alerts, new_last_time = self.filter_alerts(
            alerts, self.CSA_CREATED)
        self.CSA_CREATED = new_last_time

        return filtered_alerts

    def generate_new_alert_message(self, new_alerts) -> Embed:
        # Generate new CVE message for sending to slack
        nl = "\n"
        embed = Embed(
            title=f"🔈 *{new_alerts['title']}*",
            description=new_alerts["description"]
            if len(new_alerts["description"]) < 500 else
            new_alerts["description"][:500] + "...",
            timestamp=datetime.datetime.utcnow(),
            color=Color.light_gray(),
        )
        embed.add_field(name=f"📅  *Published*",
                        value=f"{new_alerts['created']}",
                        inline=True)
        embed.add_field(
            name=f"More Information",
            value=f"{new_alerts['csa']}",
            inline=False,
        )

        return embed
