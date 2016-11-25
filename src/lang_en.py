import sys
import util

class Parser:
    def __init__(self):
        self.MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
        self.page_parser_flag_count = 4
        self.last_episode = None
        self.episode_offset = 0
        self.postponed_set_episode_offset = False
        self.previous_season = 1
    
    def is_episode_section(self, elem, alt_episodes_heading):
        if alt_episodes_heading == 0:
            headings = ('episodes', 'episode list', 'episode guide', 'seasons', 'season list')
        elif alt_episodes_heading == 1:
            headings = ('series overview', 'broadcast and release', 'series')
        elif alt_episodes_heading == 2:
            headings = ('main series',)
        return elem.lower().replace('listing', 'list') in headings
    
    def to_num(self, text):
        lower = text.lower()
        nums = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
                'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
                'nineteen', 'twenty')
        if lower in nums:
            return str(nums.index(lower))
        if lower in ('nought', 'nil', 'null'):
            return '0'
        return text
    
    def is_season_section(self, elem):
        return \
            elem.lower().split(' ')[0] in ('season', 'series') and \
            self.to_num(elem.replace(':', ' ').split(' ')[1])[:1] in '0123456789'
    
    def parse_season(self, elem):
        return int(self.to_num(elem.replace(':', ' ').split(' ')[1]), 10)
    
    def parse_page(self, page, flags = 0):
        single_season         = (flags & 1) != 0
        no_episodes_heading   = (flags & 2) != 0
        alt_episodes_heading  = (flags & 4) >> 2
        alt_episodes_heading |= (flags & 8) >> 2
        if (no_episodes_heading and alt_episodes_heading > 0) or (alt_episodes_heading > 2):
            return []
        in_h2, in_h3, in_tr, in_td = False, False, False, False
        have_episodes, colspan, ignore = no_episodes_heading, None, None
        ignore_table = False
        rows, columns, text = [], [], ''
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
                if self.is_episode_section(elem, alt_episodes_heading):
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
        if human.lower() in ('tba', 'tbd', 'not scheduled'):
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
        else:
            date = '-'.join((date + '-..-..').split('-')[:3])
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
        return util.index_any(columns, 'noinseason', 'noinseries', 'episode', 'ep', 'episodeno',
                              'releaseorder', 'seasonepno', 'serial', 'no')
    
    def get_title_column(self, columns):
        try:
            return util.index_any(columns, 'title', 'episodetitle', 'eptitle', 'cartoons')
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
    
    def is_num(self, num):
        if num[-1] in 'abcdefghijklmnopqrstuvwxyz':
            num, alpha = num[:-1], num[-1]
        try:
            int(num, 10)
            return True
        except:
            return False
    
    def cmp_num(self, a_num, b_num):
        a_alpha, b_alpha = None, None
        if a_num[-1] in 'abcdefghijklmnopqrstuvwxyz':
            a_num, a_alpha = a_num[:-1], a_num[-1]
        if b_num[-1] in 'abcdefghijklmnopqrstuvwxyz':
            b_num, b_alpha = b_num[:-1], b_num[-1]
        a_num, b_num = int(a_num), int(b_num)
        if a_num != b_num:
            return -1 if a_num < b_num else +1
        if a_num != b_num:
            return -1 if a_num < b_num else +1
        return 0
    
    def parse_episode(self, episode):
        if '(' in episode: # TODO select the lowest
            episode = episode.split('(')[1].split(')')[0]
        for c in '–-/&':
            episode = episode.replace(c, ' ')
        episodes = []
        for e in episode.split(' '):
            if e == '':
                continue
            e = self.parse_episode_no(e)
            episodes.append('xx' if e is None else ('%02i%s' % e))
        if len(episodes) == 0:
            episodes = ['xx']
        elif len(episodes) > 1:
            if all(self.is_num(e) for e in episodes):
                for i in range(1, len(episodes)):
                    if self.cmp_num(episodes[i], episodes[i - 1]) <= 0:
                        raise Exception('Episode numbers inside a single episode is out of order')
            episodes = [episodes[0], episodes[-1]] ## See first episode in https://en.wikipedia.org/wiki/List_of_TaleSpin_episodes
        if self.season != self.previous_season or self.postponed_set_episode_offset:
            if episodes[0] == 'xx':
                self.postponed_set_episode_offset = True
            elif self.last_episode is not None and self.cmp_num(episodes[0], self.last_episode) > 0:
                self.postponed_set_episode_offset = False
                num, alpha = episodes[0], ''
                if num[-1] in 'abcdefghijklmnopqrstuvwxyz':
                    num, alpha = num[:-1], num[-1]
                self.episode_offset = int(num, 10) - 1
        if episodes[-1] != 'xx':
            self.last_episode = episodes[-1]
        if self.episode_offset > 0:
            for i in range(len(episodes)):
                episode = episodes[i]
                if episode == 'xx':
                    continue
                num, alpha = episode, ''
                if num[-1] in 'abcdefghijklmnopqrstuvwxyz':
                    num, alpha = num[:-1], num[-1]
                episodes[i] = '%02i%s' % (int(num, 10) - self.episode_offset, alpha)
        self.previous_season = self.season
        return episodes
    
    def simplify_column(self, column):
        column = column.replace('#', 'no').lower().replace('º', 'o').replace('.', '')
        ignored = ('original', 'us', 'uk')
        def sub(w):
            w = w.replace('name', 'title')
            w = w.replace('number', 'no')
            return w
        return ''.join(sub(w) for w in column.split(' ') if w not in ignored).split('[')[0]
    
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
        flagses = list(range(1 << self.page_parser_flag_count))
        for url in urls:
            page = util.get(url)
            try:
                page = util.parse_xml(page)
                for flags in flagses:
                    try:
                        episodes = self.parse_table(self.parse_page(page, flags))
                        if len(episodes) > 0:
                            return (url, episodes)
                    except:
                        pass
            except:
                pass
        return None

