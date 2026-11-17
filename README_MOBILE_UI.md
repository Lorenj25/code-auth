# CodeAuthentic — Mobile Compact & Responsive UI patch

Based on `CodeAuthentic_Source_For_Review(2).zip`. **Frontend only:** 8 modified React/CSS files.

## Improvements
- Compact header, landing page, and instructor sign-in on narrow screens
- Three compact instructor section tabs, replacing horizontal scrolling on phones
- Dashboard statistics and actions sized to fit phone widths
- Lobby list and UUID codes constrained on narrow displays; full codes remain available through copy actions
- Student upload form with shorter drop zone, tighter spacing, and responsive receipt
- Submission results render as easy-to-read **cards on phones**, retaining the full table on desktop
- Creation, dataset, logout, and code-inspection dialogs fit short mobile viewports
- Code viewer supports sideways scrolling within the modal without shifting the entire page
- 16px input text on phones to avoid unwanted iOS Safari zoom

## Install without overwriting work
1. Extract the ZIP to a **separate folder** (do not extract directly over the project).
2. Open PowerShell inside the extracted folder and run:

   `powershell -ExecutionPolicy Bypass -File .\APPLY_MOBILE_UI.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"`

3. The installer checks the **original SHA-256 hashes** of every source file against the uploaded review ZIP, creates backups in `_mobile_ui_backup_YYYYMMDD_HHMMSS`, and then installs all eight files. It refuses to overwrite a different/newer local file.
4. If it says `STOPPED SAFELY`, do **not** bypass the check. Upload the newer `src` folder/ZIP so the UI edits can be merged.

## Testing on phone sizes
- Start the existing frontend as usual (`npm run dev` in the project root).
- Chrome/Edge DevTools → Toggle device toolbar → test 320, 375, 390, 430, 768 px widths; also rotate to landscape.
- Test Home, Instructor Sign In/Register, Dashboard, Lobbies, Create Lobby modal, Submissions filters/Inspect, Student upload and success receipt in light and dark mode.
- Inspect a long code file and long UUID lobby code for layout overflow.

**Java training:** Applying this frontend-only patch does not stop an already-running CodeBERT Java process. Avoid restarting that process or modifying `ml/` and `dataset/` files. If the frontend dev server runs, Vite may consume some CPU.

## Scope & validation
Only these files were modified: `src/App.tsx`, `src/global.css`, `src/components/Navbar.tsx`, `HomeIntro.tsx`, `InstructorLogin.tsx`, `InstructorDashboard.tsx`, `StudentDashboard.tsx`, and `CodeModal.tsx`.

Syntax of all changed TSX files was checked with the TypeScript transpiler. A complete `npm run build` and browser/device visual test were **not** possible in the current environment because npm dependencies are incomplete and external package retrieval failed. Please run `npm run lint` and `npm run build` using your local project with installed packages before deploying. No backend or real model integration was changed.
