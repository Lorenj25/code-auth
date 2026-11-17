# CodeAuthentic — Safe premium logout modal fix (v2)

## Why a corrected installer?
The earlier ZIP included full files and an installer that attempted to copy `Navbar.tsx` onto itself when the ZIP was extracted directly into the project's root. This package includes **no replacement Navbar.tsx or global.css files**.

## Apply
Extract the ZIP anywhere, including into the project folder, and run in PowerShell from the extracted folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\APPLY_SAFE_LOGOUT_MODAL.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
```

The script edits only the existing logout modal JSX, appends scoped modal CSS if necessary, and makes a timestamped backup before editing. Re-running is safe.

If the older ZIP was extracted over the project, the modal may **already be updated** even though the old installer failed. The new installer detects this.

**Important:** If the previous ZIP overwrote premium navbar/header changes, this patch cannot automatically recover those changes. The script warns if the expected premium header action controls are missing. Restore the navbar from a known-good backup or provide your current `Navbar.tsx` and `global.css` for an exact merge.

No ML, Java/C/Python training, backend, or database files are changed.
