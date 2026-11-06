# Landing-Gear Torque-Link Fatigue Screening

An analytical companion study for the A350 Fleet Airworthiness Intelligence repository. It demonstrates a simplified net-section stress check and variable-amplitude fatigue calculation for one idealized landing-gear torque-link arm.

## Scope and safety

This is a portfolio-level calculation example, not a finite-element model, certified part design, maintenance instruction, or safe-life substantiation. Every dimension, load, stress concentration factor, and material fatigue property in the script is a synthetic placeholder. The simplified model omits important effects including pin bearing and bypass loads, contact, local geometry, multiaxial stress, buckling, residual stress, corrosion, manufacturing variability, and crack growth. It must not be used for aircraft design, maintenance, dispatch, or airworthiness decisions.

Replace the assumptions with approved geometry, verified load spectra, material certificates, representative fatigue test data, and applicable certification requirements before any engineering use. A realistic FEA project would also need a validated 3D CAD model, boundary-condition review, mesh-convergence study, and correlation against test or authoritative data.

## Idealized model

The screening model treats one flat link arm as a pin-holed tension member:

- Net section: `A_net = t × (w − d)`
- Local stress screen: `σ_local = Kt × F / A_net`
- Mean and alternating stress are computed from each minimum/maximum load pair.
- A Goodman correction and a user-specified Basquin S–N curve estimate cycles to failure.
- Palmgren–Miner damage is accumulated across the synthetic spectrum.
- A rough mass estimate subtracts two pin holes from a rectangular envelope.

The `Kt` value is an input placeholder; it is not computed from geometry and does not replace a 3D stress analysis. The model uses a simplified uniaxial stress state and does not calculate von Mises stress for a real torque-link assembly.

## Synthetic demonstration inputs

| Input | Demo value |
|---|---:|
| Link arm length | 260 mm |
| Width × thickness | 50 mm × 12 mm |
| Pin-hole diameter | 18 mm |
| Assumed stress concentration factor | 2.4 |
| Assumed yield / ultimate strength | 503 / 572 MPa |
| Assumed Basquin coefficient / exponent | 800 MPa / −0.10 |
| Ground-handling block | 18,000 cycles, 3–12 kN |
| Landing/braking block | 2,000 cycles, 8–45 kN |

All numbers are invented for demonstration. The material label is only a reminder of a possible alloy class; these are not certified 7075-T6 allowables or published fatigue data.

## Run

Requires Python 3.10 or later and only uses the standard library.

```bash
python engineering/torque-link-fatigue/analysis.py
```

The script writes `results/screening_report.json`, `results/spectrum_results.csv`, and `results/sn_curve.svg` under the current working directory. The S–N figure visualizes the assumed model and synthetic spectrum points; it is not experimental data.

## Files

- `analysis.py` — equations, assumptions, report generation, and SVG plot generation
- `torque-link-fbd.svg` — illustrative free-body diagram for the idealized arm

## Next engineering steps

1. Define the torque-link assembly, joints, and load paths from approved design data.
2. Derive component loads from a verified landing-gear system model and operational spectrum.
3. Build and validate a 3D CAD/FEA model; document constraints and mesh convergence.
4. Replace the placeholder S–N curve with representative material/process/environment data.
5. Correlate analysis with component tests before making fatigue or service-life claims.
