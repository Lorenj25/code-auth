# CodeAuthentic — Premium Student Upload Portal

## Purpose

This is a **frontend-only** design update based on the `StudentDashboard.tsx` shipped in the previously reviewed CodeAuthentic source and Mobile Responsive UI patch. It matches the orange/charcoal premium instructor styling without replacing `global.css` or touching the navbar.

## Changed files

- `src/components/StudentDashboard.tsx` — redesigns the student upload portal; preserves the existing lobby lookup, source-file validation, sample buttons, upload submission, and success receipt.
- `src/components/StudentDashboardPremium.css` — **new** scoped styles for the portal in both light and dark modes, with desktop/mobile breakpoints.

Only these two files are installed. Everything under `ml/`, `backend/`, and `dataset/` stays untouched. **Java training can keep running in its own PowerShell window.**

## Install (Windows PowerShell)

1. Extract this ZIP to a **separate folder** (not directly on top of the thesis project).
2. Open PowerShell in the extracted folder.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\APPLY_PREMIUM_STUDENT_UI.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
```

The installer checks that your `StudentDashboard.tsx` matches one of the two reviewed versions, then creates a backup under `.codeauth-ui-backups/` before applying the update. **If it says `STOPPED SAFELY`, do not bypass it; send the latest `StudentDashboard.tsx` to adjust the patch.**

Alternatively, if you are working in a fresh copy of the reviewed source, you can manually copy the two files into `src/components/`, preserving the directory names and the CSS import.

## What changed visually

- Premium charcoal/orange welcome header, live three-step readiness indicators
- Separate exam lobby, student identity, and file-upload panels
- Clear active/locked lobby status and stronger locked-session notice
- Responsive drag/drop upload zone and browse-file button
- Collapsible sample-code examples, file counter, selected-file list
- Premium secure submit bar and success receipt
- Scoped light/dark theme and compact mobile spacing

One existing interaction issue was corrected: **submitting exactly three files is now allowed**. Selecting a fourth file is still blocked, and the 200 KB/file and language restrictions remain unchanged.

## Local checks

After applying, in your frontend project folder run:

```powershell
npm run build
```

Then verify:

1. Desktop and mobile (320 / 375 / 390 / 768 px), dark and light themes.
2. Active and locked lobby statuses.
3. Student ID entry and quick-fill buttons.
4. Upload 1, 2, and **3** matching `.py` files, remove a file, or drag/drop a file.
5. Wrong language, duplicate filename, 200 KB limit, and error messages.
6. Successful submission displays the real receipt and appears on instructor dashboard.

**No production AI detection is activated by this UI patch.** Java/C/Python classifier behavior is unchanged.
