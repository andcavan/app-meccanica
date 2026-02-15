# App Calcoli Meccanici - V1.3.37

Applicazione Python (CustomTkinter) con tab e sotto-tab per calcoli meccanici rapidi:

- Ingranaggi:
  - Cilindrici denti diritti
  - Cilindrici elicoidali
  - Conici denti diritti
  - Conici elicoidali
  - Vite senza fine
- Molle:
  - Scrollbar nelle aree dati + pannelli input/risultati ridimensionabili (default 60/40)
  - Selezione materiale da DB materiali molle
  - Dati materiale auto-caricati sotto la scelta materiale (E, G, sigma amm, tau amm) con modifica manuale, disposti su 2 righe
  - Terminali per molle a compressione e trazione
  - Selettore radio modo calcolo: `F1/F2 N` oppure `f1/f2 mm` (in torsione: `f1/f2 gradi`)
  - Attivazione automatica campi: restano editabili solo i campi coerenti col modo radio
  - Evidenza visiva campi disattivati (`[DISATTIVO]` + sfondo piu chiaro)
  - Campi disattivati: colore conforme allo stato disabled definito dal tema
  - Punti di lavoro con coppie f1/F1 e f2/F2 (calcolo in entrambe le direzioni)
  - Layout campi lavoro su 2 righe: f1 f2 / F1 F2
  - Nelle molle a compressione la lunghezza libera `L0` e dato di progetto (input utente)
  - Dati dimensionali compressione estesi con: spire totali, diametro esterno, diametro interno
  - Per tutte le molle sono riportate anche le tensioni ai punti di lavoro 1 e 2 (relative a f1/f2 o F1/F2)
  - Verifica stress rispetto al materiale selezionato
  - Risultati molle organizzati in sezioni: Dati dimensionali / Condizioni di lavoro / Dati punti lavoro
  - Compressione sezione tonda
  - Compressione sezione rettangolare
  - Trazione sezione tonda
  - Torsione sezione tonda
  - Molla torsione: f1/f2 gestiti in gradi (non in mm)
  - Lamina
  - Tazza
  - Lamina trapezoidale: larghezza lato fisso + larghezza lato libero
  - Tazza: selezione da DB standard o dimensioni personalizzate
  - Tazza: configurazione con molle in serie e/o in parallelo
  - Tazza: DB dimensionale esteso (serie legacy + gamma DIN 2093 G1/G2/G3)
  - Materiali molle: DB ampliato con acciai armonici/legati/inox, leghe rame, superleghe e titanio
- Travi:
  - Flessione
  - Torsione
  - Selezione materiale da DB travi dedicato (separato dal DB molle) con dati E, G, sigma amm, tau amm modificabili
  - Flessione avanzata: scelta sezione (tondo, tubo, rettangolare, tubolare, sezione standard)
  - Flessione avanzata: selezione profilo standard collegata alle dimensioni correlate (h, b, tw, tf, Ix, Wx)
  - Flessione avanzata: vincoli sx/dx (appoggiata, incernierata, incastrata, libera) con controllo configurazioni impossibili/instabili
  - Flessione avanzata: tabella carichi puntuali P-x con supporto valori positivi/negativi
  - Flessione avanzata: tabella carichi distribuiti zonali (N totale, x inizio, x fine)
  - Flessione avanzata: carichi distribuiti zonali con supporto valori positivi/negativi
  - Flessione avanzata: font aumentato nelle tabelle carichi (righe e intestazioni)
  - Flessione avanzata: diagrammi taglio/momento/freccia nel pannello destro
  - Torsione avanzata: vincoli consentiti INCASTRATA-LIBERA, LIBERA-INCASTRATA, INCASTRATA-INCASTRATA
  - Torsione avanzata: scelta sezione come Flessione (TONDO, TUBO, RETTANGOLARE, TUBOLARE) con campi attivi/disattivi coerenti
  - Torsione avanzata: tabelle momenti torcenti puntuali e distribuiti zonali (con valori positivi/negativi)
  - Torsione avanzata: unita momento torcente in Nm (conversione interna automatica per i calcoli)
  - Torsione avanzata: diagrammi momento torcente T e angolo torsione theta
  - Comportamento campi attivi/disattivi nella tab Travi allineato a Molle (stati, etichette, colori)
- Tolleranze:
  - Accoppiamenti foro/albero avanzati: classi ISO foro/albero, materiali dedicati, temperatura esercizio, grafico confronto 20 gradiC vs temperatura di lavoro
  - Selezione ISO sdoppiata: posizione tolleranza + grado qualita (foro e albero)
  - Tab accoppiamento: layout sx/dx con dati albero a sinistra e dati foro a destra
  - Identificazione esplicita gioco/interferenza su limite minimo e massimo, a 20 gradiC e a temperatura esercizio
  - Risultati accoppiamento: delta ed esito limite coerenti col segno (se negativo = interferenza)
  - DB ISO esteso: classi IT01-IT18 e range dimensionali completi 0-3150 mm per fori e alberi
  - DB tolleranze dedicato con materiali aggiuntivi: acciai, acciai inox, allumini, ottoni, bronzi, materie plastiche
  - Catena quote (somma/differenza)

## Avvio

```bash
pip install -r requirements.txt
python app.py
```

## Note

- La grafica usa lo stesso tema di `APP-COMMERCIALI` (`my style 01`).
- Le formule sono orientate a calcoli preliminari.
- Il DB ISO tolleranze esteso e generato in modo parametrico (verifica normativa finale consigliata su tabelle ISO ufficiali).
- Il DB materiali molle e in `calcoli_manager/database/spring_materials.db` (seed automatico al primo avvio).
- Il DB materiali travi e in `calcoli_manager/database/beam_materials.db` (seed automatico al primo avvio).
- Il DB tolleranze e in `calcoli_manager/database/tolerance_data.db` (seed automatico al primo avvio).
- Le sezioni standard travi (IPE) sono nel DB `beam_materials.db` (tabella `beam_sections_std`, seed automatico).
- Refactor struttura: `main_app.py` contiene UI/bootstrap, motore calcoli e cataloghi spostati in `calculation_engine.py`.







