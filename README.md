# Intraday Atlas Live

Statische iPhone-Webseite mit eingebetteten TradingView-Marktreferenzen. Daten können verzögert sein. Keine automatisch berechneten PbD-/HVR-Signale oder Handelsfreigaben.

GitHub Pages: Settings → Pages → Deploy from a branch → main → /(root).

## Scanner 0.4: optionaler Wirtschaftskalender

Die Scanner-Workflows laufen ohne API-Schlüssel, markieren News dann aber **UNGEPRÜFT** und geben niemals Trades frei.

Für Trading Economics einen passenden API-Zugang buchen und unter GitHub → Settings → Secrets and variables → Actions → New repository secret einen Secret-Namen **TRADING_ECONOMICS_API_KEY** anlegen. Den Schlüssel **niemals** in README, HTML, Code oder Chat schreiben.

Der Adapter verarbeitet nur High-Impact-Termine mit expliziter Zeitzone. Sind Kalenderzeitstempel ohne UTC-Offset, bleibt die News-Prüfung bewusst **UNGEPRÜFT**; eine bestätigte Handelsfreigabe wird nicht simuliert. Die API kann kostenpflichtig sein. Kein vollständiger Schutz vor unerwarteten Nachrichten.

Die HVR-Logik ist weiterhin BOSWaves-inspiriert und nicht 1:1 gegen das Original-Pine-Script validiert; PbD bleibt ein Preis-Proxy. Scorewerte sind experimentell, nicht handelbar.
