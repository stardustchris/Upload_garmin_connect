#!/usr/bin/env python3
"""
Test d'upload d'un workout vers Garmin Connect
"""

import json
from garminconnect import Garmin

# Charger C18
with open('data/workouts_cache/S06_workouts_v6_near_final.json', 'r') as f:
    data = json.load(f)

c18 = [w for w in data['workouts'] if w['code'] == 'C18'][0]

print("=== C18 à uploader ===")
print(f"Code: {c18['code']}")
print(f"Date: {c18['date']}")
print(f"Type: {c18['type']}")
print(f"Indoor: {c18['indoor']}")
print(f"Nombre d'intervalles: {len(c18['intervals'])}")

# Afficher structure
phases = {}
for iv in c18['intervals']:
    phase = iv['phase']
    phases[phase] = phases.get(phase, 0) + 1

print("\nRépartition:")
for phase, count in sorted(phases.items()):
    print(f"  {phase}: {count}")

print("\n=== Premiers 5 intervalles ===")
for i, iv in enumerate(c18['intervals'][:5], 1):
    duration = iv.get('duration', 'N/A')
    power = iv.get('power_watts', 'N/A')
    phase = iv['phase']
    rep = f"[Rép {iv['repetition_iteration']}/{iv['repetition_total']}]" if 'repetition_iteration' in iv else ''
    print(f"{i}. {phase:20s} | {duration:5s} | {power:10s} {rep}")

print("\n⚠️  Pour uploader vers Garmin Connect, vous devez:")
print("1. Configurer vos credentials Garmin")
print("2. python-garminconnect ne supporte pas directement l'upload de workouts structurés")
print("3. Il faut utiliser l'API non documentée ou garmin-workouts CLI")
print("\n💡 Alternative: Créer le workout manuellement sur Garmin Connect avec ces valeurs")

