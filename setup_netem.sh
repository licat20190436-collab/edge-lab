#!/bin/bash
# setup_netem.sh — Configure network impairment on Docker bridge interface
# Usage: bash setup_netem.sh [none|fixed|jitter]

BRIDGE=$(docker network ls | grep edge | awk '{print $1}')
IFACE="br-${BRIDGE}"

case "$1" in
  none)
    echo "Removing network impairment..."
    tc qdisc del dev "$IFACE" root 2>/dev/null || true
    echo "Done. No impairment active."
    ;;

  fixed)
    echo "Setting fixed delay: 150ms + 5% packet loss..."
    tc qdisc del dev "$IFACE" root 2>/dev/null || true
    tc qdisc add dev "$IFACE" root netem delay 150ms loss 5%
    tc qdisc show dev "$IFACE"
    echo "Done."
    ;;

  jitter)
    echo "Setting jittered delay: 150ms ±20ms + 5% packet loss..."
    tc qdisc del dev "$IFACE" root 2>/dev/null || true
    tc qdisc add dev "$IFACE" root netem delay 150ms 20ms loss 5%
    tc qdisc show dev "$IFACE"
    echo "Done."
    ;;

  *)
    echo "Usage: $0 [none|fixed|jitter]"
    echo "  none   — remove all impairment"
    echo "  fixed  — 150ms fixed delay + 5% loss (Groups C, E)"
    echo "  jitter — 150ms ±20ms delay + 5% loss (Group F)"
    exit 1
    ;;
esac
