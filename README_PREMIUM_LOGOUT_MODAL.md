# CodeAuthentic Premium Logout Modal

This patch upgrades the logout confirmation popup to a more premium design while keeping the same logout behavior.

## Changed files
- `src/components/Navbar.tsx`
- `src/global.css`

## Install
Open PowerShell in this patch folder and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\APPLY_PREMIUM_LOGOUT_MODAL.ps1 -ProjectRoot "C:\Users\REO JOHN\Downloads\thesis-main\thesis-main"
```

The installer creates a backup of the original files before replacing them.

## What changed
- richer blurred overlay
- elevated premium modal card
- close button in the upper-right
- cleaner typography and spacing
- stronger primary and secondary action buttons
- secure-session note
- improved mobile stacking

This patch only affects frontend UI files.
