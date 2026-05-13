import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface PageSkeletonProps {
  className?: string;
  showHeader?: boolean;
  showSidebar?: boolean;
  showFooter?: boolean;
}

export function PageSkeleton({ 
  className,
  showHeader = true,
  showSidebar = false,
  showFooter = false 
}: PageSkeletonProps) {
  return (
    <div className={cn('min-h-screen bg-background', className)}>
      {showHeader && (
        <div className="border-b p-4">
          <div className="flex items-center justify-between">
            <Skeleton className="h-8 w-32" />
            <div className="flex space-x-2">
              <Skeleton className="h-8 w-20" />
              <Skeleton className="h-8 w-8 rounded-full" />
            </div>
          </div>
        </div>
      )}
      
      <div className="flex">
        {showSidebar && (
          <div className="w-64 border-r p-4 space-y-4">
            <Skeleton className="h-6 w-24" />
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          </div>
        )}
        
        <div className="flex-1 p-6 space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-96" />
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-4">
                <Skeleton className="h-48 w-full rounded-lg" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {showFooter && (
        <div className="border-t p-6">
          <div className="flex justify-between items-center">
            <Skeleton className="h-6 w-32" />
            <div className="flex space-x-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-16" />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}