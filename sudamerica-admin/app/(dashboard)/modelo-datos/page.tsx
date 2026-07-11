"use client";

import { DataModelDiagram } from "@/components/data-model/DataModelDiagram";
import { useDataModel } from "@/hooks/useAdminDataModel";
import type { DataModelColumn, DataModelTable } from "@/lib/types";
import {
	Accordion,
	Alert,
	Badge,
	Card,
	Grid,
	Group,
	ScrollArea,
	SimpleGrid,
	Skeleton,
	Stack,
	Table,
	Text,
	TextInput,
	Title,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import {
	IconAlertCircle,
	IconDatabase,
	IconGitBranch,
	IconSearch,
	IconTable,
} from "@tabler/icons-react";
import dayjs from "dayjs";
import { useEffect, useState } from "react";

function SummaryCard({
	label,
	value,
}: {
	label: string;
	value: number | string;
}) {
	return (
		<Card p="md" withBorder>
			<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
				{label}
			</Text>
			<Text size="xl" fw={700} mt={4}>
				{value}
			</Text>
		</Card>
	);
}

function ColumnFlags({ column }: { column: DataModelColumn }) {
	return (
		<Group gap="xs" wrap="wrap">
			{column.primary_key && (
				<Badge color="blue" variant="light">
					PK
				</Badge>
			)}
			{column.foreign_key && (
				<Badge color="grape" variant="light">
					FK
				</Badge>
			)}
			{column.unique && (
				<Badge color="teal" variant="light">
					UNIQUE
				</Badge>
			)}
			<Badge color={column.nullable ? "gray" : "red"} variant="light">
				{column.nullable ? "NULL" : "NOT NULL"}
			</Badge>
		</Group>
	);
}

function WrappedMonoText({ value }: { value: string }) {
	return (
		<Text
			ff="monospace"
			size="sm"
			style={{
				whiteSpace: "normal",
				overflowWrap: "anywhere",
				wordBreak: "break-word",
				lineHeight: 1.45,
			}}
		>
			{value}
		</Text>
	);
}

function matchesSearch(table: DataModelTable, rawSearch: string) {
	if (!rawSearch) return true;

	const search = rawSearch.toLowerCase();
	return [
		table.name,
		table.model_name || "",
		table.description || "",
		...table.columns.flatMap((column) => [column.name, column.type, column.foreign_key || ""]),
		...table.relations.flatMap((relation) => [
			relation.column,
			relation.references_table,
			relation.references_column,
		]),
		...table.indexes.flatMap((index) => [index.name, ...index.columns]),
	].some((value) => value.toLowerCase().includes(search));
}

function getConnectivityScore(tableName: string, tables: DataModelTable[]) {
	let score = 0;

	for (const table of tables) {
		for (const relation of table.relations) {
			if (table.name === tableName || relation.references_table === tableName) {
				score += 1;
			}
		}
	}

	return score;
}

function getDefaultFocusedTable(tables: DataModelTable[]) {
	if (tables.length === 0) return null;

	return (
		[...tables].sort((left, right) => {
			const rightScore = getConnectivityScore(right.name, tables);
			const leftScore = getConnectivityScore(left.name, tables);
			if (rightScore !== leftScore) return rightScore - leftScore;
			return left.name.localeCompare(right.name);
		})[0]?.name ?? null
	);
}

export default function ModeloDatosPage() {
	const { data, isLoading, error } = useDataModel();
	const [search, setSearch] = useState("");
	const [debouncedSearch] = useDebouncedValue(search, 250);
	const [focusedTableName, setFocusedTableName] = useState<string | null>(null);

	const filteredTables =
		data?.tables.filter((table) => matchesSearch(table, debouncedSearch)) || [];

	useEffect(() => {
		if (!data?.tables.length) {
			setFocusedTableName(null);
			return;
		}

		const hasCurrentFocus = data.tables.some((table) => table.name === focusedTableName);
		if (hasCurrentFocus) return;

		setFocusedTableName(getDefaultFocusedTable(data.tables));
	}, [data, focusedTableName]);

	if (isLoading) {
		return (
			<Stack gap="lg">
				<Title order={2}>Modelo de datos</Title>
				<Grid>
					{Array.from({ length: 4 }).map((_, index) => (
						<Grid.Col key={`summary-${index.toString()}`} span={{ base: 12, sm: 6, lg: 3 }}>
							<Skeleton h={92} radius="md" />
						</Grid.Col>
					))}
				</Grid>
				<Skeleton h={520} radius="xl" />
				<Skeleton h={44} radius="md" />
				<Skeleton h={420} radius="md" />
			</Stack>
		);
	}

	if (error || !data) {
		return (
			<Stack gap="lg">
				<Title order={2}>Modelo de datos</Title>
				<Alert
					color="red"
					icon={<IconAlertCircle size={18} />}
					title="No fue posible cargar el modelo"
				>
					{error instanceof Error ? error.message : "Error desconocido"}
				</Alert>
			</Stack>
		);
	}

	return (
		<Stack gap="lg">
			<Stack gap={4}>
				<Title order={2}>Modelo de datos</Title>
				<Text c="dimmed" size="sm">
					Vista actual del esquema administrado por la plataforma. Ultima actualizacion:{" "}
					{dayjs(data.generated_at).format("DD/MM/YYYY HH:mm")}
				</Text>
			</Stack>

			<Grid>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<SummaryCard label="Tablas" value={data.summary.total_tables} />
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<SummaryCard label="Columnas" value={data.summary.total_columns} />
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<SummaryCard label="Relaciones" value={data.summary.total_relationships} />
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<SummaryCard label="Tablas multi-tenant" value={data.summary.tenant_scoped_tables} />
				</Grid.Col>
			</Grid>

			<DataModelDiagram
				tables={data.tables}
				selectedTableName={focusedTableName}
				onSelectTable={setFocusedTableName}
			/>

			<Card p="md" withBorder>
				<Group justify="space-between" mb="md">
					<Group gap="xs">
						<IconDatabase size={18} />
						<Text fw={600}>Enums del dominio</Text>
					</Group>
					<Text size="sm" c="dimmed">
						{data.enums.length} definidos
					</Text>
				</Group>
				<SimpleGrid cols={{ base: 1, md: 2, xl: 3 }}>
					{data.enums.map((enumItem) => (
						<Card key={enumItem.name} p="sm" withBorder>
							<Text fw={600} size="sm" mb="xs">
								{enumItem.name}
							</Text>
							<Group gap="xs">
								{enumItem.values.map((value) => (
									<Badge key={`${enumItem.name}-${value}`} variant="light">
										{value}
									</Badge>
								))}
							</Group>
						</Card>
					))}
				</SimpleGrid>
			</Card>

			<Card p="md" withBorder>
				<Group justify="space-between" align="end" mb="md">
					<Stack gap={2}>
						<Group gap="xs">
							<IconTable size={18} />
							<Text fw={600}>Detalle por tablas</Text>
						</Group>
						<Text size="sm" c="dimmed">
							Busca por tabla, columna, indice o relacion. El filtro afecta esta vista detallada.
						</Text>
					</Stack>
					<Text size="sm" c="dimmed">
						{filteredTables.length} visibles
					</Text>
				</Group>

				<TextInput
					placeholder="Buscar en el modelo..."
					leftSection={<IconSearch size={16} />}
					value={search}
					onChange={(event) => setSearch(event.currentTarget.value)}
					mb="md"
				/>

				{filteredTables.length === 0 ? (
					<Text c="dimmed" ta="center" py="xl">
						No hay tablas que coincidan con esa busqueda.
					</Text>
				) : (
					<Accordion variant="contained" radius="md">
						{filteredTables.map((table) => (
							<Accordion.Item key={table.name} value={table.name}>
								<Accordion.Control>
									<Group justify="space-between" align="flex-start" wrap="wrap">
										<Stack gap={2} style={{ flex: "1 1 340px", minWidth: 0 }}>
											<Group gap="xs">
												<Text fw={600}>{table.name}</Text>
												{table.model_name && (
													<Badge variant="outline" color="dark">
														{table.model_name}
													</Badge>
												)}
											</Group>
											{table.description && (
												<Text size="sm" c="dimmed">
													{table.description}
												</Text>
											)}
										</Stack>
										<Group gap="xs" justify="flex-end" wrap="wrap" style={{ maxWidth: 420 }}>
											<Badge variant="light">{table.columns.length} columnas</Badge>
											<Badge variant="light" color="grape">
												{table.relations.length} relaciones
											</Badge>
											{table.tenant_scoped && (
												<Badge color="indigo" variant="light">
													multi-tenant
												</Badge>
											)}
											{table.has_soft_delete && (
												<Badge color="teal" variant="light">
													soft-delete
												</Badge>
											)}
											<Badge
												color="indigo"
												variant="outline"
												style={{ cursor: "pointer" }}
												onClick={(event) => {
													event.stopPropagation();
													setFocusedTableName(table.name);
												}}
											>
												ver en diagrama
											</Badge>
										</Group>
									</Group>
								</Accordion.Control>
								<Accordion.Panel>
									<Stack gap="md">
										{table.relations.length > 0 && (
											<Card p="sm" bg="gray.0">
												<Group gap="xs" mb="xs">
													<IconGitBranch size={16} />
													<Text fw={600} size="sm">
														Relaciones
													</Text>
												</Group>
												<Stack gap="xs">
													{table.relations.map((relation) => (
														<Card
															key={`${table.name}-${relation.column}-${relation.references_table}`}
															padding="xs"
															radius="md"
															withBorder
															bg="white"
														>
															<WrappedMonoText
																value={`${relation.column} -> ${relation.references_table}.${relation.references_column || "id"}${relation.on_delete ? ` (${relation.on_delete})` : ""}`}
															/>
														</Card>
													))}
												</Stack>
											</Card>
										)}

										{table.indexes.length > 0 && (
											<Card p="sm" bg="gray.0">
												<Text fw={600} size="sm" mb="xs">
													Indices
												</Text>
												<Stack gap="xs">
													{table.indexes.map((index) => (
														<Card
															key={`${table.name}-${index.name}`}
															padding="xs"
															radius="md"
															withBorder
															bg="white"
														>
															<Group gap="xs" mb={4} wrap="wrap">
																<Badge variant="light" color={index.unique ? "teal" : "gray"}>
																	{index.unique ? "UNIQUE" : "INDEX"}
																</Badge>
																<Text size="sm" fw={600}>
																	{index.name}
																</Text>
															</Group>
															<WrappedMonoText value={index.columns.join(", ")} />
														</Card>
													))}
												</Stack>
											</Card>
										)}

										<ScrollArea offsetScrollbars scrollbarSize={8} type="auto">
											<Table
												striped
												highlightOnHover
												horizontalSpacing="md"
												verticalSpacing="sm"
												style={{ minWidth: 1120, tableLayout: "fixed" }}
											>
												<Table.Thead>
													<Table.Tr>
														<Table.Th style={{ width: "20%" }}>Columna</Table.Th>
														<Table.Th style={{ width: "18%" }}>Tipo</Table.Th>
														<Table.Th style={{ width: "20%" }}>Flags</Table.Th>
														<Table.Th style={{ width: "20%" }}>Default</Table.Th>
														<Table.Th style={{ width: "22%" }}>Referencia</Table.Th>
													</Table.Tr>
												</Table.Thead>
												<Table.Tbody>
													{table.columns.map((column) => (
														<Table.Tr key={`${table.name}-${column.name}`}>
															<Table.Td>
																<WrappedMonoText value={column.name} />
															</Table.Td>
															<Table.Td>
																<WrappedMonoText value={column.type} />
															</Table.Td>
															<Table.Td>
																<ColumnFlags column={column} />
															</Table.Td>
															<Table.Td>
																{column.default ? (
																	<WrappedMonoText value={column.default} />
																) : (
																	<Text c="dimmed">—</Text>
																)}
															</Table.Td>
															<Table.Td>
																{column.foreign_key ? (
																	<WrappedMonoText value={column.foreign_key} />
																) : (
																	<Text c="dimmed">—</Text>
																)}
															</Table.Td>
														</Table.Tr>
													))}
												</Table.Tbody>
											</Table>
										</ScrollArea>
									</Stack>
								</Accordion.Panel>
							</Accordion.Item>
						))}
					</Accordion>
				)}
			</Card>
		</Stack>
	);
}
