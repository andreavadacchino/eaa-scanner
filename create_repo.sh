#!/bin/bash

echo "Per creare il repository su GitHub, hai bisogno di un Personal Access Token."
echo ""
echo "1. Vai su: https://github.com/settings/tokens/new"
echo "2. Dai un nome al token (es: 'EAA Scanner Deploy')"
echo "3. Seleziona questi permessi:"
echo "   - repo (tutti i sub-permessi)"
echo "4. Clicca 'Generate token'"
echo "5. Copia il token generato"
echo ""
echo "Poi esegui questo comando:"
echo ""
echo "export GITHUB_TOKEN='your-token-here'"
echo ""
echo "E poi:"
echo ""
cat << 'SCRIPT'
curl -H "Authorization: token $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user/repos \
     -d '{
       "name": "eaa-scanner",
       "description": "European Accessibility Act (EAA) compliance scanner with multi-tool integration and real-time monitoring",
       "private": false,
       "has_issues": true,
       "has_projects": true,
       "has_wiki": true
     }'

# Dopo la creazione, pusha il codice:
git push -u origin main
SCRIPT
