"""
Cross-platform "what is playing right now" reader.

  Windows : System Media Transport Controls (SMTC) via winrt
  macOS   : AppleScript for Spotify / Apple Music (accurate position + duration),
            then `nowplaying-cli` if installed, then Chrome/Safari tab title
            (YouTube etc.; position only if "Allow JavaScript from Apple Events"
            is enabled in the browser).
  Linux   : `playerctl` if installed.

get_media_info() returns:
  {title, artist, album, status('playing'|'paused'|'stopped'), position_ms,
   duration_ms (0 if unknown), artwork_url, source, app}
or None when nothing is playing.
"""

import asyncio
import json
import re
import shutil
import subprocess
import sys

from recognition.titles import clean_title_artist

_SEP = '\x1f'


def _finish(title, artist, album, status, position_ms, duration_ms, artwork, source, app):
    title, artist = clean_title_artist(title, artist)
    if not title:
        return None
    return {
        'title': title,
        'artist': artist,
        'album': (album or '').strip(),
        'status': status,
        'position_ms': int(max(0, position_ms or 0)),
        'duration_ms': int(max(0, duration_ms or 0)),
        'artwork_url': artwork or '',
        'source': source,
        'app': app,
    }


def _num(s):
    try:
        return float(str(s).replace(',', '.'))
    except Exception:
        return 0.0


# ───────────────────────── macOS ─────────────────────────

_SPOTIFY_SCRIPT = '''
set sep to (ASCII character 31)
tell application "Spotify"
  if player state is stopped then return ""
  set pst to player state as string
  set trk to current track
  return "Spotify" & sep & pst & sep & (name of trk) & sep & (artist of trk) & sep & (album of trk) & sep & (player position as string) & sep & ((duration of trk) as string) & sep & (artwork url of trk)
end tell
'''

_MUSIC_SCRIPT = '''
set sep to (ASCII character 31)
tell application "Music"
  if player state is stopped then return ""
  set pst to player state as string
  set trk to current track
  return "Music" & sep & pst & sep & (name of trk) & sep & (artist of trk) & sep & (album of trk) & sep & (player position as string) & sep & (((duration of trk) * 1000) as string) & sep & ""
end tell
'''


def _is_running(proc_name):
    try:
        return subprocess.run(['pgrep', '-x', proc_name], capture_output=True, timeout=2).returncode == 0
    except Exception:
        return False


def _osascript(script, timeout=3):
    try:
        out = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=timeout)
        if out.returncode != 0:
            return None
        return out.stdout.strip()
    except Exception:
        return None


def _mac_native():
    # Prefer whichever app is actually playing; fall back to a paused one.
    paused = None
    for proc, script in (('Spotify', _SPOTIFY_SCRIPT), ('Music', _MUSIC_SCRIPT)):
        if not _is_running(proc):
            continue
        info = _parse_native(_osascript(script))
        if info and info['status'] == 'playing':
            return info
        paused = paused or info
    return paused


def _parse_native(out):
    if not out:
        return None
    parts = out.split(_SEP)
    if len(parts) < 8:
        return None
    app, st, title, artist, album, pos, dur, art = parts[:8]
    status = 'playing' if st == 'playing' else 'paused'
    return _finish(title, artist, album, status, _num(pos) * 1000, _num(dur), art, 'applescript', app)


def _mac_nowplaying_cli():
    exe = shutil.which('nowplaying-cli')
    if not exe:
        return None
    try:
        out = subprocess.run(
            [exe, 'get', 'title', 'artist', 'album', 'duration', 'elapsedTime', 'playbackRate'],
            capture_output=True, text=True, timeout=3)
        vals = out.stdout.split('\n')
        if len(vals) < 6 or vals[0].strip() in ('', 'null', '(null)'):
            return None
        clean = lambda v: '' if v.strip() == 'null' or v.strip() == '(null)' else v.strip()
        rate = _num(vals[5]) if clean(vals[5]) else 0
        return _finish(clean(vals[0]), clean(vals[1]), clean(vals[2]),
                       'playing' if rate > 0 else 'paused',
                       _num(vals[4]) * 1000, _num(vals[3]) * 1000, '', 'nowplaying-cli', 'system')
    except Exception:
        return None


