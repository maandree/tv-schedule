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
    url = url.replace(' ', '_')
    for c in '%#?&': ## % first
        url = url.replace(c, ''.join('%%%02X' % b for b in c.encode('utf-8')))
    urls = ['https://en.wikipedia.org/wiki/List_of_%s_episodes',
            'https://en.wikipedia.org/wiki/%s',
            'https://en.wikipedia.org/wiki/%s_(TV_series)']
    urls = [u % url for u in urls]

def parse_page(page, flags = 0):
    single_season       = (flags & 1) != 0
    no_episodes_heading = (flags & 2) != 0
    in_h2, in_h3, in_tr, in_td = False, False, False, False
    have_episodes, colspan, ignore = no_episodes_heading, None, None
    ignore_table = False
    rows, columns, text = [], None, ''
    seasons = []
    for elem in page:
        if isinstance(elem, util.Node):
            if elem.name == 'table':
                if elem.type == util.NODE_OPEN:
                    ignore_table = elem['class'] == 'cquote'
                else:
                    ignore_table = False
            elif ignore_table:
                pass
            elif not no_episodes_heading and elem.name == 'h2':
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
            elif elem.name == ignore:
                ignore = None
            elif elem.name == 'sup':
                cls = elem['class']
                if elem.type == util.NODE_OPEN and cls is not None and 'reference' in cls.split(' '):
                    ignore = 'sup'
            elif elem.name == 'span':
                cls = elem['class']
                if elem.type == util.NODE_OPEN and cls is not None and 'sortkey' in cls.split(' '):
                    ignore = 'span'
        elif ignore_table:
            pass
        elif in_h2:
            if elem.lower() in ('episodes', 'episode list', 'episode guide', 'seasons', 'season list'):
                have_episodes = True
                if single_season:
                    rows = []
                    seasons.append(('1', rows))
        elif in_h3:
            if elem.lower().startswith('season ') or elem.startswith('series ') and elem.split(' ')[1][:1] in '0123456789':
                rows = []
                seasons.append((elem.replace(':', ' ').split(' ')[1], rows))
        elif ignore is None and in_td and have_episodes and colspan in (None, '1'):
            elem = elem.replace('\u200a', '')
            text += ' ' + elem
    if len(seasons) == 1 and len(seasons[0][1]) == 0:
        return []
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
    human = human.replace(',', ' ').replace('–', ' ').replace('-', ' ').split(' ')
    y, m, d = None, None, None
    for field in human:
        try:
            if y is None and len(field) >= 4:
                y = int(field, 10)
                continue
        except:
            pass
        try:
            if d is None:
                d = int(field, 10)
                continue
        except:
            pass
        field = field[:3].lower()
        if m is None and field in MONTHS:
            m = MONTHS.index(field) + 1
    if y is None and m is None and d is None:
        return 'Unaired\t'
    y = str(y)
    m = '..' if m is None else ('%02i' % m)
    d = '..' if d is None else ('%02i' % d)
    return '%s-%s-%s' % (y, m, d)

def parse_date(date):
    if '( ' in date:
        date = date.split('( ')[1].split(' )')[0].strip()
    elif '.' in date:
        date = date.split('.')
        date[1], date[2] = date[2], date[1]
        date = '-'.join(date)
    else:
        date = parse_human_date(date)
    if '-' not in date:
        date = parse_human_date(date)
    return date

def index_any(list, *keys):
    for key in keys:
        if key in titles:
            return titles.index(key)
    return titles.index(keys[0])

jointno = None
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
    col_episode = index_any(titles, 'noinseason', 'noinseries', 'episode', 'ep', 'episodeno', 'no', 'releaseorder')
    try:
        col_title = titles.index('title')
    except:
        col_title = None
    col_air = index_any(titles, 'airdate', 'releasedate')
    def parse_episode_no(num):
        global jointno, season
        try:
            alpha = ''
            if num[-1] in 'abcdefghijklmnopqrstuvwxyz':
                num, alpha = num[:-1], num[-1]
            num = int(num, 10)
            if jointno is None:
                jointno = num >= 100
            if jointno:
                season, num = num // 100, num % 100
            return (num, alpha)
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
        title = cols[col_title].strip() if col_title is not None else None
        air = parse_date(cols[col_air])
        if title is not None and title.startswith('"'):
            q = None
            for i, c in enumerate(title):
                if c == '"':
                    q = i
            if q is not None:
                title = (title[1:q] + title[q + 1:]).strip()
            if '"/"' in title:
                title = title.replace('"/"', '" "')
            if '" "' in title:
                title = ' '.join(('%s' if i == 0 else '(A.K.A %s)') % t for i, t in enumerate(title.split('" "')))
        if title is not None:
            print('%s\tS%02iE%s - %s' % (air, season, episode, title.replace('  ', ' ')))
        else:
            print('%s\tS%02iE%s' % (air, season, episode))
