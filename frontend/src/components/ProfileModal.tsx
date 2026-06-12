import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import {
  User,
  Mail,
  Phone,
  Building2,
  Briefcase,
  Shield,
  Clock,
  IdCard,
} from "lucide-react";

interface ProfileModalProps {
  open: boolean;
  onClose: () => void;
  user: any;
}

function Field({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
        <Icon size={15} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium text-foreground break-words">{value}</p>
      </div>
    </div>
  );
}

export function ProfileModal({ open, onClose, user }: ProfileModalProps) {
  if (!user) return null;

  const fullName =
    user.name ||
    (user.first_name || user.last_name
      ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
      : null) ||
    user.username ||
    user.employeeId;

  const initials = fullName
    ? fullName
        .split(" ")
        .slice(0, 2)
        .map((w: string) => w[0])
        .join("")
        .toUpperCase()
    : "U";

  const roleName = user.user_role_details?.name ?? user.user_role?.name ?? null;
  const officeName = user.office_details?.name ?? user.office?.name ?? null;
  const directorate = user.office_details?.directorate?.name ?? null;

  const lastLogin = user.last_login
    ? new Date(user.last_login).toLocaleString()
    : null;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>My Profile</DialogTitle>
        </DialogHeader>

        {/* Avatar + name */}
        <div className="flex items-center gap-4 rounded-lg bg-accent/40 p-4">
          <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xl font-bold">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-base font-semibold text-foreground truncate">{fullName}</p>
            {roleName && (
              <Badge className="mt-1 bg-primary/10 text-primary hover:bg-primary/10 text-xs font-medium">
                {roleName}
              </Badge>
            )}
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 pt-1">
          <Field icon={IdCard}    label="Employee ID"  value={user.employeeId || user.employee_id} />
          <Field icon={Mail}      label="Email"        value={user.email} />
          <Field icon={Phone}     label="Phone"        value={user.phoneNumber} />
          <Field icon={Briefcase} label="Designation"  value={user.designation} />
          <Field icon={Building2} label="Department"   value={user.department} />
          <Field icon={Building2} label="Office"       value={officeName} />
          {directorate && (
            <Field icon={Building2} label="Directorate" value={directorate} />
          )}
          {user.position_details?.name && (
            <Field icon={User} label="Position" value={user.position_details.name} />
          )}
          <Field
            icon={Shield}
            label="Status"
            value={
              <span className={user.isActive ? "text-green-600" : "text-destructive"}>
                {user.isActive ? "Active" : "Inactive"}
              </span>
            }
          />
          {lastLogin && (
            <Field icon={Clock} label="Last Login" value={lastLogin} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
