"use client";

import { useAuth } from "@/lib/auth";
import { Box, NavLink, ScrollArea, Stack, Text, ThemeIcon } from "@mantine/core";
import {
	IconBrandWhatsapp,
	IconBuilding,
	IconChartBar,
	IconDashboard,
	IconDatabase,
	IconKey,
	IconLogout,
	IconSettings,
	IconUsers,
} from "@tabler/icons-react";
import { usePathname, useRouter } from "next/navigation";

const NAV_ITEMS = [
	{ label: "Dashboard", href: "/", icon: IconDashboard },
	{
		label: "Organizaciones",
		href: "/organizaciones",
		aliases: ["/tenants"],
		icon: IconBuilding,
	},
	{ label: "Usuarios", href: "/users", icon: IconUsers },
	{ label: "API Keys", href: "/api-keys", icon: IconKey },
	{ label: "Modelo de datos", href: "/modelo-datos", icon: IconDatabase },
	{ label: "Métricas", href: "/metrics", icon: IconChartBar },
	{ label: "WhatsApp", href: "/whatsapp", icon: IconBrandWhatsapp },
	{ label: "Configuración", href: "/config", icon: IconSettings },
];

export function AdminSidebar() {
	const pathname = usePathname();
	const router = useRouter();
	const { logout, user } = useAuth();

	return (
		<Box w={260} h="100vh" bg="dark.7" style={{ display: "flex", flexDirection: "column" }}>
			<Box p="md" pb="xs">
				<Text fw={700} size="lg" c="white">
					Sudamerica Admin
				</Text>
				<Text size="xs" c="dimmed">
					{user?.email}
				</Text>
			</Box>

			<ScrollArea flex={1} px="xs">
				<Stack gap={2} mt="sm">
					{NAV_ITEMS.map((item) => (
						<NavLink
							key={item.href}
							label={item.label}
							leftSection={
								<ThemeIcon variant="light" size="sm" color="indigo">
									<item.icon size={16} />
								</ThemeIcon>
							}
							active={
								item.href === "/"
									? pathname === "/"
									: pathname.startsWith(item.href) ||
										(item.aliases?.some((alias) => pathname.startsWith(alias)) ?? false)
							}
							onClick={() => router.push(item.href)}
							styles={{
								root: { borderRadius: 8, color: "var(--mantine-color-gray-3)" },
							}}
						/>
					))}
				</Stack>
			</ScrollArea>

			<Box p="xs" pb="md">
				<NavLink
					label="Cerrar sesión"
					leftSection={
						<ThemeIcon variant="light" size="sm" color="red">
							<IconLogout size={16} />
						</ThemeIcon>
					}
					onClick={logout}
					styles={{
						root: { borderRadius: 8, color: "var(--mantine-color-gray-3)" },
					}}
				/>
			</Box>
		</Box>
	);
}
