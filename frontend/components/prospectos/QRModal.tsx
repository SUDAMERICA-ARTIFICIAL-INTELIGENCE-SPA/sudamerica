"use client";

import { useConfigureInstance, useGenerateQR, useWhatsAppStatus } from "@/hooks/useWhatsAppStatus";
import {
  Box,
  Button,
  Group,
  Image,
  Loader,
  Modal,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
} from "@mantine/core";
import { IconCheck, IconPhone, IconQrcode } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";

interface QRModalProps {
  opened: boolean;
  onClose: () => void;
}

type Step = "phone" | "qr" | "connected";

export function QRModal({ opened, onClose }: QRModalProps) {
  const generateQR = useGenerateQR();
  const configureInstance = useConfigureInstance();
  const configuredRef = useRef(false);
  const configureRef = useRef(configureInstance);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [step, setStep] = useState<Step>("phone");

  // Keep mutation ref current without triggering re-renders
  configureRef.current = configureInstance;

  const qrCode = generateQR.data?.qr_code ?? "";
  const shouldPollStatus = opened && step === "qr" && Boolean(qrCode);
  const { data: statusData } = useWhatsAppStatus({
    enabled: opened,
    refetchInterval: shouldPollStatus ? 3000 : false,
  });
  const isConnected = statusData?.status === "open";

  useEffect(() => {
    if (isConnected) {
      setStep("connected");
      if (!configuredRef.current) {
        configuredRef.current = true;
        configureRef.current.mutate({
          reject_call: true,
          always_online: true,
          read_messages: true,
        });
      }
    } else {
      configuredRef.current = false;
      if (qrCode) {
        setStep("qr");
      }
    }
  }, [isConnected, qrCode]);

  const handleGenerate = () => {
    const trimmed = phoneNumber.trim();
    generateQR.mutate(trimmed || undefined);
  };

  const handleClose = () => {
    configuredRef.current = false;
    configureRef.current.reset();
    setStep("phone");
    setPhoneNumber("");
    onClose();
  };

  return (
    <Modal opened={opened} onClose={handleClose} title="Conectar WhatsApp" size="md" centered>
      <Stack gap="md" align="center">
        {step === "connected" ? (
          <>
            <ThemeIcon size={60} radius="xl" color="green" variant="light">
              <IconCheck size={32} />
            </ThemeIcon>
            <Text size="lg" fw={600} ta="center">
              WhatsApp conectado
            </Text>
            <Text size="sm" c="dimmed" ta="center">
              Tu agente IA ya puede recibir y responder mensajes de WhatsApp.
            </Text>
            <Button onClick={handleClose} variant="light">
              Cerrar
            </Button>
          </>
        ) : step === "qr" ? (
          <>
            <Text size="sm" fw={500}>
              Escanea este código con tu WhatsApp
            </Text>
            <Box
              style={{
                border: "2px solid var(--mantine-color-green-6)",
                borderRadius: 12,
                padding: 8,
              }}
            >
              <Image src={qrCode} alt="QR Code WhatsApp" w={256} h={256} fit="contain" />
            </Box>
            <Group justify="center" gap="xs">
              <Loader size="xs" color="green" />
              <Text size="xs" c="dimmed">
                Esperando escaneo...
              </Text>
            </Group>
            <Text size="xs" c="dimmed" ta="center">
              Abre WhatsApp en tu teléfono &rarr; Dispositivos vinculados &rarr; Vincular
              dispositivo &rarr; Escanea el código
            </Text>
          </>
        ) : (
          <>
            <ThemeIcon size={60} radius="xl" color="green" variant="light">
              <IconPhone size={32} />
            </ThemeIcon>
            <Text size="sm" c="dimmed" ta="center">
              Ingresa el número de WhatsApp que quieres conectar con tu agente IA. Luego escanea el
              código QR desde tu teléfono.
            </Text>
            <TextInput
              label="Número de WhatsApp"
              placeholder="+56 9 1234 5678"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.currentTarget.value)}
              leftSection={<IconPhone size={16} />}
              w="100%"
              maw={300}
            />
            <Button
              onClick={handleGenerate}
              loading={generateQR.isPending}
              color="green"
              leftSection={<IconQrcode size={16} />}
              disabled={!phoneNumber.trim()}
            >
              Generar QR
            </Button>
            <Text size="xs" c="dimmed" ta="center">
              El número debe incluir el código de país (ej: +56 para Chile)
            </Text>
          </>
        )}
      </Stack>
    </Modal>
  );
}
