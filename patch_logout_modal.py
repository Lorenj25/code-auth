#!/usr/bin/env python3
"""Safe, idempotent in-place update of CodeAuthentic logout modal only."""
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys

MODAL_START = '      {logoutConfirmOpen && ('
MODAL_END = '    </>\n  );'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    patch_dir = Path(__file__).resolve().parent
    navbar_path = root / 'src' / 'components' / 'Navbar.tsx'
    css_path = root / 'src' / 'global.css'

    for p in (navbar_path, css_path):
        if not p.is_file():
            print(f'STOPPED SAFELY: Missing required file {p}', file=sys.stderr)
            return 1

    original_nav = navbar_path.read_text(encoding='utf-8-sig')
    original_css = css_path.read_text(encoding='utf-8-sig')
    source_modal = (patch_dir / 'resources' / 'modal_fragment.txt').read_text(encoding='utf-8')
    source_styles = (patch_dir / 'resources' / 'premium_logout_styles.css').read_text(encoding='utf-8')

    start = original_nav.find(MODAL_START)
    end = original_nav.find(MODAL_END, start) if start >= 0 else -1
    if start < 0 or end < 0 or original_nav.count(MODAL_START) != 1:
        print('STOPPED SAFELY: Logout dialog location changed. No files were modified.', file=sys.stderr)
        return 1
    existing_modal = original_nav[start:end]
    if 'ca-logout-shell' in existing_modal:
        new_nav = original_nav
        print('Logout dialog markup is already upgraded.')
    else:
        required = (
            'Are you sure you want to leave?',
            'logoutLeaveArt',
            'setLogoutConfirmOpen(false)',
            'onLogout();',
        )
        if not all(x in existing_modal for x in required) or '      )}' not in existing_modal:
            print('STOPPED SAFELY: Logout dialog has custom changes; refusing to overwrite it.', file=sys.stderr)
            return 1
        if "from 'lucide-react'" not in original_nav or ' X ' not in original_nav.split("from 'lucide-react'")[0].split('import')[-1] and ' X,' not in original_nav:
            # Required icon was present in the reviewed versions, avoid an invalid build if removed locally.
            if not any(x in original_nav for x in ('{ X,', ', X,', ', X }')):
                print('STOPPED SAFELY: X icon import not found; send current Navbar.tsx for a merge.', file=sys.stderr)
                return 1
        new_nav = original_nav[:start] + source_modal + original_nav[end:]

    if ('.ca-logout-btn-primary' in original_css and
            '.ca-logout-note' in original_css and
            '.ca-logout-illustration' in original_css):
        new_css = original_css
        print('Premium logout dialog styling is already installed.')
    else:
        new_css = original_css.rstrip() + '\n\n' + source_styles.strip() + '\n'

    changed = []
    if new_nav != original_nav:
        changed.append((navbar_path, new_nav))
    if new_css != original_css:
        changed.append((css_path, new_css))

    if not changed:
        print('ALREADY INSTALLED: No files changed.')
    else:
        backups = root / ('_logout_modal_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
        for p, _ in changed:
            relative = p.relative_to(root)
            dest = backups / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
        written = []
        try:
            for p, data in changed:
                tmp = p.with_name(p.name + '.logout_patch_tmp')
                tmp.write_text(data, encoding='utf-8', newline='')
                tmp.replace(p)
                written.append(p)
                print('Updated:', p.relative_to(root))
        except Exception as exc:
            for p in written:
                shutil.copy2(backups / p.relative_to(root), p)
            print(f'ERROR: Changes rolled back: {exc}', file=sys.stderr)
            return 1
        print('Backup:', backups)

    if 'ca-header-action' not in new_nav:
        print('WARNING: This Navbar.tsx does not contain the premium header action controls from the earlier navbar patch.')
        print('If your header changed after extracting the older ZIP, restore/merge the navbar from your earlier backup.')
    print('Done. ML training files were not modified.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
