#!/usr/bin/env node
/**
 * Pa11y Runner per Docker
 * Esegue Pa11y programmaticamente con configurazione corretta per container
 */

const pa11y = require('pa11y');

// Leggi URL dagli argomenti
const url = process.argv[2];
const standard = process.argv[3] || 'WCAG2AA';
const timeout = parseInt(process.argv[4]) || 60000;

if (!url) {
    console.error(JSON.stringify({
        error: 'URL parameter required'
    }));
    process.exit(1);
}

// Configurazione Pa11y ottimizzata per Docker
const options = {
    standard: standard,
    timeout: timeout,
    wait: 15000, // Aumentato per siti esterni complessi
    chromeLaunchConfig: {
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox', 
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-blink-features=AutomationControlled',
            '--headless',
            // Flag per siti esterni HTTPS
            '--ignore-ssl-errors',
            '--ignore-certificate-errors',
            '--ignore-certificate-errors-spki-list',
            '--allow-running-insecure-content',
            // Performance per siti esterni
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            // User agent realistico
            '--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ],
        headless: true,
        executablePath: '/usr/bin/chromium'
    }
};

// Esegui Pa11y
(async () => {
    try {
        const results = await pa11y(url, options);
        
        // Rimuovi proprietà interne di Pa11y per output pulito
        const cleanResults = {
            documentTitle: results.documentTitle,
            pageUrl: results.pageUrl,
            issues: results.issues.map(issue => ({
                code: issue.code,
                type: issue.type,
                typeCode: issue.typeCode,
                message: issue.message,
                context: issue.context,
                selector: issue.selector
            }))
        };
        
        // Output JSON dei risultati
        console.log(JSON.stringify(cleanResults, null, 2));
        process.exit(0);
    } catch (error) {
        console.error(JSON.stringify({
            error: error.message || 'Pa11y scan failed',
            stack: error.stack
        }));
        process.exit(1);
    }
})();