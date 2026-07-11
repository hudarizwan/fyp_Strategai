import { forwardRef } from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

interface ButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'md', ...props }, ref) => {
    return (
      <motion.button
        className={cn(
          'inline-flex items-center justify-center gap-2 font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/30 disabled:pointer-events-none disabled:opacity-50',
          {
            'rounded-full border border-white/15 bg-gradient-to-b from-white/12 to-white/6 text-white shadow-[0_10px_30px_rgba(2,6,23,0.28)] backdrop-blur-xl hover:border-white/25 hover:bg-white/15': variant === 'default',
            'rounded-full border border-white/15 bg-transparent text-white hover:bg-white/8 hover:border-white/25': variant === 'outline',
            'rounded-full border border-transparent bg-transparent text-white hover:bg-white/8': variant === 'ghost',
            'h-9 px-4 py-2 text-sm': size === 'sm',
            'h-10 px-5 py-2 text-sm': size === 'md',
            'h-11 px-6 py-2 text-base': size === 'lg',
          },
          className
        )}
        ref={ref}
        whileHover={{ y: -1 }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 500, damping: 28 }}
        {...props}
      />
    );
  }
);

Button.displayName = 'Button';

export default Button;


