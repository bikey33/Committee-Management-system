import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface FormSkeletonProps {
  fields?: number;
  showSubmitButton?: boolean;
  showTitle?: boolean;
  className?: string;
}

export function FormSkeleton({ 
  fields = 4, 
  showSubmitButton = true,
  showTitle = true,
  className 
}: FormSkeletonProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {showTitle && (
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
      )}
      
      <div className="space-y-4">
        {Array.from({ length: fields }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-10 w-full" />
          </div>
        ))}
      </div>
      
      {showSubmitButton && (
        <div className="flex gap-2 pt-4">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-20" />
        </div>
      )}
    </div>
  );
}

export function FormFieldSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-2', className)}>
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-10 w-full" />
    </div>
  );
}