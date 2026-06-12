import { Navigate, Outlet, useLocation } from "react-router-dom";
import { authService } from "@/api/auth";
import { usePermissions } from "@/contexts/PermissionContext";
import { ShieldX } from "lucide-react";

interface ProtectedRouteProps {
  requiredPermission?: string;
}

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center">
      <ShieldX size={48} className="text-muted-foreground" />
      <h2 className="text-xl font-semibold text-foreground">Access Denied</h2>
      <p className="text-muted-foreground max-w-sm">
        You don't have permission to view this page. Contact your administrator to request access.
      </p>
    </div>
  );
}

export function ProtectedRoute({ requiredPermission }: ProtectedRouteProps) {
  const location = useLocation();
  const { hasPermission, isLoading } = usePermissions();

  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  if (authService.mustChangePassword() && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  if (requiredPermission) {
    if (isLoading) return null;
    if (!hasPermission(requiredPermission)) {
      return <AccessDenied />;
    }
  }

  return <Outlet />;
}
