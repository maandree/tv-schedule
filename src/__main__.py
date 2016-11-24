#!/usr/bin/env python3

import sys

def usage():
    print('Usage: %s [-l langcode] (<show> | <url>)' % sys.argv[0], file = sys.stderr)
    sys.exit(1)

lang = None

i, n = 1, len(sys.argv)
def getarg():
    global i, j, n, m
    j += 1
    if j == m:
        i += 1
        if i == n:
            usage()
        ret = sys.argv[i]
    else:
        ret = arg[j:]
    j = m
    return ret
while i < n:
    if sys.argv[i] == '--':
        i += 1
        break
    elif not sys.argv[i].startswith('-'):
        break
    arg = sys.argv[i]
    j, m = 1, len(arg)
    while j < m:
        if arg[j] == 'l':
            lang = getarg()
        else:
            usage()
        j += 1
    i += 1
if i == n:
    usage()
show = ' '.join(sys.argv[i:])

if lang is None:
    lang = 'en'
    if show.startswith('http://') or show.startswith('https://'):
        lang = show.split(':')[1].split('/')[2].split('.')[0]
    lang = lang.lower()

if lang == 'en':
    import lang_en
    lang_en.parse(show)
else:
    print('%s: unsupported language: %s' % (sys.argv[0], lang), file = sys.stderr)
    sys.exit(1)
