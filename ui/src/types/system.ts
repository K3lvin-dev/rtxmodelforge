import type { EngineInfo } from "./engine";
import type { GpuInfo } from "./gpu";

export interface SystemState {
	gpu: GpuInfo;
	engines: EngineInfo[];
	cliAvailable: boolean;
	cliError: string | null;
	cliVersion: string | null;
}
