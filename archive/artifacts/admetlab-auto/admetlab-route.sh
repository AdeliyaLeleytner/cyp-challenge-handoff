#!/bin/bash
# Narrow host-route helper. No firewall, VPN, DNS, or default-route changes.
set -euo pipefail
ADMET_IP=121.40.210.46
case "${1:---status}" in
  --enable)
    ADMET_GATEWAY=$(/usr/sbin/ipconfig getoption en0 router)
    if [ -z "$ADMET_GATEWAY" ]; then echo 'No Wi-Fi gateway on en0.' >&2; exit 1; fi
    if /sbin/route -n get "$ADMET_IP" | /usr/bin/grep -Eq 'interface: +en0'; then
      echo 'ADMETlab already routes via Wi-Fi.'
    else
      sudo /sbin/route -n add -host "$ADMET_IP" "$ADMET_GATEWAY"
    fi
    ;;
  --disable)
    if /sbin/route -n get "$ADMET_IP" | /usr/bin/grep -Eq 'destination: +121\.40\.210\.46$'; then
      sudo /sbin/route -n delete -host "$ADMET_IP"
    else
      echo 'No explicit ADMETlab host route to remove.'
    fi
    ;;
  --status) ;;
  *) echo 'Usage: bash admetlab-route.sh --status|--enable|--disable' >&2; exit 2 ;;
esac
/sbin/route -n get "$ADMET_IP"
/sbin/route -n get default
