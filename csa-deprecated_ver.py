import datetime
import json
import logging
import pathlib
import sys
from os.path import join
from bs4 import BeautifulSoup

import yaml
import requests
from discord import Color, Embed, HTTPException


class csa_report:
    def __init__(self):

        self.CSA_URL = "https://www.csa.gov.sg"
        self.CSA_JSON_PATH = join(
            pathlib.Path(__file__).parent.absolute(), "output/record.json"
        )
        self.CSA_TIME_FORMAT = "%d %b %Y"

        self.ALERT_CREATED = datetime.datetime.now() - datetime.timedelta(days=1)
        self.ADV_CREATED = datetime.datetime.now() - datetime.timedelta(days=1)
        self.PUB_CREATED = datetime.datetime.now() - datetime.timedelta(days=1)

        self.last_title_dict = {'ALERT_LATEST_TITLE': '',
                                'ADV_LATEST_TITLE': '', 'PUB_LATEST_TITLE': ''}

        self.logger = logging.getLogger("__main__")
        self.logger.setLevel(logging.INFO)

        self.new_alerts = []
        self.new_alerts_title = []
        self.new_advs = []
        self.new_advs_title = []
        self.new_pubs = []
        self.new_pubs_title = []

        self.tup_type = ("ALERTS", "ADVISORIES", "PUBLICATIONS")

        # Load keywords from config file
        self.KEYWORDS_CONFIG_PATH = join(
            pathlib.Path(__file__).parent.absolute(), "config/config.yaml"
        )
        try:

            with open(self.KEYWORDS_CONFIG_PATH, "r") as yaml_file:
                keywords_config = yaml.safe_load(yaml_file)
                self.logger.info(f"Loaded keywords: {keywords_config}")
                self.valid = keywords_config["ALL_VALID"]
                self.keywords_i = keywords_config["DESCRIPTION_KEYWORDS_I"]
                self.keywords = keywords_config["DESCRIPTION_KEYWORDS"]
                self.product_i = keywords_config["PRODUCT_KEYWORDS_I"]
                self.product = keywords_config["PRODUCT_KEYWORDS"]
            yaml_file.close()
        except Exception as e:
            self.logger.error(e)
            sys.exit(1)

    ################## LOAD CONFIGURATIONS ####################

    def load_lasttimes(self):
        # Load lasttimes from json file

        try:

            with open(self.CSA_JSON_PATH, "r") as json_file:
                csa_record = json.load(json_file)
                self.last_title_dict['ALERT_LATEST_TITLE'] = csa_record['ALERT_LATEST_TITLE']
                self.last_title_dict['ADV_LATEST_TITLE'] = csa_record['ADV_LATEST_TITLE']
                self.last_title_dict['PUB_LATEST_TITLE'] = csa_record['PUB_LATEST_TITLE']
                self.ALERT_CREATED = datetime.datetime.strptime(
                    csa_record['ALERT_CREATED'], self.CSA_TIME_FORMAT)
                self.ADV_CREATED = datetime.datetime.strptime(
                    csa_record['ADV_CREATED'], self.CSA_TIME_FORMAT
                )
                self.PUB_CREATED = datetime.datetime.strptime(
                    csa_record['PUB_CREATED'], self.CSA_TIME_FORMAT
                )
            json_file.close()
        # If error, just keep the fault date (today - 1 day)
        except Exception as e:
            self.logger.error(f"ERROR-1: {e}")

    def update_lasttimes(self):
        # Save lasttimes in json file
        try:

            with open(self.CSA_JSON_PATH, "w") as json_file:
                json.dump(
                    {
                        "ALERT_CREATED": self.ALERT_CREATED.strftime(
                            self.CSA_TIME_FORMAT
                        ),
                        "ALERT_LATEST_TITLE": self.last_title_dict['ALERT_LATEST_TITLE'],
                        "ADV_CREATED": self.ADV_CREATED.strftime(
                            self.CSA_TIME_FORMAT
                        ),
                        "ADV_LATEST_TITLE": self.last_title_dict['ADV_LATEST_TITLE'],
                        "PUB_CREATED": self.PUB_CREATED.strftime(
                            self.CSA_TIME_FORMAT
                        ),
                        "PUB_LATEST_TITLE": self.last_title_dict['PUB_LATEST_TITLE']
                    },
                    json_file,
                )
            json_file.close()
        except Exception as e:
            self.logger.error(f"ERROR-2: {e}")

    ################## FILTER FOR PUBLISH  ####################

    def get_list(self, subdomain):

        results = []
        try:
            r = requests.get(f"{self.CSA_URL}/{subdomain}")
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                for elem in soup.select(".sc-card-block"):
                    result = {}
                    result["csa"] = f"{self.CSA_URL}{elem.get('href')}"
                    result["title"] = elem.find(class_="sc-card-title").get_text(
                        " ", strip=True
                    )
                    result["description"] = elem.find(
                        "p", class_="sc-card-desc"
                    ).get_text(" ", strip=True)
                    result["created"] = (
                        elem.find("div", class_="sc-card-publish")
                        .get_text(" ", strip=True)
                        .split(" on ")[1]
                    )
                    results.append(result)

                return results
        except (HTTPException, ConnectionError) as e:
            self.logger.error(f"{e}")
            sys.exit(1)
            # os.system("kill 1")

    def filterlist(self, listobj: list, last_create: datetime.datetime, type: str):

        filtered_objlist = []
        new_last_time = last_create
        first_article = True
        first_title = ''

        for obj in listobj:
            if first_article:
                first_title = obj['title']
                first_article = False

            # if first element title is found in any of the latest title, it will break out of loop since there's nothing to update
            if (obj['title'] in self.last_title_dict.values()):
                break

            obj_time = datetime.datetime.strptime(
                f"{obj['created']}", self.CSA_TIME_FORMAT)

            if obj_time >= last_create:
                if self.valid or self.is_summ_keyword_present(obj["description"]):
                    filtered_objlist.append(obj)

            if obj_time > new_last_time:
                new_last_time = obj_time

        if type == self.tup_type[0]:
            self.last_title_dict['ALERT_LATEST_TITLE'] = first_title
        elif type == self.tup_type[1]:
            self.last_title_dict['ADV_LATEST_TITLE'] = first_title
        elif type == self.tup_type[2]:
            self.last_title_dict['PUB_LATEST_TITLE'] = first_title

        return filtered_objlist, new_last_time

    def is_summ_keyword_present(self, summary: str):
        # Given the summary check if any keyword is present

        return any(w in summary for w in self.keywords) or any(
            w.lower() in summary.lower() for w in self.keywords_i
        )  # for each of the word in description keyword config, check if it exists in summary.

    ################## GET ALERTS FROM CSA  ####################

    def get_new_alerts(self):

        alerts = self.get_list("singcert/Alerts")
        self.new_alerts, self.ALERT_CREATED = self.filterlist(
            alerts, self.ALERT_CREATED, self.tup_type[0]
        )

        self.new_alerts_title = [new_alert["title"]
                                 for new_alert in self.new_alerts]
        self.logger.info(f"CSA Alerts: {self.new_alerts_title}")

    def generate_new_alert_message(self, new_alerts) -> Embed:
        # Generate new CVE message for sending to discord
        embed = Embed(
            title=f"🔈 *{new_alerts['title']}*",
            description=new_alerts["description"]
            if len(new_alerts["description"]) < 500
            else new_alerts["description"][:500] + "...",
            timestamp=datetime.datetime.now(),
            color=Color.brand_red(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_alerts['created']}", inline=True
        )
        embed.add_field(
            name=f"More Information",
            value=f"{new_alerts['csa']}",
            inline=False,
        )

        return embed

    ################## GET ADVISORIES FROM CSA  ####################

    def get_new_advs(self):

        adv = self.get_list("singcert/Advisories")
        self.new_advs, self.ADV_CREATED = self.filterlist(
            adv, self.ADV_CREATED, self.tup_type[1]
        )

        self.new_advs_title = [new_adv["title"] for new_adv in self.new_advs]
        self.logger.info(f"CSA Advisories: {self.new_advs_title}")

    def generate_new_adv_message(self, new_advs) -> Embed:
        # Generate new CVE message for sending to discord
        embed = Embed(
            title=f"🔈 *{new_advs['title']}*",
            description=new_advs["description"]
            if len(new_advs["description"]) < 500
            else new_advs["description"][:500] + "...",
            timestamp=datetime.datetime.now(),
            color=Color.blue(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_advs['created']}", inline=True
        )
        embed.add_field(
            name=f"More Information",
            value=f"{new_advs['csa']}",
            inline=False,
        )

        return embed

    ################## GET PUBLICATION FROM CSA  ####################

    def get_new_pubs(self):

        pub = self.get_list("singcert/Publications")
        self.new_pubs, self.PUB_CREATED = self.filterlist(
            pub, self.PUB_CREATED, self.tup_type[2]
        )

        self.new_pubs_title = [new_pub["title"] for new_pub in self.new_pubs]
        self.logger.info(f"CSA Publications: {self.new_pubs_title}")

    def generate_new_pub_message(self, new_pubs) -> Embed:
        # Generate new CVE message for sending to discord
        embed = Embed(
            title=f"🔈 *{new_pubs['title']}*",
            description=new_pubs["description"]
            if len(new_pubs["description"]) < 500
            else new_pubs["description"][:500] + "...",
            timestamp=datetime.datetime.now(),
            color=Color.yellow(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_pubs['created']}", inline=True
        )
        embed.add_field(
            name=f"More Information",
            value=f"{new_pubs['csa']}",
            inline=False,
        )

        return embed
