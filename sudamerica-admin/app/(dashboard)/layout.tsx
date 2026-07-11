"use client";

import { AdminSidebar } from "@/components/layout/AdminSidebar";
import { RequireAuth } from "@/lib/auth";
import { Box } from "@mantine/core";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RequireAuth>
      <Box style={{ display: "flex", minHeight: "100vh" }}>
        <AdminSidebar />
        <Box flex={1} p="xl" bg="gray.0" style={{ overflow: "auto" }}>
          {children}
        </Box>
      </Box>
    </RequireAuth>
  );
}
