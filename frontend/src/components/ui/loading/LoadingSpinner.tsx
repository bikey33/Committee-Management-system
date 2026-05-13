import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'primary' | 'secondary' | 'muted';
  className?: string;
  text?: string;
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6', 
  lg: 'w-8 h-8',
  xl: 'w-12 h-12'
};

const variantClasses = {
  primary: 'text-primary',
  secondary: 'text-secondary', 
  muted: 'text-muted-foreground'
};

export function LoadingSpinner({ 
  size = 'md', 
  variant = 'primary',
  className,
  text 
}: LoadingSpinnerProps) {
  return (
    <div className={cn('flex items-center justify-center gap-2', className)}>
      <Loader2 
        className={cn(
          'animate-spin',
          sizeClasses[size],
          variantClasses[variant]
        )} 
      />
      {text && (
        <span className={cn(
          'text-sm',
          variantClasses[variant]
        )}>
          {text}
        </span>
      )}
    </div>
  );
}

export function LoadingDots({ className }: { className?: string }) {
  return (
    <div className={cn('flex space-x-1', className)}>
      <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
      <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
      <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
    </div>
  );
}

export function LoadingPulse({ className }: { className?: string }) {
  return (
    <div className={cn('flex space-x-2', className)}>
      <div className="w-3 h-3 bg-primary rounded-full animate-pulse"></div>
      <div className="w-3 h-3 bg-primary rounded-full animate-pulse [animation-delay:0.2s]"></div>
      <div className="w-3 h-3 bg-primary rounded-full animate-pulse [animation-delay:0.4s]"></div>
    </div>
  );
}