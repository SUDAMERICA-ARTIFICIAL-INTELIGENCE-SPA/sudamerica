"use client";

import { motion, useSpring, useTransform } from "framer-motion";
import { useEffect } from "react";

export interface AnimatedNumberProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

export function formatNumber(v: number, decimals: number): string {
  return v.toLocaleString("es-CL", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Spring-animated number — shared by `KpiCard` and `StatCard`. Ticks from its
 * previous value to the new `value` on every render where it changes.
 */
export function AnimatedNumber({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
}: AnimatedNumberProps) {
  const spring = useSpring(0, { damping: 28, stiffness: 70 });
  const display = useTransform(spring, (v) => `${prefix}${formatNumber(v, decimals)}${suffix}`);

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  return <motion.span>{display}</motion.span>;
}
