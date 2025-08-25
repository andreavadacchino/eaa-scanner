#!/usr/bin/env node

/**
 * Axe-core Runner Node.js per Docker
 * Versione ottimizzata per container con configurazione Chrome specifica
 */

const puppeteer = require('puppeteer');
const { AxePuppeteer } = require('@axe-core/puppeteer');

if (process.argv.length < 3) {
    console.error('Usage: node axe_runner.js <url> [standard] [timeout]');
    process.exit(1);
}

const url = process.argv[2];
const standard = process.argv[3] || 'WCAG2AA';
const timeout = parseInt(process.argv[4]) || 60000;

async function runAxeCore() {
    let browser;
    try {
        // Configurazione Chrome per Docker container
        const options = {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
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
            executablePath: '/usr/bin/chromium'
        };

        browser = await puppeteer.launch(options);
        const page = await browser.newPage();
        
        // Set timeout
        page.setDefaultNavigationTimeout(timeout);
        page.setDefaultTimeout(timeout);
        
        // Navigate to URL - ottimizzato per siti esterni
        await page.goto(url, { 
            waitUntil: 'domcontentloaded', // Più veloce per siti esterni
            timeout: timeout
        });
        
        // Wait for page to be fully ready
        await new Promise(resolve => setTimeout(resolve, 5000)); // Aspetta 5 secondi per il caricamento completo

        // Run axe-core analysis
        const results = await new AxePuppeteer(page).analyze();
        
        // Format results for EAA Scanner compatibility
        const formatted = {
            scanner: 'axe-core',
            url: url,
            timestamp: new Date().toISOString(),
            violations: results.violations.map(violation => ({
                id: violation.id,
                impact: violation.impact,
                description: violation.description,
                help: violation.help,
                helpUrl: violation.helpUrl,
                tags: violation.tags,
                nodes: violation.nodes.length,
                wcag: violation.tags.filter(tag => tag.startsWith('wcag')),
                details: violation.nodes.map(node => ({
                    html: node.html,
                    target: node.target,
                    failureSummary: node.failureSummary,
                    impact: node.impact
                }))
            })),
            passes: results.passes.map(pass => ({
                id: pass.id,
                description: pass.description,
                nodes: pass.nodes.length
            })),
            inapplicable: results.inapplicable.map(item => ({
                id: item.id,
                description: item.description
            })),
            incomplete: results.incomplete.map(item => ({
                id: item.id,
                description: item.description,
                nodes: item.nodes.length
            })),
            total_violations: results.violations.length,
            total_nodes_tested: results.violations.reduce((sum, v) => sum + v.nodes.length, 0) +
                               results.passes.reduce((sum, p) => sum + p.nodes.length, 0),
            compliance_score: Math.max(0, 100 - (results.violations.length * 10))
        };

        console.log(JSON.stringify(formatted, null, 2));
        
    } catch (error) {
        const errorResult = {
            scanner: 'axe-core',
            error: true,
            message: error.message,
            url: url,
            violations: [],
            passes: [],
            total_violations: 0,
            compliance_score: 0
        };
        console.log(JSON.stringify(errorResult, null, 2));
        process.exit(1);
    } finally {
        if (browser) {
            await browser.close();
        }
    }
}

runAxeCore();