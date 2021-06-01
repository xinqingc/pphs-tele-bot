import bs4
import requests
import re
import prettytable as pt
import datetime
import pandas as pd
# import telegram

import conf.local.credentials as credentials
import conf.base.config as config


def clean_string(string):
    string = string.strip()
    string = string.replace("\n", " ")
    string = string.replace("\xa0", "")
    string = re.sub(r' +', ' ', string)
    string = string.split('(PDF')[0]
    if string == '-':
        string = string.replace("-", "")
    string = string.strip()
    return string


def pretty_table(data):
    table = pt.PrettyTable(data.columns.to_list())

    for _, row in data.iterrows():
        table.add_row(row.to_list())

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


def truncate_format_message(table, fields):
    table = f'<pre>{table.get_string(fields=fields)}</pre>'
    curr_month = convert_month(datetime.datetime.now().month)
    next_month = convert_month(datetime.datetime.now().month + 1)
    desc = f'<b>{curr_month} application for {next_month} selection</b>'
    url = f'<a href="{config.site_url}">{desc}</a>'
    table = str(table+'\n'+url)

    return table


def get_table(type):
    if type == 'available':
        url = config.site_url
        row_len = 7
    elif type == 'rent':
        url = config.rent_url
        row_len = 4

    # download page
    getPage = requests.get(url)
    getPage.raise_for_status()

    # parse html
    soup = bs4.BeautifulSoup(getPage.text, 'html.parser')

    # check if table updates
    if type == 'available':
        next_month = convert_month(datetime.datetime.now().month + 1)
        header = soup.find('h3').text
        if next_month not in header:
            raise Exception('Table not updated yet!')

    soup = soup.find('table')

    # table headers
    col_names = []
    col_names_html = soup.find('thead').find_all('tr')[-1].find_all('th')
    for i in range(len(col_names_html)):
        col_names.append(clean_string(col_names_html[i].text))

    # table body
    body = []
    body_html = soup.find('tbody').find_all('tr')
    for i in range(len(body_html)):
        row = []
        for j in range(len(body_html[i].find_all('td'))):
            row.append(clean_string(body_html[i].find_all('td')[j].text))
        if len(row) < row_len:
            row.insert(0, body[i-1][0])
        body.append(row)

    if type == 'available':
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

        col_names = col_new
        body = body[1:]
        df = pd.DataFrame(data=body, columns=col_names)

    elif type == 'rent':
        df = pd.DataFrame(data=body, columns=col_names)

    return col_names, body, df


def concat_avail_rent(row_available, row_rent, room_num):
    row_available = row_available[f'{int(room_num)}-room']
    row_rent = row_rent[f'{int(room_num)}-room']
    if row_available != '':
        concat_string = f"{row_available} - {row_rent}"
    else:
        concat_string = ''
    return concat_string


col_names, _, df = get_table('available')
_, _, rent_df = get_table('rent')

# convert address to street name
street_list = df['Address'].to_list()
for idx, val in enumerate(street_list):
    val = val.split(' ')
    # clean address
    if 'Dr' in val:
        val[val.index('Dr')] = 'Drive'
    if 'Ave' in val:
        val[val.index('Ave')] = 'Avenue'
    if 'Rd' in val:
        val[val.index('Rd')] = 'Road'
    if 'Payoh' in val:
        val = ['Toa', 'Payoh']
    for x, y in enumerate(val):
        # skip first word in address, probably 'Blk' or blk number
        if x == 0:
            pass
        else:
            # skip blk number or '&'
            if y[0].isdigit() or y == '&':
                pass
            else:
                street_list[idx] = ' '.join(val[x:])
                break

df['street'] = street_list
df['temp_index'] = list(range(len(df)))

new_rent_df = pd.DataFrame(columns=[
    'temp_index',
    'Location',
    '2-room',
    '3-room',
    '4-room'
])

for index, row in df.iterrows():
    row_list = [row['temp_index']]
    for x, y in rent_df.iterrows():
        if row['street'].lower() in y['Location'].lower():
            row_list.append(y['Location'])
            row_list.append(concat_avail_rent(row, y, 2))
            row_list.append(concat_avail_rent(row, y, 3))
            row_list.append(concat_avail_rent(row, y, 4))
            row_list = pd.DataFrame([row_list], columns=[
                'temp_index',
                'Location',
                '2-room',
                '3-room',
                '4-room'
            ])
            new_rent_df = new_rent_df.append(row_list)
            break
        else:
            pass

df = df.drop(columns=['2-room', '3-room', '4-room'])
df = df.merge(
    new_rent_df[['temp_index', '2-room', '3-room', '4-room']],
    how='left',
    on='temp_index')
df = df[col_names]

msg = truncate_format_message(pretty_table(df), config.fields)

# send table
requests.get(
    f"https://api.telegram.org/bot{credentials.token}/sendMessage?chat_id={credentials.chat_id}&parse_mode=html&text={msg}"
    )
# bot = telegram.Bot(credentials.token)
# bot.send_message(
#     credentials.chat_id,
#     msg,
#     parse_mode=telegram.ParseMode.HTML
# )
