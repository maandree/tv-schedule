import os, sys
# import pyexpat does not work, it is too strict
from subprocess import Popen, PIPE

NODE_OPEN = 0
NODE_SELF_CLOSING = 1
NODE_CLOSE = 2

cache = None

def all_indices(list, key):
    ret = []
    for i, e in enumerate(list):
        if e == key:
            ret.append(i)
    return ret

def index_any(list, *keys, select = None):
    if select is None:
        select = lambda l, k : l.index(k)
    for key in keys:
        if key in list:
            return select(list, key)
    raise Exception('no match found')

def get(url):
    cachefile = None
    if cache is not None:
        cachefile = cache + '/' + '%2F'.join(url.split('/')[4:])
        try:
            with open(cachefile, 'rb') as file:
                out = file.read()
            return out.decode('utf-8', 'replace')
        except:
            pass
    proc = Popen(['curl', url], stdout = PIPE, stderr = sys.stderr)
    out = proc.communicate()[0]
    if proc.returncode != 0:
        return None
    if cachefile is not None:
        try:
            with open(cachefile, 'wb') as file:
                file.write(out)
                file.flush()
        except:
            pass
    return out.decode('utf-8', 'replace')

class Node:
    def __init__(self, name, attrs, type):
        self.name = name
        self.attrs = attrs
        self.type = type
    def __getitem__(self, key):
        return self.attrs[key] if key in self.attrs else None
    def __repr__(self):
        a = '/' if self.type == NODE_CLOSE else ''
        c = '/' if self.type == NODE_SELF_CLOSING else ''
        b = ''
        for key in self.attrs:
            b += ' %s="%s"' % (key, self.attrs[key])
        return '<%s%s%s%s>' % (a, self.name, b, c)

