/* ── RTX Model Forge · Hardware Panel ──
   nvtop-inspired metrics display. Monospaced values, surgical color.
   This is the heart of the cockpit. */

import type { GpuInfo, PrevGpuValues } from "../types";

function formatVRAM(mb: number): string {
	if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
	return `${mb} MB`;
}

function flashClass(current: number, prev: number | undefined): string {
	if (prev !== undefined && current !== prev) return " value-updated";
	return "";
}

interface HardwarePanelProps {
	gpu: GpuInfo;
	prevValues?: PrevGpuValues;
}

export function HardwarePanel({ gpu, prevValues }: HardwarePanelProps) {
	if (!gpu.detected) {
		return (
			<div className="hardware">
				<div className="hardware__gpu-name">GPU: Nenhuma detectada</div>
				<div className="hardware__metric">
					<span className="hardware__metric-label">Status</span>
					<span
						className="hardware__metric-value hardware__metric-value--danger"
						style={{ fontSize: "var(--text-lg)" }}
					>
						Offline
					</span>
				</div>
			</div>
		);
	}

	const vramPct =
		gpu.vramTotal > 0 ? Math.round((gpu.vramUsed / gpu.vramTotal) * 100) : 0;
	const vramBarClass =
		vramPct > 95
			? "hardware__bar-fill--danger"
			: vramPct > 85
				? "hardware__bar-fill--warn"
				: "";
	const tempClass =
		gpu.temperature > 85
			? " hardware__metric-value--danger"
			: gpu.temperature > 75
				? " hardware__metric-value--warn"
				: "";

	return (
		<div className="hardware">
			<div className="hardware__gpu-name">GPU: {gpu.name}</div>

			{/* VRAM */}
			<div className="hardware__metric">
				<span className="hardware__metric-label">VRAM</span>
				<span
					className={`hardware__metric-value${vramPct > 85 ? tempClass : ""}${flashClass(gpu.vramUsed, prevValues?.vramUsed)}`}
				>
					{formatVRAM(gpu.vramUsed)}
				</span>
				<span className="hardware__metric-sub">
					/ {formatVRAM(gpu.vramTotal)} · {vramPct}%
				</span>
				<div className="hardware__bar-wrap">
					<div
						className={`hardware__bar-fill ${vramBarClass}`}
						style={{ width: `${vramPct}%` }}
					/>
				</div>
			</div>

			{/* Temperature */}
			<div className="hardware__metric">
				<span className="hardware__metric-label">Temp</span>
				<span
					className={`hardware__metric-value${tempClass}${flashClass(gpu.temperature, prevValues?.temperature)}`}
				>
					{gpu.temperature}°C
				</span>
				<span className="hardware__metric-sub">
					{gpu.temperature > 85
						? "Crítico"
						: gpu.temperature > 75
							? "Elevado"
							: "Normal"}
				</span>
			</div>

			{/* Utilization */}
			<div className="hardware__metric">
				<span className="hardware__metric-label">GPU Load</span>
				<span
					className={`hardware__metric-value${flashClass(gpu.utilization, prevValues?.utilization)}`}
				>
					{gpu.utilization}%
				</span>
				<div className="hardware__bar-wrap">
					<div
						className="hardware__bar-fill"
						style={{ width: `${gpu.utilization}%` }}
					/>
				</div>
			</div>

			{/* Core Clock */}
			<div className="hardware__metric">
				<span className="hardware__metric-label">Core Clock</span>
				<span
					className={`hardware__metric-value${flashClass(gpu.clockCore, prevValues?.clockCore)}`}
				>
					{gpu.clockCore} MHz
				</span>
			</div>

			{/* Memory Clock */}
			<div className="hardware__metric">
				<span className="hardware__metric-label">Mem Clock</span>
				<span
					className={`hardware__metric-value${flashClass(gpu.clockMem, prevValues?.clockMem)}`}
				>
					{gpu.clockMem} MHz
				</span>
			</div>
		</div>
	);
}
