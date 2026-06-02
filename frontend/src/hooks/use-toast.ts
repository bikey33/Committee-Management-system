import { useCallback } from 'react';
import { toast as sonnerToast } from 'sonner';

interface ToastProps {
  title?: string;
  description?: string;
  variant?: 'default' | 'destructive';
}

export const useToast = () => {
  const toast = useCallback((props: ToastProps) => {
    const { title, description, variant } = props;
    const message = title ? `${title}${description ? ': ' + description : ''}` : description;
    
    if (variant === 'destructive') {
      sonnerToast.error(message);
    } else {
      sonnerToast.success(message);
   } 
  }, []);

  return { toast };
};

export const toast = (props: ToastProps) => {
  const { title, description, variant } = props;
  const message = title ? `${title}${description ? ': ' + description : ''}` : description;
  
  if (variant === 'destructive') {
    sonnerToast.error(message);
  } else {
    sonnerToast.success(message);
  }
};