# Sites we look for in browser tabs (extend with MUSIC_SITES="host1,host2" in .env)
_MUSIC_HOSTS = [
    'youtube.com/watch', 'music.youtube.com', 'open.spotify.com', 'music.apple.com',
    'jiosaavn.com', 'music.amazon.', 'soundcloud.com', 'gaana.com', 'wynk.in',
    'tidal.com', 'deezer.com', 'hungama.com', 'pandora.com', 'bandcamp.com',
    'audiomack.com', 'qobuz.com', 'napster.com', 'last.fm', 'twitch.tv',
]

# Runs inside the page. Uses the Media Session API (what the OS media keys use), which almost
# every music site fills in, plus the <audio>/<video> element for exact position.
# No backslashes / double quotes issues: the script is embedded in AppleScript.
_JS = (
    "(function(){var ms=navigator.mediaSession,md=ms&&ms.metadata,r={};"
    "if(md){r.t=md.title;r.a=md.artist;r.al=md.album;"
    "if(md.artwork&&md.artwork.length)r.art=md.artwork[md.artwork.length-1].src}"
    "var els=[].slice.call(document.querySelectorAll('video,audio')).filter(function(e){return isFinite(e.duration)&&e.duration>0});"
    "var m=els.filter(function(e){return !e.paused})[0]||els[0];"
    "if(m){r.p=m.currentTime;r.d=m.duration;r.s=m.paused?'paused':'playing'}"
    "else{var p=document.querySelector('[data-testid=playback-position]'),d=document.querySelector('[data-testid=playback-duration]');"
    "if(p&&d){var f=function(x){return x.textContent.trim().split(':').reduce(function(t,v){return t*60+Number(v)},0)};"
    "var b=document.querySelector('[data-testid=control-button-playpause]');"
    "r.p=f(p);r.d=f(d);r.c=1;r.s=(b&&/pause/i.test(b.getAttribute('aria-label')||''))?'playing':'paused'}}"
    "if(!r.s&&ms)r.s=ms.playbackState==='playing'?'playing':'paused';"
    "return JSON.stringify(r)})()"
)


def _hosts():
    import os
    extra = [h.strip() for h in os.getenv('MUSIC_SITES', '').split(',') if h.strip()]
    return _MUSIC_HOSTS + extra


def _url_cond():
    return ' or '.join(f'u contains "{h}"' for h in _hosts())


def _chromium_script(app):
    return f'''
set sep to (ASCII character 31)
set rec to (ASCII character 30)
set out to ""
if application "{app}" is running then
  tell application "{app}"
    repeat with w in windows
      repeat with t in tabs of w
        set u to URL of t
        if {_url_cond()} then
          set info to ""
          try
            set info to execute t javascript "{_JS.replace('"', chr(92) + '"')}"
          end try
          set out to out & (title of t) & sep & u & sep & info & sep & (id of w) & sep & (id of t) & rec
        end if
      end repeat
    end repeat
  end tell
end if
return out
'''


def _chromium_fast_script(app, wid, tid):
    """Query ONE known tab (cheap) instead of scanning every tab of every window."""
    return f'''
set sep to (ASCII character 31)
tell application "{app}"
  try
    set t to tab id {tid} of window id {wid}
    set info to ""
    try
      set info to execute t javascript "{_JS.replace('"', chr(92) + '"')}"
    end try
    return (title of t) & sep & (URL of t) & sep & info
  on error
    return ""
  end try
end tell
'''


def _safari_script():
    return f'''
set sep to (ASCII character 31)
set rec to (ASCII character 30)
set out to ""
if application "Safari" is running then
  tell application "Safari"
    repeat with w in windows
      repeat with t in tabs of w
        set u to URL of t
        if u is not missing value and ({_url_cond()}) then
          set info to ""
          try
            set info to do JavaScript "{_JS.replace('"', chr(92) + '"')}" in t
          end try
          set out to out & (name of t) & sep & u & sep & info & rec
        end if
      end repeat
    end repeat
  end tell
end if
return out
'''


