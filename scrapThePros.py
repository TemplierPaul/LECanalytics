from urllib.request import Request, urlopen
import html
import ast
import json
import pandas as pd
import numpy as np
import math

def getHistory(name, games=None, verbose=True):
    if games is None: games = math.inf
    name = name.replace(' ', '+')
    req = Request(' http://euw.op.gg/summoner/userName=' + name , headers={'Accept-Encoding': 'deflate', 'User-Agent': 'Mozilla/5.0'})
    wp = urlopen(req).read().decode("utf-8")
    l = wp.split('GameItemWrap">')[1:]

    id = between(wp, 'summonerId=', '&')
    if verbose: print('Name', name, id)
    start = between(wp, 'data-last-info="', '"', jump=1)
    if verbose: print('Start', start)

    while len(l) < games:
        if verbose: print('API:', len(l))
        try:
            url = 'http://euw.op.gg/summoner/matches/ajax/averageAndList/startInfo=' + str(start) + '&summonerId=' + str(id)
            r = Request(url, headers={'Accept-Encoding': 'deflate', 'User-Agent': 'Mozilla/5.0'})
            s = urlopen(r).read().decode("utf-8")
            d = ast.literal_eval(s)
            start = str(d['lastInfo'])
            h = d['html']
            h = h.replace('\\/', '/')
            l += h.split('GameItemWrap">')[1:]
        except:
            if verbose: print("No more records")
            break

    out = pd.DataFrame(columns=['Date', 'Champion', 'Win', 'Kill', 'Death', 'Assist', 'Rune 1', 'Rune 2', 'Item_1', 'Item_2', 'Item_3', 'Item_4', 'Item_5', 'Item_6', 'Item_7'])
    for m in l:
        out = out.append(extractGameData(m, verbose=verbose), ignore_index=True)
    return out


def extractGameData(s, verbose=True):
    s = html.unescape(s)
    data = {}
    data['Date'] = between(s, "data-interval='60'>", '</span>')
    data['Win'] = between(s, 'GameItem ', ' ') == 'Win'
    try:
        data['Champion'] = between(s, 'champion/', '/statistics')
    except:
        data['Champion'] = between(s, 'champion\\/', '\\/statistics')

    r = between(s, '<div class="Runes">', '<div class="ChampionName">').split('Rune')
    data['Rune 1'] = between(r[1], 'alt="', '"')
    data['Rune 2'] = between(r[2], 'alt="', '"')

    data['Kill'] = between(s, '"Kill">', '</span>')
    data['Death'] = between(s, '"Death">', '</span>')
    data['Assist'] = between(s, '"Assist">', '</span>')

    i_l = between(s, '<div class="ItemList">', '<button class="Button OpenBuildButton tip"').split('<div class="Item">')[1:]
    index = 0
    for i in i_l:
        index += 1
        try:
            if between(i, 'class="Image ', '"') == 'NoItem':
                data['Item_' + str(index)] = None
            else:
                data['Item_' + str(index)] = between(i, 'alt="', '"')
        except:
            print('Could be a problem?')
    if verbose : print(data)
    return data

def between(s, c1, c2, jump=0):
    return s.split(c1)[1+jump].split(c2)[0]

def findSoloqID():
    url = 'https://www.trackingthepros.com/d/list_players?filter_region=EU&&_=1566420777677'
    req = Request(url, headers={'Accept-Encoding': 'deflate', 'User-Agent': 'Mozilla/5.0'})
    s = urlopen(req).read().decode("utf-8").replace('\\u00e4', 'a')
    l = json.loads(s)['data']
    print(len(l), l)
    output = pd.DataFrame(columns=['Name', 'Team', 'Role', 'Accounts'])
    for d in l:
        if int(d['accounts']) > 0:
            u = 'https://www.trackingthepros.com/player/' + d['name']
            r = Request(u, headers={'Accept-Encoding': 'deflate', 'User-Agent': 'Mozilla/5.0'})
            wp =  urlopen(r).read().decode("utf-8")
            try:
                ids = between(wp, 'Accounts', 'inactive_account')
                id_l = []
                j=0
                while True :
                    try:
                        id_l.append(between(ids, '[EUW]</b> ', '</td>', jump=j))
                        j +=1
                    except:
                        break
                if len(id_l)> 0:
                    print(d['name'], '->', id_l)
                else:
                    print(d['name'], '->', 'No Active EUW Account')
                dico = {
                    'Name': d['name'],
                    'Team': d['team'],
                    'Role': d['role'],
                    'Accounts': id_l
                }
                output = output.append(dico, ignore_index=True)
            except:
                raise Exception
        else:
            print(d['name'], '->', 'No Account')
            dico = {
                'Name': d['name'],
                'Team': d['team'],
                'Role': d['role'],
                'Accounts': []
            }
            output = output.append(dico, ignore_index=True)
    output.to_csv('accounts.csv')
    return output

def scrapThePros(accounts='accounts.csv'):
    col = ['Date', 'Player', 'Team', 'Role', 'Account', 'Champion', 'Win', 'Kill', 'Death', 'Assist', 'Rune 1', 'Rune 2', 'Item_1', 'Item_2', 'Item_3', 'Item_4', 'Item_5', 'Item_6', 'Item_7']
    matches = pd.DataFrame(columns=col)
    if accounts is None:
        accounts = findSoloqID()
    else:
        accounts = pd.read_csv('accounts.csv', index_col=0, sep=',')
    print(len(accounts), 'players to scrap')
    for index, row in accounts.iterrows():
        print('\nPlayer:', row['Name'])
        ids = ast.literal_eval(row['Accounts'])
        for id in ids:
            print('  -Account:', id)
            try:
                df = getHistory(id, verbose=False)
                df ['Player'] = row['Name']
                df ['Team'] = row['Team']
                df ['Role'] = row['Role']
                df ['Account'] = id
                matches = pd.concat([matches, df], axis=0, sort=True)
            except:
                print("No data to scrap")
            print('Total matches:', len(matches))
    matches.to_csv('matches.csv', columns=col)
    return matches



def main():
    return scrapThePros()
