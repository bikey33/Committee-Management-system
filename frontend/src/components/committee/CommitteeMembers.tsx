// CommitteeMembers.tsx
import { Button } from "@/components/ui/button";
import { Plus, Users } from "lucide-react";
import MemberFormItem from "./MemberFormItem";
import type { CommitteeMember } from "@/types/committee";
import { normalizeRole } from "@/config/committeeRoleConfig";

interface CommitteeMembersProps {
  members: CommitteeMember[];
  onAddMember: () => void;
  onUpdateMember: (index: number, field: keyof CommitteeMember, value: string) => void;
  onRemoveMember: (index: number) => void;
  disabled?: boolean;
}

const CommitteeMembers = ({
  members,
  onAddMember,
  onUpdateMember,
  onRemoveMember,
  disabled = false,
}: CommitteeMembersProps) => {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-muted-foreground" />
          <h3 className="text-lg font-semibold">Committee Members</h3>
        </div>
        <Button
          type="button"
          onClick={onAddMember}
          variant="outline"
          className="flex w-full items-center justify-center gap-2 sm:w-auto"
          disabled={disabled}
        >
          <Plus className="h-4 w-4" />
          Add Member
        </Button>
      </div>

      <div className="space-y-4">
        {[...members].sort((a, b) => {
          const roleA = normalizeRole(a.role);
          const roleB = normalizeRole(b.role);
          const order = ['chairperson', 'secretary', 'member', 'subject_expert', 'invitee', 'sub_coordinator'];
          const indexA = order.indexOf(roleA);
          const indexB = order.indexOf(roleB);
          const sortA = indexA === -1 ? 999 : indexA;
          const sortB = indexB === -1 ? 999 : indexB;
          return sortA - sortB;
        }).map((member, index) => (
          <MemberFormItem
            key={member.id || `member-${index}`}
            member={member}
            index={index}
            onUpdate={onUpdateMember}
            onRemove={onRemoveMember}
          />
        ))}
      </div>

      {members.length === 0 && (
        <div className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-muted-foreground">
          No members added yet. Click "Add Member" to begin.
        </div>
      )}
    </div>
  );
};

export default CommitteeMembers;