_BROWSERS = ('Google Chrome', 'Brave Browser', 'Microsoft Edge', 'Arc', 'Vivaldi', 'Chromium')


_tab_cache = {'app': None, 'wid': None, 'tid': None, 'scan_at': 0.0}
FULL_SCAN_EVERY = 8.0      # s: re-scan all tabs this often (catches switching to another music tab)
IDLE_SCAN_EVERY = 3.0      # s: when no music tab is known, scan this rarely


def _mac_browser():
    """Music in browser tabs (any site in _MUSIC_HOSTS), read via the Media Session API.

    Scanning every tab is expensive (and stalls the browser's UI thread), so after finding the
    music tab we poll just that tab and only rescan occasionally.
    """
    import time
    now = time.monotonic()
    c = _tab_cache

    # Fast path: one known tab
    if c['app'] and now - c['scan_at'] < FULL_SCAN_EVERY:
        out = _osascript(_chromium_fast_script(c['app'], c['wid'], c['tid']), timeout=4)
        parts = (out or '').split(_SEP)
        if len(parts) >= 3 and parts[0]:
            m = _parse_tab(c['app'], parts[0], parts[1], parts[2])
            if m and (m['status'] == 'playing' or now - c["scan_at"] < 4.0):
                return m                     # playing, or paused very recently scanned
        c['app'] = None                      # tab gone / paused a while: rescan (another tab may be playing)
    elif not c['app'] and now - c['scan_at'] < IDLE_SCAN_EVERY:
        return None

    c['scan_at'] = now
    found = []
    jobs = [(app, _chromium_script(app)) for app in _BROWSERS if _is_running(app)]
    if _is_running('Safari'):
        jobs.append(('Safari', _safari_script()))
    for app, script in jobs:
        out = _osascript(script, timeout=6)
        for rec in (out or '').split('\x1e'):
            parts = rec.split(_SEP)
            if len(parts) < 3 or not parts[0]:
                continue
            m = _parse_tab(app, parts[0], parts[1], parts[2])
            if m:
                if len(parts) >= 5 and app != 'Safari':
                    m['_tab'] = (app, parts[3], parts[4])
                found.append(m)
    if not found:
        return None
    best = next((m for m in found if m['status'] == 'playing'), found[0])
    tab = best.pop('_tab', None)
    for m in found:
        m.pop('_tab', None)
    if tab:
        c['app'], c['wid'], c['tid'] = tab
    return best


def _parse_tab(app, tab_title, url, info):
    meta = {}
    try:
        meta = json.loads(info) if info else {}
    except Exception:
        pass

    title, artist = (meta.get('t') or '').strip(), (meta.get('a') or '').strip()
    if not title:
        # No Media Session metadata: fall back to the tab title
        title = tab_title
        if 'open.spotify.com' in url:
            if ' • ' not in title:
                return None      # idle Spotify tab ("Spotify – Web Player")
            title, artist = [x.strip() for x in title.split(' • ', 1)]
        else:
            title = re.sub(r'\s*[-|]\s*(YouTube( Music)?|Apple Music|JioSaavn|Amazon Music|SoundCloud)\s*$', '', title).strip()
            title = re.sub(r'^\(\d+\)\s*', '', title)           # "(3) Song" notification counter

    if 'youtube.com' in url and 'music.youtube.com' not in url and ' - ' in title:
        artist = ''      # on plain YouTube the "artist" is just the channel; the title carries the real one
    known = 'p' in meta
    status = meta.get('s') or 'playing'
    pos = (meta.get('p') or 0) * 1000
    dur = (meta.get('d') or 0) * 1000
    m = _finish(title, artist, meta.get('al') or '', status, pos, dur, meta.get('art') or '', 'browser', app)
    if m:
        m['position_known'] = known
        m['meta_artist'] = bool(artist)                           # artist came from the site itself
        m['coarse'] = bool(meta.get('c'))                         # position is whole seconds (Spotify web DOM timer)
    return m


def _mac_info():
    return _mac_native() or _mac_nowplaying_cli() or _mac_browser()


# ───────────────────────── Windows ─────────────────────────

_win_loop = None


