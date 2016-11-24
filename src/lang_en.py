import sys
import util

class Parser:
    def __init__(self):
        self.MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
    
    def is_episode_section(self, elem):
        return elem.lower() in ('episodes', 'episode list', 'episode guide', 'seasons', 'season list')
    
    def is_season_section(self, elem):
        return elem.lower().split(' ')[0] in ('season', 'series') and elem.split(' ')[1][:1] in '0123456789'
    
    def parse_season(self, elem):
        return int(elem.replace(':', ' ').split(' ')[1], 10)
    
    def parse_page(self, page, flags = 0):
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
                    if in_h2 and have_episodes:
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
                if self.is_episode_section(elem):
                    have_episodes = True
                    if single_season:
                        rows = []
                        seasons.append((1, rows))
            elif in_h3:
                if self.is_season_section(elem):
                    rows = []
                    seasons.append((self.parse_season(elem), rows))
            elif ignore is None and in_td and have_episodes and colspan in (None, '1'):
                elem = elem.replace('\u200a', '')
                text += ' ' + elem
        if len(seasons) == 1 and len(seasons[0][1]) == 0:
            return []
        return seasons
    
    def parse_human_date(self, human):
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
            if m is None and field in self.MONTHS:
                m = self.MONTHS.index(field) + 1
        if y is None and m is None and d is None:
            return 'Unaired\t'
        y = str(y)
        m = '..' if m is None else ('%02i' % m)
        d = '..' if d is None else ('%02i' % d)
        return '%s-%s-%s' % (y, m, d)
    
    def parse_date(self, date):
        if '( ' in date:
            date = date.split('( ')[1].split(' )')[0].strip()
            date = date.split('T')[0] # See https://en.wikipedia.org/wiki/List_of_Shameless_(UK_TV_series)_episodes S10E09
        elif '.' in date:
            date = date.split('.')
            date[1], date[2] = date[2], date[1]
            date = '-'.join(date)
        else:
            date = self.parse_human_date(date)
        if '-' not in date:
            date = self.parse_human_date(date)
        return date
    
    def parse_episode_no(self, num):
        try:
            alpha = ''
            if num[-1] in 'abcdefghijklmnopqrstuvwxyz':
                num, alpha = num[:-1], num[-1]
            if '.' in num:
                self.jointno = False
                (self.season, num) = num.split('.')
                self.season = int(self.season, 10)
            num = int(num, 10)
            if self.jointno is None:
                self.jointno = num >= 100
            if self.jointno:
                self.season, num = num // 100, num % 100
            return (num, alpha)
        except: # See https://en.wikipedia.org/wiki/List_of_Everybody_Loves_Raymond_episodes between S06E20 and S06E21
            return None # extra
    
    def get_episode_column(self, columns):
        return util.index_any(columns, 'noinseason', 'noinseries', 'episode', 'ep', 'episodeno', 'no', 'releaseorder')
    
    def get_title_column(self, columns):
        try:
            return util.index_any(columns, 'title', 'episodetitle', 'eptitle')
        except:
            return None
    
    def get_date_column(self, columns):
        return util.index_any(columns, 'airdate', 'releasedate')
    
    def parse_title(self, title):
        title = title.strip()
        if title.startswith('"'):
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
        return title.replace('  ', ' ')
    
    def parse_episode(self, episode):
        if '(' in episode:
            episode = episode.split('(')[1].split(')')[0]
        for c in '–-/':
            episode = episode.replace(c, ' ')
        episodes = []
        for e in episode.split(' '):
            if e == '':
                continue
            e = self.parse_episode_no(e)
            episodes.append('xx' if e is None else ('%02i%s' % e))
        return episodes
    
    def simplify_column(self, column):
        column = column.replace('#', 'no').lower().replace('º', 'o').replace('.', '')
        ignored = ('original', 'us', 'uk')
        return ''.join(w for w in column.split(' ') if w not in ignored).split('[')[0]
    
    def parse_table(self, seasons):
        self.jointno = None
        found = []
        for self.season, episodes in seasons:
            if len(episodes) == 0:
                continue
            columns, episodes = [self.simplify_column(t) for t in episodes[0]], episodes[1:]
            col_episode = self.get_episode_column(columns)
            col_title = self.get_title_column(columns)
            col_date = self.get_date_column(columns)
            for cols in episodes:
                episode = '-'.join(self.parse_episode(cols[col_episode]))
                title = self.parse_title(cols[col_title]) if col_title is not None else None
                date = self.parse_date(cols[col_date])
                if title is not None:
                    found.append('%s\tS%02iE%s - %s' % (date, self.season, episode, title))
                else:
                    found.append('%s\tS%02iE%s' % (date, self.season, episode))
        return found
    
    def parse(self, urls):
        for url in urls:
            page = util.get(url)
            try:
                page = util.parse_xml(page)
                for flags in range(1 << 2):
                    episodes = self.parse_table(self.parse_page(page, flags))
                    if len(episodes) > 0:
                        for episode in episodes:
                            print(episode)
                        return True
            except:
                pass
        return False

def parse(show):
    if show.startswith('https://') or show.startswith('http://'):
        urls = [show]
    else:
        url = show.replace(' ', '_')
        for c in '%#?&': ## % first
            url = url.replace(c, ''.join('%%%02X' % b for b in c.encode('utf-8')))
        urls = ['https://en.wikipedia.org/wiki/List_of_%s_episodes',
                'https://en.wikipedia.org/wiki/%s',
                'https://en.wikipedia.org/wiki/%s_(TV_series)']
        urls = [u % url for u in urls]
    
    if not Parser().parse(urls):
        print('%s: don\'t know how to parse' % sys.argv[0], file = sys.stderr)
        sys.exit(1)
