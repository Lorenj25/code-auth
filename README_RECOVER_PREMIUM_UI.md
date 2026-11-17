# CodeAuthentic — premium UI recovery (November 17, 2026)

## Why this fix?
The first logout-modal ZIP contained **full older copies** of `src/components/Navbar.tsx` and `src/global.css`. If it was extracted directly into your project, those older files could replace the newer premium instructor dashboard and navbar styling. The result is a partially unstyled dashboard with missing theme/logout controls.

This recovery restores the **premium navbar**, **premium instructor dashboard CSS**, and **upgraded logout modal** together, based on the reviewed patch versions. It does not replace your InstructorDashboard, StudentDashboard, backend, database, model files, or datasets.

## Install
1. Extract this ZIP **outside** the thesis project (for example to `Downloads\CodeAuthentic_Recovery`).
2. Open PowerShell in that extracted folder, and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\RESTORE_PREMIUM_UI.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
```

3. Verify the navbar Light/Dark and Logout controls and the dashboard cards. Refresh the browser with `Ctrl+Shift+R`.

## Safety behavior
- Reads local files **first**, then compares them to known reviewed versions.
- Refuses to replace unknown new versions. Upload your current `Navbar.tsx` and `global.css` if the script stops safely.
- Creates a timestamped `_premium_ui_recovery_backup_*` folder before writing.
- Does **not** modify `.venv`, `ml`, datasets, backend, or database.

## Verification
The recovered CSS was parsed and the installer was tested against the known broken combination, already restored combination, and an unknown stylesheet. A full Vite build/browser test must still be done on the Windows laptop.
