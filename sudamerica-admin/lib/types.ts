export interface AuthTokens {
	access_token: string;
	refresh_token: string;
}

export interface JwtPayload {
	sub: string;
	tenant_id: string;
	role: string;
	email?: string;
	exp: number;
	iat: number;
}

export interface Usuario {
	id: string;
	tenant_id: string;
	nombre: string;
	apellido: string;
	email: string;
	role: string;
	activo: boolean;
	created_at: string;
	updated_at: string;
}

export interface AuthState {
	user: Usuario | null;
	tokens: AuthTokens | null;
}

export interface PaginatedResponse<T> {
	data: T[];
	meta: {
		total: number;
		page: number;
		page_size: number;
		total_pages: number;
	};
}

// ── Admin types ──

export interface TenantAdmin {
	id: string;
	nombre: string;
	slug: string;
	plan: string;
	max_users: number;
	max_leads_mes: number;
	stripe_customer_id: string | null;
	stripe_subscription_id: string | null;
	config: Record<string, unknown> | null;
	activo: boolean;
	created_at: string;
	updated_at: string;
	user_count: number;
	lead_count: number;
}

export interface UserAdmin {
	id: string;
	tenant_id: string;
	email: string;
	nombre: string;
	apellido: string;
	role: string;
	email_verified: boolean;
	activo: boolean;
	created_at: string;
	updated_at: string;
	tenant_nombre: string | null;
}

export interface MetricsOverview {
	total_tenants: number;
	active_tenants: number;
	total_users: number;
	total_leads_month: number;
	total_conversations_today: number;
	mrr: number;
	active_whatsapp_instances: number;
}

export interface TimeseriesPoint {
	date: string;
	tenants: number;
	leads: number;
	conversations: number;
}

export interface TopTenantItem {
	tenant_id: string;
	tenant_nombre: string;
	plan: string;
	leads: number;
	conversations: number;
	users: number;
}

export interface PlatformKeyInfo {
	provider: string;
	masked_key: string;
	status: string;
	balance: number | null;
}

export interface PlatformKeysResponse {
	openai: PlatformKeyInfo | null;
	gemini: PlatformKeyInfo | null;
}

export interface TenantKeyItem {
	id: string;
	tenant_id: string;
	tenant_nombre: string | null;
	provider: string;
	masked_key: string;
	created_at: string;
}

// ── Password reset (P0-2 quality gate) ──

export interface ResetPasswordResponse {
	reset_token: string;
	temp_password: string;
	expires_at: string;
}

export interface SetPasswordRequest {
	reset_token: string;
	new_password: string;
}

export interface WhatsAppInstance {
	id: string;
	tenant_id: string;
	tenant_nombre: string | null;
	instance_name: string;
	status: string;
	phone: string | null;
}

export interface ServiceHealth {
	name: string;
	url: string;
	status: string;
	latency_ms: number | null;
}

export interface DataModelSummary {
	total_tables: number;
	total_columns: number;
	tenant_scoped_tables: number;
	total_relationships: number;
}

export interface DataModelEnum {
	name: string;
	values: string[];
}

export interface DataModelColumn {
	name: string;
	type: string;
	nullable: boolean;
	primary_key: boolean;
	unique: boolean;
	default: string | null;
	foreign_key: string | null;
}

export interface DataModelRelation {
	column: string;
	references_table: string;
	references_column: string;
	on_delete: string | null;
}

export interface DataModelIndex {
	name: string;
	columns: string[];
	unique: boolean;
}

export interface DataModelTable {
	name: string;
	model_name: string | null;
	description: string | null;
	tenant_scoped: boolean;
	has_soft_delete: boolean;
	columns: DataModelColumn[];
	relations: DataModelRelation[];
	indexes: DataModelIndex[];
}

export interface DataModelResponse {
	generated_at: string;
	summary: DataModelSummary;
	enums: DataModelEnum[];
	tables: DataModelTable[];
}
