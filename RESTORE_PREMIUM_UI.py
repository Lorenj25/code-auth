#!/usr/bin/env python3
"""Restore CodeAuthentic premium UI from the reviewed frontend resources.

Refuses to overwrite unknown files. Makes per-file backups, no ML/back-end access.
"""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MODAL_START = '      {logoutConfirmOpen && ('
MODAL_END = '    </>\n  );'


def read(path):
    return path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')


def replace_modal(nav, modal):
    start = nav.find(MODAL_START)
    end = nav.find(MODAL_END, start) if start >= 0 else -1
    if start < 0 or end < 0 or nav.count(MODAL_START) != 1:
        raise ValueError('Cannot locate a unique logout modal block')
    return nav[:start] + modal + nav[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    src = Path(__file__).resolve().parent / 'resources'
    navfile = root / 'src/components/Navbar.tsx'
    cssfile = root / 'src/global.css'
    if not navfile.is_file() or not cssfile.is_file():
        print('STOPPED SAFELY: Expected src/components/Navbar.tsx and src/global.css were not both found.', file=sys.stderr)
        return 1
    oldnav, oldcss = read(navfile), read(cssfile)
    premium_nav = read(src / 'Navbar.premium.tsx')
    broken_nav = read(src / 'Navbar.old.tsx')
    premium_css = read(src / 'global.recovered.css')
    modal = (premium_nav[premium_nav.index(MODAL_START):premium_nav.index(MODAL_END, premium_nav.index(MODAL_START))])

    try:
        # Existing premium header can have later local changes: preserve those, and
        # upgrade its dialog only if it is the reviewed dialog from the old UI.
        if 'ca-header-action' in oldnav and 'ca-profile-trigger' in oldnav:
            current_start = oldnav.index(MODAL_START)
            current_end = oldnav.index(MODAL_END, current_start)
            current_modal = oldnav[current_start:current_end]
            if 'ca-logout-shell' in current_modal:
                newnav = oldnav
                print('[NAV] Premium header and modal already present. Preserving file.')
            elif 'Come back soon!' in current_modal and 'onLogout();' in current_modal:
                newnav = replace_modal(oldnav, modal)
                print('[NAV] Preserving premium header, upgrading only logout modal.')
            else:
                raise ValueError('Premium navbar has a custom logout dialog that cannot be merged safely')
        elif 'const [navHidden, setNavHidden]' in oldnav and 'ca-logout-shell' in oldnav:
            # Check old navbar non-modal portions against the older reviewed source.
            oldstart=broken_nav.index(MODAL_START);oldend=broken_nav.index(MODAL_END, oldstart)
            navstart=oldnav.index(MODAL_START);navend=oldnav.index(MODAL_END, navstart)
            if oldnav[:navstart] != broken_nav[:oldstart] or oldnav[navend:] != broken_nav[oldend:]:
                raise ValueError('Older navbar contains additional edits; refusing wholesale restoration')
            newnav = premium_nav
            print('[NAV] Restoring the premium header and keeping the new logout modal.')
        elif oldnav == premium_nav:
            newnav=oldnav
            print('[NAV] Already restored.')
        else:
            raise ValueError('Unrecognized Navbar.tsx version; will not overwrite newer edits')

        # CSS in the first logout patch lacked both premium navbar styling and the
        # instructor dashboard styling. Recover only recognized older stylesheets.
        known_css = [read(src / f'global.{name}.css') for name in ('logout','mobile','nav')]
        if oldcss in known_css:
            newcss = premium_css
            print('[CSS] Replacing recognized older stylesheet with merged premium CSS.')
        elif 'Premium instructor console' in oldcss and '.ca-header-action' in oldcss:
            if '.ca-logout-btn-primary' in oldcss and '.ca-logout-illustration' in oldcss:
                newcss = oldcss
                print('[CSS] Premium dashboard and logout modal styles already present.')
            else:
                modal_css = read(src / 'global.recovered.css').split('/* Logout confirm — elevated premium card with richer contrast */', 1)[1]
                newcss = oldcss.rstrip() + '\n\n/* Logout confirm — elevated premium card with richer contrast */' + modal_css
                print('[CSS] Preserving current premium styles and adding missing logout styles.')
        else:
            raise ValueError('Unrecognized stylesheet; not overwriting possible newer UI changes')
    except (ValueError, IndexError) as exc:
        print('STOPPED SAFELY:', exc, file=sys.stderr)
        print('Please upload current Navbar.tsx and global.css for an exact merge.', file=sys.stderr)
        return 1

    changed=[(navfile,newnav),(cssfile,newcss)]
    changed=[(p,data) for p,data in changed if read(p)!=data]
    if not changed:
        print('ALREADY RESTORED. No files changed.')
        return 0
    backup=root/('_premium_ui_recovery_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    for p,_ in changed:
        dest=backup/p.relative_to(root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p,dest)
    written=[]
    try:
        for p, data in changed:
            tmp=p.with_name(p.name + '.premium_restore_tmp')
            tmp.write_text(data,encoding='utf-8',newline='')
            tmp.replace(p)
            written.append(p)
            print('Updated:',p.relative_to(root))
    except Exception as exc:
        for p in written:
            shutil.copy2(backup/p.relative_to(root),p)
        print('ERROR: File write failed; changes rolled back:',exc,file=sys.stderr)
        return 1
    print('Backup:',backup)
    print('Restored premium navbar, dashboard styles, and logout modal; ML/backend untouched.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
