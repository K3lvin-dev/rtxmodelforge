/* ── RTX Model Forge · useKeyboard ──
   Global keyboard shortcuts. Surgical: one key = one operation. */

import { useEffect } from "react";
import type { KeyboardHandlers } from "../types";

export function useKeyboard(handlers: KeyboardHandlers): void {
	useEffect(() => {
		function onKeyDown(e: KeyboardEvent) {
			const tag = (e.target as HTMLElement).tagName;
			if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
			if (e.metaKey || e.ctrlKey || e.altKey) return;

			const key = e.key.toLowerCase();

			const map: Record<string, (() => void) | undefined> = {
				p: handlers.prepare,
				s: handlers.serve,
				c: handlers.chat,
				r: handlers.run,
				l: handlers.login,
				d: handlers.doctor,
				i: handlers.list,
				x: handlers.delete,
			};

			const handler = map[key];
			if (handler) {
				e.preventDefault();
				handler();
			}
		}

		window.addEventListener("keydown", onKeyDown);
		return () => window.removeEventListener("keydown", onKeyDown);
	}, [handlers]);
}
