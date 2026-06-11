/* ── RTX Model Forge · Footer ── */

interface FooterProps {
	cliVersion: string | null;
	pollIntervalMs: number;
}

export function Footer({ cliVersion, pollIntervalMs }: FooterProps) {
	return (
		<footer className="footer">
			<span className="footer__item">
				RTXMF
				{cliVersion && ` v${cliVersion}`}
			</span>
			<span className="footer__item">Poll: {pollIntervalMs / 1000}s</span>
		</footer>
	);
}
