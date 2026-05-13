import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { authService } from "@/api/auth";

export function ProtectedRoute() {
  const isAuthenticated = authService.isAuthenticated();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
