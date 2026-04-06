
# One Pace – La versione manga più fedele di One Piece

**One Pace** è un progetto collaborativo che mira a ricreare l’esperienza di One Piece seguendo fedelmente il manga originale di Eiichiro Oda. L’anime di One Piece, pur essendo molto amato, contiene numerosi filler, scene allungate e aggiunte non canoniche che rallentano la narrazione. One Pace elimina questi elementi, offrendo una versione più scorrevole, coerente e fedele al manga.

Il nostro obiettivo è rendere questa versione accessibile anche al pubblico italiano, tramite la traduzione dei sottotitoli degli episodi di One Pace.

---


## Struttura del repository

- **sources/**: Episodi e speciali suddivisi per saghe e capitoli, da cui vengono realizzate le traduzioni (sottotitoli originali, file video, ecc).
- **translations/**: Traduzioni italiane completate, organizzate per saga e episodio.
- **to-do-arcs/**: Episodi e saghe ancora da tradurre o in lavorazione.
- **videos/**: Video finali delle versioni One Pace (non sempre disponibili).
- **extract_en.ps1**: Script per estrarre sottotitoli inglesi.
- **prompt.txt**: Prompt di esempio per la traduzione automatica.
- **README.md**: Questo file.


## Come contribuire

Siamo sempre alla ricerca di collaboratori! Puoi contribuire in diversi modi:

### 1. Traduzione sottotitoli
1. Scegli una saga o un episodio non ancora tradotto nella cartella `sources/` o `to-do-arcs/`.
2. Traduci i sottotitoli dall’inglese all’italiano, mantenendo la fedeltà al manga e lo stile dei personaggi.
3. Salva la traduzione nella cartella corrispondente in `translations/`, seguendo la struttura delle cartelle.

### 2. Revisione
1. Controlla le traduzioni già presenti per correggere errori grammaticali, di stile o di coerenza.
2. Segnala o correggi eventuali problemi direttamente nei file.

### 3. Sincronizzazione e timing
1. Se hai esperienza con file SRT, puoi aiutare a migliorare la sincronizzazione dei sottotitoli.

### 4. Script e automazione
1. Migliora o crea nuovi script per automatizzare l’estrazione, la conversione o la gestione dei sottotitoli.

---

## Linee guida per i collaboratori

- **Fedeltà**: Segui il più possibile il manga originale.
- **Terminologia**: Mantieni la terminologia ufficiale di One Piece (nomi, tecniche, luoghi, ecc). Consulta le traduzioni ufficiali quando possibile.
- **Stile**: Rispetta il carattere e il modo di parlare dei personaggi.
 **Pull Request**: Se vuoi proporre modifiche, apri una pull request chiara e dettagliata verso il branch `main`.



## Domande frequenti (FAQ)

**Chi può contribuire?**
Chiunque abbia passione per One Piece e conoscenze di inglese e italiano può aiutare, anche senza esperienza tecnica.

**Serve saper usare Git?**
No, ma se vuoi puoi inviare le traduzioni anche via email o altri canali concordati.

**Posso proporre miglioramenti agli script?**
Certo! Ogni contributo tecnico è benvenuto.

---


## Estrarre sottotitoli da video (OCR video → SRT)

Per estrarre sottotitoli impressi nel video (hard-sub) e generare un file SRT:

1. Installa le dipendenze Python:
   - `pip install -r requirements-ocr.txt`
2. Installa Tesseract OCR nel sistema:
   - Windows: scarica Tesseract e assicurati che `tesseract.exe` sia nel `PATH`
3. Esegui lo script:
   - `python ocr_video_to_srt.py "percorso\\video.mp4" --lang eng+ita --sample-fps 4`

Opzioni utili:
- `--bottom-ratio`: porzione bassa del frame dove cercare i sottotitoli (default `0.30`)
- `--similarity-threshold`: soglia per unire OCR simili (default `0.82`)
- `--max-seconds`: limita l'analisi ai primi N secondi (utile per test veloci)
- `--tesseract-cmd`: percorso esplicito di `tesseract.exe` se non nel `PATH`

---

## Contatti

Per domande, suggerimenti o per unirti al progetto, apri una issue o contatta il responsabile: gabriele.lentini99@gmail.com
