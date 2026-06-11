/* ── RTX Model Forge · useSystemState ──
   Polls the CLI for GPU metrics + engine status. Returns the full state tree. */

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSystemState } from "../lib/cli";
import type { PrevGpuValues, SystemState } from "../types";

const POLL_INTERVAL_MS = 2000;

export interface UseSystemStateReturn {
	state: SystemState | null;
	prevValues: PrevGpuValues;
	loading: boolean;
	error: string | null;
	refresh: () => void;
	isFirstRun: boolean;
}

export function useSystemState(): UseSystemStateReturn {
	const [state, setState] = useState<SystemState | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [isFirstRun, setIsFirstRun] = useState(true);
	const [prevValues, setPrevValues] = useState<PrevGpuValues>({
		vramUsed: undefined,
		temperature: undefined,
		utilization: undefined,
		clockCore: undefined,
		clockMem: undefined,
	});
	const mountedRef = useRef(true);
	const isFirstRunRef = useRef(true);

	const refresh = useCallback(async () => {
		try {
			const next = await fetchSystemState();
			if (!mountedRef.current) return;

			setState((prev) => {
				if (prev) {
					setPrevValues({
						vramUsed: prev.gpu.vramUsed,
						temperature: prev.gpu.temperature,
						utilization: prev.gpu.utilization,
						clockCore: prev.gpu.clockCore,
						clockMem: prev.gpu.clockMem,
					});
				}
				return next;
			});
			setError(null);

			if (isFirstRunRef.current) {
				isFirstRunRef.current = false;
				setIsFirstRun(false);
			}
		} catch (err) {
			if (!mountedRef.current) return;
			setError(
				err instanceof Error ? err.message : "Failed to fetch system state",
			);
		} finally {
			if (mountedRef.current) setLoading(false);
		}
	}, []);

	useEffect(() => {
		mountedRef.current = true;
		refresh();
		const interval = setInterval(refresh, POLL_INTERVAL_MS);
		return () => {
			mountedRef.current = false;
			clearInterval(interval);
		};
	}, [refresh]);

	return { state, prevValues, loading, error, refresh, isFirstRun };
}
