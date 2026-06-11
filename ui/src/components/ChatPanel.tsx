/* ── RTX Model Forge · Chat Panel ──
   Conversation interface. Streaming tokens, mono-forward, zero decorative bubbles.
   The model talks like an engineer, not a chatbot. */

import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat } from "../lib/cli";
import type { SystemState } from "../types";

interface ChatMessage {
	role: "user" | "model";
	content: string;
	timestamp: number;
	streaming?: boolean;
	tokens?: number;
	tokensPerSec?: number;
}

interface ChatPanelProps {
	state: SystemState;
	onClose: () => void;
}

export function ChatPanel({ state, onClose }: ChatPanelProps) {
	const [messages, setMessages] = useState<ChatMessage[]>([]);
	const [input, setInput] = useState("");
	const [streaming, setStreaming] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const messagesEndRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLTextAreaElement>(null);
	const abortRef = useRef<(() => void) | null>(null);

	const runningEngine = state.engines.find((e) => e.status === "running");
	const hasModel = !!runningEngine;

	useEffect(() => {
		if (messages.length > 0) {
			messagesEndRef.current?.scrollIntoView({
				behavior: "smooth",
				block: "end",
			});
		}
	}, [messages]);

	useEffect(() => {
		inputRef.current?.focus({ preventScroll: true });
	}, []);

	const handleSend = useCallback(async () => {
		const text = input.trim();
		if (!text || !hasModel || streaming) return;

		setError(null);
		setInput("");
		setStreaming(true);

		const userMsg: ChatMessage = {
			role: "user",
			content: text,
			timestamp: Date.now(),
		};
		setMessages((prev) => [...prev, userMsg]);

		const modelMsg: ChatMessage = {
			role: "model",
			content: "",
			timestamp: Date.now(),
			streaming: true,
		};
		setMessages((prev) => [...prev, modelMsg]);

		try {
			const startTime = Date.now();
			let tokenCount = 0;

			const abort = streamChat(
				text,
				(token) => {
					tokenCount++;
					setMessages((prev) => {
						const updated = [...prev];
						const lastIdx = updated.length - 1;
						const last = updated[lastIdx];
						if (last?.role === "model") {
							updated[lastIdx] = {
								...last,
								content: last.content + token,
								tokens: tokenCount,
								tokensPerSec:
									Math.round(
										(tokenCount / ((Date.now() - startTime) / 1000)) * 10,
									) / 10,
							};
						}
						return updated;
					});
				},
				() => {
					setMessages((prev) => {
						const updated = [...prev];
						const lastIdx = updated.length - 1;
						const last = updated[lastIdx];
						if (last?.role === "model") {
							updated[lastIdx] = {
								...last,
								streaming: false,
							};
						}
						return updated;
					});
					setStreaming(false);
				},
				(err) => {
					setError(err.message || "Stream failed");
					setMessages((prev) => prev.slice(0, -1));
					setStreaming(false);
				},
			);

			abortRef.current = abort;
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to start chat");
			setMessages((prev) => prev.slice(0, -1));
			setStreaming(false);
		}
	}, [input, hasModel, streaming]);

	const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
		if (e.key === "Enter" && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	};

	const handleStop = () => {
		if (abortRef.current) {
			abortRef.current();
			abortRef.current = null;
		}
		setStreaming(false);
		setMessages((prev) => {
			const updated = [...prev];
			const last = updated[updated.length - 1];
			if (last?.role === "model") {
				last.streaming = false;
			}
			return updated;
		});
	};

	if (!hasModel) {
		return (
			<aside className="chat">
				<div className="chat__header">
					<span className="chat__title">Chat</span>
					<button
						className="chat__close"
						onClick={onClose}
						aria-label="Close chat"
					>
						×
					</button>
				</div>
				<div className="chat__empty">
					<span className="chat__empty-icon">⊘</span>
					<h3 className="chat__empty-title">Nenhum modelo servindo</h3>
					<p className="chat__empty-body">
						Execute Serve para iniciar uma engine de inferência e começar a
						conversar com o modelo.
					</p>
					<button
						className="chat__empty-action"
						onClick={() =>
							window.dispatchEvent(
								new CustomEvent("rtxmf:run", { detail: "serve" }),
							)
						}
					>
						Serve
						<span className="chat__kbd">S</span>
					</button>
				</div>
			</aside>
		);
	}

	return (
		<aside className="chat">
			<div className="chat__header">
				<div className="chat__header-info">
					<span className="chat__title">Chat</span>
					<span className="chat__model">
						{runningEngine.model} :{runningEngine.port}
					</span>
				</div>
				<button
					className="chat__close"
					onClick={onClose}
					aria-label="Close chat"
				>
					×
				</button>
			</div>

			{error && (
				<div className="chat__error">
					<span>{error}</span>
					<button
						className="chat__error-dismiss"
						onClick={() => setError(null)}
					>
						×
					</button>
				</div>
			)}

			<div className="chat__messages">
				{messages.length === 0 && (
					<div className="chat__welcome">
						<span className="chat__welcome-label">READY</span>
						<p className="chat__welcome-text">
							Converse com {runningEngine.model}. Digite uma pergunta ou prompt.
						</p>
					</div>
				)}
				{messages.map((msg, i) => (
					<div key={i} className={`chat__message chat__message--${msg.role}`}>
						<span className="chat__message-role">
							{msg.role === "user" ? "USER" : "MODEL"}
						</span>
						<div className="chat__message-content">
							{msg.content}
							{msg.streaming && <span className="chat__cursor">▊</span>}
						</div>
						{msg.role === "model" && !msg.streaming && msg.tokens && (
							<span className="chat__message-meta">
								{msg.tokens} tokens · {msg.tokensPerSec} t/s
							</span>
						)}
					</div>
				))}
				<div ref={messagesEndRef} />
			</div>

			<div className="chat__input-wrap">
				<textarea
					ref={inputRef}
					className="chat__input"
					value={input}
					onChange={(e) => setInput(e.target.value)}
					onKeyDown={handleKeyDown}
					placeholder={
						streaming
							? "Gerando resposta..."
							: "Digite sua mensagem (Enter para enviar)"
					}
					disabled={streaming}
					rows={1}
				/>
				{streaming ? (
					<button
						className="chat__send chat__send--stop"
						onClick={handleStop}
						aria-label="Stop generation"
					>
						■
					</button>
				) : (
					<button
						className="chat__send"
						onClick={handleSend}
						disabled={!input.trim()}
						aria-label="Send message"
					>
						→
					</button>
				)}
			</div>
		</aside>
	);
}
