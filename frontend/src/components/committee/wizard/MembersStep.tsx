
import { Button } from "@/components/ui/button";
import { Plus, Users, Pencil, Trash2, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import MemberFormItem from "../MemberFormItem";
import EmployeeSearch from "./EmployeeSearch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { CommitteeMember } from "@/types/committee";
import type { Employee } from "@/types/employee";
import { getRoleConfig, countMembersByRole, normalizeRole } from "@/config/committeeRoleConfig";

interface MembersStepProps {
  members: CommitteeMember[];
  onUpdateMember: (index: number, field: keyof CommitteeMember, value: string) => void;
  onRemoveMember: (index: number) => void;
  onAddMember: (member: CommitteeMember) => void;
}

const MembersStep = ({
  members,
  onAddMember,
  onUpdateMember,
  onRemoveMember,
}: MembersStepProps) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [tempMember, setTempMember] = useState<CommitteeMember | null>(null);

  const roleCounts = countMembersByRole(members);

  const handleEmployeeSelect = (employee: Employee) => {
    setIsAdding(true);
    setEditingIndex(null);
    setTempMember({
      employeeId: employee.employee_id || employee.employeeId || '',
      name: employee.name || '',
      email: employee.email || '',
      office: employee.office?.name || employee.department || '',
      phone: employee.phone || '',
      position: employee.designation || '',
      role: '',
      tasks: [],
    });
  };

  const handleManualAdd = () => {
    setIsAdding(true);
    setEditingIndex(null);
    setTempMember({
      employeeId: '',
      name: '',
      email: '',
      office: '',
      phone: '',
      position: '',
      role: '',
      tasks: [],
    });
  };

  const handleEdit = (index: number) => {
    setIsAdding(false);
    setEditingIndex(index);
    setTempMember({ ...members[index] });
  };

  const handleRemove = (index: number) => {
    onRemoveMember(index);
  };

  const handleUpdateTempMember = (index: number, field: keyof CommitteeMember, value: string) => {
    if (tempMember) {
      setTempMember({ ...tempMember, [field]: value });
    }
  };

  const handleDoneEditing = () => {
    if (!tempMember) {
      setEditingIndex(null);
      setIsAdding(false);
      return;
    }

    if (isAdding) {
      if (tempMember) {
        onAddMember(tempMember);
      }
    } else if (editingIndex !== null) {
      // Update existing member
      if (tempMember) {
        Object.entries(tempMember).forEach(([key, value]) => {
          if (key !== 'tasks' && typeof value === 'string') {
            onUpdateMember(editingIndex, key as keyof CommitteeMember, value);
          }
        });
      }
    }

    setTempMember(null);
    setEditingIndex(null);
    setIsAdding(false);
  };

  const handleCloseModal = () => {
    setTempMember(null);
    setEditingIndex(null);
    setIsAdding(false);
  };

  // Sort members so Co-ordinator (chairperson) is always at the top
  const sortedDisplayMembers = [...members]
    .map((member, originalIndex) => ({ ...member, originalIndex }))
    .sort((a, b) => {
      const roleA = normalizeRole(a.role);
      const roleB = normalizeRole(b.role);
      
      const order = ['chairperson', 'secretary', 'member', 'subject_expert', 'invitee', 'sub_coordinator'];
      const indexA = order.indexOf(roleA);
      const indexB = order.indexOf(roleB);
      
      const sortA = indexA === -1 ? 999 : indexA;
      const sortB = indexB === -1 ? 999 : indexB;
      
      return sortA - sortB;
    });

  // Get list of already selected employee IDs to exclude from search
  const excludeIds = members
    .map(m => m.employeeId)
    .filter(Boolean);

  return (
    <div className="space-y-6">
      {/* Role Summary */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {roleCounts.map(({ role, count, config }) => (
          <div key={role} className={`p-4 rounded-lg border ${config.cardBg} ${config.cardBorder}`}>
            <div className="flex flex-col items-center justify-center text-center space-y-2">
              <span className={`font-semibold text-sm ${config.cardTextColor}`}>{config.label}</span>
              <span className={`text-xl font-bold ${config.cardCountColor}`}>{count}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Employee Search & Manual Add */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg">
            <Users className="w-4 h-4 text-[hsl(209,100%,32%)]" />
          </div>
          <h4 className="text-sm font-bold text-slate-800 tracking-tight">
            Search and Add Employees
          </h4>
        </div>

        <div className="flex flex-row items-start gap-4">
          <div className="flex-1">
            <EmployeeSearch
              onSelectEmployee={handleEmployeeSelect}
              excludeIds={excludeIds}
            />
          </div>
          <div className="flex items-center h-10 gap-4">
            <span className="text-xs font-medium text-muted-foreground tracking-wider">Or</span>
            <Button
              type="button"
              onClick={handleManualAdd}
              className="bg-[hsl(209,100%,32%)] hover:bg-[hsl(209,100%,25%)] text-white text-xs font-bold transition-all flex items-center gap-2 px-6 h-full whitespace-nowrap border-none"
            >
              <Plus className="h-4 w-4" />
              Add Manually
            </Button>
          </div>
        </div>
      </div>

      {/* Members List (Table & Editing Modal) */}
      <div className="space-y-6">
        <Dialog open={tempMember !== null} onOpenChange={(open) => !open && handleCloseModal()}>
          <DialogContent className="max-w-4xl p-8 overflow-hidden border-none shadow-2xl bg-white">
            <DialogHeader className="mb-6">
              <DialogTitle className="flex items-center gap-2 text-xl font-bold text-primary tracking-tight">
                {isAdding ? <Plus className="w-6 h-6" /> : <Pencil className="w-6 h-6" />}
                <span>{isAdding ? 'Add New Member' : `Edit Member: ${tempMember?.name}`}</span>
              </DialogTitle>
            </DialogHeader>

            <div className="bg-white">
              {tempMember && (
                <MemberFormItem
                  member={tempMember}
                  index={0}
                  onUpdate={handleUpdateTempMember}
                  onRemove={() => handleCloseModal()}
                  onAddAnother={handleDoneEditing}
                  isLast={true}
                  isAdding={isAdding}
                  otherCoordinatorExists={members.some((m, idx) =>
                    idx !== editingIndex && (m.role?.toLowerCase() === 'coordinator' || m.role?.toLowerCase() === 'chairperson' || m.role?.toLowerCase() === 'co-ordinator')
                  )}
                />
              )}
            </div>
          </DialogContent>
        </Dialog>

        {members.length > 0 && (
          <div className="rounded-xl border border-t-4 border-t-[hsl(209,100%,32%)] bg-white overflow-hidden shadow-sm">
            <Table>
              <TableHeader className="bg-[hsl(209_100%_32%)]">
                <TableRow className="hover:bg-transparent border-b border-white/10">
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider">Employee ID</TableHead>
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider">Name</TableHead>
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider">Email</TableHead>
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider">Office</TableHead>
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider">Position</TableHead>
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider">Role</TableHead>
                  <TableHead className="text-[11px] font-bold text-white h-10 tracking-wider text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedDisplayMembers.map((member, index) => (
                  <TableRow
                    key={member.id || `member-${member.originalIndex}`}
                    className={member.originalIndex === editingIndex ? "bg-muted" : "hover:bg-muted/50"}
                  >
                    <TableCell className="font-medium">{member.employeeId || 'N/A'}</TableCell>
                    <TableCell>{member.name || 'N/A'}</TableCell>
                    <TableCell className="text-muted-foreground">{member.email || 'N/A'}</TableCell>
                    <TableCell>
                      {member.office ? (
                        <Badge variant="secondary" className="bg-slate-100 text-slate-700 hover:bg-slate-200 border-none font-normal">
                          {member.office}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground font-light">N/A</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {member.position ? (
                        <Badge variant="secondary" className="bg-blue-50 text-blue-700 hover:bg-blue-100 border-none font-normal">
                          {member.position}
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground font-light">N/A</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={getRoleConfig(member.role || 'member').badgeClasses}
                      >
                        {getRoleConfig(member.role || 'member').label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-primary hover:text-primary hover:bg-primary/10"
                          onClick={() => handleEdit(member.originalIndex)}
                          title="Edit member"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => handleRemove(member.originalIndex)}
                          title="Remove member"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {members.length === 0 && (
          <div className="text-center py-10 bg-slate-50/50 rounded-xl border-2 border-dashed border-slate-200">
            <Users className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <h4 className="font-medium text-slate-600 mb-1">No Members Added</h4>
            <p className="text-sm text-slate-400 max-w-xs mx-auto">
              Search for employees or add them manually to start forming your committee.
            </p>
          </div>
        )}
      </div>

      <div className="bg-muted/50 p-4 rounded-lg">
        <h4 className="font-medium text-sm mb-2">Member Guidelines</h4>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• Each committee must have exactly one Co-ordinator (Secretary is optional)</li>
          <li>• Employee IDs will auto-fill member information when available</li>
          <li>• Ensure all required fields are completed for each member</li>
          <li>• All members will be notified via email upon committee creation</li>
        </ul>
      </div>
    </div >
  );
};

export default MembersStep;
