# CodeAuthentic — Premium Instructor UI Refresh

This is a **frontend-only** patch for the **current Mobile Responsive UI + Premium Mobile Navbar** baseline. It updates exactly two files:

- `src/components/InstructorDashboard.tsx`
- `src/global.css`

It does **not** change `ml/`, `backend/`, datasets, saved classifier candidates, training cache, login, API connections, or the database.

## What's new

- Warm, modern orange/charcoal design, improved readability and contrast
- Premium sticky sidebar with polished account block and active section indicators
- Dark-gradient page headers for the three instructor sections
- Metric tiles with icons and carefully spaced typography
- Dashboard quick-access lobby cards and a real-data analysis snapshot
- Premium examination lobby management panels
- Better submission filters, table visual hierarchy, and mobile cards
- Existing profile dropdown, Dark Mode, and Logout remain in the global navbar
- Responsive layout from narrow phones through wide desktops; respects reduced motion

## Install (Windows PowerShell)

1. Extract ZIP to a **separate folder** (do not overwrite the project manually).
2. Open PowerShell in the extracted patch folder.
3. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\APPLY_PREMIUM_INSTRUCTOR_UI.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
```

The installer verifies the checksums of both current files **before** changing either file. It stops safely if either file has been edited since the previous patches. It creates a timestamped backup folder in your project before replacing files. It can be rerun and will skip already-updated files.

If a safety check stops, do **not** bypass it. Send your current `src/components/InstructorDashboard.tsx` and `src/global.css` to merge safely.

## Test after installation

- Open `localhost:3000` and hard refresh (`Ctrl+Shift+R`).
- On desktop, open Dashboard, Examination Lobbies, and Live Student Submissions.
- Switch between light and dark via the **navbar**.
- Try at widths 320px, 375px, 390px, 768px, and desktop (Chrome DevTools Device Toolbar).
- Check lobby selection, create/copy/share/lock/unlock/delete (use test data), student switch, search, risk filter, CSV export, inspect code modal, and logout confirmation.
- Check that failed analyses are still shown as **Failed** (not given invented AI scores).

## Validation notes

TypeScript/JSX parsed and transpiled with the available offline TypeScript compiler without syntax diagnostics. A full Vite build and live browser/API test are not included because the local copy of project dependencies is incomplete. **Test in your local project before deploying.**
