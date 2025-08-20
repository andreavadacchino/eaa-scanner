# Generazione PDF - Guida Completa

## Panoramica

Il sistema EAA Scanner supporta la generazione automatica di report PDF utilizzando diversi engine con sistema di fallback intelligente. WeasyPrint è l'engine primario raccomandato per la massima qualità e compatibilità CSS.

## Engine Supportati

### 1. WeasyPrint (Raccomandato) ⭐
- **Engine nativo Python** con supporto CSS avanzato
- **Installazione**: `pip install weasyprint`
- **Vantaggi**: 
  - Supporto completo CSS3, @page rules, font internazionali
  - Controllo preciso layout, margini e intestazioni/piè di pagina
  - Ottimizzazione automatica font e immagini
  - Migliore resa tipografica

### 2. Chrome/Chromium Headless
- **Engine browser-based** con supporto JavaScript
- **Rilevamento automatico** di: google-chrome, chrome, chromium, brave
- **Vantaggi**: JavaScript rendering, accurata resa CSS moderna
- **Limitazioni**: Controllo limitato su intestazioni/margini

### 3. wkhtmltopdf
- **Engine tradizionale** con supporto CSS limitato  
- **Installazione**: Tramite package manager sistema
- **Vantaggi**: Stabile, veloce
- **Limitazioni**: CSS3 limitato, problemi con font moderni

## Configurazione

### Variabili di Ambiente

```bash
# Engine PDF da utilizzare (auto, weasyprint, chrome, wkhtmltopdf)
PDF_ENGINE=weasyprint

# Formato pagina (A4, Letter, A3, etc)
PDF_PAGE_FORMAT=A4

# Margini in pollici (top,right,bottom,left)
PDF_MARGINS="1,0.75,1,0.75"

# Chrome/Chromium personalizzato
CHROME_CMD=/path/to/chrome
```

### CLI Arguments

```bash
# Specificare engine PDF
python3 -m eaa_scanner.cli --pdf_engine weasyprint

# Formato pagina
python3 -m eaa_scanner.cli --pdf_format A4

# Margini personalizzati
python3 -m eaa_scanner.cli --pdf_margins "1,0.75,1,0.75"
```

### Configurazione Config.py

```python
from eaa_scanner.config import Config

config = Config(
    url="https://example.com",
    company_name="ACME Corp",
    email="team@example.com",
    pdf_engine="weasyprint",      # Engine preferito
    pdf_page_format="A4",         # Formato pagina
    pdf_margins="1,0.75,1,0.75"   # Margini personalizzati
)
```

## Utilizzo Programmatico

### Generazione PDF Base

```python
from pathlib import Path
from eaa_scanner.pdf import html_to_pdf

# Conversione automatica con fallback
success = html_to_pdf(
    html_path=Path("report.html"),
    pdf_path=Path("report.pdf"),
    engine="auto"  # Prova weasyprint → chrome → wkhtmltopdf
)
```

### Opzioni Avanzate

```python
from eaa_scanner.pdf import create_pdf_with_options

success = create_pdf_with_options(
    html_path=Path("report.html"),
    pdf_path=Path("report.pdf"),
    engine="weasyprint",
    page_format="A4",
    margins={'top': 1, 'right': 0.75, 'bottom': 1, 'left': 0.75},
    css_extra="@page { margin-top: 2cm; }",
    timeout=120
)
```

### Verifica Engine Disponibili

```python
from eaa_scanner.pdf import get_pdf_engines_status

status = get_pdf_engines_status()
for engine, info in status.items():
    if info['available']:
        print(f"✅ {engine}: {info['description']}")
    else:
        print(f"❌ {engine}: {info['description']}")
```

## Caratteristiche Avanzate WeasyPrint

### CSS Print-Friendly Ottimizzato

Il sistema include CSS ottimizzato per stampa con:

- **@page rules** con intestazioni e numerazione pagine
- **Controllo interruzioni pagina** per evitare divisioni indesiderate
- **Styling print-specific** con colori e font ottimizzati
- **Supporto responsive** per diversi formati pagina
- **Margini intelligenti** con spazio sufficiente per rilegatura

### Font e Internazionalizzazione

```python
# WeasyPrint supporta automaticamente:
# - Font di sistema (Arial, Times, etc.)
# - Caratteri internazionali (Unicode completo)
# - Font web (@font-face CSS)
# - Fallback intelligenti
```

## Troubleshooting

### WeasyPrint Non Installato

```bash
# Installazione base
pip install weasyprint

# Con dipendenze sistema (Ubuntu/Debian)
sudo apt-get install python3-dev python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# macOS con Homebrew
brew install cairo pango gdk-pixbuf libffi
```

### Chrome Non Trovato

```bash
# Imposta path personalizzato
export CHROME_CMD=/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome

# O installa Chromium
sudo apt-get install chromium-browser  # Ubuntu
brew install --cask chromium          # macOS
```

### Problemi di Rendering

1. **CSS non applicato correttamente**:
   - Verifica percorsi relativi delle risorse
   - Usa CSS inline per compatibilità massima

2. **Font mancanti**:
   - WeasyPrint: installa font di sistema
   - Chrome: verifica font web caricate

3. **Immagini non visualizzate**:
   - Usa percorsi assoluti o data URLs
   - Verifica permessi file

## Script di Test

Esegui script di test per verificare configurazione:

```bash
# Test completo tutti gli engine
python3 test_pdf.py

# Output esperato:
# ✅ WEASYPRINT - Engine PDF nativo Python
# ✅ CHROME - Engine basato su Chromium  
# ❌ WKHTMLTOPDF - Non installato
```

## Best Practices

### Performance
- **WeasyPrint**: Ottimale per report complessi con CSS avanzato
- **Chrome**: Migliore per layout JavaScript-dipendenti
- **wkhtmltopdf**: Più veloce per report semplici

### Qualità Output
1. **WeasyPrint** per massima qualità tipografica
2. **Chrome** per fedeltà rendering moderno
3. **wkhtmltopdf** per compatibilità legacy

### Configurazione Produzione
```python
# Configurazione robusta con fallback
config = Config(
    pdf_engine="auto",           # Fallback automatico
    pdf_page_format="A4",        # Standard europeo
    pdf_margins="2,1.5,2,1.5",   # Margini generosi per stampa
)
```

## Integrazione Workflow

Il sistema PDF si integra automaticamente nel workflow di scansione:

1. **Scansione** → Risultati normalizzati
2. **Report HTML** → Generazione con template Jinja2
3. **Conversione PDF** → Engine automatico con fallback
4. **Output** → HTML + PDF disponibili simultaneamente

Entrambi i file vengono salvati nella directory di output con naming coerente:
- `report_CompanyName.html`
- `report_CompanyName.pdf`