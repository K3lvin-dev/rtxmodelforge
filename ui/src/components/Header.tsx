/* ── RTX Model Forge · Header ── */

import type { Theme } from "../types";

interface HeaderProps {
	gpuDetected: boolean;
	cliAvailable: boolean;
	cliVersion: string | null;
	theme?: Theme;
	onToggleTheme?: () => void;
}

export function Header({
	gpuDetected,
	cliAvailable,
	cliVersion,
	theme,
	onToggleTheme,
}: HeaderProps) {
	const systemDot = !cliAvailable ? "err" : gpuDetected ? "ok" : "err";

	return (
		<header className="header">
			<div className="header__brand">
				<span className={`header__brand-dot header__brand-dot--${systemDot}`} />
				RTX Model Forge
			</div>
			<div className="header__status">
				<span className="header__status-item">
					<span
						className={`header__status-dot header__status-dot--${cliAvailable ? "ok" : "err"}`}
					/>
					{cliAvailable ? "CLI" : "CLI offline"}
				</span>
				{gpuDetected && (
					<span className="header__status-item">
						<span className="header__status-dot header__status-dot--ok" />
						GPU
					</span>
				)}
				{cliVersion && (
					<span className="header__status-item">v{cliVersion}</span>
				)}
				{onToggleTheme && (
					<div
						data-impeccable-variants="ae8332d8"
						data-impeccable-variant-count="3"
						style={{ display: "contents" }}
					>
						{/* impeccable-variants-start ae8332d8 */}
						<style
							data-impeccable-css="ae8332d8"
							dangerouslySetInnerHTML={{
								__html: `
                  [data-impeccable-variant="1"] {
                    background: oklch(0.68 0.10 200 / var(--p-color-amount, 1));
                    border-color: transparent !important;
                    color: var(--ink);
                  }
                  [data-impeccable-variant="1"]:hover {
                    background: oklch(0.74 0.12 200 / var(--p-color-amount, 1));
                  }
                  [data-impeccable-variant="1"]:active {
                    background: oklch(0.55 0.08 200 / var(--p-color-amount, 1));
                  }
                  [data-impeccable-variant="2"] {
                    border-color: transparent !important;
                    width: 32px;
                    height: 32px;
                  }
                  [data-impeccable-variant="2"]:hover {
                    background: var(--surface-hi);
                  }
                  [data-impeccable-variant="2"][data-p-shape="square"] {
                    border-radius: var(--radius-sm);
                  }
                  [data-impeccable-variant="2"][data-p-shape="circle"] {
                    border-radius: 50%;
                  }
                  [data-impeccable-variant="3"][data-p-size="sm"] {
                    width: 24px;
                    height: 24px;
                    font-size: 12px;
                  }
                  [data-impeccable-variant="3"][data-p-size="md"] {
                    width: 28px;
                    height: 28px;
                  }
                  [data-impeccable-variant="3"][data-p-size="lg"] {
                    width: 36px;
                    height: 36px;
                    font-size: 18px;
                  }
                  [data-impeccable-variant="3"]:hover {
                    background: var(--surface-hi);
                    border-color: var(--muted);
                    color: var(--ink);
                  }
                `,
							}}
						/>
						<button
							className="header__theme-toggle"
							data-impeccable-variant="1"
							data-impeccable-params={JSON.stringify([
								{
									id: "color-amount",
									kind: "range",
									min: 0,
									max: 1,
									step: 0.05,
									default: 1,
									label: "Color amount",
								},
							])}
							onClick={onToggleTheme}
							aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
							title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
						>
							{theme === "dark" ? "☀" : "☾"}
						</button>
						<button
							className="header__theme-toggle"
							data-impeccable-variant="2"
							data-impeccable-params={JSON.stringify([
								{
									id: "shape",
									kind: "steps",
									default: "circle",
									label: "Shape",
									options: [
										{ value: "square", label: "Square" },
										{ value: "circle", label: "Circle" },
									],
								},
							])}
							style={{ display: "none" }}
							onClick={onToggleTheme}
							aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
							title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
						>
							{theme === "dark" ? "☀" : "☾"}
						</button>
						<button
							className="header__theme-toggle"
							data-impeccable-variant="3"
							data-impeccable-params={JSON.stringify([
								{
									id: "size",
									kind: "steps",
									default: "md",
									label: "Size",
									options: [
										{ value: "sm", label: "Small" },
										{ value: "md", label: "Medium" },
										{ value: "lg", label: "Large" },
									],
								},
							])}
							style={{ display: "none" }}
							onClick={onToggleTheme}
							aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
							title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
						>
							{theme === "dark" ? "☀" : "☾"}
						</button>
						{/* impeccable-variants-end ae8332d8 */}
					</div>
				)}
			</div>
		</header>
	);
}
