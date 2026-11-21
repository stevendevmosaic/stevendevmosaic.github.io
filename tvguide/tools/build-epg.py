#!/usr/bin/env python3
"""Convert the Freeview-EPG XMLTV file (github.com/dp247/Freeview-EPG) into the small static JSON
files the UK TV Guide reads. Replaces the blocked Sky awk.epgsky.com API.

  python3 -I build-epg.py [OUT_DIR] [epg.xml]      (downloads the XMLTV if no file is given)

Output (per region):  OUT/<region>/channels.json   [{sid,num,name,g}]
                      OUT/<region>/<yyyymmdd>.json {sid: [[start_epoch, secs, title, synopsis, genre, new], ...]}
sid = Sky provider id (same as the old API, so logos/picks keep working) or the XMLTV id when Sky has none.
Day = London-local date of the programme start. Genre codes: 3 movies, 5 news, 6 kids, 7 sport, 9 music/radio.
"""
import sys, os, re, json, gzip, urllib.request, datetime as dt
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'data')
SRC = sys.argv[2] if len(sys.argv) > 2 else None
XML_URL = 'https://raw.githubusercontent.com/dp247/Freeview-EPG/master/epg.xml'
LIST_URL = 'https://raw.githubusercontent.com/wiki/dp247/Freeview-EPG/Channels-list.md'
LON = ZoneInfo('Europe/London')

# Regional variants to keep per region (XMLTV ids) -> display name
REGIONS = {
    'scotland': {'BBCOneScotHD.uk': 'BBC One Scotland', 'STVCentral.uk': 'STV', 'Channel4Scotland.uk': 'Channel 4',
                 'STVCentralPlus1.uk': 'STV +1', 'Channel4Plus1Scotland.uk': 'Channel 4 +1'},
    'london': {'BBCOneLondonHD.uk': 'BBC One London', 'ITV1London.uk': 'ITV1', 'Channel4London.uk': 'Channel 4',
               'ITV1Plus1London.uk': 'ITV1 +1', 'Channel4Plus1London.uk': 'Channel 4 +1'},
}
REGIONAL = re.compile(r'^(BBCOne(?!ScotHD|LondonHD)|ITV1(?!Plus1Granada)|ITV1Plus1|Channel4(?!HD)|STV|BBCTwo(?!HD)|BBCRadio(?!Scotland|Alba)|Channel4Plus1)')
KEEP_ALWAYS = {'BBCTwoHD.uk', 'BBCScotland.uk', 'BBCRScotland.uk'}
NUM_OVERRIDE = {'BBC One Scotland': 101, 'BBC One London': 101, 'STV': 103, 'ITV1': 103}
OLD_SID = {'STVCentral.uk': '6210', 'STVCentralPlus1.uk': 'stv-c-p1'}   # keep the old STV id so saved picks still match

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'uktvguide-build'}), timeout=120) as r:
        return r.read()

def norm(n): return re.sub(r'[^a-z0-9+]', '', n.lower().replace('&', 'and').replace(' hd', '').replace('+1', 'plus1'))

def kind(name, cat):
    n = name.lower()
    if re.search(r'radio|\bfm\b|kiss|magic|kerrang|absolute|heart|capital|classic fm|smooth|planet rock|jazz|gigs|mtv|music|vh1|4music|clubland|the box|box hits|kisstory|now 80|now 90|now 70|now rock|scuzz|flaunt|chart', n): return 9
    if re.search(r'news|parliament|cnn|jazeera|\bcna\b|cnbc|bloomberg|euronews|newsmax|arise|france 24|dw\b|nhk|gb news|sky news', n): return 5
    if re.search(r'cbbc|cbeebies|cartoon|nick|disney|boomerang|pop\b|tiny|milkshake|citv|kids|baby|duck|cartoonito|trollied|sky kids', n): return 6
    if re.search(r'sport|eurosport|tnt|racing|laliga|mutv|lfc|chelsea|golf|motor|wwe|boxing|darts|cricket|premier league', n): return 7
    if re.search(r'movie|film|cinema|horror|western|talking pictures|great! movies|sony|action', n): return 3
    return 0

