export type EngineStatus = "running" | "stopped" | "building";

export interface EngineInfo {
	name: string;
	status: EngineStatus;
	model: string | null;
	port: number | null;
}
