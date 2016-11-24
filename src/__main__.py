#!/usr/bin/env python3

import sys
import util

if len(sys.argv) < 2:
    print('Usage: %s (<show> | <url>)' % sys.argv[0], file = sys.stderr)
    sys.exit(1)

url = ' '.join(sys.argv[1:])
if url.startswith('https://') or url.startswith('http://'):
    urls = [url]
else:
    url = url.replace(' ', '_').replace('[', '(').replace(']', ')')
    urls = ['https://en.wikipedia.org/wiki/List_of_%s_episodes',
            'https://en.wikipedia.org/wiki/%s']
    urls = [u % url for u in urls]

def parse_page(page, flags = 0):
    single_season       = (flags & 1) != 0
    no_episodes_heading = (flags & 2) != 0
    in_h2, in_h3, in_tr, in_td = False, False, False, False
    have_episodes, colspan, ignore = no_episodes_heading, None, False
    rows, columns, text = [], None, ''
    seasons = []
    for elem in page:
        if isinstance(elem, util.Node):
            if not no_episodes_heading and elem.name == 'h2':
                in_h2 = elem.type == util.NODE_OPEN
                if in_h2:
                    if have_episodes:
                        break
            elif elem.name == ('h2' if no_episodes_heading else 'h3'):
                in_h3 = elem.type == util.NODE_OPEN
                if in_h3:
                    rows = []
            elif elem.name == 'tr':
                in_tr = elem.type == util.NODE_OPEN
                if not in_tr:
                    if columns is not None and len(columns) > 0:
                        rows.append(columns)
                    columns = []
            elif in_tr and elem.name in ('td', 'th'):
                in_td = elem.type == util.NODE_OPEN
                if in_td:
                    colspan = elem['colspan']
                    text = ''
                elif len(text) > 0:
                    columns.append(text[1:])
            elif elem.name == 'sup':
                ignore = elem.type == util.NODE_OPEN and elem['class'] == 'reference'
        elif in_h2:
            if elem.lower() in ('episodes', 'episode list', 'episode guide', 'seasons', 'season list'):
                have_episodes = True
                if single_season:
                    rows = []
                    seasons.append(('1', rows))
        elif in_h3:
            if elem.lower().startswith('season ') or elem.startswith('series '):
                rows = []
                seasons.append((elem.replace(':', ' ').split(' ')[1], rows))
        elif not ignore and in_td and have_episodes and colspan in (None, "1"):
            elem = elem.replace('\u200a', '')
            text += ' ' + elem
    return seasons

seasons = []
for url in urls:
    page = util.get(url)
    try:
        page = util.parse_xml(page)
        for flags in range(1 << 2):
            seasons = parse_page(page, flags)
            if len(seasons) > 0:
                break
        if len(seasons) > 0:
            break
    except:
        pass
if len(seasons) == 0:
    print('%s: don\'t know how to parse' % sys.argv[0], file = sys.stderr)
    sys.exit(1)

MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')

def parse_human_date(human):
    if human in ('TBA', 'TBD'):
        return '....-..-..'
    human = human.replace(',', ' ').replace('  ', ' ').split(' ')
    y, m, d = None, None, None
    for field in human:
        try:
            if len(field) >= 4:
                y = int(field, 10)
                continue
        except:
            pass
        try:
            d = int(field, 10)
            continue
        except:
            pass
        m = MONTHS.index(field[:3].lower()) + 1
    y = str(y)
    m = '..' if m is None else ('%02i' % m)
    d = '..' if d is None else ('%02i' % d)
    return '%s-%s-%s' % (y, m, d)

def index_any(list, *keys):
    for key in keys:
        if key in titles:
            return titles.index(key)
    return titles.index(keys[0])

alphabet = 'abcdefghijklmnopqrstuvwxyz'
for season, episodes in seasons:
    if len(episodes) == 0:
        continue
    try:
        season = int(season)
    except:
        continue
    def simplify(t):
        t = t.replace('#', 'no').lower().replace('º', 'o').replace('.', '')
        ignored = ('original', 'us', 'uk')
        return ''.join(w for w in t.split(' ') if w not in ignored).split('[')[0]
    titles = [simplify(t) for t in episodes[0]]
    episodes = episodes[1:]
    col_episode = index_any(titles, 'noinseason', 'noinseries', 'ep', 'episodeno', 'no', 'releaseorder')
    col_title = titles.index('title')
    col_air = index_any(titles, 'airdate', 'releasedate')
    def parse_episode_no(num):
        try:
            alpha = ''
            if num[-1] in alphabet:
                num, alpha = num[:-1], num[-1]
            return (int(num, 10), alpha)
        except: # See https://en.wikipedia.org/wiki/List_of_Everybody_Loves_Raymond_episodes between S06E20 and S06E21
            return None # extra
    for cols in episodes:
        episode = cols[col_episode]
        if '(' in episode:
            episode = episode.split('(')[1].split(')')[0]
        for c in '–-/':
            episode = episode.replace(c, ' ')
        episodes = []
        for e in episode.split(' '):
            if e == '':
                continue
            e = parse_episode_no(e)
            episodes.append('xx' if e is None else ('%02i%s' % e))
        episode = '-'.join(episodes)
        title = cols[col_title].strip()
        air = cols[col_air]
        if '(' in air:
            air = air.split('(')[1].split(')')[0].strip()
        elif '.' in air:
            air = air.split('.')
            air[1], air[2] = air[2], air[1]
            air = '-'.join(air)
        else:
            air = parse_human_date(air)
        if '-' not in air:
            air = parse_human_date(air)
        if title.startswith('"'):
            q = None
            for i, c in enumerate(title):
                if c == '"':
                    q = i
            if q is not None:
                title = (title[1:q] + title[q + 1:]).strip()
            if '" "' in title:
                title = ' '.join(('%s' if i == 0 else '(A.K.A %s)') % t for i, t in enumerate(title.split('" "')))
        print('%s\tS%02iE%s - %s' % (air, season, episode, title.replace('  ', ' ')))
