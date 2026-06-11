export type OperationId =
	| "prepare"
	| "serve"
	| "chat"
	| "run"
	| "login"
	| "doctor"
	| "list"
	| "delete";

export interface OpDef {
	id: OperationId;
	label: string;
	kbd: string;
	disabled: boolean;
	disabledReason: string | null;
	statusLabel: string | null;
	statusKind: "ok" | "warn" | "err" | null;
}

export interface KeyboardHandlers {
	[key: string]: () => void;
}

export interface CommandResult {
	ok: boolean;
	output: string;
	error: string | null;
}
