from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from bs4 import BeautifulSoup
import requests
import sqlite3
import datetime

SCOPES = ['https://www.googleapis.com/auth/calendar']

if __name__ == '__main__':
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    payload = {"userid": "INSERT_MACID", "pwd": "INSERT_PASSWORD"}
    session = requests.Session()

    s = session.post("https://epprd.mcmaster.ca/psp/prepprd/?cmd=login", data=payload)
    s = session.get("https://csprd.mcmaster.ca/psc/prcsprd/EMPLOYEE/SA/c/SA_LEARNER_SERVICES.SSS_STUDENT_CENTER.GBL")
    soup = BeautifulSoup(s.text, 'html.parser')

    courses_tbl = soup.find("table", {"class": "PSLEVEL1GRID"})
    table_rows = courses_tbl.find_all("tr")[1:]

    courses = []
    for course in table_rows:
        things = course.find_all("span")
        name = things[0].text.split("\r")[0]
        dept, code = name[:name.index("-")].split()
        sec = name[name.index("-") + 1:]

        try:
            conn = sqlite3.connect("courses.db")
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM '{dept}' WHERE ID = '{code}'")
            course_info = cur.fetchone()
            conn.close()
        except:
            courses.append("ERROR")
            course_info = ["Could not retrieve name"]

        course_name = course_info[0].replace("-", f"{sec} -")

        locations, starts, ends = [], [], []

        for i in range(0, len(things[1].text.split("\r")), 2):
            times = [things[1].text.split("\r")[i]]
            locations.append(things[1].text.split("\r")[i + 1])
            days_str = times[0].split()[0]
            days = [days_str[i:i + 2] for i in range(0, len(days_str), 2)]
            diff = {"Mo": 6, "Tu": 0, "We": 1, "Th": 2, "Fr": 3}
            start, end = times[0].split(" ")[1::2]

            if len(days) > 1 and days[0] == "Mo":
                start = datetime.datetime(2021, 9, 7 + diff[days[1]], int(start[:start.index(":")]) + 12 * (
                        start[-2:] == "PM" and start[:start.index(":")] != "12"), int(start[-4:-2]))
                end = datetime.datetime(2021, 9, 7 + diff[days[1]], int(end[:end.index(":")]) + 12 * (
                        end[-2:] == "PM" and end[:end.index(":")] != "12"), int(end[-4:-2]))
            else:
                start = datetime.datetime(2021, 9, 7 + diff[days[0]], int(start[:start.index(":")]) + 12 * (
                        start[-2:] == "PM" and start[:start.index(":")] != "12"), int(start[-4:-2]))
                end = datetime.datetime(2021, 9, 7 + diff[days[0]], int(end[:end.index(":")]) + 12 * (
                        end[-2:] == "PM" and end[:end.index(":")] != "12"), int(end[-4:-2]))

            event = {
                "kind": "calendar#event",
                "summary": course_name,
                "location": locations[int(i / 2)],
                "start": {
                    "dateTime": start.isoformat(),
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": end.isoformat(),
                    "timeZone": "America/New_York"
                },
                "recurrence": [
                    "RRULE:" + "FREQ=WEEKLY;BYDAY=" + ",".join(days) + ";UNTIL=20211209T000000Z"
                ]
            }

            event_result = service.events().insert(calendarId='primary', body=event).execute()
