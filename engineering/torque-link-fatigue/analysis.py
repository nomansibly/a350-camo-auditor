"""Illustrative fatigue screening for one simplified landing-gear torque-link arm.

This is a transparent analytical example, not an FEA solver or an approved
aircraft maintenance/design method. All dimensions, loads, and material data are
synthetic placeholders and must be replaced with verified project data.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Geometry:
    arm_length_mm: float = 260.0
    width_mm: float = 50.0
    thickness_mm: float = 12.0
    pin_hole_diameter_mm: float = 18.0
    assumed_kt: float = 2.4
    density_kg_m3: float = 2810.0


@dataclass(frozen=True)
class Material:
    label: str = "7075-T6-like placeholder (not certified data)"
    yield_strength_mpa: float = 503.0
    ultimate_strength_mpa: float = 572.0
    fatigue_coefficient_mpa: float = 800.0
    basquin_exponent: float = -0.10


@dataclass(frozen=True)
class SpectrumBlock:
    name: str
    cycles: int
    force_min_kn: float
    force_max_kn: float


GEOMETRY = Geometry()
MATERIAL = Material()
SPECTRUM = (
    SpectrumBlock("Ground handling", 18_000, 3.0, 12.0),
    SpectrumBlock("Landing and braking", 2_000, 8.0, 45.0),
)


def validate_inputs(geometry: Geometry, material: Material, spectrum: tuple[SpectrumBlock, ...]) -> None:
    if geometry.width_mm <= geometry.pin_hole_diameter_mm:
        raise ValueError("Link width must be greater than the pin-hole diameter.")
    if min(geometry.arm_length_mm, geometry.thickness_mm, geometry.density_kg_m3, geometry.assumed_kt) <= 0:
        raise ValueError("Geometry, density, and Kt must be positive.")
    if min(material.yield_strength_mpa, material.ultimate_strength_mpa,
           material.fatigue_coefficient_mpa) <= 0 or material.basquin_exponent >= 0:
        raise ValueError("Material strengths must be positive and Basquin exponent negative.")
    if not spectrum or any(block.cycles <= 0 or block.force_max_kn < block.force_min_kn
                           for block in spectrum):
        raise ValueError("Spectrum blocks need positive cycles and max force >= min force.")


def net_area_mm2(geometry: Geometry) -> float:
    """Net tensile section at a single pin hole; bearing/bypass effects omitted."""
    return geometry.thickness_mm * (geometry.width_mm - geometry.pin_hole_diameter_mm)


def basquin_cycles(stress_amplitude_mpa: float, material: Material) -> float:
    """Return cycles from the assumed stress-amplitude Basquin relation."""
    if stress_amplitude_mpa <= 0:
        return math.inf
    return (stress_amplitude_mpa / material.fatigue_coefficient_mpa) ** (1.0 / material.basquin_exponent)


def evaluate_block(block: SpectrumBlock, geometry: Geometry, material: Material) -> dict[str, float | str | int]:
    area = net_area_mm2(geometry)
    kt = geometry.assumed_kt
    sigma_min = kt * block.force_min_kn * 1000.0 / area
    sigma_max = kt * block.force_max_kn * 1000.0 / area
    sigma_a = (sigma_max - sigma_min) / 2.0
    sigma_m = (sigma_max + sigma_min) / 2.0
    goodman_denominator = 1.0 - sigma_m / material.ultimate_strength_mpa
    if goodman_denominator <= 0:
        corrected_amplitude = math.inf
        life_cycles = 0.0
    else:
        corrected_amplitude = sigma_a / goodman_denominator
        life_cycles = basquin_cycles(corrected_amplitude, material)
    damage = block.cycles / life_cycles if life_cycles > 0 else math.inf
    return {
        "block": block.name,
        "cycles": block.cycles,
        "force_min_kN": block.force_min_kn,
        "force_max_kN": block.force_max_kn,
        "local_sigma_min_MPa": sigma_min,
        "local_sigma_max_MPa": sigma_max,
        "stress_amplitude_MPa": sigma_a,
        "mean_stress_MPa": sigma_m,
        "Goodman_corrected_amplitude_MPa": corrected_amplitude,
        "Basquin_life_cycles": life_cycles,
        "Miner_damage": damage,
    }


def analyze(geometry: Geometry = GEOMETRY, material: Material = MATERIAL,
            spectrum: tuple[SpectrumBlock, ...] = SPECTRUM) -> dict[str, object]:
    validate_inputs(geometry, material, spectrum)
    rows = [evaluate_block(block, geometry, material) for block in spectrum]
    area = net_area_mm2(geometry)
    worst_peak = max(float(row["local_sigma_max_MPa"]) for row in rows)
    total_damage = sum(float(row["Miner_damage"]) for row in rows)

    # Rough rectangular-envelope mass estimate minus two pin holes; no fillets,
    # pockets, bushings, fasteners, or local shape effects are modeled.
    net_volume_mm3 = (geometry.arm_length_mm * geometry.width_mm
                      - 2 * math.pi * (geometry.pin_hole_diameter_mm / 2) ** 2) * geometry.thickness_mm
    estimated_mass_kg = net_volume_mm3 * 1e-9 * geometry.density_kg_m3

    return {
        "scope": "Synthetic educational screening model; not FEA or approved design data.",
        "geometry": asdict(geometry),
        "material_placeholder": asdict(material),
        "net_section_area_mm2": area,
        "peak_local_stress_MPa": worst_peak,
        "yield_factor_of_safety_screen": material.yield_strength_mpa / worst_peak,
        "estimated_mass_kg": estimated_mass_kg,
        "spectrum_cycle_count": sum(block.cycles for block in spectrum),
        "Miner_damage_screen": total_damage,
        "spectrum_results": rows,
        "limitations": [
            "The applied link loads, Kt, geometry, material strengths, and S-N curve are placeholders.",
            "The model omits bearing, bypass, pin contact, buckling, multiaxial loading, residual stress, corrosion, and crack growth.",
            "A Miner sum below one or a yield factor above one is not a safe-life or airworthiness determination.",
        ],
    }


def write_sn_plot(path: Path, material: Material, results: dict[str, object]) -> None:
    """Write a dependency-free SVG of the assumed Basquin curve and spectrum points."""
    width, height = 900, 560
    left, right, top, bottom = 105, 840, 80, 455
    min_cycles, max_cycles = 1.0, 1e9
    min_stress, max_stress = 10.0, 1000.0

    def xmap(value: float) -> float:
        return left + (math.log10(max(min_cycles, min(max_cycles, value))) / 9.0) * (right - left)

    def ymap(value: float) -> float:
        return bottom - (math.log10(max(min_stress, min(max_stress, value)) / min_stress) / 2.0) * (bottom - top)

    points = []
    for exponent in range(10):
        cycles = 10.0 ** exponent
        stress = material.fatigue_coefficient_mpa * cycles ** material.basquin_exponent
        points.append(f"{xmap(cycles):.1f},{ymap(stress):.1f}")
    plot = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="560" viewBox="0 0 900 560" role="img" aria-labelledby="title desc">',
        '<title id="title">Illustrative Basquin S-N curve</title>',
        '<desc id="desc">Assumed fatigue curve and two synthetic load-spectrum stress amplitudes. Not test data.</desc>',
        '<rect width="900" height="560" fill="#ffffff"/>',
        '<text x="105" y="38" font-family="Arial" font-size="23" font-weight="700" fill="#0f172a">Torque-link fatigue screening · assumed S–N curve</text>',
        '<text x="105" y="61" font-family="Arial" font-size="14" fill="#64748b">Basquin model from placeholder inputs · not material test data</text>',
    ]
    for exponent in range(10):
        x = xmap(10.0 ** exponent)
        plot.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="#e2e8f0"/>')
        plot.append(f'<text x="{x:.1f}" y="{bottom + 25}" text-anchor="middle" font-family="Arial" font-size="12" fill="#475569">10^{exponent}</text>')
    for exponent in range(1, 4):
        stress = 10.0 ** exponent
        y = ymap(stress)
        plot.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        plot.append(f'<text x="{left - 14}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="12" fill="#475569">{int(stress)}</text>')
    plot.extend([
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#2563eb" stroke-width="4"/>',
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#334155" stroke-width="2"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#334155" stroke-width="2"/>',
        f'<text x="{(left + right) / 2:.0f}" y="530" text-anchor="middle" font-family="Arial" font-size="15" fill="#0f172a">Cycles to failure (log scale)</text>',
        f'<text x="28" y="270" transform="rotate(-90 28 270)" text-anchor="middle" font-family="Arial" font-size="15" fill="#0f172a">Stress amplitude (MPa, log scale)</text>',
    ])
    for row in results["spectrum_results"]:
        cycles = float(row["Basquin_life_cycles"])
        stress = float(row["Goodman_corrected_amplitude_MPa"])
        if math.isfinite(cycles) and math.isfinite(stress):
            x, y = xmap(cycles), ymap(stress)
            label = str(row["block"])
            plot.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="#dc2626" stroke="#ffffff" stroke-width="2"/>')
            plot.append(f'<text x="{min(x + 12, right - 140):.1f}" y="{y - 10:.1f}" font-family="Arial" font-size="13" fill="#991b1b">{label}</text>')
    plot.append('<text x="105" y="492" font-family="Arial" font-size="12" fill="#64748b">Synthetic inputs only; this plot is a model visualization, not a certification result.</text>')
    plot.append('</svg>')
    path.write_text("\n".join(plot) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("results"),
                        help="Directory for generated JSON, CSV, and SVG outputs")
    args = parser.parse_args()
    result = analyze()
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "screening_report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (args.outdir / "spectrum_results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result["spectrum_results"][0].keys()))
        writer.writeheader()
        writer.writerows(result["spectrum_results"])
    write_sn_plot(args.outdir / "sn_curve.svg", MATERIAL, result)
    print("Torque-link fatigue screening — illustrative model only")
    print(f"Net section area: {result['net_section_area_mm2']:.1f} mm²")
    print(f"Peak local stress screen: {result['peak_local_stress_MPa']:.1f} MPa")
    print(f"Yield factor screen: {result['yield_factor_of_safety_screen']:.2f}")
    print(f"Estimated mass: {result['estimated_mass_kg']:.3f} kg")
    print(f"Miner damage screen: {result['Miner_damage_screen']:.6g}")
    print(f"Outputs written to: {args.outdir.resolve()}")
    print("These values are not a safe-life, FEA, or airworthiness result.")


if __name__ == "__main__":
    main()
