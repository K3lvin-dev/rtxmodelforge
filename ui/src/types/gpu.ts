export interface GpuInfo {
	name: string;
	vramTotal: number;
	vramUsed: number;
	temperature: number;
	utilization: number;
	clockCore: number;
	clockMem: number;
	detected: boolean;
}
