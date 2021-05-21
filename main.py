import bs4, requests
import re
import pandas as pd


def clean_string(string):
    string = string.replace("\n", "")
    string = string.replace("\xa0", "")
    string = re.sub(r' +', ' ', string)
    string = string.split('(PDF')[0]
    return string.strip()


# download page data
getPage = requests.get('https://www.hdb.gov.sg/cs/infoweb/residential/renting-a-flat/renting-from-hdb/parenthood-provisional-housing-schemepphs/application-procedure/flats-available-for-application-')
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
        j+=1
    elif body[0][i] != '' and body[0][i+1] != '':
        col_new.append('Available - '+body[0][i])
    else:
        col_new.append('Available - '+body[0][i])
        j+=1

df = pd.DataFrame(data=body[1:], columns=col_new)
print(df)
