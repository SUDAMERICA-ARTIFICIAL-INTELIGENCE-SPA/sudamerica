"use client";

import {
	useDeactivateTenant,
	useTenant,
	useTenants,
	useUpdateTenant,
} from "@/hooks/useAdminTenants";
import { useUsers } from "@/hooks/useAdminUsers";
import type { TenantAdmin, UserAdmin } from "@/lib/types";
import {
	ActionIcon,
	Alert,
	Badge,
	Button,
	Card,
	Center,
	Divider,
	Drawer,
	Group,
	Loader,
	Pagination,
	Select,
	SimpleGrid,
	Skeleton,
	Stack,
	Table,
	Text,
	TextInput,
	ThemeIcon,
	Title,
	Tooltip,
} from "@mantine/core";
import { useDebouncedValue, useDisclosure } from "@mantine/hooks";
import { modals } from "@mantine/modals";
import {
	IconAlertCircle,
	IconArrowsLeftRight,
	IconBuilding,
	IconEye,
	IconSearch,
	IconTrash,
	IconUsers,
} from "@tabler/icons-react";
import dayjs from "dayjs";
import type { ElementType } from "react";
import { useState } from "react";

const ROLE_COLORS: Record<string, string> = {
	SUPERADMIN: "red",
	ADMIN: "indigo",
	ASESOR: "teal",
	VIEWER: "gray",
};

interface SummaryCardProps {
	color: string;
	icon: ElementType;
	label: string;
	value: number;
}

function SummaryCard({ color, icon: Icon, label, value }: SummaryCardProps) {
	return (
		<Card withBorder p="lg" radius="md">
			<Group justify="space-between" align="flex-start">
				<div>
					<Text size="xs" tt="uppercase" fw={700} c="dimmed">
						{label}
					</Text>
					<Text size="xl" fw={700} mt={6}>
						{value}
					</Text>
				</div>
				<ThemeIcon size="xl" radius="md" variant="light" color={color}>
					<Icon size={22} />
				</ThemeIcon>
			</Group>
		</Card>
	);
}

function getErrorMessage(error: unknown, fallback: string) {
	if (error instanceof Error && error.message) {
		return error.message;
	}

	return fallback;
}

function TenantUsersTable({
	isLoading,
	totalUsers,
	users,
	usersError,
}: {
	isLoading: boolean;
	totalUsers: number;
	users: UserAdmin[];
	usersError: unknown;
}) {
	if (isLoading) {
		return (
			<Center py="xl">
				<Loader size="sm" />
			</Center>
		);
	}

	if (usersError) {
		return (
			<Alert color="red" icon={<IconAlertCircle size={16} />} variant="light">
				{getErrorMessage(usersError, "No fue posible cargar los empleados de la organizacion.")}
			</Alert>
		);
	}

	if (users.length === 0) {
		return (
			<Alert color="gray" variant="light">
				Esta organizacion no tiene empleados asociados.
			</Alert>
		);
	}

	return (
		<Stack gap="sm">
			<Group justify="space-between">
				<Text fw={600}>Empleados asociados</Text>
				<Text size="sm" c="dimmed">
					{users.length === totalUsers
						? `${totalUsers} usuario${totalUsers === 1 ? "" : "s"}`
						: `Mostrando ${users.length} de ${totalUsers} usuarios`}
				</Text>
			</Group>

			<div style={{ overflowX: "auto" }}>
				<Table striped highlightOnHover>
					<Table.Thead>
						<Table.Tr>
							<Table.Th>Nombre</Table.Th>
							<Table.Th>Email</Table.Th>
							<Table.Th>Rol</Table.Th>
							<Table.Th>Estado</Table.Th>
							<Table.Th>Creado</Table.Th>
						</Table.Tr>
					</Table.Thead>
					<Table.Tbody>
						{users.map((user) => (
							<Table.Tr key={user.id}>
								<Table.Td fw={500}>
									{user.nombre} {user.apellido}
								</Table.Td>
								<Table.Td>{user.email}</Table.Td>
								<Table.Td>
									<Badge color={ROLE_COLORS[user.role] || "gray"} variant="light">
										{user.role}
									</Badge>
								</Table.Td>
								<Table.Td>
									<Badge color={user.activo ? "green" : "red"} variant="dot">
										{user.activo ? "Activo" : "Inactivo"}
									</Badge>
								</Table.Td>
								<Table.Td>{dayjs(user.created_at).format("DD/MM/YYYY")}</Table.Td>
							</Table.Tr>
						))}
					</Table.Tbody>
				</Table>
			</div>
		</Stack>
	);
}

