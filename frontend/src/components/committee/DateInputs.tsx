
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Calendar } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface DateInputsProps {
  formDate: string;
  specificationDate: string;
  reviewDate: string;
  onFormDateChange: (date: string) => void;
  onSpecificationDateChange: (date: string) => void;
  onReviewDateChange: (date: string) => void;
  disabled?: boolean;
}

const DateInputs = ({
  formDate,
  specificationDate,
  reviewDate,
  onFormDateChange,
  onSpecificationDateChange,
  onReviewDateChange,
}: DateInputsProps) => {
  const { toast } = useToast();

  const validateDates = (formDate: string, specDate: string, reviewDate: string) => {
    const formDateTime = new Date(formDate).getTime();
    const specDateTime = new Date(specDate).getTime();
    const reviewDateTime = new Date(reviewDate).getTime();

    if (specDateTime <= formDateTime) {
      toast({
        title: "Invalid date",
        description: "Specification date must be after formation date",
        variant: "destructive",
      });
      return false;
    }

    if (reviewDateTime <= specDateTime) {
      toast({
        title: "Invalid date",
        description: "Review date must be after specification date",
        variant: "destructive",
      });
      return false;
    }

    return true;
  };

  const handleFormDateChange = (date: string) => {
    if (validateDates(date, specificationDate, reviewDate)) {
      onFormDateChange(date);
    }
  };

  const handleSpecDateChange = (date: string) => {
    if (validateDates(formDate, date, reviewDate)) {
      onSpecificationDateChange(date);
    }
  };

  const handleReviewDateChange = (date: string) => {
    if (validateDates(formDate, specificationDate, date)) {
      onReviewDateChange(date);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="formation-date">Formation Date</Label>
          <Input
            id="formation-date"
            type="date"
            value={formDate}
            onChange={(e) => handleFormDateChange(e.target.value)}
            min={new Date().toISOString().split("T")[0]}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="specification-date">Specification Submission Date</Label>
          <Input
            id="specification-date"
            type="date"
            value={specificationDate}
            onChange={(e) => handleSpecDateChange(e.target.value)}
            min={formDate}
            required
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="review-date">Review Date</Label>
        <div className="flex items-center gap-4">
          <Input
            id="review-date"
            type="date"
            value={reviewDate}
            onChange={(e) => handleReviewDateChange(e.target.value)}
            min={specificationDate}
          />
          <Button type="button" variant="outline" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Schedule
          </Button>
        </div>
      </div>
    </div>
  );
};

export default DateInputs;
