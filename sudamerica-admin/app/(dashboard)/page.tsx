"use client";

import { useMetricsOverview, useMetricsTimeseries } from "@/hooks/useAdminMetrics";
import { Card, Grid, Group, Skeleton, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import {
	IconBrandWhatsapp,
	IconBuilding,
	IconCurrencyDollar,
	IconMessageCircle,
	IconRobot,
	IconUserPlus,
	IconUsers,
} from "@tabler/icons-react";
import {
	Area,
	AreaChart,
	CartesianGrid,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

interface KpiCardProps {
	label: string;
	value: string | number;
	icon: React.ElementType;
	color: string;
}

function KpiCard({ label, value, icon: Icon, color }: KpiCardProps) {
	return (
		<Card p="md">
			<Group justify="space-between">
				<div>
					<Text size="xs" c="dimmed" tt="uppercase" fw={600}>
						{label}
					</Text>
					<Text size="xl" fw={700} mt={4}>
						{value}
					</Text>
				</div>
				<ThemeIcon size="xl" radius="md" variant="light" color={color}>
					<Icon size={24} />
				</ThemeIcon>
			</Group>
		</Card>
	);
}

export default function DashboardPage() {
	const { data: overview, isLoading } = useMetricsOverview();
	const { data: timeseries } = useMetricsTimeseries(30);

	if (isLoading || !overview) {
		return (
			<Stack gap="lg">
				<Title order={2}>Dashboard</Title>
				<Grid>
					{Array.from({ length: 7 }).map((_, i) => (
						<Grid.Col key={`skel-${i.toString()}`} span={{ base: 12, sm: 6, lg: 3 }}>
							<Skeleton h={90} radius="md" />
						</Grid.Col>
					))}
				</Grid>
			</Stack>
		);
	}

	return (
		<Stack gap="lg">
			<Title order={2}>Dashboard</Title>

			<Grid>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="Organizaciones activas"
						value={overview.active_tenants}
						icon={IconBuilding}
						color="indigo"
					/>
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="Total usuarios"
						value={overview.total_users}
						icon={IconUsers}
						color="teal"
					/>
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="Leads este mes"
						value={overview.total_leads_month}
						icon={IconUserPlus}
						color="orange"
					/>
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="Conversaciones hoy"
						value={overview.total_conversations_today}
						icon={IconMessageCircle}
						color="cyan"
					/>
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="MRR"
						value={`$${overview.mrr.toFixed(0)}`}
						icon={IconCurrencyDollar}
						color="green"
					/>
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="WhatsApp conectados"
						value={overview.active_whatsapp_instances}
						icon={IconBrandWhatsapp}
						color="green"
					/>
				</Grid.Col>
				<Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
					<KpiCard
						label="Total organizaciones"
						value={overview.total_tenants}
						icon={IconRobot}
						color="violet"
					/>
				</Grid.Col>
			</Grid>

			{timeseries && timeseries.length > 0 && (
				<Card p="md">
					<Text fw={600} mb="md">
						Tendencia últimos 30 días
					</Text>
					<ResponsiveContainer width="100%" height={300}>
						<AreaChart data={timeseries}>
							<CartesianGrid strokeDasharray="3 3" />
							<XAxis dataKey="date" tick={{ fontSize: 12 }} />
							<YAxis tick={{ fontSize: 12 }} />
							<Tooltip />
							<Area
								type="monotone"
								dataKey="leads"
								stroke="#4C6EF5"
								fill="#4C6EF5"
								fillOpacity={0.1}
								name="Leads"
							/>
							<Area
								type="monotone"
								dataKey="conversations"
								stroke="#37B24D"
								fill="#37B24D"
								fillOpacity={0.1}
								name="Conversaciones"
							/>
						</AreaChart>
					</ResponsiveContainer>
				</Card>
			)}
		</Stack>
	);
}
