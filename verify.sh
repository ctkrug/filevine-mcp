#!/usr/bin/env bash
# verify.sh — the "is this actually safe to show someone" check.
#
# One green smoke run on your own machine, on one day, is not proof. This runs three
# gates that map to the ways this kit could embarrass you in front of a reviewer:
#
#   Gate 1  COLD CLONE     A reviewer clones and builds from zero. We clone the *committed*
#                          tree into a throwaway dir and run setup there — catching
#                          "works on my machine" and anything you forgot to commit.
#   Gate 2  SMOKE          The full 31-check behavioural suite on the working tree.
#   Gate 3  EVERGREEN      Time-travel: the demo must read identically on dates spanning
#                          years. This is the guarantee that just silently broke once.
#
# Exit 0 only if all three pass. Run it before every send.
set -uo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
pass=0; fail=0
ok(){ printf '  \033[32m✓\033[0m %s\n' "$1"; pass=$((pass+1)); }
no(){ printf '  \033[31m✗\033[0m %s\n' "$1"; fail=$((fail+1)); }

echo "── Gate 1: cold clone (a reviewer's fresh checkout) ──"
if [ -n "$(git status --porcelain)" ]; then
  echo "  ⚠ working tree has uncommitted changes — the clone tests only what's COMMITTED."
  echo "    Commit first if you want those changes covered."
fi
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
if git clone --quiet "$ROOT" "$TMP/clone" 2>/dev/null; then
  if ( cd "$TMP/clone" && ./setup.sh ) >"$TMP/clone.log" 2>&1; then
    ok "fresh clone builds a venv and passes its smoke suite from zero"
  else
    no "fresh clone failed to build/pass — last lines:"; tail -6 "$TMP/clone.log" | sed 's/^/      /'
  fi
else
  no "git clone of the local repo failed"
fi

echo "── Gate 2: smoke suite (working tree) ──"
if .venv/bin/python test_smoke.py >"$TMP/smoke.log" 2>&1; then
  n=$(grep -c '  PASS' "$TMP/smoke.log")
  ok "all $n smoke checks pass"
else
  no "smoke failed:"; grep -iE 'FAIL|Error' "$TMP/smoke.log" | head -4 | sed 's/^/      /'
fi

echo "── Gate 3: evergreen across the calendar ──"
if .venv/bin/python test_evergreen.py >"$TMP/ever.log" 2>&1; then
  grep -E '  (PASS|baseline|Evergreen)' "$TMP/ever.log" | sed 's/^/  /'
  ok "demo reads identically on every simulated date"
else
  no "evergreen drift detected:"; grep -iE 'FAIL|drift|->' "$TMP/ever.log" | head -8 | sed 's/^/      /'
fi

echo
if [ "$fail" -eq 0 ]; then
  printf '\033[32m✅ ALL GATES PASS\033[0m (%d checks). Safe to show.\n' "$pass"
else
  printf '\033[31m❌ %d gate(s) failed\033[0m, %d passed. Do not ship until green.\n' "$fail" "$pass"
  exit 1
fi
