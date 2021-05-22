import bs4
import requests
import re
import prettytable as pt
import telegram
import datetime

import conf.local.credentials as credentials
import conf.base.config as config


def clean_string(string):
    string = string.strip()
    string = string.replace("\n", "")
    string = string.replace("\xa0", "")
    string = re.sub(r' +', ' ', string)
    string = string.split('(PDF')[0]
    if string == '-':
        string = string.replace("-", "")
    return string


def create_table(columns, data):
    table = pt.PrettyTable(columns)

    for row in data:
        table.add_row(row)

    return table


def convert_month(month):
    month_dict = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December'
    }
    if month == 13:
        month = month_dict[1]
    else:
        month = month_dict[month]
    return month


def truncate_parse_table(table, fields):
    table = f'<pre>{table.get_string(fields=fields)}</pre>'
    curr_month = convert_month(datetime.datetime.now().month)
    next_month = convert_month(datetime.datetime.now().month + 1)
    desc = f'<b>{curr_month} application for {next_month} selection</b>'
    url = f'<a href="{config.site_url}">{desc}</a>'
    table = str(table+'\n'+url)

    return table


# download page data
getPage = requests.get(config.site_url)
getPage.raise_for_status()

# parse html
soup = bs4.BeautifulSoup(getPage.text, 'html.parser')
soup = soup.find('table')

# table headers
col_names = []
col_names_html = soup.find('thead').find_all('th')
for i in range(len(col_names_html)):
    col_names.append(clean_string(col_names_html[i].text))

# table body
body = []
body_html = soup.find('tbody').find_all('tr')
for i in range(len(body_html)):
    row = []
    for j in range(len(body_html[i].find_all('td'))):
        row.append(clean_string(body_html[i].find_all('td')[j].text))
    if len(row) < 7:
        row.insert(0, body[i-1][0])
    body.append(row)

col_new = []
j = 0
for i in range(len(body[0])):
    if body[0][i] == '':
        col_new.append(col_names[j])
        j += 1
    elif body[0][i] != '' and body[0][i+1] != '':
        col_new.append(body[0][i])
    else:
        col_new.append(body[0][i])
        j += 1

# send table
# print(create_table(col_new, body[1:]))
# requests.get(
#     f"https://api.telegram.org/bot{credentials.token}/sendMessage?chat_id={credentials.chat_id}&parse_mode=ParseMode.Markdown&text={create_table(col_new, body[1:])}"
#     )
bot = telegram.Bot(credentials.token)
msg = truncate_parse_table(create_table(col_new, body[1:]), config.fields)
bot.send_message(credentials.chat_id, msg, parse_mode=telegram.ParseMode.HTML)
