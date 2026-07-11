"use client";

import type { DataModelTable } from "@/lib/types";
import {
	Badge,
	Box,
	Card,
	Group,
	ScrollArea,
	Select,
	SimpleGrid,
	Stack,
	Text,
	ThemeIcon,
} from "@mantine/core";
import {
	IconArrowLeft,
	IconArrowRight,
	IconChartArrowsVertical,
	IconDatabase,
	IconTopologyStar3,
} from "@tabler/icons-react";
import type { ElementType } from "react";

const DIAGRAM_WIDTH = 1240;
const SIDE_NODE_WIDTH = 284;
const SIDE_NODE_HEIGHT = 104;
const FOCUS_NODE_WIDTH = 356;
const FOCUS_NODE_HEIGHT = 132;

type ConnectionDirection = "incoming" | "outgoing" | "self";

interface DiagramConnection {
	table: DataModelTable;
	tableName: string;
	labels: string[];
}

interface DataModelDiagramProps {
	tables: DataModelTable[];
	selectedTableName: string | null;
	onSelectTable: (tableName: string | null) => void;
}

function truncate(value: string, maxLength: number) {
	if (value.length <= maxLength) return value;
	if (maxLength <= 3) return value.slice(0, maxLength);
	return `${value.slice(0, maxLength - 3)}...`;
}

function summarizeLabels(labels: string[]) {
	if (labels.length === 0) return "Sin columnas relacionadas";
	if (labels.length === 1) return labels[0];
	return `${labels[0]} (+${labels.length - 1})`;
}

function formatLabel(fromTable: string, column: string, toTable: string, referencedColumn: string) {
	const target = referencedColumn ? `${toTable}.${referencedColumn}` : toTable;
	return `${fromTable}.${column} -> ${target}`;
}

function getTone(direction: Exclude<ConnectionDirection, "self"> | "focus") {
	if (direction === "incoming") {
		return {
			background: "#fff4e6",
			border: "#f08c00",
			text: "#8f5a00",
			accent: "#ffd8a8",
		};
	}

	if (direction === "outgoing") {
		return {
			background: "#ebfbee",
			border: "#2f9e44",
			text: "#1b4332",
			accent: "#b2f2bb",
		};
	}

	return {
		background: "#edf2ff",
		border: "#4263eb",
		text: "#1d3557",
		accent: "#bac8ff",
	};
}

function buildConnectionMap(
	tables: DataModelTable[],
	selectedTableName: string,
	direction: Exclude<ConnectionDirection, "self">,
) {
	const map = new Map<string, DiagramConnection>();

	for (const table of tables) {
		for (const relation of table.relations) {
			if (direction === "outgoing" && table.name === selectedTableName) {
				if (relation.references_table === selectedTableName) continue;

				const label = formatLabel(
					table.name,
					relation.column,
					relation.references_table,
					relation.references_column,
				);
				const existing = map.get(relation.references_table);

				if (existing) {
					existing.labels.push(label);
					continue;
				}

				const target = tables.find((candidate) => candidate.name === relation.references_table);
				if (!target) continue;

				map.set(relation.references_table, {
					table: target,
					tableName: target.name,
					labels: [label],
				});
			}

			if (
				direction === "incoming" &&
				relation.references_table === selectedTableName &&
				table.name !== selectedTableName
			) {
				const label = formatLabel(
					table.name,
					relation.column,
					relation.references_table,
					relation.references_column,
				);
				const existing = map.get(table.name);

				if (existing) {
					existing.labels.push(label);
					continue;
				}

				map.set(table.name, {
					table,
					tableName: table.name,
					labels: [label],
				});
			}
		}
	}

	return [...map.values()].sort((left, right) => {
		if (right.labels.length !== left.labels.length) {
			return right.labels.length - left.labels.length;
		}
		return left.tableName.localeCompare(right.tableName);
	});
}

function buildSelfConnections(tables: DataModelTable[], selectedTableName: string) {
	const selected = tables.find((table) => table.name === selectedTableName);
	if (!selected) return [];

	return selected.relations
		.filter((relation) => relation.references_table === selectedTableName)
		.map((relation) => ({
			table: selected,
			tableName: selected.name,
			labels: [
				formatLabel(
					selected.name,
					relation.column,
					relation.references_table,
					relation.references_column,
				),
			],
		}));
}

function distributeYPositions(count: number, canvasHeight: number, nodeHeight: number) {
	if (count === 0) return [];
	if (count === 1) return [canvasHeight / 2 - nodeHeight / 2];

	const top = 54;
	const bottom = 54;
	const available = canvasHeight - top - bottom - nodeHeight;
	const step = available / (count - 1);
	return Array.from({ length: count }, (_, index) => top + step * index);
}

