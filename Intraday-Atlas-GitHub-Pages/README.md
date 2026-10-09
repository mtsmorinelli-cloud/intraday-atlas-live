# Intraday Atlas Live – iPhone

Statische, mobiloptimierte HTML-Webseite mit TradingView-Kurswidgets und M15-Chart. **Keine selbst berechneten Trading-Signale**; Marktdaten können verzögert sein.

## Veröffentlichung direkt auf dem iPhone
1. GitHub in Safari öffnen und anmelden.
2. Neues **öffentliches** Repository `intraday-atlas-live` erstellen.
3. Im Repository **Add file → Upload files** auswählen und `index.html`, `manifest.webmanifest`, `icon.svg` sowie `.nojekyll` hochladen (oder zunächst nur `index.html`, die allein funktioniert).
4. **Settings → Pages → Build and deployment → Deploy from a branch → main → /(root) → Save**.
5. Auf die Veröffentlichung warten und `https://<BENUTZERNAME>.github.io/intraday-atlas-live/` öffnen.
6. In Safari **Teilen → Zum Home-Bildschirm** wählen.

Hinweise: Die URL ist erst nach erfolgreichem GitHub-Pages-Deployment erreichbar. Die Webseite ist öffentlich. TradingView kann Daten verzögert anzeigen oder einzelne Symbole nicht unterstützen. Das Broker-Symbol GAUUSD# bleibt ungeklärt. PbD/HVR, News und Entry/SL/TP werden **nicht** automatisch berechnet. Keine API-Schlüssel in öffentliches HTML schreiben.
