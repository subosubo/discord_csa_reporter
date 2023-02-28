import datetime
import json
import logging
import pathlib
import sys
import yaml
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from discord import Color, Embed, HTTPException
from os.path import join
from bs4 import BeautifulSoup
from typing import List, Tuple


class csa_report:
    def __init__(self):

        self.CSA_URL = "https://www.csa.gov.sg"
        self.CSA_JSON_PATH = join(
            pathlib.Path(__file__).parent.absolute(), "output/record.json"
        )
        self.CSA_TIME_FORMAT = "%d %b %Y"

        self.ALERT_CREATED = datetime.datetime.now() - datetime.timedelta(days=1)
        self.ADV_CREATED = datetime.datetime.now() - datetime.timedelta(days=1)
        self.BULLET_CREATED = datetime.datetime.now() - datetime.timedelta(days=1)

        self.last_title_dict = {'ALERT_LATEST_TITLE': '',
                                'ADV_LATEST_TITLE': '', 'BULLET_LATEST_TITLE': ''}

        self.logger = logging.getLogger("__main__")
        self.logger.setLevel(logging.INFO)

        self.new_alerts = []
        self.new_alerts_title = []
        self.new_advs = []
        self.new_advs_title = []
        self.new_bullet = []
        self.new_bullet_title = []

        self.tup_type = ("ALERTS", "ADVISORIES", "BULLETINS")

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
                self.last_title_dict['BULLET_LATEST_TITLE'] = csa_record['BULLET_LATEST_TITLE']
                self.ALERT_CREATED = datetime.datetime.strptime(
                    csa_record['ALERT_CREATED'], self.CSA_TIME_FORMAT)
                self.ADV_CREATED = datetime.datetime.strptime(
                    csa_record['ADV_CREATED'], self.CSA_TIME_FORMAT
                )
                self.BULLET_CREATED = datetime.datetime.strptime(
                    csa_record['BULLET_CREATED'], self.CSA_TIME_FORMAT
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
                        "BULLET_CREATED": self.BULLET_CREATED.strftime(
                            self.CSA_TIME_FORMAT
                        ),
                        "BULLET_LATEST_TITLE": self.last_title_dict['BULLET_LATEST_TITLE']
                    },
                    json_file,
                )
            json_file.close()
        except Exception as e:
            self.logger.error(f"ERROR-2: {e}")

    ################## FILTER FOR ARTICLES  ####################

    def get_list(self, subdomain):

        results = []
        try:
            r = requests.get(f"{self.CSA_URL}/{subdomain}")
            if r.status_code == 200:

                options = webdriver.ChromeOptions()

                # run the browser in headless mode (without GUI)
                options.add_argument('--headless')

                driver = webdriver.Chrome(options=options)
                driver.get(f"{self.CSA_URL}/{subdomain}")
                # looking for the date, since it is one of the elements that renders along with javascript
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'm-card-article__note')))

                if element:
                    soup = BeautifulSoup(driver.page_source, "lxml")
                    for elem in soup.select("a.m-card-article"):
                        # if there is a link href for each section for m-card-article, assume that there is a report for publishing
                        if elem.get('href'):
                            result = {}
                            result["csa"] = f"{self.CSA_URL}{elem.get('href')}"
                            result["title"] = elem.find(
                                'div', class_="m-card-article__title truncate-3-lines").get_text(" ", strip=True)
                            result["description"] = elem.find(
                                'div', class_="m-card-article__desc truncate-3-lines").get_text(" ", strip=True)
                            result["created"] = elem.find(
                                'div', class_="m-card-article__note").get_text(" ", strip=True)
                            results.append(result)

                driver.quit()
                return results
        except (HTTPException, ConnectionError) as e:
            self.logger.error(f"{e}")
            sys.exit(1)

    def filterlist(self, obj_list: List[dict], last_create: datetime.datetime, obj_type: str) -> Tuple[List[dict], datetime.datetime]:
        filtered_list = []
        new_last_create = last_create
        first_title = ''

        for obj in obj_list:
            # first_title will contain the title of the first object in the list, indicating that the first object has been processed.
            if not first_title:
                first_title = obj['title']

            # if first element title is found in any of the latest title, it will break out of loop since there's nothing to update
            obj_time = datetime.datetime.strptime(
                f"{obj['created']}", self.CSA_TIME_FORMAT)
            if obj_time < last_create or obj['title'] in self.last_title_dict.values():
                break

            if self.valid or self.is_summ_keyword_present(obj["description"]):
                filtered_list.append(obj)

            if obj_time > new_last_create:
                new_last_create = obj_time

        self.last_title_dict[f'{obj_type}_LATEST_TITLE'] = first_title

        return filtered_list, new_last_create

    def is_summ_keyword_present(self, summary: str):
        # Given the summary check if any keyword is present

        return any(w in summary for w in self.keywords) or any(
            w.lower() in summary.lower() for w in self.keywords_i
        )  # for each of the word in description keyword config, check if it exists in summary.

    ################## GET ALERTS FROM CSA  ####################

    def get_new_alerts(self):

        alerts = self.get_list("alerts-advisories/alerts")
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

        adv = self.get_list("alerts-advisories/Advisories")
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

    ################## GET BULLETINS FROM CSA  ####################

    def get_new_bulletin(self):

        bullet = self.get_list("alerts-advisories/security-bulletins")
        self.new_bullet, self.BULLET_CREATED = self.filterlist(
            bullet, self.BULLET_CREATED, self.tup_type[2]
        )

        self.new_bullet_title = [new_bullet["title"]
                                 for new_bullet in self.new_bullet]
        self.logger.info(f"CSA Bulletins: {self.new_bullet_title}")

    def generate_new_bulletin_message(self, new_bullet) -> Embed:
        # Generate new CVE message for sending to discord
        embed = Embed(
            title=f"🔈 *{new_bullet['title']}*",
            description=new_bullet["description"]
            if len(new_bullet["description"]) < 500
            else new_bullet["description"][:500] + "...",
            timestamp=datetime.datetime.now(),
            color=Color.yellow(),
        )
        embed.add_field(
            name=f"📅  *Published*", value=f"{new_bullet['created']}", inline=True
        )
        embed.add_field(
            name=f"More Information",
            value=f"{new_bullet['csa']}",
            inline=False,
        )

        return embed
