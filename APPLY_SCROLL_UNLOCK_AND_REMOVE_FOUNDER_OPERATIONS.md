# Scroll unlock and Founder Operations Center removal

This patch corrects the previous route scroll repair, which used delayed
animation-frame and timer resets. Those callbacks could fire after the user
started scrolling and make the page appear locked.

It now:

- resets the browser page and independently scrolling sidebar once per route;
- allows normal mouse-wheel, touchpad, touch, Page Up/Down, Home/End scrolling;
- removes the floating Founder Tools launcher;
- removes the standalone `/founder-tools` frontend entry;
- removes the Founder Operations panel from document intake;
- keeps backend records, migrations, compliance data, vault data, and APIs;
- renames the dashboard shortcut card to `Workspace shortcuts`.

Apply from the running project directory:

```bash
cd /home/ps/Project/startup-intelligence-platform
unzip -o ~/Downloads/frontend-scroll-unlock-remove-founder-operations-hotfix.zip -d .
chmod +x scripts/frontend_scroll_unlock_repair.sh
./scripts/frontend_scroll_unlock_repair.sh
```

Do not use `--gpu`. This repair only rebuilds the frontend and does not restart
or delete the backend database.