export default function OrganizationsPage() {
	const [search, setSearch] = useState("");
	const [debouncedSearch] = useDebouncedValue(search, 300);
	const [planFilter, setPlanFilter] = useState<string | null>(null);
	const [page, setPage] = useState(1);
	const [selectedTenant, setSelectedTenant] = useState<TenantAdmin | null>(null);
	const [drawerOpened, drawer] = useDisclosure(false);

	const { data, isLoading, error } = useTenants({
		page,
		search: debouncedSearch || undefined,
		plan: planFilter || undefined,
	});
	const updateMutation = useUpdateTenant();
	const deactivateMutation = useDeactivateTenant();

	const selectedTenantId = selectedTenant?.id ?? "";
	const {
		data: tenantDetail,
		isLoading: tenantDetailLoading,
		error: tenantDetailError,
	} = useTenant(selectedTenantId);
	const {
		data: tenantUsers,
		isLoading: tenantUsersLoading,
		error: tenantUsersError,
	} = useUsers(
		{
			page: 1,
			page_size: 100,
			tenant_id: selectedTenantId || undefined,
		},
		{
			enabled: drawerOpened && !!selectedTenantId,
		},
	);

	const organizations = data?.data ?? [];
	const currentTenant = tenantDetail ?? selectedTenant;
	const organizationsTotal = data?.meta.total ?? 0;
	const totalVisibleEmployees = organizations.reduce(
		(total, tenant) => total + tenant.user_count,
		0,
	);
	const totalVisiblePro = organizations.filter((tenant) => tenant.plan === "PRO").length;
	const totalVisibleActive = organizations.filter((tenant) => tenant.activo).length;

	const openTenantDetail = (tenant: TenantAdmin) => {
		setSelectedTenant(tenant);
		drawer.open();
	};

	const closeTenantDetail = () => {
		drawer.close();
		setSelectedTenant(null);
	};

	const togglePlan = (tenant: TenantAdmin) => {
		const nextPlan = tenant.plan === "FREE" ? "PRO" : "FREE";
		const maxUsers = nextPlan === "PRO" ? 15 : 3;
		const maxLeadsMes = nextPlan === "PRO" ? 999999 : 100;

		updateMutation.mutate({
			id: tenant.id,
			data: {
				plan: nextPlan,
				max_users: maxUsers,
				max_leads_mes: maxLeadsMes,
			},
		});
	};

	const confirmDeactivate = (tenant: TenantAdmin) => {
		modals.openConfirmModal({
			title: "Desactivar organizacion",
			children: (
				<Text size="sm">
					Esta accion desactiva <b>{tenant.nombre}</b> y sus usuarios perderan acceso al panel.
				</Text>
			),
			labels: { confirm: "Desactivar", cancel: "Cancelar" },
			confirmProps: { color: "red" },
			onConfirm: () => {
				deactivateMutation.mutate(tenant.id);
				if (selectedTenant?.id === tenant.id) {
					closeTenantDetail();
				}
			},
		});
	};

	return (
		<Stack gap="lg">
			<Stack gap={4}>
				<Title order={2}>Organizaciones</Title>
				<Text c="dimmed">
					Administra los restaurantes creados y revisa los empleados asociados a cada organizacion.
				</Text>
			</Stack>

			<SimpleGrid cols={{ base: 1, sm: 2, xl: 4 }}>
				<SummaryCard
					color="indigo"
					icon={IconBuilding}
					label="Organizaciones"
					value={organizationsTotal}
				/>
				<SummaryCard
					color="teal"
					icon={IconUsers}
					label="Empleados visibles"
					value={totalVisibleEmployees}
				/>
				<SummaryCard color="green" icon={IconBuilding} label="Activas" value={totalVisibleActive} />
				<SummaryCard color="grape" icon={IconBuilding} label="Plan PRO" value={totalVisiblePro} />
			</SimpleGrid>

			<Group align="end">
				<TextInput
					placeholder="Buscar por nombre"
					leftSection={<IconSearch size={16} />}
					value={search}
					onChange={(event) => {
						setSearch(event.currentTarget.value);
						setPage(1);
					}}
					w={320}
				/>
				<Select
					placeholder="Plan"
					data={[
						{ value: "FREE", label: "FREE" },
						{ value: "PRO", label: "PRO" },
					]}
					value={planFilter}
					onChange={(value) => {
						setPlanFilter(value);
						setPage(1);
					}}
					clearable
					w={160}
				/>
			</Group>

			{isLoading ? (
				<Card withBorder p="md">
					<Stack gap="sm">
						{Array.from({ length: 6 }).map((_, index) => (
							<Skeleton key={`organization-skeleton-${index.toString()}`} h={44} />
						))}
					</Stack>
				</Card>
			) : error ? (
				<Alert color="red" icon={<IconAlertCircle size={16} />} variant="light">
					{getErrorMessage(error, "No fue posible cargar las organizaciones.")}
				</Alert>
			) : organizations.length === 0 ? (
				<Card withBorder p="xl">
					<Stack gap={4}>
						<Text fw={600}>No hay organizaciones para mostrar.</Text>
						<Text size="sm" c="dimmed">
							{debouncedSearch || planFilter
								? "Ajusta los filtros para encontrar otra organizacion."
								: "Todavia no se han creado restaurantes en la plataforma."}
						</Text>
					</Stack>
				</Card>
			) : (
				<Card withBorder p={0}>
					<div style={{ overflowX: "auto" }}>
						<Table striped highlightOnHover>
							<Table.Thead>
								<Table.Tr>
									<Table.Th>Organizacion</Table.Th>
									<Table.Th>Plan</Table.Th>
									<Table.Th>Empleados</Table.Th>
									<Table.Th>Leads del mes</Table.Th>
									<Table.Th>Creado</Table.Th>
									<Table.Th>Estado</Table.Th>
									<Table.Th>Acciones</Table.Th>
								</Table.Tr>
							</Table.Thead>
							<Table.Tbody>
								{organizations.map((tenant) => (
									<Table.Tr key={tenant.id}>
										<Table.Td>
											<Stack gap={2}>
												<Text fw={600}>{tenant.nombre}</Text>
												<Text size="xs" c="dimmed">
													{tenant.slug}
												</Text>
											</Stack>
										</Table.Td>
										<Table.Td>
											<Badge color={tenant.plan === "PRO" ? "indigo" : "gray"} variant="light">
												{tenant.plan}
											</Badge>
										</Table.Td>
										<Table.Td>
											<Text fw={500}>{tenant.user_count}</Text>
											<Text size="xs" c="dimmed">
												Limite: {tenant.max_users}
											</Text>
										</Table.Td>
										<Table.Td>
											<Text fw={500}>{tenant.lead_count}</Text>
											<Text size="xs" c="dimmed">
												Max: {tenant.max_leads_mes}
											</Text>
										</Table.Td>
										<Table.Td>{dayjs(tenant.created_at).format("DD/MM/YYYY")}</Table.Td>
										<Table.Td>
											<Badge color={tenant.activo ? "green" : "red"} variant="dot">
												{tenant.activo ? "Activa" : "Inactiva"}
											</Badge>
										</Table.Td>
										<Table.Td>
											<Group gap="xs" wrap="nowrap">
												<Tooltip label="Ver detalle">
													<ActionIcon variant="subtle" onClick={() => openTenantDetail(tenant)}>
														<IconEye size={16} />
													</ActionIcon>
												</Tooltip>
												<Tooltip label={`Cambiar a ${tenant.plan === "FREE" ? "PRO" : "FREE"}`}>
													<ActionIcon
														variant="subtle"
														color="blue"
														onClick={() => togglePlan(tenant)}
													>
														<IconArrowsLeftRight size={16} />
													</ActionIcon>
												</Tooltip>
												<Tooltip label="Desactivar">
													<ActionIcon
														variant="subtle"
														color="red"
														onClick={() => confirmDeactivate(tenant)}
													>
														<IconTrash size={16} />
													</ActionIcon>
												</Tooltip>
											</Group>
										</Table.Td>
									</Table.Tr>
								))}
							</Table.Tbody>
						</Table>
					</div>
				</Card>
			)}

			{data?.meta && data.meta.total_pages > 1 && (
				<Group justify="center">
					<Pagination total={data.meta.total_pages} value={page} onChange={setPage} />
				</Group>
			)}

			<Drawer
				opened={drawerOpened}
				onClose={closeTenantDetail}
				title={currentTenant ? `Organizacion: ${currentTenant.nombre}` : "Detalle de organizacion"}
				position="right"
				size="xl"
			>
				{!currentTenant && tenantDetailLoading ? (
					<Stack gap="sm">
						<Skeleton h={28} radius="sm" />
						<Skeleton h={20} radius="sm" />
						<Skeleton h={20} radius="sm" />
						<Skeleton h={220} radius="sm" />
					</Stack>
				) : currentTenant ? (
					<Stack gap="lg">
						{tenantDetailError && (
							<Alert color="yellow" icon={<IconAlertCircle size={16} />} variant="light">
								{getErrorMessage(
									tenantDetailError,
									"No fue posible cargar el detalle completo de la organizacion.",
								)}
							</Alert>
						)}

						<Card withBorder p="md">
							<Stack gap="sm">
								<Group justify="space-between" align="flex-start">
									<div>
										<Text fw={700} size="lg">
											{currentTenant.nombre}
										</Text>
										<Text size="sm" c="dimmed">
											Slug: {currentTenant.slug}
										</Text>
									</div>
									<Badge color={currentTenant.activo ? "green" : "red"} variant="dot">
										{currentTenant.activo ? "Activa" : "Inactiva"}
									</Badge>
								</Group>

								<SimpleGrid cols={{ base: 1, sm: 2 }}>
									<Text size="sm">
										Plan: <Badge variant="light">{currentTenant.plan}</Badge>
									</Text>
									<Text size="sm">
										Creado: {dayjs(currentTenant.created_at).format("DD/MM/YYYY HH:mm")}
									</Text>
									<Text size="sm">
										Empleados: {currentTenant.user_count} / {currentTenant.max_users}
									</Text>
									<Text size="sm">
										Leads del mes: {currentTenant.lead_count} / {currentTenant.max_leads_mes}
									</Text>
								</SimpleGrid>

								<Group>
									<Button
										variant="light"
										onClick={() => togglePlan(currentTenant)}
										loading={updateMutation.isPending}
									>
										Cambiar a {currentTenant.plan === "FREE" ? "PRO" : "FREE"}
									</Button>
									<Button
										color="red"
										variant="light"
										onClick={() => confirmDeactivate(currentTenant)}
										loading={deactivateMutation.isPending}
									>
										Desactivar organizacion
									</Button>
								</Group>
							</Stack>
						</Card>

						{currentTenant.config && (
							<Card withBorder p="md">
								<Stack gap="sm">
									<Text fw={600}>Configuracion</Text>
									<pre
										style={{
											background: "var(--mantine-color-gray-0)",
											borderRadius: 8,
											fontSize: 12,
											margin: 0,
											overflowX: "auto",
											padding: 12,
										}}
									>
										{JSON.stringify(currentTenant.config, null, 2)}
									</pre>
								</Stack>
							</Card>
						)}

						<Divider />

						<TenantUsersTable
							isLoading={tenantUsersLoading}
							totalUsers={tenantUsers?.meta.total ?? currentTenant.user_count}
							users={tenantUsers?.data ?? []}
							usersError={tenantUsersError}
						/>
					</Stack>
				) : (
					<Alert color="yellow" icon={<IconAlertCircle size={16} />} variant="light">
						Selecciona una organizacion para ver su informacion.
					</Alert>
				)}
			</Drawer>
		</Stack>
	);
}
