# 📊 Sistema Generazione Report Accessibilità

Sistema professionale per la generazione di report di accessibilità web conformi alle normative italiane ed europee.

## 🚀 Quick Start

```bash
# 1. Esegui scansione (opzionale - usa dati esistenti)
python3 -m eaa_scanner.cli --url https://example.com --real

# 2. Genera report (3 livelli disponibili)
python3 generate_italian_compliance_report.py      # Base AgID (12KB)
python3 generate_professional_italian_report.py    # Professionale (23KB)
python3 generate_enhanced_professional_report.py   # Avanzato (53KB) ⭐ Consigliato
```

## 📋 Caratteristiche

### ✅ Conformità Normativa
- **WCAG 2.1** Livello A e AA
- **Legge Stanca** (L. 4/2004)
- **Linee Guida AgID** 2024
- **European Accessibility Act** (EAA)
- **EN 301 549** v3.2.1

### 📝 Contenuti Report
- Analisi 4 principi P.O.U.R. (Percepibile, Utilizzabile, Comprensibile, Robusto)
- Descrizioni testuali dettagliate (non solo tabelle)
- Piano di remediation con owner e priorità
- Glossario criteri WCAG con esempi
- Stima investimenti e ROI
- Procedura di reclamo e contatti
- Note legali e disclaimer professionali

### 🎨 Design Professionale
- Font Titillium Web (standard AgID)
- Colori istituzionali italiani
- Layout responsive e print-friendly
- Box informativi differenziati
- Tabelle accessibili con scope e caption

## 📊 Esempio Output Reale

Scansione di **www.principiadv.com**:
```
Totale problemi: 127
├── Critici: 3 (bloccano accesso)
├── Alta priorità: 100 (barriere significative)
├── Media priorità: 24 (difficoltà superabili)
└── Bassa priorità: 0
Compliance Score: 0.0% (Non Conforme)
```

## 🏗️ Architettura

```
Sistema Multi-Agente
├── Executive Agent (sintesi strategica)
├── Technical Agent (analisi tecnica)
├── Compliance Agent (conformità normativa)
├── Remediation Agent (piano interventi)
├── Recommendations Agent (raccomandazioni)
└── Quality Controller (validazione output)
```

## 📁 Struttura File

```
accessibility-report/
├── generate_*.py                    # Generatori report (3 versioni)
├── eaa_scanner/
│   ├── agents/                      # Sistema multi-agente
│   │   ├── orchestrator.py          # Coordinatore agenti
│   │   ├── compliance_agent.py      # Verifica conformità
│   │   └── ...
│   └── report_generator.py          # Core generazione
├── output/                          # Report HTML generati
├── demo/                            # Esempi audit professionali
└── docs/                            # Documentazione
```

## 🔧 Requisiti

- Python 3.8+
- FastAPI
- Jinja2
- email-validator

```bash
pip install -r requirements.txt
```

## 💡 Utilizzo Avanzato

### Con Docker
```bash
docker-compose -f docker-compose.fastapi.yml up
# API disponibile su http://localhost:8000
```

### API REST
```bash
curl -X POST http://localhost:8000/api/v2/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "scan_id": "v2scan_y8MPUlktSlw",
    "report_type": "enterprise",
    "language": "it",
    "include_remediation": true
  }'
```

## 📈 Livelli Report

### 1️⃣ Base AgID (12 KB)
- Conformità essenziale
- 4 principi WCAG
- Stile minimale
- Per comunicazioni AgID

### 2️⃣ Professionale (23 KB)
- Struttura formale completa
- Piano remediation dettagliato
- Quadro normativo esteso
- Per management e stakeholder

### 3️⃣ Avanzato (53 KB) ⭐
- Massima completezza
- Descrizioni pre-tabella
- Glossario WCAG esteso
- Stima investimenti e ROI
- Per team tecnici e consulenza

## 🎯 Casi d'Uso

- ✅ **Audit di conformità** per siti PA
- ✅ **Due diligence** pre-acquisizione
- ✅ **Dichiarazione Accessibilità** AgID
- ✅ **Compliance EAA** (scadenza 28/06/2025)
- ✅ **Certificazione** ISO 30071

## 📞 Supporto

Per assistenza sulla generazione report:
- 📧 accessibility@principiadv.com
- 📱 +39 02 XXXX XXXX
- 🌐 [GitHub Issues](https://github.com/andreavadacchino/eaa-scanner/issues)

## 📜 Licenza

MIT License - Vedi file LICENSE

---

**Sviluppato da**: Principia SRL  
**Ultimo aggiornamento**: 25/01/2025  
**Versione**: 1.0.0