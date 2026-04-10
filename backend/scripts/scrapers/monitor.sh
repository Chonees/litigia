#!/bin/bash
# Monitor all PJN scraper VPS instances
# Usage: bash scripts/scrapers/monitor.sh
# Auto-refreshes every 30 seconds. Ctrl+C to stop.

SERVERS=(
    "149.28.52.214|pjn-0|CABA"
    "45.76.19.148|pjn-1|Buenos Aires"
    "45.32.206.98|pjn-2|Cordoba+Mendoza"
    "45.32.163.1|pjn-3|Salta+Jujuy"
    "140.82.21.105|pjn-4|Corrientes+Chaco"
    "155.138.175.113|pjn-5|Chubut+EntreRios"
    "216.238.110.134|pjn-6|Formosa+LaPampa"
    "149.28.195.165|pjn-7|LaRioja+Misiones"
    "64.176.5.210|pjn-8|Neuquen+RioNegro"
    "80.240.28.129|pjn-9|SanJuan+Catamarca"
)

while true; do
    clear
    echo "================================================================"
    echo "  PJN SCRAPER MONITOR — $(date '+%Y-%m-%d %H:%M:%S')"
    echo "================================================================"
    echo ""

    TOTAL=0

    for entry in "${SERVERS[@]}"; do
        IFS='|' read -r IP NAME JURIS <<< "$entry"

        RESULT=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 -o BatchMode=yes "root@$IP" \
            "wc -l /data/clean/pjn_tribunales.jsonl 2>/dev/null | awk '{print \$1}'; tail -1 /data/logs/scraper.log 2>/dev/null" 2>/dev/null)

        COUNT=$(echo "$RESULT" | head -1)
        LAST_LOG=$(echo "$RESULT" | tail -1)

        if [ -z "$COUNT" ] || [ "$COUNT" = "" ]; then
            COUNT="?"
            STATUS="OFFLINE"
        else
            TOTAL=$((TOTAL + COUNT))
            STATUS="OK"
        fi

        printf "  %-12s %-20s %6s sentencias  %s\n" "$NAME" "$JURIS" "$COUNT" "$STATUS"
        echo "    $LAST_LOG" | head -c 120
        echo ""
    done

    echo ""
    echo "  ================================================"
    echo "  TOTAL: $TOTAL sentencias"
    echo "  ================================================"
    echo ""
    echo "  [Refreshing in 30 seconds... Ctrl+C to stop]"

    sleep 30
done
