/* ── RTX Model Forge · App Root ──
   Cockpit shell. State machine: loading → hardware check → operations.
   Every state is handled. No dead ends. */

import { useCallback, useEffect, useState } from "react";
import {
	FirstRunDiagnostic,
	NoEnginesDiagnostic,
	NoGpuDiagnostic,
} from "./components/Diagnostic";
import { ErrorBanner } from "./components/ErrorBanner";
import { Footer } from "./components/Footer";
import { HardwarePanel } from "./components/HardwarePanel";
import { Header } from "./components/Header";
import { Layout } from "./components/Layout";
import { OperationsPanel } from "./components/OperationsPanel";
import { useKeyboard } from "./hooks/useKeyboard";
import { useSystemState } from "./hooks/useSystemState";
import { useTheme } from "./hooks/useTheme";
import { executeCommand } from "./lib/cli";
import type { OperationId } from "./types";

const POLL_MS = 2000;

export default function App() {
	const { state, prevValues, loading, error, refresh, isFirstRun } =
		useSystemState();
	const { theme, toggle: toggleTheme } = useTheme();
	const [bannerError, setBannerError] = useState<string | null>(null);
	const [chatOpen, setChatOpen] = useState(false);

	const runOperation = useCallback(
		async (opId: OperationId) => {
			setBannerError(null);
			try {
				const result = await executeCommand(opId);
				if (!result.ok) {
					setBannerError(`${opId}: ${result.error || "falhou"}`);
				} else {
					refresh();
				}
			} catch (err) {
				setBannerError(
					`${opId}: ${err instanceof Error ? err.message : "erro desconhecido"}`,
				);
			}
		},
		[refresh],
	);

	const handlers = {
		prepare: () => runOperation("prepare"),
		serve: () => runOperation("serve"),
		chat: () => setChatOpen((o) => !o),
		run: () => runOperation("run"),
		login: () => runOperation("login"),
		doctor: () => runOperation("doctor"),
		list: () => runOperation("list"),
		delete: () => runOperation("delete"),
		refresh,
	};

	useKeyboard(handlers);

	useEffect(() => {
		function onRun(e: Event) {
			const detail = (e as CustomEvent).detail as OperationId;
			runOperation(detail);
		}
		window.addEventListener("rtxmf:run", onRun);
		return () => window.removeEventListener("rtxmf:run", onRun);
	}, [runOperation]);

	/* ── Loading skeleton ── */
	if (loading && !state) {
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					minHeight: "100dvh",
				}}
			>
				<Header
					theme={theme}
					onToggleTheme={toggleTheme}
					gpuDetected={false}
					cliAvailable={false}
					cliVersion={null}
				/>
				<main className="main">
					<div className="hardware">
						<div
							className="skeleton"
							style={{ height: "88px", borderRadius: "var(--radius-lg)" }}
						/>
						<div
							className="skeleton"
							style={{ height: "88px", borderRadius: "var(--radius-lg)" }}
						/>
						<div
							className="skeleton"
							style={{ height: "88px", borderRadius: "var(--radius-lg)" }}
						/>
						<div
							className="skeleton"
							style={{ height: "88px", borderRadius: "var(--radius-lg)" }}
						/>
					</div>
					<div
						style={{
							marginTop: "var(--space-10)",
							display: "flex",
							flexDirection: "column",
							gap: "1px",
						}}
					>
						{[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
							<div
								key={i}
								className="skeleton"
								style={{
									height: "40px",
									borderRadius:
										i === 1
											? "var(--radius-lg) var(--radius-lg) 0 0"
											: i === 8
												? "0 0 var(--radius-lg) var(--radius-lg)"
												: "0",
								}}
							/>
						))}
					</div>
				</main>
				<Footer cliVersion={null} pollIntervalMs={POLL_MS} />
			</div>
		);
	}

	/* ── Error state (CLI completely unreachable) ── */
	if (!state?.cliAvailable) {
		return (
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					minHeight: "100dvh",
				}}
			>
				<Header
					theme={theme}
					onToggleTheme={toggleTheme}
					gpuDetected={false}
					cliAvailable={false}
					cliVersion={null}
				/>
				{error && (
					<ErrorBanner message={`CLI: ${error}`} onDismiss={() => refresh()} />
				)}
				<main className="main">
					<div className="diagnostic">
						<span className="diagnostic__icon">✕</span>
						<h2 className="diagnostic__title">CLI não respondeu</h2>
						<p className="diagnostic__body">
							Verifique a instalação do RTX Model Forge. O comando `rtxmf` deve
							estar disponível no PATH.
						</p>
						<button className="diagnostic__action" onClick={() => refresh()}>
							Tentar novamente
						</button>
					</div>
				</main>
				<Footer cliVersion={null} pollIntervalMs={POLL_MS} />
			</div>
		);
	}

	/* ── GPU not detected ── */
	if (!state.gpu.detected) {
		return (
			<Layout
				theme={theme}
				onToggleTheme={toggleTheme}
				cliVersion={state.cliVersion}
				pollIntervalMs={POLL_MS}
				bannerError={bannerError}
				onDismissError={() => setBannerError(null)}
				chatOpen={chatOpen}
				chatState={state}
				onCloseChat={() => setChatOpen(false)}
			>
				<NoGpuDiagnostic />
				<div style={{ marginTop: "var(--space-10)" }} />
				<OperationsPanel state={state} handlers={handlers} onError={setBannerError} />
			</Layout>
		);
	}

	/* ── First run (GPU detected, has engines, not seen before) ── */
	if (isFirstRun && state.engines.length > 0) {
		return (
			<Layout
				theme={theme}
				onToggleTheme={toggleTheme}
				cliVersion={state.cliVersion}
				pollIntervalMs={POLL_MS}
				bannerError={bannerError}
				onDismissError={() => setBannerError(null)}
				chatOpen={chatOpen}
				chatState={state}
				onCloseChat={() => setChatOpen(false)}
			>
				<FirstRunDiagnostic />
				<div style={{ marginTop: "var(--space-10)" }} />
				<HardwarePanel gpu={state.gpu} prevValues={prevValues} />
				<div style={{ marginTop: "var(--space-10)" }} />
				<OperationsPanel state={state} handlers={handlers} onError={setBannerError} />
			</Layout>
		);
	}

	/* ── No engines (GPU detected, nothing installed) ── */
	if (state.engines.length === 0) {
		return (
			<Layout
				theme={theme}
				onToggleTheme={toggleTheme}
				cliVersion={state.cliVersion}
				pollIntervalMs={POLL_MS}
				bannerError={bannerError}
				onDismissError={() => setBannerError(null)}
				chatOpen={chatOpen}
				chatState={state}
				onCloseChat={() => setChatOpen(false)}
			>
				<NoEnginesDiagnostic />
				<div style={{ marginTop: "var(--space-10)" }} />
				<HardwarePanel gpu={state.gpu} prevValues={prevValues} />
				<div style={{ marginTop: "var(--space-10)" }} />
				<OperationsPanel state={state} handlers={handlers} onError={setBannerError} />
			</Layout>
		);
	}

	/* ── Normal operating state ── */
	return (
		<Layout
			theme={theme}
			onToggleTheme={toggleTheme}
			cliVersion={state.cliVersion}
			pollIntervalMs={POLL_MS}
			bannerError={bannerError}
			onDismissError={() => setBannerError(null)}
			chatOpen={chatOpen}
			chatState={state}
			onCloseChat={() => setChatOpen(false)}
		>
			<HardwarePanel gpu={state.gpu} prevValues={prevValues} />
			<div style={{ marginTop: "var(--space-10)" }} />
			<OperationsPanel state={state} handlers={handlers} onError={setBannerError} />
		</Layout>
	);
}
