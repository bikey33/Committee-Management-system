import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Committee } from "@/types/committee";

interface CommitteeManagementProps {
  initialCommittee: Committee;
  onClose?: () => void;
}

const CommitteeManagement = ({ initialCommittee, onClose }: CommitteeManagementProps) => {
  return (
    <div className="p-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Committee Management</CardTitle>
            {onClose && (
              <Button variant="outline" onClick={onClose}>Close</Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="text-sm text-muted-foreground">Selected committee</div>
            <div className="text-lg font-semibold">{initialCommittee?.name}</div>
            <div className="text-sm">Type: {initialCommittee?.committee_type}</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CommitteeManagement;



