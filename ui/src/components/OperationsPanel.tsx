/* ── RTX Model Forge · Operations Panel ──
   Command list. Each row = one CLI operation with status, shortcut, and action. */

import { useCallback, useRef, useState } from "react";
import { executeCommand } from "../lib/cli";
import type { OpDef, OperationId, SystemState } from "../types";

interface Tooltip {
	text: string;
	x: number;
	y: number;
}

interface Handlers {
	prepare?: () => void | Promise<void>;
	serve?: () => void | Promise<void>;
	chat?: () => void | Promise<void>;
	run?: () => void | Promise<void>;
	login?: () => void | Promise<void>;
	doctor?: () => void | Promise<void>;
	list?: () => void | Promise<void>;
	delete?: () => void | Promise<void>;
	refresh?: () => void;
}

interface OperationsPanelProps {
	state: SystemState;
	handlers: Handlers;
}

export function OperationsPanel({ state, handlers }: OperationsPanelProps) {
	const [loadingOp, setLoadingOp] = useState<OperationId | null>(null);
	const loadingRef = useRef<OperationId | null>(null);
	const [tooltip, setTooltip] = useState<Tooltip | null>(null);

	const runningEngine = state.engines.find((e) => e.status === "running");
	const hasEngines = state.engines.length > 0;
	const gpuOk = state.gpu.detected;
	const cliOk = state.cliAvailable;

	const ops: OpDef[] = [
		{
			id: "prepare",
			label: "Prepare",
			kbd: "P",
			disabled: !cliOk,
			disabledReason: !cliOk ? "CLI indisponível" : null,
			statusLabel: hasEngines ? `${state.engines.length} engine(s)` : "Nenhuma",
			statusKind: hasEngines ? "ok" : "warn",
		},
		{
			id: "serve",
			label: "Serve",
			kbd: "S",
			disabled: !cliOk || !hasEngines,
			disabledReason: !cliOk
				? "CLI indisponível"
				: !hasEngines
					? "Execute Prepare primeiro"
					: null,
			statusLabel: runningEngine
				? `${runningEngine.model} :${runningEngine.port}`
				: !hasEngines
					? "Sem engines"
					: "Parado",
			statusKind: runningEngine ? "ok" : null,
		},
		{
			id: "chat",
			label: "Chat",
			kbd: "C",
			disabled: !cliOk || !runningEngine,
			disabledReason: !cliOk
				? "CLI indisponível"
				: !runningEngine
					? "Nenhuma engine servindo"
					: null,
			statusLabel: runningEngine ? "Disponível" : "Indisponível",
			statusKind: runningEngine ? "ok" : "warn",
		},
		{
			id: "run",
			label: "Run",
			kbd: "R",
			disabled: !cliOk || !hasEngines,
			disabledReason: !cliOk
				? "CLI indisponível"
				: !hasEngines
					? "Execute Prepare primeiro"
					: null,
			statusLabel: hasEngines ? "Pronto" : "Sem engines",
			statusKind: hasEngines ? "ok" : null,
		},
		{
			id: "doctor",
			label: "Doctor",
			kbd: "D",
			disabled: !cliOk,
			disabledReason: !cliOk ? "CLI indisponível" : null,
			statusLabel: gpuOk ? "Sistema OK" : "GPU não detectada",
			statusKind: gpuOk ? "ok" : "err",
		},
		{
			id: "list",
			label: "List",
			kbd: "I",
			disabled: !cliOk,
			disabledReason: !cliOk ? "CLI indisponível" : null,
			statusLabel: hasEngines ? `${state.engines.length} engine(s)` : "Vazio",
			statusKind: null,
		},
		{
			id: "login",
			label: "Login",
			kbd: "L",
			disabled: !cliOk,
			disabledReason: !cliOk ? "CLI indisponível" : null,
			statusLabel: "HuggingFace",
			statusKind: "ok",
		},
		{
			id: "delete",
			label: "Delete",
			kbd: "X",
			disabled: !cliOk || !hasEngines,
			disabledReason: !cliOk
				? "CLI indisponível"
				: !hasEngines
					? "Nada para deletar"
					: null,
			statusLabel: null,
			statusKind: null,
		},
	];

	const handleClick = useCallback(
		async (op: OpDef) => {
			if (op.disabled || loadingRef.current) return;

			const handler = handlers[op.id];
			if (handler) {
				loadingRef.current = op.id;
				setLoadingOp(op.id);
				try {
					await handler();
				} finally {
					loadingRef.current = null;
					setLoadingOp(null);
				}
				return;
			}

			loadingRef.current = op.id;
			setLoadingOp(op.id);
			try {
				await executeCommand(op.id);
				handlers.refresh?.();
			} finally {
				loadingRef.current = null;
				setLoadingOp(null);
			}
		},
		[handlers],
	);

	return (
		<div className="operations">
			<span className="operations__header">Operações</span>
			<div className="operations__list">
				{ops.map((op) => {
					const isLoading = loadingOp === op.id;
					const isDisabled = op.disabled || loadingOp !== null;

					return (
						<button
							key={op.id}
							className={[
								"operations__item",
								isDisabled && "operations__item--disabled",
								isLoading && "operations__item--loading",
							]
								.filter(Boolean)
								.join(" ")}
							disabled={isDisabled}
							onClick={() => handleClick(op)}
							onMouseEnter={(e) => {
								if (op.disabledReason) {
									const rect = e.currentTarget.getBoundingClientRect();
									setTooltip({
										text: op.disabledReason,
										x: rect.left,
										y: rect.bottom + 4,
									});
								}
							}}
							onMouseLeave={() => setTooltip(null)}
						>
							<span className="operations__name">{op.label}</span>
							{op.statusLabel && (
								<span
									className={`operations__status${op.statusKind ? ` operations__status--${op.statusKind}` : ""}`}
								>
									{op.statusLabel}
								</span>
							)}
							{isLoading ? (
								<span className="operations__spinner" />
							) : (
								<span className="operations__kbd">{op.kbd}</span>
							)}
						</button>
					);
				})}
			</div>

			{tooltip && (
				<div
					className="tooltip"
					style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
				>
					{tooltip.text}
				</div>
			)}
		</div>
	);
}