async def _win_async():
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    )
    manager = await MediaManager.request_async()
    session = manager.get_current_session()
    if session is None:
        return None
    info = await session.try_get_media_properties_async()
    playback = session.get_playback_info()
    timeline = session.get_timeline_properties()
    status = {4: 'playing', 5: 'paused', 3: 'stopped'}.get(int(playback.playback_status), 'stopped')
    if status == 'stopped':
        return None
    pos = timeline.position.total_seconds() * 1000
    try:
        dur = (timeline.end_time - timeline.start_time).total_seconds() * 1000
    except Exception:
        dur = 0
    app = ''
    try:
        app = session.source_app_user_model_id or ''
    except Exception:
        pass
    return _finish(info.title or '', info.artist or '', info.album_title or '',
                   status, pos, dur, '', 'smtc', app)


def _win_info():
    global _win_loop
    try:
        if _win_loop is None or _win_loop.is_closed():
            _win_loop = asyncio.new_event_loop()
        return _win_loop.run_until_complete(_win_async())
    except ImportError:
        return None
    except Exception as e:
        print(f"[MediaSession] SMTC error: {e}")
        return None


# ───────────────────────── Linux ─────────────────────────

def _linux_info():
    exe = shutil.which('playerctl')
    if not exe:
        return None
    try:
        fmt = _SEP.join(['{{title}}', '{{artist}}', '{{album}}', '{{status}}',
                         '{{position}}', '{{mpris:length}}', '{{mpris:artUrl}}'])
        out = subprocess.run([exe, 'metadata', '--format', fmt], capture_output=True, text=True, timeout=3)
        p = out.stdout.strip().split(_SEP)
        if len(p) < 7:
            return None
        return _finish(p[0], p[1], p[2], 'playing' if p[3] == 'Playing' else 'paused',
                       _num(p[4]) / 1000, _num(p[5]) / 1000, p[6], 'mpris', 'playerctl')
    except Exception:
        return None


def get_media_info():
    if sys.platform == 'darwin':
        return _mac_info()
    if sys.platform == 'win32':
        return _win_info()
    return _linux_info()


# ───────────────────────── Controls (seek / play / next) ─────────────────────────

_MAC_APPS = {'Spotify': 'Spotify', 'Music': 'Music'}
_MAC_CMD = {'toggle': 'playpause', 'next': 'next track', 'prev': 'previous track'}


def control(action, app='', position_sec=None):
    """action: 'toggle' | 'next' | 'prev' | 'seek'. Returns True if the command was sent."""
    if sys.platform == 'darwin':
        target = _MAC_APPS.get(app)
        if not target:
            # nothing controllable: pick whichever native player is running
            target = next((p for p in _MAC_APPS if _is_running(p)), None)
        if not target:
            return False
        if action == 'seek':
            cmd = f'set player position to {float(position_sec):.2f}'
        else:
            cmd = _MAC_CMD.get(action)
            if not cmd:
                return False
        return _osascript(f'tell application "{target}" to {cmd}') is not None
    if sys.platform == 'win32':
        try:
            return _win_loop_run(_win_control(action, position_sec))
        except Exception as e:
            print(f"[MediaSession] control error: {e}")
            return False
    if shutil.which('playerctl'):
        cmd = {'toggle': ['play-pause'], 'next': ['next'], 'prev': ['previous'],
               'seek': ['position', f'{float(position_sec or 0):.2f}']}.get(action)
        return bool(cmd) and subprocess.run(['playerctl', *cmd], capture_output=True).returncode == 0
    return False


def _win_loop_run(coro):
    global _win_loop
    if _win_loop is None or _win_loop.is_closed():
        _win_loop = asyncio.new_event_loop()
    return _win_loop.run_until_complete(coro)


async def _win_control(action, position_sec):
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    )
    session = (await MediaManager.request_async()).get_current_session()
    if session is None:
        return False
    if action == 'toggle':
        return await session.try_toggle_play_pause_async()
    if action == 'next':
        return await session.try_skip_next_async()
    if action == 'prev':
        return await session.try_skip_previous_async()
    if action == 'seek':
        return await session.try_change_playback_position_async(int(float(position_sec) * 10_000_000))
    return False