def parse_xml(text, with_nbsp = False):
    entities = {
        'nbsp' : ' ',         'lt' : '<',        'gt' : '>',        'amp' : '&',       'quot' : '"',      'apos' : '\'',
        'cent' : '¢',         'pound' : '£',     'yen' : '¥',       'euro' : '€',      'copy' : '©',      'reg' : '®',
        'forall' : '∀',       'part' : '∂',      'exist' : '∃',     'empty' : '∅',     'nabla' : '∇',     'isin' : '∈',
        'notin' : '∉',        'ni' : '∋',        'prod' : '∏',      'sum' : '∑',       'minus' : '−',     'lowast' : '∗',
        'radic' : '√',        'prop' : '∝',      'infin' : '∞',     'ang' : '∠',       'and' : '∧',       'or' : '∨',
        'cap' : '∩',          'cup' : '∪',       'int' : '∫',       'there4' : '∴',    'sim' : '∼',       'cong' : '≅',
        'asymp' : '≈',        'ne' : '≠',        'equiv' : '≡',     'le' : '≤',        'ge' : '≥',        'sub' : '⊂',
        'sup' : '⊃',          'nsub' : '⊄',      'sube' : '⊆',      'supe' : '⊇',      'oplus' : '⊕',     'otimes' : '⊗',
        'perp' : '⊥',         'sdot' : '⋅',      'Alpha' : 'Α',     'Beta' : 'Β',      'Gamma' : 'Γ',     'Delta' : 'Δ',
        'Epsilon' : 'Ε',      'Zeta' : 'Ζ',      'Eta' : 'Η',       'Theta' : 'Θ',     'Iota' : 'Ι',      'Kappa' : 'Κ',
        'Lambda' : 'Λ',       'Mu' : 'Μ',        'Nu' : 'Ν',        'Xi' : 'Ξ',        'Omicron' : 'Ο',   'Pi' : 'Π',
        'Rho' : 'Ρ',          'Sigma' : 'Σ',     'Tau' : 'Τ',       'Upsilon' : 'Υ',   'Phi' : 'Φ',       'Chi' : 'Χ',
        'Psi' : 'Ψ',          'Omega' : 'Ω',     'alpha' : 'α',     'beta' : 'β',      'gamma' : 'γ',     'delta' : 'δ',
        'epsilon' : 'ε',      'zeta' : 'ζ',      'eta' : 'η',       'theta' : 'θ',     'iota' : 'ι',      'kappa' : 'κ',
        'lambda' : 'λ',       'mu' : 'μ',        'nu' : 'ν',        'xi' : 'ξ',        'omicron' : 'ο',   'pi' : 'π',
        'rho' : 'ρ',          'sigmaf' : 'ς',    'sigma' : 'σ',     'tau' : 'τ',       'upsilon' : 'υ',   'phi' : 'φ',
        'chi' : 'χ',          'psi' : 'ψ',       'omega' : 'ω',     'thetasym' : 'ϑ',  'upsih' : 'ϒ',     'straightphi' : 'ϕ',
        'piv' : 'ϖ',          'Gammad' : 'Ϝ',    'gammad' : 'ϝ',    'varkappa' : 'ϰ',  'varrho' : 'ϱ',    'straightepsilon' : 'ϵ',
        'backepsilon' : '϶',  'iexcl' : '¡',     'curren' : '¤',    'brvbar' : '¦',    'sect' : '§',      'uml' : '¨',
        'ordf' : 'ª',         'laquo' : '«',     'not' : '¬',       'shy' : '-',       'macr' : '°',      'deg' : '±',
        'sup2' : '²',         'sup3' : '³',      'acute' : '´',     'micro' : 'µ',     'para' : '¶',      'middot' : '·',
        'cedil' : '¸',        'sup1' : '¹',      'ordm' : 'º',      'raquo' : '»',     'frac14' : '¼',    'frac12' : '½',
        'frac34' : '¾',       'iquest' : '¿',    'Agrave' : 'À',    'Aacute' : 'Á',    'Acirc' : 'Â',     'Atilde' : 'Ã',
        'Auml' : 'Ä',         'Aring' : 'Å',     'AElig' : 'Æ',     'Ccedil' : 'Ç',    'Egrave' : 'È',    'Eacute' : 'É',
        'Ecirc' : 'Ê',        'Euml' : 'Ë',      'Igrave' : 'Ì',    'Iacute' : 'Í',    'Icirc' : 'Î',     'Iuml' : 'Ï',
        'ETH' : 'Ð',          'Ntilde' : 'Ñ',    'Ograve' : 'Ò',    'Oacute' : 'Ó',    'Ocirc' : 'Ô',     'Otilde' : 'Õ',
        'Ouml' : 'Ö',         'times' : '×',     'Oslash' : 'Ø',    'Ugrave' : 'Ù',    'Uacute' : 'Ú',    'Ucirc' : 'Û',
        'Uuml' : 'Ü',         'Yacute' : 'Ý',    'THORN' : 'Þ',     'szlig' : 'ß',     'agrave' : 'à',    'aacute' : 'á',
        'acirc' : 'â',        'atilde' : 'ã',    'auml' : 'ä',      'aring' : 'å',     'aelig' : 'æ',     'ccedil' : 'ç',
        'egrave' : 'è',       'eacute' : 'é',    'ecirc' : 'ê',     'euml' : 'ë',      'igrave' : 'ì',    'iacute' : 'í',
        'icirc' : 'î',        'iuml' : 'ï',      'eth' : 'ð',       'ntilde' : 'ñ',    'ograve' : 'ò',    'oacute' : 'ó',
        'ocirc' : 'ô',        'otilde' : 'õ',    'ouml' : 'ö',      'divide' : '÷',    'oslash' : 'ø',    'ugrave' : 'ù',
        'uacute' : 'ú',       'ucirc' : 'û',     'uuml' : 'ü',      'yacute' : 'ý',    'thorn' : 'þ',     'yuml' : 'ÿ',
        'fnof' : 'ƒ',         'imped' : 'Ƶ',     'gacute' : 'ǵ',    'jmath' : 'ȷ',     'circ' : 'ˆ',      'tilde' : '˜',
        'image' : 'ℑ',        'weierp' : '℘',    'real' : 'ℜ',      'trade' : '™',     'alefsym' : 'ℵ',   'loz' : '◊',
        'spades' : '♠',       'clubs' : '♣',     'hearts' : '♥',    'diams' : '♦',     'larr' : '←',      'uarr' : '↑',
        'rarr' : '↓',         'darr' : '→',      'harr' : '↔',      'crarr' : '↵',     'lArr' : '⇐',      'uArr' : '⇑',
        'rArr' : '⇒',         'dArr' : '⇓',      'hArr' : '⇔',      'Idot' : 'İ',      'inodot' : 'ı',    'kgreen' : 'ĸ',
        'Amacr' : 'Ā',        'Abreve' : 'Ă',    'Aogon' : 'Ą',     'Cacute' : 'Ć',    'Ccirc' : 'Ĉ',     'Cdod' : 'Ċ',
        'Ccaron' : 'Č',       'Dcaron' : 'Ď',    'Dstrok' : 'Đ',    'Emacr' : 'Ē',     'Edot' : 'Ė',      'Eogon' : 'Ę',
        'Ecaron' : 'Ě',       'Gcirc' : 'Ĝ',     'Gbreve' : 'Ğ',    'Gdot' : 'Ġ',      'Gcedil' : 'Ģ',    'Hcirc' : 'Ĥ',
        'Hstrok' : 'Ħ',       'Itilde' : 'Ĩ',    'Imacr' : 'Ī',     'Iogon' : 'Į',     'IJlog' : 'Ĳ',     'Jcirc' : 'Ĵ',
        'Kcedil' : 'Ķ',       'Lacute' : 'Ĺ',    'Lcedil' : 'Ļ',    'Lcaron' : 'Ľ',    'Lmidot' : 'Ŀ',    'Lstrok' : 'Ł',
        'Nacute' : 'Ń',       'Ncedil' : 'Ņ',    'Ncaron' : 'Ň',    'ENG' : 'Ŋ',       'Omacr' : 'Ō',     'Odblac' : 'Ő',
        'OElig' : 'Œ',        'Racute' : 'Ŕ',    'Rcedil' : 'Ŗ',    'Rcaron' : 'Ř',    'Sacute' : 'Ś',    'Scirc' : 'Ŝ',
        'Scedil' : 'Ş',       'Scaron' : 'Š',    'Tcedil' : 'Ţ',    'Tcaron' : 'Ť',    'Tstrok' : 'Ŧ',    'Utilde' : 'Ũ',
        'Umacr' : 'Ū',        'Ubreve' : 'Ŭ',    'Uring' : 'Ů',     'Udblac' : 'Ű',    'Uogon' : 'Ų',     'Wcirc' : 'Ŵ',
        'Ycirc' : 'Ŷ',        'Zacute' : 'Ź',    'Zdot' : 'Ż',      'Zcaron' : 'Ž',    'napos' : 'ŉ',     'Yuml' : 'Ÿ',
        'amacr' : 'ā',        'abreve' : 'ă',    'aogon' : 'ą',     'cacute' : 'ć',    'ccirc' : 'ĉ',     'cdod' : 'ċ',
        'ccaron' : 'č',       'dcaron' : 'ď',    'dstrok' : 'đ',    'emacr' : 'ē',     'edot' : 'ė',      'eogon' : 'ę',
        'ecaron' : 'ě',       'gcirc' : 'ĝ',     'gbreve' : 'ğ',    'gdot' : 'ġ',      'gcedil' : 'ģ',    'hcirc' : 'ĥ',
        'hstrok' : 'ħ',       'itilde' : 'ĩ',    'imacr' : 'ī',     'iogon' : 'į',     'ijlog' : 'ĳ',     'jcirc' : 'ĵ',
        'kcedil' : 'ķ',       'lacute' : 'ĺ',    'lcedil' : 'ļ',    'lcaron' : 'ľ',    'lmidot' : 'ŀ',    'lstrok' : 'ł',
        'nacute' : 'ń',       'ncedil' : 'ņ',    'ncaron' : 'ň',    'eng' : 'ŋ',       'omacr' : 'ō',     'odblac' : 'ő',
        'oelig' : 'œ',        'racute' : 'ŕ',    'rcedil' : 'ŗ',    'rcaron' : 'ř',    'sacute' : 'ś',    'scirc' : 'ŝ',
        'scedil' : 'ş',       'scaron' : 'š',    'tcedil' : 'ţ',    'tcaron' : 'ť',    'tstrok' : 'ŧ',    'utilde' : 'ũ',
        'umacr' : 'ū',        'ubreve' : 'ŭ',    'uring' : 'ů',     'udblac' : 'ű',    'uogon' : 'ų',     'wcirc' : 'ŵ',
        'ycirc' : 'ŷ',        'zacute' : 'ź',    'zdot' : 'ż',      'zcaron' : 'ž',    'frasl' : '⁄',     'oline' : '‾',
        'rsaquo' : '›',       'lsaquo' : '‹',    'prime' : '′',     'Prime' : '″',     'permil' : '‰',    'hellip' : '…',
        'lsquo' : '‘',        'rsquo' : '’',     'sbquo' : '‚',     'ldquo' : '“',     'rdquo' : '”',     'bdquo' : '„',
        'dagger' : '†',       'Dagger' : '‡',    'bull' : '•',      'ndash' : '–',     'mdash' : '—',     'ensp' : ' ',
        'emsp' : ' ',         'thinsp' : ' ',    'zwnj':chr(8204),  'zwj':chr(8205),   'lrm':chr(8206),   'rlm':chr(8207)
    }
    def p(text, trim):
        if trim:
            text = text.replace('\t', ' ').replace('\r', ' ').replace('\n', ' ').replace('\f', ' ')
            while '  ' in text:
                text = text.replace('  ', ' ')
            if text.startswith(' '):
                text = text[1:]
            if text.endswith(' '):
                text = text[:-1]
        buf, amp = '', None
        for c in text:
            if amp is not None:
                if c == ';':
                    if amp.startswith('#x'):
                        buf += chr(int(amp[2:], 16))
                    elif amp == '#0':
                        buf += '\0'
                    elif amp.startswith('#0'):
                        buf += chr(int(amp[2:], 8))
                    elif amp.startswith('#'):
                        buf += chr(int(amp[1:], 10))
                    else:
                        buf += entities[amp];
                    amp = None
                else:
                    amp += c
            elif c == '&':
                amp = ''
            else:
                buf += c
        if not with_nbsp:
            buf = buf.replace(' ', ' ')
        return buf
    ret = []
    buf, quote, lt, cdata = '', None, False, None
    for c in text:
        if lt:
            if cdata is not None:
                buf += c
                if len(cdata) > 0:
                    if c == cdata[0]:
                        cdata = cdata[1:]
                    else:
                        cdata = None
                elif buf.endswith(']]>'):
                    ret.append(buf[len('![CDATA[') : -3])
                    lt, buf, cdata = False, '', None
            elif quote is None and c == '>':
                cdata = None
                typ = NODE_OPEN
                if buf.startswith('/'):
                    typ = NODE_CLOSE
                    buf = buf[1:]
                elif buf.endswith('/'):
                    typ = NODE_SELF_CLOSING
                    buf = buf[:-1]
                elif buf.startswith('!') or buf.startswith('?'):
                    typ = -1
                if typ >= 0:
                    name, have_name, attr, key, value = '', False, {}, '', None
                    for c in buf:
                        if not have_name:
                            if c == ' ':
                                have_name = True
                            else:
                                name += c
                        elif c in '\"\'' and (quote is None or c == quote):
                            if quote is None:
                                quote = c
                            else:
                                quote = None
                        elif value is None:
                            if key == '' and c == ' ':
                                pass
                            elif c == ' ':
                                attr[key] = 'true'
                            elif c == '=':
                                if key == '':
                                    key = c
                                else:
                                    value = ''
                            else:
                                key += c
                        else:
                            if c == ' ' and quote is None:
                                attr[key] = p(value, False)
                                key, value = '', None
                            else:
                                value += c
                    if not key == '':
                        attr[key] = ('true' if value is None else p(value, False))
                    ret.append(Node(name, attr, typ))
                lt, buf = False, ''
            else:
                buf += c
                if c in '\"\'':
                    if quote is None:
                        quote = c
                    elif quote == c:
                        quote = None
        elif c == '<':
            buf = p(buf, True)
            if not buf == '':
                ret.append(buf)
            lt, buf, cdata = True, '', '![CDATA['
        else:
            buf += c
    if not lt:
        buf = p(buf, True)
        if not buf == '':
            ret.append(buf)
    ret_ = ret
    ret = []
    for e in ret_:
        if isinstance(e, str) and len(ret) > 0 and isinstance(ret[-1], str):
            ret = ret[:-1] + [ret[-1] + e]
        else:
            ret.append(e)
    return ret
