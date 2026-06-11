/* ── RTX Model Forge · Layout Component
   Cockpit shell structure. Eliminates duplication across app states. */

import type { ReactNode } from "react";
import type { SystemState } from "../types";
import { ChatPanel } from "./ChatPanel";
import { ErrorBanner } from "./ErrorBanner";
import { Footer } from "./Footer";
import { Header } from "./Header";

interface LayoutProps {
	theme: "dark" | "light";
	onToggleTheme: () => void;
	cliVersion: string | null;
	pollIntervalMs: number;
	bannerError?: string | null;
	onDismissError?: () => void;
	chatOpen?: boolean;
	chatState?: SystemState;
	onCloseChat?: () => void;
	children: ReactNode;
}

export function Layout({
	theme,
	onToggleTheme,
	cliVersion,
	pollIntervalMs,
	bannerError,
	onDismissError,
	chatOpen = false,
	chatState,
	onCloseChat,
	children,
}: LayoutProps) {
	const gpuDetected = chatState?.gpu.detected ?? false;
	const cliAvailable = chatState?.cliAvailable ?? cliVersion !== null;

	return (
		<div className={`app-shell${chatOpen ? " app-shell--split" : ""}`}>
			<div className="app-shell__main">
				<Header
					theme={theme}
					onToggleTheme={onToggleTheme}
					gpuDetected={gpuDetected}
					cliAvailable={cliAvailable}
					cliVersion={cliVersion}
				/>
				{bannerError && onDismissError && (
					<ErrorBanner message={bannerError} onDismiss={onDismissError} />
				)}
				<main className="main">{children}</main>
				<Footer cliVersion={cliVersion} pollIntervalMs={pollIntervalMs} />
			</div>
			{chatOpen && chatState && onCloseChat && (
				<ChatPanel state={chatState} onClose={onCloseChat} />
			)}
		</div>
	);
}
