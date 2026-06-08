import { Navigate, Outlet, useLocation } from "react-router-dom";
import { authService } from "@/api/auth";

export function ProtectedRoute() {
  const location = useLocation();

  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  // Hard block: a user who must change their password cannot reach any other
  // page until they do so.
  if (authService.mustChangePassword() && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  return <Outlet />;
}
