# PyInstaller spec: builds a self-contained backend (no Python needed on the user's machine).
#   cd backend && pyinstaller livelyrics-backend.spec --noconfirm
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hidden = (
    collect_submodules('engineio.async_drivers')      # Socket.IO "threading" mode is imported dynamically
    + collect_submodules('socketio')
    + ['simple_websocket', 'wsproto', 'acoustid', 'bs4', 'dotenv']
)
import sys
if sys.platform == 'win32':
    for mod in ('winrt.runtime', 'winrt.windows.media.control', 'winrt.windows.foundation',
                'winrt.windows.foundation.collections', 'winrt.windows.storage.streams'):
        try:
            hidden += [mod] + collect_submodules(mod)
        except Exception:
            hidden.append(mod)
datas = collect_data_files('certifi') + collect_data_files('groq')

a = Analysis(
    ['app.py'],
    pathex=['.'],
    datas=datas,
    hiddenimports=hidden,
    excludes=['tkinter', 'matplotlib', 'pytest', 'IPython', 'PIL'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='livelyrics-backend', console=True, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='livelyrics-backend', upx=False)
