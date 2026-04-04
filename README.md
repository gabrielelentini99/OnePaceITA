# One Pace – La versione manga più fedele di One Piece

One Pace è un progetto dedicato a ricreare l’esperienza di One Piece seguendo fedelmente il manga originale, eliminando filler, allungamenti e aggiunte non canoniche presenti nell’anime. L’obiettivo è offrire una versione più scorrevole, coerente e fedele all’opera di Eiichiro Oda.

## Cosa faccio
Mi occupo della traduzione in italiano dei sottotitoli degli episodi di One Pace, rendendo accessibile questa versione anche al pubblico italiano.

## Struttura del repository
- **sources/**: Episodi e speciali suddivisi per saghe e capitoli, da cui vengono realizzate le traduzioni.
- **translations/**: Traduzioni italiane completate, organizzate per saga.

## Come contribuire
1. Scegli una saga o un episodio da tradurre nella cartella "sources".
2. Salva la traduzione nella cartella corrispondente in "translations".

## Note
- Mantieni la struttura delle cartelle per facilitare la collaborazione.
- Per domande o suggerimenti, contatta il responsabile del progetto.

## OCR video -> SRT (hard-sub)
Per estrarre sottotitoli impressi nel video (hardcoded) e generare un file SRT:

1. Installa le dipendenze Python:
	- `pip install -r requirements-ocr.txt`
2. Installa Tesseract OCR nel sistema:
	- Windows: installa Tesseract e assicurati che `tesseract.exe` sia nel `PATH`
3. Esegui lo script:
	- `python ocr_video_to_srt.py "percorso\\video.mp4" --lang eng+ita --sample-fps 4`

Opzioni utili:
- `--bottom-ratio`: porzione bassa del frame dove cercare i sottotitoli (default `0.30`)
- `--similarity-threshold`: soglia per unire OCR simili (default `0.82`)
- `--max-seconds`: limita l'analisi ai primi N secondi (utile per test veloci)
- `--tesseract-cmd`: percorso esplicito di `tesseract.exe` se non nel `PATH`
