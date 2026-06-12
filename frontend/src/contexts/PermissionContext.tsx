import React, { createContext, useContext } from "react";
import { useQuery } from "@tanstack/react-query";
import { authService } from "@/api/auth";

interface PermissionContextValue {
  permissions: string[];
  isLoading: boolean;
  hasPermission: (codename: string) => boolean;
  isSuperAdmin: boolean;
}

const PermissionContext = createContext<PermissionContextValue>({
  permissions: [],
  isLoading: false,
  hasPermission: () => false,
  isSuperAdmin: false,
});

export function PermissionProvider({ children }: { children: React.ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: ["userMe"],
    queryFn: authService.getMe,
    enabled: authService.isAuthenticated(),
    staleTime: 0,              // always refetch when the query is used
    refetchOnWindowFocus: true, // pick up permission changes when user switches tabs
    refetchOnMount: true,       // refetch every time the provider mounts
  });

  const permissions: string[] = data?.permissions ?? [];
  const roleName: string = data?.user_role_details?.name ?? "";
  const isSuperAdmin =
    data?.is_superuser === true ||
    roleName.toLowerCase().replace(" ", "") === "superadmin";

  const hasPermission = (codename: string): boolean => {
    if (isSuperAdmin) return true;
    return permissions.includes(codename);
  };

  return (
    <PermissionContext.Provider value={{ permissions, isLoading, hasPermission, isSuperAdmin }}>
      {children}
    </PermissionContext.Provider>
  );
}

export function usePermissions(): PermissionContextValue {
  return useContext(PermissionContext);
}