def main():
    xml = open(SRC, 'rb').read() if SRC else get(XML_URL)
    listmd = get(LIST_URL).decode('utf8')
    pid = {}
    for l in listmd.splitlines():
        p = [x.strip() for x in l.split('|')]
        if len(p) > 6 and p[1] in ('sky', 'freeview') and re.fullmatch(r'\d+', p[4]): pid[p[3]] = p[4]
    nums = json.load(open(os.path.join(HERE, 'sky-numbers-raw.json')))
    byname = {}
    for n, name in nums.items():
        for part in re.split(r'[;/]|\(', name):
            k = norm(part.strip(' )'))
            if k and k not in byname: byname[k] = int(n)

    root = ET.fromstring(xml)
    chans = {}
    for c in root.findall('channel'):
        chans[c.get('id')] = c.findtext('display-name', '').strip()
    progs = {}
    for p in root.findall('programme'):
        progs.setdefault(p.get('channel'), []).append(p)

    for region, want in REGIONS.items():
        rdir = os.path.join(OUT, region); os.makedirs(rdir, exist_ok=True)
        cl, days = [], {}
        for xid, raw in chans.items():
            if any(xid in w for r, w in REGIONS.items() if r != region) and xid not in want: continue
            if xid.endswith('.ie') or raw.endswith('ROI'): continue          # Republic of Ireland variants
            if xid.endswith('.uk') and xid[:-3] + 'HD.uk' in chans: continue  # prefer the HD feed (as the old guide did)
            if xid in want: name = want[xid]
            elif xid in KEEP_ALWAYS or not REGIONAL.match(xid): name = re.sub(r'\s*HD$', '', raw).strip()
            else: continue
            if xid.startswith('BBCRadio') and xid not in KEEP_ALWAYS and not pid.get(xid): continue
            sid = OLD_SID.get(xid) or pid.get(xid) or xid
            num = NUM_OVERRIDE.get(name) or byname.get(norm(name)) or byname.get(norm(raw)) or 0
            g = kind(name, None)
            cl.append({'sid': sid, 'num': num, 'name': name, 'g': g})
            for p in progs.get(xid, []):
                t = p.findtext('title', '').strip()
                if not t: continue
                st = dt.datetime.strptime(p.get('start')[:14], '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc)
                if p.get('start')[15:] and p.get('start')[15:] != '+0000':
                    pass  # feed is UTC (+0000); other offsets not seen
                en = dt.datetime.strptime(p.get('stop')[:14], '%Y%m%d%H%M%S').replace(tzinfo=dt.timezone.utc)
                d = int((en - st).total_seconds())
                if d <= 0: continue
                sy = (p.findtext('desc', '') or '').strip().replace('\n', ' ')
                if len(sy) > 320: sy = sy[:317].rsplit(' ', 1)[0] + '…'
                ep = [e.text for e in p.findall('episode-num') if e.get('system') == 'onscreen']
                if ep and sy and ep[0] not in t: sy = f'{ep[0]}. {sy}'
                eg = 3 if any(c.text == 'Movie' for c in p.findall('category')) else g
                key = st.astimezone(LON).strftime('%Y%m%d')
                days.setdefault(key, {}).setdefault(sid, []).append([int(st.timestamp()), d, t, sy, eg, 1 if p.find('premiere') is not None else 0])
        cl.sort(key=lambda c: (c['num'] or 9999, c['name']))
        # channels with no Sky number: radio -> 900+, others -> 1000+ (the page shows numbers >= 1000 as blank)
        un = [c for c in cl if not c['num']]
        for i, c in enumerate(x for x in un if x['g'] == 9): c['num'] = 900 + i
        for i, c in enumerate(x for x in un if not x['num']): c['num'] = 1000 + i
        cl.sort(key=lambda c: (c['num'], c['name']))
        json.dump(cl, open(os.path.join(rdir, 'channels.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
        for f in os.listdir(rdir):
            if re.fullmatch(r'\d{8}\.json', f): os.remove(os.path.join(rdir, f))
        for key, d in days.items():
            for evs in d.values(): evs.sort()
            json.dump(d, open(os.path.join(rdir, key + '.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
        meta = {'built': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'days': sorted(days)}
        json.dump(meta, open(os.path.join(rdir, 'meta.json'), 'w'))
        un = [c['name'] for c in cl if not c['num']]
        print(f'{region}: {len(cl)} channels ({len(un)} unnumbered), days {meta["days"][0]}..{meta["days"][-1]}')
        print('  unnumbered sample:', un[:25])

main()
