"use client";

import { AIAutoResponseToggle } from "@/components/prospectos/AIAutoResponseToggle";
import { ConversationChat } from "@/components/prospectos/ConversationChat";
import { ConversationList } from "@/components/prospectos/ConversationList";
import { DeliveryGroupBanner } from "@/components/prospectos/DeliveryGroupBanner";
import { OutboundComposer } from "@/components/prospectos/OutboundComposer";
import { QRModal } from "@/components/prospectos/QRModal";
import { WhatsAppStatus } from "@/components/prospectos/WhatsAppStatus";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { useConversationWebSocket } from "@/hooks/useConversationWebSocket";
import { ActionIcon, Box, Divider, Group, Paper, Select, Stack, Text } from "@mantine/core";
import { useDisclosure, useMediaQuery } from "@mantine/hooks";
import { IconArrowLeft, IconBrandWhatsapp, IconMessages } from "@tabler/icons-react";
import { useCallback, useState } from "react";

const CANAL_OPTIONS = [
  { value: "", label: "Todos los canales" },
  { value: "WHATSAPP", label: "WhatsApp" },
  { value: "WEB", label: "Web" },
  { value: "EMAIL", label: "Email" },
];

export default function ProspectosPage() {
  useConversationWebSocket();
  const [qrOpened, { open: openQR, close: closeQR }] = useDisclosure(false);
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const [selectedLeadName, setSelectedLeadName] = useState<string | null>(null);
  const [canalFilter, setCanalFilter] = useState<string>("");
  const isMobile = useMediaQuery("(max-width: 48em)");

  const handleSelectThread = useCallback((leadId: string, leadName?: string | null) => {
    setSelectedLeadId(leadId);
    setSelectedLeadName(leadName ?? null);
  }, []);

  const handleBack = useCallback(() => {
    setSelectedLeadId(null);
    setSelectedLeadName(null);
  }, []);

  // On mobile: show list OR chat, not both
  const showList = !isMobile || !selectedLeadId;
  const showChat = !isMobile || !!selectedLeadId;

  return (
    <>
      <QRModal opened={qrOpened} onClose={closeQR} />

      <Stack gap="md" className="prospectos-fullheight" style={{ overflow: "hidden" }}>
        {/* Header — hidden on mobile when chat is open */}
        {showList && (
          <Box style={{ flexShrink: 0 }}>
            <PageHeader
              title="Prospectos"
              actions={
                <>
                  <AIAutoResponseToggle />
                  <WhatsAppStatus onConnectClick={openQR} />
                </>
              }
            />
          </Box>
        )}

        {showList && <DeliveryGroupBanner />}

        {/* Main content: conversation list + chat */}
        <div
          style={{
            flex: 1,
            display: "flex",
            gap: "var(--mantine-spacing-md)",
            minHeight: 0,
            overflow: "hidden",
          }}
        >
          {/* Left panel: thread list */}
          {showList && (
            <Paper
              withBorder
              radius="md"
              p="sm"
              style={{
                width: isMobile ? "100%" : "clamp(260px, 33.33%, 380px)",
                flexShrink: 0,
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
              }}
            >
              <Group justify="space-between" style={{ flexShrink: 0 }} wrap="wrap" gap="xs">
                <Text size="sm" fw={600}>
                  Conversaciones
                </Text>
                <Select
                  size="xs"
                  data={CANAL_OPTIONS}
                  value={canalFilter}
                  onChange={(v) => setCanalFilter(v ?? "")}
                  w={140}
                  clearable={false}
                />
              </Group>
              <Divider my="sm" style={{ flexShrink: 0 }} />
              <Box style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
                <ConversationList
                  selectedLeadId={selectedLeadId}
                  onSelectThread={handleSelectThread}
                  canalFilter={canalFilter || undefined}
                />
              </Box>
            </Paper>
          )}

          {/* Right panel: chat view */}
          {showChat && (
            <Paper
              withBorder
              radius="md"
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
                minHeight: 0,
                width: isMobile ? "100%" : undefined,
              }}
            >
              {selectedLeadId ? (
                <>
                  <Group
                    p="sm"
                    gap="sm"
                    justify="space-between"
                    style={{
                      borderBottom: "1px solid var(--mantine-color-default-border)",
                      flexShrink: 0,
                    }}
                  >
                    <Group gap="sm">
                      {isMobile && (
                        <ActionIcon
                          onClick={handleBack}
                          variant="subtle"
                          size="sm"
                          aria-label="Volver a conversaciones"
                        >
                          <IconArrowLeft size={18} />
                        </ActionIcon>
                      )}
                      <IconBrandWhatsapp size={18} color="#25D366" />
                      <Text size="sm" fw={600} truncate>
                        {selectedLeadName || `Lead ${selectedLeadId.slice(0, 8)}...`}
                      </Text>
                    </Group>
                    <OutboundComposer
                      leadId={selectedLeadId}
                      leadName={selectedLeadName || `Lead ${selectedLeadId.slice(0, 8)}...`}
                    />
                  </Group>
                  <Box style={{ flex: 1, minHeight: 0, position: "relative" }}>
                    <ConversationChat
                      leadId={selectedLeadId}
                      leadName={selectedLeadName || `Lead ${selectedLeadId.slice(0, 8)}...`}
                    />
                  </Box>
                </>
              ) : (
                <Box
                  style={{
                    flex: 1,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <EmptyState
                    icon={<IconMessages size={48} color="var(--mantine-color-gray-3)" />}
                    title="Selecciona una conversacion para ver el historial"
                  />
                </Box>
              )}
            </Paper>
          )}
        </div>
      </Stack>
    </>
  );
}
