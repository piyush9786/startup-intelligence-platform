# Frontend route-scroll repair

This hotfix prevents authenticated pages from reopening halfway down the document.

It adds:

- browser history scroll restoration set to `manual` before React mounts;
- a route-wide `RouteScrollManager`;
- repeated scroll resets across browser paint/restoration timing;
- resets for app-owned scroll containers;
- a regression test;
- a Docker frontend rebuild script;
- a read-only inventory script for the older model-training and crawler project.

## Apply

From the current project directory:

```bash
unzip -o ~/Downloads/frontend-scroll-and-legacy-inventory-hotfix.zip -d .
chmod +x scripts/frontend_scroll_repair.sh scripts/inspect_legacy_assets.sh
./scripts/frontend_scroll_repair.sh
```

Then use `Ctrl+Shift+R` once.

## Inspect previous model/crawl data

```bash
./scripts/inspect_legacy_assets.sh \
  /home/ps/Pictures/startup-intelligence-platform-main
```

The script is read-only. It creates `legacy-assets-YYYYMMDD-HHMMSS.txt` in the current project. Review or upload that report before copying old assets into the live database or application directories.
