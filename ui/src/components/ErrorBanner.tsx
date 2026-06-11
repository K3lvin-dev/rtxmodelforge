/* ── RTX Model Forge · Error Banner ── */

interface ErrorBannerProps {
	message: string;
	onDismiss: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
	return (
		<div className="error-banner">
			<span>⚠</span>
			<span className="error-banner__text">{message}</span>
			<button className="error-banner__dismiss" onClick={onDismiss}>
				Dismiss
			</button>
		</div>
	);
}