class Darkwing_Duck(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.seasons = ['disney afternoon', 'abc season 1', 'abc season 2']
    def is_season_section(self, elem):
        return elem.lower().split('(')[0].strip() in self.seasons
    def parse_season(self, elem):
        return self.seasons.index(elem.lower().split('(')[0].strip()) + 1

class Wacky_Races(Parser):
    def __init__(self):
        Parser.__init__(self)
    def parse_episode(self, episode):
        if episode.startswith('WR-'):
            episode = episode[3:]
        return Parser.parse_episode(self, episode)

class Tiny_Toon_Adventures(Parser):
    def __init__(self):
        Parser.__init__(self)
        self.modify_episode = None
    def parse_episode(self, episode):
        episode = episode.split(' ')[0]
        if self.modify_episode is None:
            e = episode
            for c in '123456789':
                e = e.replace(c, '0')
            self.modify_episode = e in ('0-000', '00-000')
        if self.modify_episode:
            episode = episode.split('-')[1]
        return Parser.parse_episode(self, episode)

def parse(show):
    renames = {
        'Two Guys, a Girl and a Pizza Place' : 'Two Guys and a Girl',
    }
    
    if show.startswith('https://') or show.startswith('http://'):
        urls = [show]
    else:
        if show in renames:
            show = renames[show]
        url = show.replace(' ', '_')
        for c in '%#?&': ## % first
            url = url.replace(c, ''.join('%%%02X' % b for b in c.encode('utf-8')))
        urls = ['https://en.wikipedia.org/wiki/List_of_%s_episodes',
                'https://en.wikipedia.org/wiki/%s',
                'https://en.wikipedia.org/wiki/%s_(TV_series)']
        urls = [u % url for u in urls]
    
    def is_article(show):
        for url in urls:
            if url.split('?')[0].split('#')[0].split('/')[-1] == show:
                return True
        return False
    
    articles = {
        'List_of_Darkwing_Duck_episodes'        : Darkwing_Duck,
        'Wacky_Races'                           : Wacky_Races,
        'List_of_Tiny_Toon_Adventures_episodes' : Tiny_Toon_Adventures
    }
    
    parser = None
    for article in articles:
        if is_article(article):
            parser = articles[article]()
    if parser is None:
        parser = Parser()
    
    return parser.parse(urls)