function createPath(startX: number, startY: number, endX: number, endY: number) {
	const delta = Math.max(90, Math.abs(endX - startX) / 2);
	return `M ${startX} ${startY} C ${startX + delta} ${startY}, ${endX - delta} ${endY}, ${endX} ${endY}`;
}

function renderNode({
	table,
	connectionLabels,
	direction,
	x,
	y,
	width,
	height,
	interactive,
	onClick,
}: {
	table: DataModelTable;
	connectionLabels: string[];
	direction: ConnectionDirection;
	x: number;
	y: number;
	width: number;
	height: number;
	interactive: boolean;
	onClick?: () => void;
}) {
	const tone = getTone(direction === "self" ? "focus" : direction);
	const descriptor = truncate(
		table.model_name ||
			table.description ||
			(table.tenant_scoped ? "Tabla multi-tenant" : "Tabla global"),
		34,
	);
	const stats = `${table.columns.length} col | ${table.relations.length} rel`;
	const connectionSummary =
		direction === "self"
			? summarizeLabels(connectionLabels)
			: `${connectionLabels.length} enlace${connectionLabels.length === 1 ? "" : "s"} directo${connectionLabels.length === 1 ? "" : "s"}`;

	return (
		<g
			onClick={onClick}
			onKeyDown={(event) => {
				if (!interactive || !onClick) return;
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					onClick();
				}
			}}
			style={interactive ? { cursor: "pointer" } : undefined}
			tabIndex={interactive ? 0 : -1}
			role={interactive ? "button" : undefined}
		>
			<title>{[table.name, ...connectionLabels].join("\n")}</title>
			<rect
				x={x}
				y={y}
				width={width}
				height={height}
				rx={20}
				fill={tone.background}
				stroke={tone.border}
				strokeWidth={2}
			/>
			<rect x={x + 12} y={y + 12} width={width - 24} height={8} rx={4} fill={tone.accent} />
			<text x={x + 18} y={y + 38} fill={tone.text} fontSize="16" fontWeight="700">
				{truncate(table.name, 28)}
			</text>
			<text x={x + 18} y={y + 60} fill={tone.text} fontSize="12" opacity="0.85">
				{descriptor}
			</text>
			<text x={x + 18} y={y + 82} fill={tone.text} fontSize="12" fontWeight="600">
				{stats}
			</text>
			<text x={x + 18} y={y + height - 18} fill={tone.text} fontSize="11" opacity="0.8">
				{truncate(connectionSummary, 42)}
			</text>
		</g>
	);
}

function RelationshipList({
	title,
	description,
	icon,
	color,
	connections,
	onSelectTable,
	emptyText,
}: {
	title: string;
	description: string;
	icon: ElementType;
	color: string;
	connections: DiagramConnection[];
	onSelectTable: (tableName: string) => void;
	emptyText: string;
}) {
	const Icon = icon;

	return (
		<Card withBorder p="md" radius="lg" h="100%">
			<Stack gap="md">
				<Group justify="space-between" align="start">
					<Group gap="sm" align="center">
						<ThemeIcon color={color} variant="light" size="lg" radius="md">
							<Icon size={18} />
						</ThemeIcon>
						<Stack gap={0}>
							<Text fw={700}>{title}</Text>
							<Text size="sm" c="dimmed">
								{description}
							</Text>
						</Stack>
					</Group>
					<Badge variant="light" color={color}>
						{connections.length}
					</Badge>
				</Group>

				{connections.length === 0 ? (
					<Text c="dimmed" size="sm">
						{emptyText}
					</Text>
				) : (
					<Stack gap="sm">
						{connections.map((connection) => (
							<Card
								key={`${title}-${connection.tableName}`}
								withBorder
								padding="sm"
								radius="md"
								style={{ cursor: "pointer" }}
								onClick={() => onSelectTable(connection.tableName)}
							>
								<Stack gap={4}>
									<Group justify="space-between" align="start">
										<Text fw={600}>{connection.tableName}</Text>
										<Badge
											color={connection.table.tenant_scoped ? "indigo" : "gray"}
											variant="light"
										>
											{connection.table.tenant_scoped ? "multi-tenant" : "global"}
										</Badge>
									</Group>
									{connection.labels.map((label) => (
										<Text
											key={label}
											size="xs"
											c="dimmed"
											ff="monospace"
											style={{ overflowWrap: "anywhere", wordBreak: "break-word" }}
										>
											{label}
										</Text>
									))}
								</Stack>
							</Card>
						))}
					</Stack>
				)}
			</Stack>
		</Card>
	);
}

