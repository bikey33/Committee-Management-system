import React, { useState } from "react";
import { Building2, Users, User, Contact, BarChart3, LayoutDashboard, LogOut, Shield, LucideIcon } from "lucide-react";
import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { authService } from "@/api/auth";
import { ThemeToggle } from "@/components/ThemeToggle";
import { PermissionGate } from "@/components/PermissionGate";
import { ProfileModal } from "@/components/ProfileModal";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  permission: string | null;
}

const navItems: NavItem[] = [
  { to: "/",           label: "Dashboard",  icon: LayoutDashboard, end: true,  permission: null },
  { to: "/offices",    label: "Offices",    icon: Building2,                   permission: "settings.offices" },
  { to: "/committees", label: "Committees", icon: Users,                        permission: "committee.view" },
  { to: "/employees",  label: "Employees",  icon: Contact,                      permission: "users.view" },
  { to: "/users",      label: "Users",      icon: User,                         permission: "users.view" },
  { to: "/reports",    label: "Reports",    icon: BarChart3,                    permission: "reports.view" },
  { to: "/roles",      label: "Roles",      icon: Shield,                       permission: "roles.manage" },
];

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex shrink-0 items-center gap-3 rounded-md px-3 py-2 transition-colors ${
    isActive
      ? "bg-primary text-primary-foreground font-medium"
      : "hover:bg-accent hover:text-accent-foreground font-medium text-sidebar-foreground"
  }`;

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { data: user } = useQuery({
    queryKey: ["userMe"],
    queryFn: authService.getMe,
  });

  const [profileOpen, setProfileOpen] = useState(false);

  const handleLogout = () => {
    authService.logout();
  };

  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground md:flex-row">
      {/* Sidebar */}
      <aside className="flex w-full flex-col border-b border-border bg-sidebar text-sidebar-foreground shadow-sm md:w-64 md:border-b-0 md:border-r">
        {/* Logo Area */}
        <div className="flex items-center gap-3 border-b border-border px-4 py-4 sm:px-6 sm:py-5">
          <div className="bg-primary text-primary-foreground p-2 rounded-lg">
            <LayoutDashboard size={20} />
          </div>
          <div className="flex flex-col">
            <span className="font-semibold leading-tight text-foreground">Committee</span>
            <span className="text-xs text-muted-foreground">Manager</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex gap-2 overflow-x-auto px-3 py-3 md:flex-1 md:flex-col md:space-y-2 md:overflow-visible md:px-3 md:py-4">
          {navItems.map((item) => {
            const link = (
              <NavLink key={item.to} to={item.to} end={item.end} className={navLinkClass}>
                <item.icon size={20} />
                <span>{item.label}</span>
              </NavLink>
            );
            return item.permission ? (
              <PermissionGate key={item.to} codename={item.permission}>
                {link}
              </PermissionGate>
            ) : link;
          })}
        </nav>

        {/* User Profile Area */}
        <div className="border-t border-border p-3 sm:p-4">
          <div className="flex items-center justify-between bg-accent/50 p-3 rounded-lg border border-border/50">
            <button
              onClick={() => setProfileOpen(true)}
              className="flex min-w-0 flex-1 items-center gap-3 overflow-hidden text-left hover:opacity-80 transition-opacity"
              title="View profile"
            >
              <div className="bg-primary/10 text-primary w-8 h-8 rounded-full flex items-center justify-center font-semibold flex-shrink-0">
                {user?.username?.[0]?.toUpperCase() || user?.employee_id?.[0]?.toUpperCase() || "U"}
              </div>
              <div className="flex flex-col overflow-hidden">
                <span className="text-sm font-medium text-foreground truncate">
                  {user?.name || (user?.first_name ? `${user.first_name} ${user.last_name}` : user?.username) || "User"}
                </span>
                <span className="text-xs text-muted-foreground truncate">
                  {user?.employeeId || user?.employee_id || user?.email || "Employee"}
                </span>
                {user?.user_role_details?.name && (
                  <span className="mt-0.5 inline-block max-w-fit rounded-sm bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary leading-tight truncate">
                    {user.user_role_details.name}
                  </span>
                )}
              </div>
            </button>
            <div className="flex items-center gap-1">
              <ThemeToggle />
              <button
                onClick={handleLogout}
                className="text-muted-foreground hover:text-destructive transition-colors p-1 cursor-pointer"
                title="Log out"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </div>

        <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} user={user} />
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col bg-slate-50 md:h-screen md:overflow-y-auto">
        <div className="mx-auto w-full max-w-7xl px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
