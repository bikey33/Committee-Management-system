
import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { CommitteeFormationLetter } from "@/types/letter";

interface LetterViewerProps {
  letter: CommitteeFormationLetter;
  onClose: () => void;
}

const LetterViewer = ({ letter, onClose }: LetterViewerProps) => {
  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="h-[92vh] w-[95vw] max-w-4xl sm:h-[80vh] sm:w-[95vw]">
        <DialogHeader>
          <DialogTitle>Letter Preview - {letter.referenceNumber}</DialogTitle>
        </DialogHeader>
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
              <div>
                <p className="font-semibold">Reference Number</p>
                <p>{letter.referenceNumber}</p>
              </div>
              <div>
                <p className="font-semibold">Issue Date</p>
                <p>{new Date(letter.issueDate).toLocaleDateString()}</p>
              </div>
              <div>
                <p className="font-semibold">Department</p>
                <p>{letter.department}</p>
              </div>
              <div>
                <p className="font-semibold">Status</p>
                <p className="capitalize">{letter.status}</p>
              </div>
            </div>
            
            <div>
              <p className="font-semibold">Purpose</p>
              <p>{letter.purpose}</p>
            </div>

            <div>
              <p className="font-semibold">Distributions</p>
              {letter.distributions.length > 0 ? (
                <ul className="list-disc pl-5">
                  {letter.distributions.map((dist, index) => (
                    <li key={index}>
                      Member ID: {dist.memberId} - Sent: {new Date(dist.sentDate).toLocaleDateString()}
                      {dist.acknowledgmentDate && 
                        ` - Acknowledged: ${new Date(dist.acknowledgmentDate).toLocaleDateString()}`
                      }
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500">No distributions yet</p>
              )}
            </div>

            <div className="border rounded-lg p-4">
              <p className="font-semibold mb-2">Document Preview</p>
              <iframe
                src={letter.fileUrl}
                className="w-full h-[400px] border rounded"
                title={`Preview of ${letter.fileName}`}
              />
            </div>
          </div>
        </ScrollArea>
        <div className="flex justify-end">
          <Button onClick={onClose} className="w-full sm:w-auto">Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default LetterViewer;
