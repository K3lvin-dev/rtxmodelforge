export * from "./chat";
export * from "./engine";
export * from "./gpu";
export * from "./operations";
export * from "./system";
export * from "./theme";

export interface PrevGpuValues {
	vramUsed: number | undefined;
	temperature: number | undefined;
	utilization: number | undefined;
	clockCore: number | undefined;
	clockMem: number | undefined;
}
