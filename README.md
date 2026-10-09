# Intraday Atlas Live

Statische iPhone-Webseite mit eingebetteten TradingView-Marktreferenzen. Daten können verzögert sein. Keine automatisch berechneten PbD-/HVR-Signale oder Handelsfreigaben.

GitHub Pages: Settings → Pages → Deploy from a branch → main → /(root).

## Scanner 0.4: optionaler Wirtschaftskalender

Die Scanner-Workflows laufen ohne API-Schlüssel, markieren News dann aber **UNGEPRÜFT** und geben niemals Trades frei.

Für Trading Economics einen passenden API-Zugang buchen und unter GitHub → Settings → Secrets and variables → Actions → New repository secret einen Secret-Namen **TRADING_ECONOMICS_API_KEY** anlegen. Den Schlüssel **niemals** in README, HTML, Code oder Chat schreiben.

Der Adapter verarbeitet nur High-Impact-Termine mit expliziter Zeitzone. Sind Kalenderzeitstempel ohne UTC-Offset, bleibt die News-Prüfung bewusst **UNGEPRÜFT**; eine bestätigte Handelsfreigabe wird nicht simuliert. Die API kann kostenpflichtig sein. Kein vollständiger Schutz vor unerwarteten Nachrichten.

Die HVR-Logik ist weiterhin BOSWaves-inspiriert und nicht 1:1 gegen das Original-Pine-Script validiert; PbD bleibt ein Preis-Proxy. Scorewerte sind experimentell, nicht handelbar.

## Scanner 0.5: reproduzierbare PbD-/HVR-Validierung

Die neue Vergleichssoftware `validation/compare_signals.py` gleicht unabhängig dokumentierte Original-Indikatorsignale mit Scanner-Ergebnissen **zeitstempel- und marktgenau** ab. Sie meldet Übereinstimmungen, Abweichungen und fehlende Beobachtungen getrennt.

1. Original-Pine-Script von BOSWaves und genaue PbD-Definition bereitstellen. Eine bloße Preis-Proxy-Logik ist **keine** Originalumsetzung.
2. Identische M15-OHLCV-Daten mit Zeitzone und Datenanbieter für Original und Python verwenden.
3. Unabhängige Originalsignale in `validation/reference_template.csv` und Scanner-Signale in `validation/observed_template.csv` eintragen (Zeitstempel UTC, Markt, Indikator, Zustand).
4. Vergleich ausführen: `python -m validation.compare_signals --reference validation/reference_template.csv --observed validation/observed_template.csv`.
5. Abweichungen einzeln prüfen, besonders Pivot-Bestätigung nach 12 Folgebalken, HVR-Zonenalter, Volume/RVOL, Hold/Flip und PbD-Regimewechsel.

Ohne echte Referenzsignale meldet der Vergleich **nicht validiert**. Ein erfolgreiches technisches Testergebnis ist kein Beleg für Originaltreue, Trade-Qualität oder Profitabilität.

H4-Bias berücksichtigt ab Version 0.5 nur noch vollständig aggregierte Vier-Stunden-Kerzen. Die Strategie bleibt ausdrücklich ohne Handelsfreigabe.
