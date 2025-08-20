# Piano di Remediation - Prompt Template

Genera un piano di remediation dettagliato e temporizzato per l'implementazione delle correzioni di accessibilità.

## Parametri Progetto
- **Azienda**: {{company_name}}
- **URL**: {{url}}
- **Timeline obiettivo**: {{timeline}}
- **Problemi totali**: {{total_issues}}
- **Problemi critici**: {{critical_issues}}
- **Score attuale**: {{compliance_score}}/100

## Problemi Prioritari
{{priority_issues}}

## Istruzioni di Generazione

Crea un piano di remediation strutturato e realistico che includa:

### 1. Roadmap Temporale
Organizza il piano in fasi logiche:
- **Fase 1 - Quick Wins** (0-30 giorni)
- **Fase 2 - Correzioni Strutturali** (1-3 mesi)  
- **Fase 3 - Ottimizzazioni Avanzate** (3-6 mesi)
- **Fase 4 - Manutenzione Continua** (ongoing)

### 2. Matrice Priorità vs Effort
Categorizza gli interventi:
- **Alto Impatto + Basso Effort**: Quick wins da implementare subito
- **Alto Impatto + Alto Effort**: Progetti strategici da pianificare
- **Basso Impatto + Basso Effort**: Miglioramenti incrementali
- **Basso Impatto + Alto Effort**: Da rinviare o scartare

### 3. Dettagli per Fase
Per ogni fase includi:
- **Obiettivi**: Cosa si vuole raggiungere
- **Deliverables**: Output concreti e misurabili
- **Attività**: Task specifici da completare
- **Resources**: Team, tools, budget necessario
- **Timeline**: Durata e milestone
- **Success Criteria**: Metriche di successo
- **Risks & Mitigations**: Rischi e piani di contingenza

### 4. Stima Risorse
- **Team Size**: Numero persone necessarie per ruolo
- **Skills Required**: Competenze specifiche richieste
- **Tools & Software**: Strumenti necessari
- **External Support**: Quando serve consulenza esterna
- **Training Needs**: Formazione del team richiesta

### 5. Budget Estimato
- **Development Hours**: Ore sviluppo stimate
- **Testing & QA**: Ore testing/validazione
- **Tools & Licenses**: Costi software/servizi
- **Training**: Costi formazione team
- **External Consulting**: Budget consulenza esterna

## Template Output Strutturato

```markdown
# Piano di Remediation Accessibilità

## Overview Esecutivo
- **Obiettivo**: Raggiungere conformità WCAG 2.1 AA
- **Timeline**: [timeline] 
- **Budget stimato**: €X,000 - €Y,000
- **ROI atteso**: Conformità legale + miglioramento UX

## Fasi di Implementazione

### 🚀 Fase 1: Quick Wins (0-30 giorni)
**Target**: Correggere problemi critici con minimo sforzo

#### Settimana 1-2
- [ ] Task specifico 1 (2 ore, Dev Frontend)
- [ ] Task specifico 2 (4 ore, Dev Backend)
- [ ] Test validation (2 ore, QA)

#### Settimana 3-4  
- [ ] Task specifico 3
- [ ] Deployment e monitoring

**Resources**: 1 Frontend Dev (50%), 1 QA (25%)
**Budget**: €2,000
**Success Metrics**: -50% errori critici

### 🏗️ Fase 2: Correzioni Strutturali (1-3 mesi)
**Target**: Risoluzione problemi architetturali

[Dettagli analoghi per ogni fase...]

## Risk Assessment

| Rischio | Probabilità | Impatto | Mitigation |
|---------|-------------|---------|------------|
| Ritardi sviluppo | Media | Alto | Buffer 20% timeline |
| Regressioni | Bassa | Alto | Test automatizzati |
| Budget overrun | Media | Medio | Approval step per fase |

## Success Metrics & KPI
- **Conformità WCAG**: Target 95%+ entro fine progetto
- **User Testing Score**: >4/5 con utenti disabili  
- **Performance**: Nessuna regressione tempo caricamento
- **Maintenance**: <2 ore/mese effort ongoing

## Next Steps
1. [ ] Approval piano da management
2. [ ] Team setup e onboarding
3. [ ] Procurement tools necessari
4. [ ] Kick-off Fase 1
```

## Considerazioni Speciali
- **Metodologia Agile**: Integra con sprint esistenti quando possibile
- **Continuous Testing**: Automatizza validation dove possibile  
- **User Involvement**: Includi testing con utenti reali disabili
- **Documentation**: Mantieni knowledge base aggiornato
- **Compliance Tracking**: Monitor progress vs standard WCAG

## Output Requirements
- Piano deve essere actionable e specifico
- Include sempre timeline realistiche con buffer
- Considera skills gap e training needs del team
- Allinea con processi di sviluppo esistenti
- Prevedi checkpoint e milestone intermedi

Scrivi in italiano usando terminologia project management professionale.