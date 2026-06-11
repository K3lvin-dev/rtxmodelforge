/* ── RTX Model Forge · Theme Hook ── */

import { useEffect, useState } from "react";
import type { Theme } from "../types";

const STORAGE_KEY = "rtxmf-theme";

export function useTheme(): { theme: Theme; toggle: () => void } {
	const [theme, setTheme] = useState<Theme>(() => {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored === "dark" || stored === "light") return stored;
		if (window.matchMedia?.("(prefers-color-scheme: light)").matches)
			return "light";
		return "dark";
	});

	useEffect(() => {
		document.documentElement.setAttribute("data-theme", theme);
		localStorage.setItem(STORAGE_KEY, theme);
	}, [theme]);

	const toggle = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

	return { theme, toggle };
}
