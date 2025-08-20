# Raccomandazioni Tecniche - Prompt Template

Genera raccomandazioni tecniche dettagliate per la remediation dei problemi di accessibilità.

## Contesto Scansione
- **Azienda**: {{company_name}}
- **URL**: {{url}}
- **Problemi identificati**: {{total_issues}}
- **Problemi critici**: {{critical_issues}}
- **Score attuale**: {{compliance_score}}/100

## Dettagli Problemi (campione)
{{issues_summary}}

## Istruzioni Generazione

Crea raccomandazioni tecniche specifiche e attuabili, organizzate per:

### 1. Categorie WCAG
Raggruppa le raccomandazioni per principi WCAG:
- **Percepibilità** (Perceivable)
- **Utilizzabilità** (Operable)  
- **Comprensibilità** (Understandable)
- **Robustezza** (Robust)

### 2. Priorità di Implementazione
- **🔴 Critico**: Blocca completamente l'accesso
- **🟠 Alto**: Impedisce l'uso efficace
- **🟡 Medio**: Degrada l'esperienza
- **🟢 Basso**: Miglioramenti minori

### 3. Dettagli Tecnici per ogni Raccomandazione
- **Problema**: Descrizione chiara del problema
- **Impact**: Chi viene colpito e come
- **Solution**: Step tecnici specifici per risolvere
- **Code Example**: Esempio di codice corretto (se applicabile)
- **Testing**: Come verificare la correzione
- **Resources**: Link a documentazione WCAG/WAI

### 4. Stima Implementazione
Per ogni raccomandazione includi:
- **Effort**: Tempo stimato (ore/giorni)
- **Complexity**: Livello tecnico richiesto
- **Dependencies**: Prerequisiti o dipendenze
- **Risk**: Possibili impatti su sistemi esistenti

## Formato Output
Utilizza questa struttura Markdown:

```markdown
## [Principio WCAG] - [Categoria]

### 🔴 [Titolo Raccomandazione]
**Criterio WCAG**: [X.X.X Nome Criterio]
**Problema**: [Descrizione]
**Impatto utenti**: [Chi e come]
**Soluzione**:
1. Step 1
2. Step 2
3. Step 3

**Esempio Codice**:
```html
<button aria-label="Chiudi finestra di dialogo">×</button>
```

**Test di Verifica**:
- [ ] Screen reader legge correttamente
- [ ] Focus visibile
- [ ] Funziona solo con tastiera

**Effort**: 2-4 ore | **Complexity**: Basso | **Priority**: Critico
```

## Linee Guida Specifiche
- Sii specifico e pratico, evita generalità
- Includi sempre esempi di codice quando rilevante
- Riferisciti a standard WCAG 2.1 AA specifici
- Considera diversi tipi di disabilità (motoria, visiva, auditiva, cognitiva)
- Suggerisci tools e tecniche di testing
- Mantieni focus su soluzioni implementabili

## Tecnologie Target
Assumi stack tecnologico moderno:
- HTML5 semantico
- CSS moderno (Grid, Flexbox)
- JavaScript ES2020+
- Framework moderni (React, Vue, Angular se rilevante)
- Screen reader (NVDA, JAWS, VoiceOver)

Scrivi sempre in italiano con terminologia tecnica appropriata.