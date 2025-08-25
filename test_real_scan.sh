#!/bin/bash

# Test script per verificare che gli scanner funzionino correttamente nel container Docker
# Questo script testa i fix applicati per Pa11y, Axe, e Lighthouse

set -e

echo "🧪 Test degli scanner di accessibilità nel container Docker"
echo "======================================================"

# Verifica che il container sia in esecuzione
if ! docker ps | grep -q eaa-scanner; then
    echo "❌ Container 'eaa-scanner' non trovato. Avvialo prima con:"
    echo "   docker-compose up -d"
    exit 1
fi

echo "✅ Container Docker trovato"

# Test URL di esempio
TEST_URL="https://www.example.com"

echo ""
echo "🔍 Test Pa11y con flags Chromium corretti..."
docker exec eaa-scanner pa11y \
    --reporter json \
    --chromium-path /usr/bin/chromium \
    --chromium-launch-args "--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage" \
    $TEST_URL > /tmp/pa11y_result.json 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Pa11y: SUCCESS"
    # Verifica che il risultato sia JSON valido
    if jq empty /tmp/pa11y_result.json 2>/dev/null; then
        echo "✅ Pa11y: Output JSON valido"
        echo "📊 Issues trovate: $(jq '. | length' /tmp/pa11y_result.json 2>/dev/null || echo 'N/A')"
    else
        echo "⚠️  Pa11y: Output non in formato JSON"
    fi
else
    echo "❌ Pa11y: FAILED"
    echo "Debug output:"
    head -5 /tmp/pa11y_result.json
fi

echo ""
echo "🔍 Test Axe-core con flags Chrome corretti..."
docker exec eaa-scanner npx @axe-core/cli \
    --stdout \
    --browser chrome \
    --chrome-path /usr/bin/chromium \
    --chrome-options "--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --headless=new" \
    $TEST_URL > /tmp/axe_result.json 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Axe-core: SUCCESS"
    if jq empty /tmp/axe_result.json 2>/dev/null; then
        echo "✅ Axe-core: Output JSON valido"
        echo "📊 Violations: $(jq '.[0].violations | length' /tmp/axe_result.json 2>/dev/null || echo 'N/A')"
    else
        echo "⚠️  Axe-core: Output non in formato JSON"
    fi
else
    echo "❌ Axe-core: FAILED"
    echo "Debug output:"
    head -5 /tmp/axe_result.json
fi

echo ""
echo "🔍 Test Lighthouse con flags Chrome corretti..."
docker exec eaa-scanner lighthouse $TEST_URL \
    --only-categories=accessibility \
    --quiet \
    --output=json \
    --output-path=stdout \
    --chrome-executable=/usr/bin/chromium \
    --chrome-flags="--headless=new --no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage" \
    > /tmp/lighthouse_result.json 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Lighthouse: SUCCESS"
    if jq empty /tmp/lighthouse_result.json 2>/dev/null; then
        echo "✅ Lighthouse: Output JSON valido"
        echo "📊 Accessibility score: $(jq '.categories.accessibility.score * 100 | floor' /tmp/lighthouse_result.json 2>/dev/null || echo 'N/A')%"
    else
        echo "⚠️  Lighthouse: Output non in formato JSON"
    fi
else
    echo "❌ Lighthouse: FAILED"
    echo "Debug output:"
    head -5 /tmp/lighthouse_result.json
fi

echo ""
echo "🎯 Test completo EAA Scanner con modalità REAL..."
docker exec eaa-scanner python3 -m eaa_scanner.cli \
    --url $TEST_URL \
    --company_name "Test Company" \
    --email "test@example.com" \
    --real \
    --timeout 30 > /tmp/eaa_full_result.txt 2>&1

if [ $? -eq 0 ]; then
    echo "✅ EAA Scanner completo: SUCCESS"
    echo "📁 Risultati salvati in: $(grep 'Report salvato:' /tmp/eaa_full_result.txt | cut -d' ' -f3 || echo 'N/A')"
else
    echo "❌ EAA Scanner completo: FAILED"
    echo "Debug output:"
    tail -10 /tmp/eaa_full_result.txt
fi

echo ""
echo "🧹 Cleanup file temporanei..."
rm -f /tmp/pa11y_result.json /tmp/axe_result.json /tmp/lighthouse_result.json /tmp/eaa_full_result.txt

echo "✅ Test completato!"
echo ""
echo "💡 Se tutti i test sono passati, gli scanner funzionano correttamente nel container."
echo "💡 Se alcuni test sono falliti, controlla i log del container: docker logs eaa-scanner"
