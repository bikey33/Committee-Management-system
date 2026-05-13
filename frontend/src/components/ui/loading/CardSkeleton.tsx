import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface CardSkeletonProps {
  showHeader?: boolean;
  showImage?: boolean;
  showActions?: boolean;
  className?: string;
}

export function CardSkeleton({ 
  showHeader = true,
  showImage = false,
  showActions = false,
  className 
}: CardSkeletonProps) {
  return (
    <Card className={cn('w-full', className)}>
      {showHeader && (
        <CardHeader>
          <div className="space-y-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </CardHeader>
      )}
      
      <CardContent className="space-y-4">
        {showImage && (
          <Skeleton className="h-48 w-full rounded-lg" />
        )}
        
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
        
        {showActions && (
          <div className="flex gap-2 pt-4">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-16" />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function CardGridSkeleton({ 
  count = 6, 
  columns = 3,
  ...cardProps 
}: { 
  count?: number; 
  columns?: number; 
} & CardSkeletonProps) {
  return (
    <div 
      className="grid gap-6"
      style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} {...cardProps} />
      ))}
    </div>
  );
}