export function DataModelDiagram({
	tables,
	selectedTableName,
	onSelectTable,
}: DataModelDiagramProps) {
	const tableOptions = [...tables]
		.sort((left, right) => left.name.localeCompare(right.name))
		.map((table) => ({
			value: table.name,
			label: table.name,
		}));

	const selectedTable = tables.find((table) => table.name === selectedTableName) ?? null;

	if (!selectedTable) {
		return (
			<Card withBorder p="xl" radius="xl">
				<Text c="dimmed">No hay una tabla seleccionada para el diagrama.</Text>
			</Card>
		);
	}

	const incoming = buildConnectionMap(tables, selectedTable.name, "incoming");
	const outgoing = buildConnectionMap(tables, selectedTable.name, "outgoing");
	const selfConnections = buildSelfConnections(tables, selectedTable.name);
	const connectedTableCount = new Set([
		...incoming.map((connection) => connection.tableName),
		...outgoing.map((connection) => connection.tableName),
	]).size;

	const canvasHeight = Math.max(incoming.length, outgoing.length, 1) * 156 + 180;
	const leftNodeY = distributeYPositions(incoming.length, canvasHeight, SIDE_NODE_HEIGHT);
	const rightNodeY = distributeYPositions(outgoing.length, canvasHeight, SIDE_NODE_HEIGHT);
	const leftX = 48;
	const centerX = DIAGRAM_WIDTH / 2 - FOCUS_NODE_WIDTH / 2;
	const rightX = DIAGRAM_WIDTH - SIDE_NODE_WIDTH - 48;
	const centerY = canvasHeight / 2 - FOCUS_NODE_HEIGHT / 2;

	return (
		<Card
			withBorder
			radius="xl"
			p="lg"
			style={{
				background: "linear-gradient(180deg, rgba(248,249,250,1) 0%, rgba(255,255,255,1) 100%)",
			}}
		>
			<Stack gap="lg">
				<Group justify="space-between" align="end">
					<Stack gap={4}>
						<Group gap="xs">
							<ThemeIcon variant="light" color="indigo" size="lg" radius="md">
								<IconTopologyStar3 size={18} />
							</ThemeIcon>
							<Text fw={700} size="lg">
								Diagrama relacional
							</Text>
						</Group>
						<Text size="sm" c="dimmed">
							Selecciona una tabla para ver quien la referencia y a que tablas apunta.
						</Text>
					</Stack>

					<Select
						label="Tabla foco"
						placeholder="Selecciona una tabla"
						searchable
						data={tableOptions}
						value={selectedTable.name}
						onChange={onSelectTable}
						w={320}
					/>
				</Group>

				<SimpleGrid cols={{ base: 1, sm: 3 }}>
					<Card withBorder padding="md" radius="lg">
						<Stack gap={2}>
							<Text size="xs" c="dimmed" tt="uppercase" fw={700}>
								Tablas entrantes
							</Text>
							<Text size="xl" fw={800}>
								{incoming.length}
							</Text>
							<Text size="sm" c="dimmed">
								Tablas que tienen FKs hacia {selectedTable.name}
							</Text>
						</Stack>
					</Card>
					<Card withBorder padding="md" radius="lg">
						<Stack gap={2}>
							<Text size="xs" c="dimmed" tt="uppercase" fw={700}>
								Tablas conectadas
							</Text>
							<Text size="xl" fw={800}>
								{connectedTableCount}
							</Text>
							<Text size="sm" c="dimmed">
								Vecindad directa visible en el diagrama
							</Text>
						</Stack>
					</Card>
					<Card withBorder padding="md" radius="lg">
						<Stack gap={2}>
							<Text size="xs" c="dimmed" tt="uppercase" fw={700}>
								Tablas salientes
							</Text>
							<Text size="xl" fw={800}>
								{outgoing.length}
							</Text>
							<Text size="sm" c="dimmed">
								Tablas referenciadas desde {selectedTable.name}
							</Text>
						</Stack>
					</Card>
				</SimpleGrid>

				<Card
					withBorder
					radius="lg"
					p="md"
					style={{
						background:
							"radial-gradient(circle at top, rgba(237,242,255,0.55), rgba(255,255,255,0.98) 38%)",
					}}
				>
					<Stack gap="sm">
						<Group justify="space-between">
							<Group gap="xs">
								<ThemeIcon variant="light" color="gray" size="md">
									<IconDatabase size={16} />
								</ThemeIcon>
								<Text fw={600}>Mapa de conexiones directas</Text>
							</Group>
							<Group gap="xs">
								<Badge color="orange" variant="light">
									Entrantes
								</Badge>
								<Badge color="indigo" variant="light">
									Foco
								</Badge>
								<Badge color="green" variant="light">
									Salientes
								</Badge>
							</Group>
						</Group>

						<ScrollArea type="always" offsetScrollbars>
							<Box style={{ minWidth: DIAGRAM_WIDTH }}>
								<svg
									width="100%"
									height={canvasHeight}
									viewBox={`0 0 ${DIAGRAM_WIDTH} ${canvasHeight}`}
									preserveAspectRatio="xMidYMid meet"
								>
									<title>{`Diagrama relacional de ${selectedTable.name}`}</title>
									<defs>
										<pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
											<path
												d="M 28 0 L 0 0 0 28"
												fill="none"
												stroke="rgba(73, 80, 87, 0.08)"
												strokeWidth="1"
											/>
										</pattern>
									</defs>
									<rect
										x="0"
										y="0"
										width={DIAGRAM_WIDTH}
										height={canvasHeight}
										rx="28"
										fill="url(#grid)"
									/>

									{incoming.map((connection, index) => {
										const y = leftNodeY[index];
										return (
											<g key={`incoming-${connection.tableName}`}>
												<path
													d={createPath(
														leftX + SIDE_NODE_WIDTH,
														y + SIDE_NODE_HEIGHT / 2,
														centerX,
														centerY + FOCUS_NODE_HEIGHT / 2,
													)}
													fill="none"
													stroke="rgba(240, 140, 0, 0.7)"
													strokeWidth="2.5"
													strokeDasharray="8 8"
													strokeLinecap="round"
												/>
												{renderNode({
													table: connection.table,
													connectionLabels: connection.labels,
													direction: "incoming",
													x: leftX,
													y,
													width: SIDE_NODE_WIDTH,
													height: SIDE_NODE_HEIGHT,
													interactive: true,
													onClick: () => onSelectTable(connection.tableName),
												})}
											</g>
										);
									})}

									{outgoing.map((connection, index) => {
										const y = rightNodeY[index];
										return (
											<g key={`outgoing-${connection.tableName}`}>
												<path
													d={createPath(
														centerX + FOCUS_NODE_WIDTH,
														centerY + FOCUS_NODE_HEIGHT / 2,
														rightX,
														y + SIDE_NODE_HEIGHT / 2,
													)}
													fill="none"
													stroke="rgba(47, 158, 68, 0.72)"
													strokeWidth="2.5"
													strokeDasharray="8 8"
													strokeLinecap="round"
												/>
												{renderNode({
													table: connection.table,
													connectionLabels: connection.labels,
													direction: "outgoing",
													x: rightX,
													y,
													width: SIDE_NODE_WIDTH,
													height: SIDE_NODE_HEIGHT,
													interactive: true,
													onClick: () => onSelectTable(connection.tableName),
												})}
											</g>
										);
									})}

									{renderNode({
										table: selectedTable,
										connectionLabels: [
											`${incoming.length} entrantes | ${outgoing.length} salientes`,
										],
										direction: "self",
										x: centerX,
										y: centerY,
										width: FOCUS_NODE_WIDTH,
										height: FOCUS_NODE_HEIGHT,
										interactive: false,
									})}
								</svg>
							</Box>
						</ScrollArea>

						{incoming.length === 0 && outgoing.length === 0 && (
							<Text size="sm" c="dimmed">
								Esta tabla no tiene relaciones directas detectadas en el snapshot actual.
							</Text>
						)}
					</Stack>
				</Card>

				<SimpleGrid cols={{ base: 1, lg: 3 }}>
					<RelationshipList
						title="Entrantes"
						description="Tablas que dependen de la tabla foco"
						icon={IconArrowLeft}
						color="orange"
						connections={incoming}
						onSelectTable={(tableName) => onSelectTable(tableName)}
						emptyText="Ninguna tabla referencia esta tabla."
					/>
					<RelationshipList
						title="Salientes"
						description="Tablas que la tabla foco referencia"
						icon={IconArrowRight}
						color="green"
						connections={outgoing}
						onSelectTable={(tableName) => onSelectTable(tableName)}
						emptyText="La tabla foco no apunta a otras tablas."
					/>
					<RelationshipList
						title="Auto-relaciones"
						description="Referencias circulares sobre la misma tabla"
						icon={IconChartArrowsVertical}
						color="grape"
						connections={selfConnections}
						onSelectTable={(tableName) => onSelectTable(tableName)}
						emptyText="No hay auto-relaciones en esta tabla."
					/>
				</SimpleGrid>
			</Stack>
		</Card>
	);
}
