# Fixed desktop sidebar hotfix

This patch keeps the left navigation attached to the viewport while the main
page scrolls. The brand, startup card and statistics remain stationary. If the
menu is taller than the screen, only the menu itself scrolls.

## Apply

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/frontend-fixed-sidebar-hotfix.zip -d .
chmod +x scripts/frontend_fixed_sidebar_repair.sh
./scripts/frontend_fixed_sidebar_repair.sh
```

Do not use `--gpu`; this repair rebuilds only the React frontend.

Open `http://localhost:5173/dashboard` and press `Ctrl+Shift+R` once.
