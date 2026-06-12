import React from "react";
import { usePermissions } from "@/contexts/PermissionContext";

interface PermissionGateProps {
  codename: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function PermissionGate({ codename, children, fallback = null }: PermissionGateProps) {
  const { hasPermission, isLoading } = usePermissions();
  if (isLoading) return null;
  return hasPermission(codename) ? <>{children}</> : <>{fallback}</>;
}
