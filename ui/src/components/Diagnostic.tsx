/* ── RTX Model Forge · Diagnostic States ──
   Empty states that teach the interface. Not a wizard, not a tour. */

export function NoGpuDiagnostic() {
	return (
		<div className="diagnostic">
			<span className="diagnostic__icon">⚠</span>
			<h2 className="diagnostic__title">Nenhuma GPU NVIDIA detectada</h2>
			<p className="diagnostic__body">
				O RTX Model Forge requer uma GPU NVIDIA com suporte a CUDA. Verifique a
				instalação dos drivers e execute o diagnóstico.
			</p>
			<button
				className="diagnostic__action"
				onClick={() =>
					window.dispatchEvent(
						new CustomEvent("rtxmf:run", { detail: "doctor" }),
					)
				}
			>
				Executar Doctor
				<span className="diagnostic__kbd">D</span>
			</button>
		</div>
	);
}

export function NoEnginesDiagnostic() {
	return (
		<div className="diagnostic">
			<span className="diagnostic__icon">⟳</span>
			<h2 className="diagnostic__title">Nenhuma engine instalada</h2>
			<p className="diagnostic__body">
				GPU detectada. Execute Prepare para compilar sua primeira engine de
				inferência e começar a rodar modelos localmente.
			</p>
			<button
				className="diagnostic__action"
				onClick={() =>
					window.dispatchEvent(
						new CustomEvent("rtxmf:run", { detail: "prepare" }),
					)
				}
			>
				Prepare
				<span className="diagnostic__kbd">P</span>
			</button>
		</div>
	);
}

export function FirstRunDiagnostic() {
	return (
		<div className="diagnostic">
			<span className="diagnostic__icon">✓</span>
			<h2 className="diagnostic__title">RTX Model Forge pronto</h2>
			<p className="diagnostic__body">
				GPU detectada, engines instaladas. Sirva um modelo para começar.
			</p>
			<button
				className="diagnostic__action"
				onClick={() =>
					window.dispatchEvent(
						new CustomEvent("rtxmf:run", { detail: "serve" }),
					)
				}
			>
				Serve
				<span className="diagnostic__kbd">S</span>
			</button>
		</div>
	);
}
